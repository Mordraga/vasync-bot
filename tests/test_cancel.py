from datetime import datetime, timezone

from bot.cogs.cancel import format_collab_option_label
from bot.schemas import Collab, CollabStatus


def _collab(discord_ids: list[int]) -> Collab:
    return Collab(
        id=1,
        discord_ids=discord_ids,
        start_at_utc=datetime(2026, 9, 20, 18, 0, tzinfo=timezone.utc),
        reminder_sent=False,
        status=CollabStatus.CONFIRMED,
        thread_id=None,
    )


def test_format_collab_option_label_excludes_caller_from_count():
    label = format_collab_option_label(_collab([1, 2, 3]), caller_discord_id=1)
    assert "2 other(s)" in label


def test_format_collab_option_label_includes_date():
    label = format_collab_option_label(_collab([1, 2]), caller_discord_id=1)
    assert "Sep 20" in label
