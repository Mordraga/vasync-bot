from datetime import date, datetime

import httpx

from bot.config import Settings
from bot.identity import CallerIdentity
from bot.schemas import Collab, CollabMatch


class VasyncApiClient:
    """Thin async wrapper around vasync-database. One atomic method per
    endpoint - no business logic lives here, only request/response shaping."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._client = httpx.AsyncClient(base_url=settings.vasync_api_base_url, timeout=10.0)

    async def aclose(self) -> None:
        await self._client.aclose()

    def _service_headers(self) -> dict[str, str]:
        return {"X-Service-Token": self._settings.service_token}

    async def get_match(
        self, discord_ids: list[int], start_date: date, end_date: date, caller: CallerIdentity
    ) -> CollabMatch:
        response = await self._client.get(
            "/collab/match",
            params={
                "discord_ids": ",".join(str(discord_id) for discord_id in discord_ids),
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
            },
            headers=caller.as_headers(self._settings.service_token),
        )
        response.raise_for_status()
        return CollabMatch.model_validate(response.json())

    async def confirm_collab(self, discord_ids: list[int], start_at_utc: datetime) -> Collab:
        response = await self._client.post(
            "/collab/confirm",
            json={"discord_ids": discord_ids, "start_at_utc": start_at_utc.isoformat()},
            headers=self._service_headers(),
        )
        response.raise_for_status()
        return Collab.model_validate(response.json())

    async def list_upcoming(self) -> list[Collab]:
        response = await self._client.get("/collab/upcoming", headers=self._service_headers())
        response.raise_for_status()
        return [Collab.model_validate(item) for item in response.json()]

    async def mark_reminder_sent(self, collab_id: int) -> None:
        response = await self._client.post(
            f"/collab/{collab_id}/reminder-sent", headers=self._service_headers()
        )
        response.raise_for_status()

    async def upsert_user(
        self, discord_id: int, display_name: str, timezone: str, role: str
    ) -> None:
        response = await self._client.put(
            f"/users/{discord_id}",
            json={"discord_id": discord_id, "display_name": display_name, "timezone": timezone, "role": role},
            headers=self._service_headers(),
        )
        response.raise_for_status()
