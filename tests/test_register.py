from datetime import date, time

import pytest

from bot.cogs.register import parse_override_date, parse_override_time


def test_parse_override_date_accepts_iso_format():
    assert parse_override_date("2026-09-20") == date(2026, 9, 20)


def test_parse_override_date_rejects_bad_format():
    with pytest.raises(ValueError):
        parse_override_date("09/20/2026")


def test_parse_override_time_accepts_24h_format():
    assert parse_override_time("18:30") == time(18, 30)


def test_parse_override_time_rejects_bad_format():
    with pytest.raises(ValueError):
        parse_override_time("6:30 PM")
