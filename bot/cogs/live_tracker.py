"""Background Twitch live-status poller for registered entities, plus the
/live command that reads the cached result vasync-database stores.

Polling (not an on-demand check per /live call) so /live stays instant and
so the poll interval doubles as one shared rate-limit budget against
Twitch's API regardless of how often people run the command."""

import asyncio
import logging

import discord
from discord import app_commands
from discord.ext import commands

from bot.schemas import LiveEntity
from bot.twitch_client import TwitchClient

logger = logging.getLogger(__name__)


def format_live_list(entities: list[LiveEntity]) -> str:
    if not entities:
        return "No one's live right now."
    lines = [f"🔴 **{entity.display_name}** — twitch.tv/{entity.twitch_username}" for entity in entities]
    return "\n".join(lines)


class LiveTracker(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self._task: asyncio.Task | None = None

        settings = bot.settings
        if settings.twitch_client_id and settings.twitch_client_secret:
            self._twitch: TwitchClient | None = TwitchClient(
                settings.twitch_client_id, settings.twitch_client_secret
            )
        else:
            self._twitch = None

    async def cog_load(self) -> None:
        if self._twitch is None:
            logger.warning(
                "TWITCH_CLIENT_ID/TWITCH_CLIENT_SECRET not set - live entity tracking disabled"
            )
            return
        self._task = asyncio.create_task(self._poll_loop())

    async def cog_unload(self) -> None:
        if self._task is not None:
            self._task.cancel()
        if self._twitch is not None:
            await self._twitch.aclose()

    async def _poll_loop(self) -> None:
        while True:
            try:
                await self._poll_once()
            except Exception:
                logger.exception("live-status poll failed")

            settings = await self.bot.api.get_settings()
            await asyncio.sleep(settings.live_poll_interval_minutes * 60)

    async def _poll_once(self) -> None:
        assert self._twitch is not None
        linked = await self.bot.api.list_twitch_linked()
        if not linked:
            return

        live_logins = await self._twitch.get_live_logins([user.twitch_username for user in linked])

        for user in linked:
            await self.bot.api.update_live_status(
                user.discord_id, user.twitch_username.lower() in live_logins
            )

    @app_commands.command(name="live", description="See which entities are currently live on Twitch")
    async def live(self, interaction: discord.Interaction) -> None:
        entities = await self.bot.api.list_live_entities()
        await interaction.response.send_message(format_live_list(entities))


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(LiveTracker(bot))
