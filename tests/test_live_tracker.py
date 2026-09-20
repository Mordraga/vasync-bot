from bot.cogs.live_tracker import format_live_list
from bot.schemas import LiveEntity


def test_format_live_list_empty():
    assert format_live_list([]) == "No signals detected. All entities accounted for."


def test_format_live_list_includes_name_and_channel():
    entities = [LiveEntity(discord_id=1, display_name="Grem", twitch_username="gremthereaper")]
    message = format_live_list(entities)
    assert "Grem" in message
    assert "twitch.tv/gremthereaper" in message


def test_format_live_list_one_line_per_entity():
    entities = [
        LiveEntity(discord_id=1, display_name="A", twitch_username="a_stream"),
        LiveEntity(discord_id=2, display_name="B", twitch_username="b_stream"),
    ]
    assert len(format_live_list(entities).splitlines()) == 2
