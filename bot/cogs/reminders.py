"""Confirmed-collab reminders (spec section 4). The bot owns scheduling;
vasync-database only stores whether a reminder has fired yet, so a bot
restart can rehydrate pending reminders via ``/collab/upcoming``."""

import asyncio
import logging
from datetime import datetime, timedelta, timezone

import discord
from discord.ext import commands

from bot.formatting import format_reminder_message
from bot.schemas import Collab

REMINDER_LEAD = timedelta(minutes=15)
logger = logging.getLogger(__name__)


def compute_reminder_time(start_at_utc: datetime, lead: timedelta = REMINDER_LEAD) -> datetime:
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
        reminder_at = compute_reminder_time(collab.start_at_utc)
        delay = (reminder_at - datetime.now(timezone.utc)).total_seconds()
        if delay > 0:
            await asyncio.sleep(delay)

        start_unix = int(collab.start_at_utc.timestamp())
        for discord_id in collab.discord_ids:
            try:
                await notify_participant(self.bot, discord_id, start_unix)
            except discord.DiscordException:
                logger.exception("failed to DM %s for collab %s", discord_id, collab.id)

        await self.bot.api.mark_reminder_sent(collab.id)
        self._tasks.pop(collab.id, None)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(ReminderScheduler(bot))
