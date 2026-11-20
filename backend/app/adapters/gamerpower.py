"""GamerPower (https://www.gamerpower.com/api-read): a third-party giveaway aggregator.

Verified against real responses on 2026-11-20 for platforms: steam, epic-games-store, gog,
ubisoft (the last two returned "no active giveaways"). Attribution to GamerPower is required.
"""

import logging
import re
import time
from collections.abc import Callable
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from typing import Any

import httpx

from app.adapters.http import FetchError, Throttle, get_json
from app.adapters.models import AdapterFetch, NormalizedPromotion, SupportStatus
from app.models.enums import Platform, PromotionStatus, PromotionType

logger = logging.getLogger(__name__)

API_URL = "https://www.gamerpower.com/api/giveaways"
SOURCE = "gamerpower"

PLATFORM_PARAMS: dict[str, Platform] = {
    "steam": Platform.STEAM,
    "epic-games-store": Platform.EPIC,
    "gog": Platform.GOG,
    "ubisoft": Platform.UBISOFT,
    "origin": Platform.EA,  # NOT verified yet; not in the defaults
}
# Epic is excluded on purpose: it gets its own first-party adapter. EA ("origin") is excluded
# until that platform name is confirmed against a real response.
DEFAULT_PLATFORMS = ("steam", "gog", "ubisoft")

_TITLE_SUFFIX = re.compile(r"\s*\([^()]*\)\s*(?:Key\s+)?Giveaway\s*$", re.IGNORECASE)
_FREE_WEEKEND = re.compile(r"free\s+weekend", re.IGNORECASE)
_WORTH = re.compile(r"^\$\s*([\d,]+(?:\.\d{1,2})?)$")
_STATUS = {"active": PromotionStatus.ACTIVE, "expired": PromotionStatus.EXPIRED}


class NormalizationError(ValueError):
    """One raw item could not be turned into a NormalizedPromotion."""


def clean_title(raw_title: str) -> str:
    """'Dwarven Realms (Steam) Key Giveaway' -> 'Dwarven Realms'."""
    cleaned = _TITLE_SUFFIX.sub("", raw_title).strip()
    return cleaned or raw_title.strip()


def parse_worth(worth: object) -> int | None:
    """'$19.99' -> 1999 (USD cents). 'N/A' or anything unrecognised -> None."""
    if not isinstance(worth, str):
        return None
    match = _WORTH.match(worth.strip())
    if match is None:
        return None
    try:
        return int((Decimal(match.group(1).replace(",", "")) * 100).to_integral_value())
    except InvalidOperation:
        return None


def parse_end_date(value: object) -> datetime | None:
    """'2026-11-26 23:59:00' -> datetime in UTC; 'N/A' -> None.

    ASSUMPTION: GamerPower does not state a timezone, so UTC is assumed. Its end times look
    like end-of-day values (23:59:00), so treat them as approximate.
    """
    if not isinstance(value, str) or value.strip().upper() in ("", "N/A"):
        return None
    try:
        return datetime.strptime(value.strip(), "%Y-%m-%d %H:%M:%S").replace(tzinfo=UTC)
    except ValueError as exc:
        raise NormalizationError(f"unparseable end_date {value!r}") from exc


def _promotion_type(title: str, description: str) -> PromotionType:
    # Heuristic: GamerPower is a giveaway site, so "Giveaway" in the title is our only
    # evidence of free-to-keep. Free weekends are caught by their wording. Anything else is
    # UNKNOWN rather than a guess.
    if _FREE_WEEKEND.search(f"{title} {description}"):
        return PromotionType.FREE_WEEKEND
    if "giveaway" in title.lower():
        return PromotionType.FREE_TO_KEEP
    return PromotionType.UNKNOWN


def normalize_item(raw: Any, platform: Platform) -> NormalizedPromotion:
    if not isinstance(raw, dict):
        raise NormalizationError("item is not an object")
    for key in ("id", "title", "status"):
        if key not in raw:
            raise NormalizationError(f"missing field {key!r}")
    status = _STATUS.get(str(raw["status"]).strip().lower())
    if status is None:
        raise NormalizationError(f"unknown status {raw['status']!r}")

    raw_title = str(raw["title"])
    description = str(raw.get("description") or "")
    original = parse_worth(raw.get("worth"))
    return NormalizedPromotion(
        platform=platform,
        # A GamerPower id identifies the GIVEAWAY, not the game. Matching the same game across
        # sources is a later concern, so each giveaway is its own game row for now.
        platform_game_id=f"gamerpower-{raw['id']}",
        title=clean_title(raw_title),
        promotion_type=_promotion_type(raw_title, description),
        status=status,
        is_free=True,
        source=SOURCE,
        # Links go through GamerPower's redirect page, not straight to the store.
        store_url=raw.get("open_giveaway_url") or raw.get("gamerpower_url"),
        image_url=raw.get("image"),
        source_url=raw.get("gamerpower_url"),
        # published_date is when GamerPower listed it, not when the promotion started.
        start_date=None,
        end_date=parse_end_date(raw.get("end_date")),
        original_price_minor=original,
        current_price_minor=0,
        currency="USD" if original is not None else None,  # "worth" is a USD market value
        region=None,
        discount_percent=100 if original is not None else None,
    )


class GamerPowerAdapter:
    source = SOURCE
    support_status = SupportStatus.PARTIAL
    allowed_hosts = frozenset({"www.gamerpower.com"})

    def __init__(
        self,
        client: httpx.Client,
        platforms: tuple[str, ...] = DEFAULT_PLATFORMS,
        throttle: Throttle | None = None,
        max_attempts: int = 3,
        backoff_base: float = 1.0,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        unknown = [p for p in platforms if p not in PLATFORM_PARAMS]
        if unknown:
            raise ValueError(f"unknown GamerPower platform(s): {unknown}")
        self._client = client
        self._platforms = platforms
        self._throttle = throttle or Throttle(1.0)
        self._max_attempts = max_attempts
        self._backoff_base = backoff_base
        self._sleep = sleep

    def fetch_free_games(self) -> AdapterFetch:
        result = AdapterFetch()
        for param in self._platforms:
            result.requests_total += 1
            self._throttle.wait()
            try:
                payload = get_json(
                    self._client,
                    API_URL,
                    params={"platform": param, "type": "game"},
                    max_attempts=self._max_attempts,
                    backoff_base=self._backoff_base,
                    sleep=self._sleep,
                )
                raw_items = self._extract_items(payload)
            except FetchError as exc:
                logger.warning("GamerPower platform %s failed: %s", param, exc)
                result.requests_failed += 1
                result.errors.append(f"{param}: {exc}")
                continue
            for raw in raw_items:
                try:
                    result.items.append(normalize_item(raw, PLATFORM_PARAMS[param]))
                except NormalizationError as exc:
                    logger.warning("GamerPower %s: dropped item (%s)", param, exc)
                    result.dropped += 1
                    result.errors.append(f"{param}: {exc}")
        return result

    @staticmethod
    def _extract_items(payload: Any) -> list[Any]:
        if isinstance(payload, list):
            return payload
        # Verified 2026-11-20: with no giveaways the API returns an OBJECT with status 0,
        # not an empty list. That is a normal "nothing right now", not an error.
        if isinstance(payload, dict) and payload.get("status") == 0:
            return []
        raise FetchError("unexpected response shape")
