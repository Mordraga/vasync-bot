"""The /collab slash command (spec section 4): asks vasync-database for
shared windows, prints them with Discord timestamps, and lets the caller
confirm one - which schedules a reminder."""

from datetime import date, datetime, timedelta, timezone

import discord
from discord import app_commands
from discord.ext import commands

from bot.formatting import format_match_summary, format_plain_window_label
from bot.identity import identity_from_member
from bot.schemas import CollabMatch, MatchWindow

DEFAULT_MATCH_WINDOW_DAYS = 14
MAX_SELECT_OPTIONS = 25


def build_date_range(days_ahead: int = DEFAULT_MATCH_WINDOW_DAYS) -> tuple[date, date]:
    today = datetime.now(timezone.utc).date()
    return today, today + timedelta(days=days_ahead)


def collect_participant_ids(members: list[discord.Member]) -> list[int]:
    return list(dict.fromkeys(member.id for member in members))


class ConfirmCollabView(discord.ui.View):
    def __init__(self, discord_ids: list[int], windows: list[MatchWindow]) -> None:
        super().__init__(timeout=300)
        self._discord_ids = discord_ids
        self.add_item(self._build_select(windows[:MAX_SELECT_OPTIONS]))

    def _build_select(self, windows: list[MatchWindow]) -> discord.ui.Select:
        options = [
            discord.SelectOption(label=format_plain_window_label(window), value=str(window.start_unix))
            for window in windows
        ]
        select = discord.ui.Select(placeholder="Confirm a window...", options=options)
        select.callback = self._on_select
        return select

    async def _on_select(self, interaction: discord.Interaction) -> None:
        start_unix = int(interaction.data["values"][0])
        start_at_utc = datetime.fromtimestamp(start_unix, tz=timezone.utc)

        collab = await interaction.client.api.confirm_collab(self._discord_ids, start_at_utc)
        interaction.client.get_cog("ReminderScheduler").schedule(collab)

        await interaction.response.edit_message(
            content=f"Confirmed! A reminder will go out before <t:{start_unix}:F>.", view=None
        )


class Collab(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="collab", description="Find shared collab availability")
    @app_commands.describe(
        user1="First person to compare", user2="Second person to compare",
        user3="Optional third person", user4="Optional fourth person",
    )
    async def collab(
        self,
        interaction: discord.Interaction,
        user1: discord.Member,
        user2: discord.Member,
        user3: discord.Member | None = None,
        user4: discord.Member | None = None,
    ) -> None:
        await interaction.response.defer()

        members = [member for member in (user1, user2, user3, user4) if member is not None]
        discord_ids = collect_participant_ids(members)

        settings = await self.bot.api.get_settings()
        start_date, end_date = build_date_range(settings.match_window_days)

        caller = identity_from_member(interaction.user)
        match: CollabMatch = await self.bot.api.get_match(discord_ids, start_date, end_date, caller)

        content = format_match_summary(match)
        view = ConfirmCollabView(discord_ids, match.windows) if match.windows else None
        await interaction.followup.send(content=content, view=view)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Collab(bot))
