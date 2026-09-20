# vasync-bot

The Discord "tentacle" for the VAsync Scheduling Daemon (spec section 4).
It is deliberately thin: it does no scheduling math and no timezone
rendering itself - it asks `vasync-database` for shared windows and lets
Discord's own `<t:...>` markup render them per viewer.

## Layout

- `bot/identity.py` - builds the `X-Discord-*` identity headers from a
  `discord.Member`.
- `bot/api_client.py` - one atomic async method per vasync-database
  endpoint the bot needs.
- `bot/formatting.py` - pure string helpers around Discord timestamp
  markup.
- `bot/cogs/collab.py` - `/collab` slash command + the confirm-a-window UI.
- `bot/cogs/reminders.py` - schedules and (on restart) rehydrates
  confirmed-collab reminders.
- `bot/twitch_client.py` - minimal Twitch Helix client (app access token +
  Get Streams) used only by `bot/cogs/live_tracker.py`.
- `bot/cogs/live_tracker.py` - polls Twitch for every entity with a
  Twitch link registered (set from the dashboard) and pushes live/offline
  status to vasync-database; `/live` reads that cached status back. Also
  posts a one-line announcement to `live_announce_channel_id` (staff
  setting, dashboard admin panel) the moment someone transitions from
  offline to live - not on every poll, and never for someone already
  live. Stays disabled (logs a warning) if
  `TWITCH_CLIENT_ID`/`TWITCH_CLIENT_SECRET` aren't set; announcements stay
  off (no error) if no channel is configured.

The reminder lead time, `/collab` match window, and live-poll interval
aren't hardcoded here - cogs call `VasyncApiClient.get_settings()` each
time they need them, so changes staff make in the dashboard's admin panel
take effect without a bot restart (the poll loop itself still finishes its
current sleep before picking up a changed interval).

## Running locally

```bash
cp .env.example .env   # DISCORD_TOKEN, guild ID, SERVICE_TOKEN, VASYNC_API_BASE_URL
pip install -e ".[dev]"
python -m bot.main
```

Requires a running `vasync-database` instance at `VASYNC_API_BASE_URL`
with a matching `SERVICE_TOKEN`.

## Tests

```bash
pytest
```

Covers the pure helpers: timestamp formatting, identity headers,
reminder-time math, and the `/collab` argument-collection logic. No
Discord connection or running API is required.
