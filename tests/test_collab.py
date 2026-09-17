from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from bot.cogs.collab import build_date_range, build_thread_name, collect_participant_ids


@dataclass
class FakeMember:
    id: int
    display_name: str = ""


def test_collect_participant_ids_dedupes_preserving_order():
    members = [FakeMember(1), FakeMember(2), FakeMember(1)]
    assert collect_participant_ids(members) == [1, 2]


def test_build_date_range_spans_requested_days():
    start, end = build_date_range(days_ahead=7)
    assert end - start == timedelta(days=7)
    assert start == datetime.now(timezone.utc).date()


def test_build_thread_name_lists_display_names():
    members = [FakeMember(1, "Mordraga"), FakeMember(2, "Grem")]
    assert build_thread_name(members) == "Collab: Mordraga, Grem"


def test_build_thread_name_truncated_to_discord_limit():
    members = [FakeMember(i, "x" * 30) for i in range(10)]
    assert len(build_thread_name(members)) <= 100
