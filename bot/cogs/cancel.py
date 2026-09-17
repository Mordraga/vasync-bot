"""The /cancel-collab slash command: lets any participant withdraw from a
confirmed collab. Symmetric with declining a proposal - withdrawing only
drops that one person, unless it's the last one left, in which case the
whole collab is cancelled (see vasync-database's is_collab_still_viable)."""

import logging

import discord
from discord import app_commands
from discord.ext import commands

from bot.formatting import discord_timestamp, format_mentions
from bot.schemas import Collab

MAX_SELECT_OPTIONS = 25
logger = logging.getLogger(__name__)


def format_collab_option_label(collab: Collab, caller_discord_id: int) -> str:
    others = [d for d in collab.discord_ids if d != caller_discord_id]
    start = collab.start_at_utc.strftime("%a %b %d - %I:%M %p UTC")
    return f"{start} with {len(others)} other(s)"


class CancelCollabView(discord.ui.View):
    def __init__(self, caller_discord_id: int, collabs: list[Collab]) -> None:
        super().__init__(timeout=300)
        self._caller_discord_id = caller_discord_id
        self._collabs_by_id = {collab.id: collab for collab in collabs}
        self.add_item(self._build_select(collabs[:MAX_SELECT_OPTIONS]))

    def _build_select(self, collabs: list[Collab]) -> discord.ui.Select:
        options = [
            discord.SelectOption(label=format_collab_option_label(collab, self._caller_discord_id), value=str(collab.id))
            for collab in collabs
        ]
        select = discord.ui.Select(placeholder="Cancel which collab?", options=options)
        select.callback = self._on_select
        return select

    async def _on_select(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer()

        collab_id = int(interaction.data["values"][0])
        collab = self._collabs_by_id[collab_id]

        result = await interaction.client.api.cancel_collab(collab_id, self._caller_discord_id)
        start = discord_timestamp(int(collab.start_at_utc.timestamp()), "F")

        if result.fully_cancelled:
            note = f"The collab at {start} was cancelled."
            if result.thread_id:
                try:
                    thread = await interaction.client.fetch_channel(result.thread_id)
                    await thread.delete()
                except (discord.NotFound, discord.Forbidden):
                    logger.warning("could not delete collab thread %s", result.thread_id)
        else:
            note = f"<@{self._caller_discord_id}> dropped out of the collab at {start}. It's still on with {format_mentions(result.remaining_discord_ids)}."
            if result.thread_id:
                try:
                    thread = await interaction.client.fetch_channel(result.thread_id)
                    await thread.remove_user(discord.Object(id=self._caller_discord_id))
                except (discord.NotFound, discord.Forbidden):
                    logger.warning("could not remove %s from thread %s", self._caller_discord_id, result.thread_id)

        for discord_id in result.remaining_discord_ids:
            try:
                user = await interaction.client.fetch_user(discord_id)
                await user.send(note)
            except discord.DiscordException:
                logger.exception("failed to notify %s that collab %s changed", discord_id, collab_id)

        await interaction.edit_original_response(content="Done.", view=None)


class Cancel(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="cancel-collab", description="Cancel or withdraw from an upcoming collab")
    async def cancel_collab(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer(ephemeral=True)

        collabs = await self.bot.api.list_upcoming_for_user(interaction.user.id)
        if not collabs:
            await interaction.followup.send("You have no upcoming confirmed collabs.")
            return

        view = CancelCollabView(interaction.user.id, collabs)
        await interaction.followup.send(content="Pick a collab to cancel:", view=view)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Cancel(bot))
