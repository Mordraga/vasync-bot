"""Minimal wrapper around Twitch's Helix API - just enough to ask "which of
these logins are live right now" for the live-entity poller."""

import time

import httpx

TOKEN_URL = "https://id.twitch.tv/oauth2/token"
HELIX_BASE = "https://api.twitch.tv/helix"
MAX_LOGINS_PER_REQUEST = 100
TOKEN_EXPIRY_MARGIN_SECONDS = 60


class TwitchClient:
    def __init__(self, client_id: str, client_secret: str) -> None:
        self._client_id = client_id
        self._client_secret = client_secret
        self._client = httpx.AsyncClient(timeout=10.0)
        self._access_token: str | None = None
        self._token_expires_at: float = 0.0

    async def aclose(self) -> None:
        await self._client.aclose()

    async def _get_access_token(self) -> str:
        if self._access_token and time.monotonic() < self._token_expires_at:
            return self._access_token

        response = await self._client.post(
            TOKEN_URL,
            data={
                "client_id": self._client_id,
                "client_secret": self._client_secret,
                "grant_type": "client_credentials",
            },
        )
        response.raise_for_status()
        payload = response.json()

        self._access_token = payload["access_token"]
        self._token_expires_at = time.monotonic() + payload["expires_in"] - TOKEN_EXPIRY_MARGIN_SECONDS
        return self._access_token

    async def get_live_logins(self, logins: list[str]) -> set[str]:
        """Returns the subset of `logins` (case-insensitive) that are
        currently live. Twitch caps user_login params at 100/request."""
        if not logins:
            return set()

        token = await self._get_access_token()
        headers = {"Client-Id": self._client_id, "Authorization": f"Bearer {token}"}

        live: set[str] = set()
        for start in range(0, len(logins), MAX_LOGINS_PER_REQUEST):
            batch = logins[start : start + MAX_LOGINS_PER_REQUEST]
            response = await self._client.get(
                f"{HELIX_BASE}/streams",
                params={"user_login": batch},
                headers=headers,
            )
            response.raise_for_status()
            live.update(stream["user_login"].lower() for stream in response.json()["data"])

        return live
