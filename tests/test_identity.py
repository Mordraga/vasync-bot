from bot.identity import CallerIdentity


def test_as_headers_includes_service_token_and_identity():
    identity = CallerIdentity(discord_id=42, guild_id=99, role_ids={1, 2})
    headers = identity.as_headers("secret")

    assert headers["X-Service-Token"] == "secret"
    assert headers["X-Discord-User-Id"] == "42"
    assert headers["X-Discord-Guild-Id"] == "99"
    assert set(headers["X-Discord-Role-Ids"].split(",")) == {"1", "2"}


def test_as_headers_with_no_roles_is_empty_string():
    identity = CallerIdentity(discord_id=42, guild_id=99, role_ids=set())
    assert identity.as_headers("secret")["X-Discord-Role-Ids"] == ""
