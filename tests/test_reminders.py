from datetime import datetime, timedelta, timezone

from bot.cogs.reminders import compute_reminder_time


def test_compute_reminder_time_subtracts_lead_time():
    start = datetime(2026, 6, 1, 20, 0, tzinfo=timezone.utc)
    assert compute_reminder_time(start, timedelta(minutes=15)) == start - timedelta(minutes=15)


def test_compute_reminder_time_uses_default_lead():
    start = datetime(2026, 6, 1, 20, 0, tzinfo=timezone.utc)
    assert compute_reminder_time(start) == start - timedelta(minutes=15)
