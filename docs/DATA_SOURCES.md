# Data sources and adapter status (Phase 3)

Last verified: **2026-11-20**, from real responses the project owner downloaded and shared.
Nothing below is marked SUPPORTED: that needs a first-party source tested against real responses.

## Summary

| Platform | Source | Status | Verified against real data? |
|---|---|---|---|
| Epic | Epic `freeGamesPromotions` (first-party, undocumented) | **Not implemented yet** | Response file (`epic.json`) received by the owner but not yet shared with me. |
| Steam | GamerPower | PARTIAL | Yes: 1 real giveaway parsed |
| GOG | GamerPower | PARTIAL | Endpoint answered, but no giveaway existed to parse |
| Ubisoft | GamerPower | PARTIAL | Endpoint answered, but no giveaway existed to parse |
| EA app | GamerPower (`origin`) | UNSUPPORTED | Platform name not confirmed |
| Rockstar | none found | UNSUPPORTED | n/a |

## GamerPower adapter

- **Data source:** `GET https://www.gamerpower.com/api/giveaways?platform=<p>&type=game`. No API
  key. A third party, not the stores. **Attribution to GamerPower is required** (their terms);
  add it to the UI/README before publishing.
- **Platforms queried by default:** `steam`, `gog`, `ubisoft`. Epic is skipped on purpose (it gets
  its own first-party adapter). `origin` (EA) is available but off until confirmed.
- **Supported promotion types:** free-to-keep only, derived from "Giveaway" in the title. Free
  weekends are detected by wording; anything else is `UNKNOWN`. This is a heuristic.
- **Fields available:** id, title, worth (USD market value), image, description, instructions,
  GamerPower URLs, published date, end date, status, platforms.
- **Fields missing:** the real store URL (links go through GamerPower's redirect page), the
  store's own game ID (so the same game cannot yet be matched across sources), a start date
  (`published_date` is when GamerPower listed it, not when the promotion began), and the
  timezone of `end_date`.
- **Verified behaviour (2026-11-20):**
  - Returns a JSON list when giveaways exist.
  - Returns an **object** `{"status":0,"status_message":"No active giveaways..."}` when there are
    none. The adapter treats this as a successful, empty scan.
  - `end_date` is `"N/A"` for some giveaways (the Steam one) and `"YYYY-MM-DD HH:MM:SS"` otherwise.
  - Unknown platform name `ea-origin` returns HTTP 404.
- **Limitations and risks:**
  - `end_date` timezone is **assumed UTC** and is undocumented. The sample end times are all
    `23:59:00`, which looks like end-of-day rather than the store's exact deadline. **Do not use
    GamerPower end times for precise countdowns without checking them against the store.** Phase 4
    should prefer the first-party Epic time when both are known.
  - Each GamerPower giveaway becomes its own `games` row (`gamerpower-<id>`). Cross-source
    de-duplication is Phase 4 work.
  - Some "giveaways" need extra steps (the Steam sample needs an Alienware account and 10 ARP
    points). The data does not say so in a structured field.
  - Rate limits are not documented in what I verified. The adapter waits 1s between requests,
    retries only timeouts/429/5xx with exponential backoff, and honours `Retry-After` (capped 60s).
- **Last successful scan:** recorded per run in `platform_scan_logs` (wired up in Phase 5).

## Reliability design (all adapters)

- Timeout on every request (`HTTP_TIMEOUT_SECONDS`), bounded retries, throttle between calls.
- Normalise, then validate (https only, allow-listed hosts, timezone-aware dates, sane prices).
- Invalid items are dropped and counted; they never reach the database.
- `run_scan` never raises: a crash becomes a FAILED result, and other adapters still run.
- A scan is SUCCESS, PARTIAL (some errors/drops), or FAILED (every request failed).

## Still to verify

1. Epic response format (needs `epic.json`).
2. Whether GamerPower lists GOG/Ubisoft/EA items, and what they look like.
3. GamerPower `end_date` timezone (compare against store deadlines once Epic data is in).
4. Steam price endpoint and its rate limits (Phase 4).
