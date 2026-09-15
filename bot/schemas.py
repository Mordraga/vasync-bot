"""Minimal mirrors of the vasync-database response shapes the bot actually
reads. Kept intentionally small (not a full copy of that service's
schemas) so this repo stays agnostic to fields it never touches."""

from datetime import date, datetime

from pydantic import BaseModel


class MatchWindow(BaseModel):
    date: date
    status: int  # Status IntEnum: 0=NO, 1=MAYBE, 2=YES
    start_unix: int
    end_unix: int


class CollabMatch(BaseModel):
    discord_ids: list[int]
    windows: list[MatchWindow]


class Collab(BaseModel):
    id: int
    discord_ids: list[int]
    start_at_utc: datetime
    reminder_sent: bool
