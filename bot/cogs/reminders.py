"""Confirmed-collab reminders (spec section 4). The bot owns scheduling;
vasync-database only stores whether a reminder has fired yet, so a bot
restart can rehydrate pending reminders via ``/collab/upcoming``."""

import asyncio
import logging
from datetime import datetime, timedelta, timezone

import discord
from discord.ext import commands

from bot.formatting import format_reminder_message
from bot.schemas import Collab, CollabStatus

DEFAULT_REMINDER_LEAD = timedelta(minutes=15)
logger = logging.getLogger(__name__)


def compute_reminder_time(start_at_utc: datetime, lead: timedelta = DEFAULT_REMINDER_LEAD) -> datetime:
    return start_at_utc - lead


async def notify_participant(bot: commands.Bot, discord_id: int, start_unix: int) -> None:
    user = await bot.fetch_user(discord_id)
    await user.send(format_reminder_message(start_unix))


class ReminderScheduler(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self._tasks: dict[int, asyncio.Task] = {}

    async def cog_load(self) -> None:
        for collab in await self.bot.api.list_upcoming():
            self.schedule(collab)

    def schedule(self, collab: Collab) -> None:
        if collab.id in self._tasks:
            return
        self._tasks[collab.id] = asyncio.create_task(self._run(collab))

    async def _run(self, collab: Collab) -> None:
        settings = await self.bot.api.get_settings()
        reminder_at = compute_reminder_time(collab.start_at_utc, timedelta(minutes=settings.reminder_lead_minutes))
        delay = (reminder_at - datetime.now(timezone.utc)).total_seconds()
        if delay > 0:
            await asyncio.sleep(delay)

        # Re-check live state: a participant may have withdrawn via
        # /cancel-collab (shrinking discord_ids) or cancelled the whole
        # thing since this task was scheduled.
        live = await self.bot.api.get_collab(collab.id)
        if live.status is not CollabStatus.CONFIRMED:
            self._tasks.pop(collab.id, None)
            return

        start_unix = int(live.start_at_utc.timestamp())
        for discord_id in live.discord_ids:
            try:
                await notify_participant(self.bot, discord_id, start_unix)
            except discord.DiscordException:
                logger.exception("failed to DM %s for collab %s", discord_id, live.id)

        await self.bot.api.mark_reminder_sent(live.id)

        if live.thread_id:
            delay_to_start = (live.start_at_utc - datetime.now(timezone.utc)).total_seconds()
            if delay_to_start > 0:
                await asyncio.sleep(delay_to_start)
            try:
                thread = await self.bot.fetch_channel(live.thread_id)
                await thread.delete()
            except (discord.NotFound, discord.Forbidden):
                logger.warning("could not delete collab thread %s", live.thread_id)

        self._tasks.pop(collab.id, None)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(ReminderScheduler(bot))
