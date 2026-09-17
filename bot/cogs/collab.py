"""The /collab slash command (spec section 4): asks vasync-database for
shared windows, prints them with Discord timestamps in a private thread
scoped to the participants, and drives mutual DM confirmation once a time
is proposed."""

import logging
from datetime import date, datetime, timedelta, timezone

import discord
import httpx
from discord import app_commands
from discord.ext import commands

from bot.formatting import (
    format_all_declined_message,
    format_confirmed_message,
    format_match_summary,
    format_plain_window_label,
    format_proposal_message,
)
from bot.identity import identity_from_member
from bot.schemas import CollabMatch, CollabStatus, MatchWindow

DEFAULT_MATCH_WINDOW_DAYS = 14
MAX_SELECT_OPTIONS = 25
logger = logging.getLogger(__name__)


def build_date_range(days_ahead: int = DEFAULT_MATCH_WINDOW_DAYS) -> tuple[date, date]:
    today = datetime.now(timezone.utc).date()
    return today, today + timedelta(days=days_ahead)


def collect_participant_ids(members: list[discord.Member]) -> list[int]:
    return list(dict.fromkeys(member.id for member in members))


def build_thread_name(members: list[discord.Member]) -> str:
    name = "Collab: " + ", ".join(member.display_name for member in members)
    return name[:100]


async def _delete_thread(bot: commands.Bot, thread_id: int) -> None:
    try:
        thread = await bot.fetch_channel(thread_id)
        await thread.delete()
    except (discord.NotFound, discord.Forbidden):
        logger.warning("could not delete collab thread %s", thread_id)


class ConfirmCollabView(discord.ui.View):
    def __init__(self, initiator_discord_id: int, discord_ids: list[int], windows: list[MatchWindow]) -> None:
        super().__init__(timeout=300)
        self._initiator_discord_id = initiator_discord_id
        self._other_discord_ids = [d for d in discord_ids if d != initiator_discord_id]
        self.add_item(self._build_select(windows[:MAX_SELECT_OPTIONS]))

    def _build_select(self, windows: list[MatchWindow]) -> discord.ui.Select:
        options = [
            discord.SelectOption(label=format_plain_window_label(window), value=str(window.start_unix))
            for window in windows
        ]
        select = discord.ui.Select(placeholder="Propose a window...", options=options)
        select.callback = self._on_select
        return select

    async def _on_select(self, interaction: discord.Interaction) -> None:
        start_unix = int(interaction.data["values"][0])
        start_at_utc = datetime.fromtimestamp(start_unix, tz=timezone.utc)
        thread_id = interaction.channel.id if isinstance(interaction.channel, discord.Thread) else None

        try:
            collab = await interaction.client.api.propose_collab(
                self._initiator_discord_id, self._other_discord_ids, start_at_utc, thread_id
            )
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 404:
                await interaction.response.edit_message(
                    content="You need to sign into the VAsync dashboard once before you can confirm a collab time.",
                    view=None,
                )
                return
            raise

        message = format_proposal_message(start_unix, self._initiator_discord_id)
        for discord_id in self._other_discord_ids:
            try:
                user = await interaction.client.fetch_user(discord_id)
                await user.send(message, view=CollabResponseView(collab.id))
            except discord.DiscordException:
                logger.exception("failed to DM %s a collab proposal for collab %s", discord_id, collab.id)

        await interaction.response.edit_message(
            content=f"Proposed <t:{start_unix}:F> — waiting on confirmation from the others.", view=None
        )


class CollabResponseView(discord.ui.View):
    def __init__(self, collab_id: int) -> None:
        super().__init__(timeout=None)
        self._collab_id = collab_id

    async def _respond(self, interaction: discord.Interaction, accept: bool) -> None:
        result = await interaction.client.api.respond_to_collab(self._collab_id, interaction.user.id, accept)

        if result.pending:
            await interaction.response.edit_message(
                content="Recorded — waiting on the rest of the group.", view=None
            )
            return

        collab = await interaction.client.api.get_collab(self._collab_id)
        start_unix = int(collab.start_at_utc.timestamp())

        if result.status is CollabStatus.CONFIRMED:
            interaction.client.get_cog("ReminderScheduler").schedule(collab)
            initiator_message = format_confirmed_message(
                start_unix, result.accepted_discord_ids, result.declined_discord_ids
            )
            if collab.thread_id:
                try:
                    thread = await interaction.client.fetch_channel(collab.thread_id)
                    await thread.send(initiator_message)
                except (discord.NotFound, discord.Forbidden):
                    logger.warning("could not post confirmation in thread %s", collab.thread_id)
        else:
            initiator_message = format_all_declined_message(start_unix)
            if collab.thread_id:
                await _delete_thread(interaction.client, collab.thread_id)

        for discord_id in result.accepted_discord_ids:
            if discord_id == interaction.user.id:
                continue
            try:
                user = await interaction.client.fetch_user(discord_id)
                await user.send(initiator_message)
            except discord.DiscordException:
                logger.exception("failed to notify %s of collab %s outcome", discord_id, self._collab_id)

        await interaction.response.edit_message(
            content=f"Recorded: you {'accepted' if accept else 'declined'}.", view=None
        )

    @discord.ui.button(label="Accept", style=discord.ButtonStyle.success)
    async def accept(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await self._respond(interaction, accept=True)

    @discord.ui.button(label="Decline", style=discord.ButtonStyle.danger)
    async def decline(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await self._respond(interaction, accept=False)


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

        if not match.windows or not isinstance(interaction.channel, discord.TextChannel):
            await interaction.followup.send(content=content)
            return

        all_members = members if interaction.user in members else [interaction.user, *members]
        thread = await interaction.channel.create_thread(
            name=build_thread_name(all_members),
            type=discord.ChannelType.private_thread,
            invitable=False,
        )
        for member in all_members:
            await thread.add_user(member)

        view = ConfirmCollabView(interaction.user.id, discord_ids, match.windows)
        await thread.send(content=content, view=view)
        await interaction.followup.send(content=f"Started {thread.mention} for this collab.")


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Collab(bot))
