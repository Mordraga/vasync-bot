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

from bot.schemas import LiveEntity, TwitchLinkedUser
from bot.twitch_client import TwitchClient

logger = logging.getLogger(__name__)


def format_live_list(entities: list[LiveEntity]) -> str:
    if not entities:
        return "No signals detected. All entities accounted for."
    lines = [
        f"🔴 **{entity.display_name}** — signal holding at twitch.tv/{entity.twitch_username}"
        for entity in entities
    ]
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

        previously_live_ids = {entity.discord_id for entity in await self.bot.api.list_live_entities()}
        live_logins = await self._twitch.get_live_logins([user.twitch_username for user in linked])

        newly_live = [
            user
            for user in linked
            if user.twitch_username.lower() in live_logins and user.discord_id not in previously_live_ids
        ]

        for user in linked:
            await self.bot.api.update_live_status(
                user.discord_id, user.twitch_username.lower() in live_logins
            )

        if newly_live:
            await self._announce(newly_live)

    async def _announce(self, newly_live: list[TwitchLinkedUser]) -> None:
        settings = await self.bot.api.get_settings()
        if settings.live_announce_channel_id is None:
            return

        try:
            channel = self.bot.get_channel(settings.live_announce_channel_id) or await self.bot.fetch_channel(
                settings.live_announce_channel_id
            )
        except discord.DiscordException:
            logger.exception("could not reach live-announce channel %s", settings.live_announce_channel_id)
            return

        for user in newly_live:
            try:
                await channel.send(
                    f"🔴 **Signal detected.** <@{user.discord_id}> has no-clipped back into reality — "
                    f"twitch.tv/{user.twitch_username}"
                )
            except discord.DiscordException:
                logger.exception("failed to post live announcement for %s", user.discord_id)

    @app_commands.command(name="live", description="See which entities are currently live on Twitch")
    async def live(self, interaction: discord.Interaction) -> None:
        entities = await self.bot.api.list_live_entities()
        await interaction.response.send_message(format_live_list(entities))


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(LiveTracker(bot))
