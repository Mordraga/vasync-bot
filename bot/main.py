import asyncio
import logging

import discord
from discord.ext import commands

from bot.api_client import VasyncApiClient
from bot.config import get_settings

EXTENSIONS = ("bot.cogs.collab", "bot.cogs.reminders")

logging.basicConfig(level=logging.INFO)


class VasyncBot(commands.Bot):
    def __init__(self) -> None:
        self.settings = get_settings()
        super().__init__(command_prefix=commands.when_mentioned, intents=discord.Intents.default())
        self.api = VasyncApiClient(self.settings)

    async def setup_hook(self) -> None:
        for extension in EXTENSIONS:
            await self.load_extension(extension)

        guild = discord.Object(id=self.settings.vasync_guild_id)
        self.tree.copy_global_to(guild=guild)
        await self.tree.sync(guild=guild)

    async def close(self) -> None:
        await self.api.aclose()
        await super().close()


def main() -> None:
    bot = VasyncBot()
    bot.run(bot.settings.discord_token)


if __name__ == "__main__":
    main()
