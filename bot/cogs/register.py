"""The /register-day slash command: a Discord-native shortcut for setting a
single date's availability override, mirroring the dashboard's per-date
override editor (PUT /users/{discord_id}/availability/overrides/{date})."""

from datetime import date, datetime, time

import discord
import httpx
from discord import app_commands
from discord.ext import commands

from bot.identity import identity_from_member

STATUS_CHOICES = [
    app_commands.Choice(name="Yes", value=2),
    app_commands.Choice(name="Maybe", value=1),
    app_commands.Choice(name="No", value=0),
]

NOT_REGISTERED_MESSAGE = (
    "You're not registered yet — sign into the VAsync dashboard once first so your "
    "timezone is set, then this command will work."
)


def parse_override_date(raw: str) -> date:
    return datetime.strptime(raw, "%Y-%m-%d").date()


def parse_override_time(raw: str) -> time:
    return datetime.strptime(raw, "%H:%M").time()


class Register(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="register-day", description="Set your availability for a single date")
    @app_commands.describe(
        date="Date in YYYY-MM-DD",
        status="Your availability that day",
        start="Window start, HH:MM (24h)",
        end="Window end, HH:MM (24h)",
    )
    @app_commands.choices(status=STATUS_CHOICES)
    async def register_day(
        self,
        interaction: discord.Interaction,
        date: str,
        status: app_commands.Choice[int],
        start: str,
        end: str,
    ) -> None:
        await interaction.response.defer(ephemeral=True)

        try:
            override_date = parse_override_date(date)
            window_start = parse_override_time(start)
            window_end = parse_override_time(end)
        except ValueError:
            await interaction.followup.send("Couldn't parse that — use YYYY-MM-DD for the date and HH:MM for times.")
            return

        caller = identity_from_member(interaction.user)
        try:
            await self.bot.api.upsert_override(
                caller, interaction.user.id, override_date, status.value, window_start, window_end
            )
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 404:
                await interaction.followup.send(NOT_REGISTERED_MESSAGE)
                return
            raise

        await interaction.followup.send(
            f"Set {override_date.isoformat()} to **{status.name}** ({start}–{end})."
        )


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Register(bot))
