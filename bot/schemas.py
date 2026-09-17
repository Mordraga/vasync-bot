"""Minimal mirrors of the vasync-database response shapes the bot actually
reads. Kept intentionally small (not a full copy of that service's
schemas) so this repo stays agnostic to fields it never touches."""

from datetime import date, datetime
from enum import StrEnum

from pydantic import BaseModel


class MatchWindow(BaseModel):
    date: date
    status: int  # Status IntEnum: 0=NO, 1=MAYBE, 2=YES
    start_unix: int
    end_unix: int


class CollabMatch(BaseModel):
    discord_ids: list[int]
    windows: list[MatchWindow]


class CollabStatus(StrEnum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"


class Collab(BaseModel):
    id: int
    discord_ids: list[int]
    start_at_utc: datetime
    reminder_sent: bool
    status: CollabStatus
    thread_id: int | None


class CollabRespondResult(BaseModel):
    pending: bool
    status: CollabStatus | None
    accepted_discord_ids: list[int]
    declined_discord_ids: list[int]
    thread_id: int | None


class CollabCancelResult(BaseModel):
    fully_cancelled: bool
    remaining_discord_ids: list[int]
    thread_id: int | None


class BotSettings(BaseModel):
    reminder_lead_minutes: int
    match_window_days: int
