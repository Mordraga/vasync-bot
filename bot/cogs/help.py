"""The /vasync-help slash command: lists every registered slash command and
its description, so users don't have to guess what's available."""

import discord
from discord import app_commands
from discord.ext import commands


def format_command_list(commands_: list[app_commands.Command]) -> str:
    lines = [f"**/{command.name}** — {command.description}" for command in commands_]
    return "\n".join(lines)


class Help(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="vasync-help", description="List available VAsync commands")
    async def vasync_help(self, interaction: discord.Interaction) -> None:
        commands_ = sorted(self.bot.tree.get_commands(), key=lambda c: c.name)
        await interaction.response.send_message(format_command_list(commands_), ephemeral=True)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Help(bot))
