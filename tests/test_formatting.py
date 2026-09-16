from bot.formatting import (
    discord_timestamp,
    format_match_summary,
    format_plain_window_label,
    format_reminder_message,
    format_window_line,
)
from bot.schemas import CollabMatch, MatchWindow


def test_discord_timestamp_uses_discords_markup():
    assert discord_timestamp(1234567890, "R") == "<t:1234567890:R>"


def test_discord_timestamp_defaults_to_full_style():
    assert discord_timestamp(1234567890) == "<t:1234567890:F>"


def test_format_window_line_includes_start_and_end():
    window = MatchWindow(date="2026-06-01", status=2, start_unix=100, end_unix=200)
    line = format_window_line(window)
    assert "<t:100:t>" in line
    assert "<t:200:t>" in line


def test_format_plain_window_label_has_no_discord_markup():
    window = MatchWindow(date="2026-09-20", status=2, start_unix=1789585200, end_unix=1789596000)
    label = format_plain_window_label(window)
    assert "<t:" not in label
    assert "07:00 PM" in label
    assert "10:00 PM" in label
    assert "UTC" in label


def test_format_match_summary_empty_windows():
    match = CollabMatch(discord_ids=[1, 2], windows=[])
    assert format_match_summary(match) == "No shared availability found for that range."


def test_format_match_summary_splits_best_and_possible():
    match = CollabMatch(
        discord_ids=[1, 2],
        windows=[
            MatchWindow(date="2026-06-01", status=2, start_unix=100, end_unix=200),
            MatchWindow(date="2026-06-02", status=1, start_unix=300, end_unix=400),
        ],
    )
    summary = format_match_summary(match)
    assert "**Best matches**" in summary
    assert "**Possible matches**" in summary


def test_format_reminder_message_includes_relative_and_absolute():
    message = format_reminder_message(1234567890)
    assert "<t:1234567890:R>" in message
    assert "<t:1234567890:F>" in message
