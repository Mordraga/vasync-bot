from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    discord_token: str
    vasync_guild_id: int

    service_token: str
    vasync_api_base_url: str = "http://localhost:8000"

    # Optional: live entity tracking (bot/cogs/live_tracker.py) just stays
    # disabled, logging a warning, until both are set - no reason a missing
    # Twitch app should take the whole bot down.
    twitch_client_id: str | None = None
    twitch_client_secret: str | None = None


@lru_cache
def get_settings() -> Settings:
    return Settings()
