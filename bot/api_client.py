from datetime import date, datetime, time

import httpx

from bot.config import Settings
from bot.identity import CallerIdentity
from bot.schemas import (
    BotSettings,
    Collab,
    CollabCancelResult,
    CollabMatch,
    CollabRespondResult,
    LiveEntity,
    TwitchLinkedUser,
)


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

    async def propose_collab(
        self, initiator_discord_id: int, other_discord_ids: list[int], start_at_utc: datetime, thread_id: int | None
    ) -> Collab:
        response = await self._client.post(
            "/collab/propose",
            json={
                "initiator_discord_id": initiator_discord_id,
                "other_discord_ids": other_discord_ids,
                "start_at_utc": start_at_utc.isoformat(),
                "thread_id": thread_id,
            },
            headers=self._service_headers(),
        )
        response.raise_for_status()
        return Collab.model_validate(response.json())

    async def respond_to_collab(self, collab_id: int, discord_id: int, accept: bool) -> CollabRespondResult:
        response = await self._client.post(
            f"/collab/{collab_id}/respond",
            json={"discord_id": discord_id, "accept": accept},
            headers=self._service_headers(),
        )
        response.raise_for_status()
        return CollabRespondResult.model_validate(response.json())

    async def cancel_collab(self, collab_id: int, discord_id: int) -> CollabCancelResult:
        response = await self._client.post(
            f"/collab/{collab_id}/cancel",
            json={"discord_id": discord_id},
            headers=self._service_headers(),
        )
        response.raise_for_status()
        return CollabCancelResult.model_validate(response.json())

    async def get_collab(self, collab_id: int) -> Collab:
        response = await self._client.get(f"/collab/{collab_id}", headers=self._service_headers())
        response.raise_for_status()
        return Collab.model_validate(response.json())

    async def list_upcoming(self) -> list[Collab]:
        response = await self._client.get("/collab/upcoming", headers=self._service_headers())
        response.raise_for_status()
        return [Collab.model_validate(item) for item in response.json()]

    async def list_upcoming_for_user(self, discord_id: int) -> list[Collab]:
        response = await self._client.get(f"/collab/upcoming/{discord_id}", headers=self._service_headers())
        response.raise_for_status()
        return [Collab.model_validate(item) for item in response.json()]

    async def mark_reminder_sent(self, collab_id: int) -> None:
        response = await self._client.post(
            f"/collab/{collab_id}/reminder-sent", headers=self._service_headers()
        )
        response.raise_for_status()

    async def upsert_user(
        self, discord_id: int, display_name: str, timezone: str, role_ids: list[int]
    ) -> None:
        response = await self._client.put(
            f"/users/{discord_id}",
            json={
                "discord_id": discord_id,
                "display_name": display_name,
                "timezone": timezone,
                "role_ids": role_ids,
            },
            headers=self._service_headers(),
        )
        response.raise_for_status()

    async def upsert_override(
        self, caller: CallerIdentity, discord_id: int, override_date: date, status: int, window_start: time, window_end: time
    ) -> None:
        response = await self._client.put(
            f"/users/{discord_id}/availability/overrides/{override_date.isoformat()}",
            json={
                "override_date": override_date.isoformat(),
                "status": status,
                "window_start": window_start.isoformat(),
                "window_end": window_end.isoformat(),
            },
            headers=caller.as_headers(self._settings.service_token),
        )
        response.raise_for_status()

    async def get_settings(self) -> BotSettings:
        response = await self._client.get("/settings", headers=self._service_headers())
        response.raise_for_status()
        return BotSettings.model_validate(response.json())

    async def list_twitch_linked(self) -> list[TwitchLinkedUser]:
        response = await self._client.get("/users/twitch-linked", headers=self._service_headers())
        response.raise_for_status()
        return [TwitchLinkedUser.model_validate(item) for item in response.json()]

    async def update_live_status(self, discord_id: int, is_live: bool) -> None:
        response = await self._client.put(
            f"/users/{discord_id}/live-status",
            json={"is_live": is_live},
            headers=self._service_headers(),
        )
        response.raise_for_status()

    async def list_live_entities(self) -> list[LiveEntity]:
        response = await self._client.get("/users/live", headers=self._service_headers())
        response.raise_for_status()
        return [LiveEntity.model_validate(item) for item in response.json()]
