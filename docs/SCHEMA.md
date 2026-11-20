# Database schema (Phase 2)

SQLite for development; written to stay PostgreSQL-compatible (portable types, no SQLite-only
features, enums stored as VARCHAR). Migrations: `alembic upgrade head`.

## Conventions

- **Times** are timezone-aware UTC (`UTCDateTime` type refuses naive datetimes).
- **Money** is integer minor units plus a currency code and region. Prices in different
  currencies or regions are never compared.
- **Foreign keys** are enforced (SQLite `PRAGMA foreign_keys=ON` on every connection) and use
  `ON DELETE CASCADE`.
- Repositories `flush` but never `commit`; callers use `session_scope` for transactions.

## Tables

| Table | Purpose | Unique constraints | Extra indexes |
|---|---|---|---|
| `users` | Owner (single-user MVP, one row) | - | - |
| `user_devices` | Push tokens (used in Phase 10) | `push_token` | `user_id` |
| `games` | One row per game per store | `(platform, platform_game_id)` | `title` |
| `promotions` | A free/discount window for a game | `(game_id, dedupe_key)` | `(status, end_date)` |
| `price_history` | Observed prices over time | `(game_id, currency, region, source, observed_at)` | `(game_id, observed_at)` |
| `wishlist_items` | Games the user tracks | `(user_id, game_id)` | `game_id` |
| `price_alerts` | Alerts already fired (dedupe) | `(wishlist_item_id, dedupe_key)` | - |
| `giveaway_reminders` | Scheduled giveaway reminders | `(user_id, promotion_id, offset_minutes)` | `promotion_id`, `(status, scheduled_for)` |
| `notification_preferences` | Per type/channel on/off | `(user_id, notification_type, channel)` | - |
| `notification_logs` | Delivery history | - | `(dedupe_key, channel)`, `(user_id, created_at)` |
| `platform_scan_logs` | One row per adapter run | - | `(source, started_at)` |

Check constraints: `promotions.discount_percent BETWEEN 0 AND 100`, `price_history.price_minor >= 0`.

### Why these indexes

- `promotions (status, end_date)`: the "active promotions" query and the expiry job.
- `giveaway_reminders (status, scheduled_for)`: the every-minute "what is due" query.
- `price_history (game_id, observed_at)`: history charts and "recorded lowest" per game.
- `notification_logs (dedupe_key, channel)`: "was this already sent?" before every notification.
- Unique constraints double as indexes for their leading columns, so no separate index exists
  where one would be redundant (e.g. `wishlist_items.user_id`).

## Changes from the Phase 0 plan (and why)

1. **`promotions.dedupe_key` (new, replaces `start_date` in the unique key).** A unique constraint
   including a nullable `start_date` does not stop duplicates when the start is unknown (NULLs are
   distinct in SQL). The key `"<source>|<type>|<start or 'unknown'>"` is always present, so the
   database enforces uniqueness. The end date is deliberately not in the key, so an extended
   giveaway updates the same row. Known limit: if a source first reports no start date and later
   reports one, that is treated as a new promotion (revisit in Phase 4 if it occurs).
2. **Prices on `promotions`** (original/current price, currency, region, discount %), as the
   Phase 2 brief requires. The plan only had them on `price_history`.
3. **No `platforms` or `wishlists` tables.** Platform is an enum column, and since the MVP has one
   wishlist per user, `wishlist_items` hangs directly off `users`. Both remain easy to split out.
4. **`platform_scan_logs.source`** instead of `platform`, because aggregators such as GamerPower
   are sources but not stores.
5. **`price_alerts.dedupe_key` is unique per wishlist item**, not globally.
6. **Not enforced by the database:** "one reminder per offset" is enforced, but the SENT status
   transition is enforced by the repository's atomic `UPDATE ... WHERE status = 'PENDING'`.

## Known limitations

- Duplicate checks are check-then-insert backed by the unique constraints. That is safe for the
  single-process MVP; two processes racing would get an `IntegrityError` rather than a duplicate.
- SQLite cannot alter some constraints in place; Alembic runs in batch mode for SQLite.
