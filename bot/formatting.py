"""Atomic string-building helpers around Discord's <t:...> timestamp
markup. The bot never converts these to a human timezone itself - Discord
renders them per-viewer, and the timezone math already happened in
vasync-database (spec section 3)."""

from datetime import datetime, timezone

from bot.schemas import CollabMatch, MatchWindow

STATUS_YES = 2
STATUS_MAYBE = 1

_STATUS_EMOJI = {STATUS_YES: "✅", STATUS_MAYBE: "\U0001f7e1"}


def discord_timestamp(unix_seconds: int, style: str = "F") -> str:
    return f"<t:{unix_seconds}:{style}>"


def format_window_line(window: MatchWindow) -> str:
    emoji = _STATUS_EMOJI.get(window.status, "")
    start = discord_timestamp(window.start_unix, "t")
    end = discord_timestamp(window.end_unix, "t")
    return f"{emoji} {discord_timestamp(window.start_unix, 'D')} — {start} to {end}"


def format_plain_window_label(window: MatchWindow) -> str:
    """Select-menu option labels are plain text - Discord only expands
    <t:...> markup in message content, not in component labels (this is
    why the confirm dropdown was showing literal "<t:...:D>" text). Since
    a dropdown has no single viewer to localize for, this renders in UTC
    with an explicit label rather than guessing a timezone."""
    start = datetime.fromtimestamp(window.start_unix, tz=timezone.utc)
    end = datetime.fromtimestamp(window.end_unix, tz=timezone.utc)
    emoji = _STATUS_EMOJI.get(window.status, "")
    return f"{emoji} {start.strftime('%a %b %d')} - {start.strftime('%I:%M %p')} to {end.strftime('%I:%M %p')} UTC"


def format_match_summary(match: CollabMatch) -> str:
    if not match.windows:
        return "No shared availability found for that range."

    best = [w for w in match.windows if w.status == STATUS_YES]
    possible = [w for w in match.windows if w.status == STATUS_MAYBE]

    sections: list[str] = []
    if best:
        sections.append("**Best matches**\n" + "\n".join(format_window_line(w) for w in best))
    if possible:
        sections.append("**Possible matches**\n" + "\n".join(format_window_line(w) for w in possible))
    return "\n\n".join(sections)


def format_reminder_message(start_unix: int) -> str:
    relative = discord_timestamp(start_unix, "R")
    absolute = discord_timestamp(start_unix, "F")
    return f"Hey! You have a collab {relative}!\nStart time: {absolute}"
