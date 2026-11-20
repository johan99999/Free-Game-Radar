import json
from datetime import UTC, datetime
from pathlib import Path

import httpx
import pytest

from app.adapters.gamerpower import (
    GamerPowerAdapter,
    NormalizationError,
    clean_title,
    normalize_item,
    parse_end_date,
    parse_worth,
)
from app.adapters.http import Throttle
from app.adapters.runner import run_scan
from app.models.enums import Platform, PromotionStatus, PromotionType, ScanStatus

FIXTURES = Path(__file__).parent / "fixtures"


def load(name: str):
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


STEAM = "gamerpower_steam_2026-11-20.json"
EPIC = "gamerpower_epic_2026-11-20.json"
NONE = "gamerpower_none_2026-11-20.json"


def make_adapter(handler, platforms=("steam", "gog", "ubisoft")) -> GamerPowerAdapter:
    return GamerPowerAdapter(
        httpx.Client(transport=httpx.MockTransport(handler)),
        platforms=platforms,
        throttle=Throttle(0),
        sleep=lambda _: None,
    )


# ---- parsing helpers ----


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("Dwarven Realms (Steam) Key Giveaway", "Dwarven Realms"),
        ("Mark of the Deep (Epic Games) Giveaway", "Mark of the Deep"),
        (
            "Contractor: The Clean Up Part 2 (Epic Games) Giveaway",
            "Contractor: The Clean Up Part 2",
        ),
        ("Plain Title", "Plain Title"),
        ("(Steam) Giveaway", "(Steam) Giveaway"),  # never clean a title down to nothing
    ],
)
def test_clean_title(raw: str, expected: str) -> None:
    assert clean_title(raw) == expected


def test_parse_worth() -> None:
    assert parse_worth("$19.99") == 1999
    assert parse_worth("$4.99") == 499
    assert parse_worth("$1,299.00") == 129900
    assert parse_worth("N/A") is None
    assert parse_worth(None) is None


def test_parse_end_date() -> None:
    assert parse_end_date("2026-11-26 23:59:00") == datetime(2026, 11, 26, 23, 59, tzinfo=UTC)
    assert parse_end_date("N/A") is None
    assert parse_end_date(None) is None
    with pytest.raises(NormalizationError):
        parse_end_date("next Tuesday")


# ---- normalizing real responses ----


def test_normalizes_real_steam_item() -> None:
    promo = normalize_item(load(STEAM)[0], Platform.STEAM)
    assert promo.platform == Platform.STEAM
    assert promo.platform_game_id == "gamerpower-3716"
    assert promo.title == "Dwarven Realms"
    assert promo.promotion_type == PromotionType.FREE_TO_KEEP
    assert promo.status == PromotionStatus.ACTIVE
    assert promo.is_free is True
    assert promo.end_date is None  # the API said "N/A"
    assert promo.start_date is None
    assert (promo.original_price_minor, promo.current_price_minor) == (999, 0)
    assert (promo.currency, promo.discount_percent) == ("USD", 100)
    assert promo.source == "gamerpower"
    assert promo.store_url == "https://www.gamerpower.com/open/dwarven-realms-steam-key-giveaway"


def test_normalizes_real_item_with_end_date() -> None:
    promo = normalize_item(load(EPIC)[0], Platform.EPIC)
    assert promo.title == "Mark of the Deep"
    assert promo.end_date == datetime(2026, 11, 26, 23, 59, tzinfo=UTC)
    assert promo.original_price_minor == 1999


@pytest.mark.parametrize(
    "bad",
    [
        "not an object",
        {"title": "x", "status": "Active"},  # no id
        {"id": 1, "status": "Active"},  # no title
        {"id": 1, "title": "x", "status": "Weird"},
        {"id": 1, "title": "x", "status": "Active", "end_date": "garbage"},
    ],
)
def test_malformed_items_raise(bad: object) -> None:
    with pytest.raises(NormalizationError):
        normalize_item(bad, Platform.STEAM)


def test_free_weekend_wording_is_not_classified_as_free_to_keep() -> None:
    raw = {"id": 9, "title": "Cool Game Free Weekend Giveaway", "status": "Active"}
    assert normalize_item(raw, Platform.STEAM).promotion_type == PromotionType.FREE_WEEKEND


def test_unrecognised_wording_is_unknown_not_guessed() -> None:
    raw = {"id": 9, "title": "Cool Game", "status": "Active"}
    assert normalize_item(raw, Platform.STEAM).promotion_type == PromotionType.UNKNOWN


# ---- the adapter over (mocked) HTTP ----


def test_fetch_requests_each_platform_once_with_expected_params() -> None:
    seen: list[dict[str, str]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(dict(request.url.params))
        return httpx.Response(200, json=load(NONE))

    make_adapter(handler).fetch_free_games()
    assert seen == [
        {"platform": "steam", "type": "game"},
        {"platform": "gog", "type": "game"},
        {"platform": "ubisoft", "type": "game"},
    ]


def test_empty_object_response_means_no_giveaways_not_an_error() -> None:
    adapter = make_adapter(lambda request: httpx.Response(200, json=load(NONE)))
    fetched = adapter.fetch_free_games()
    assert fetched.items == []
    assert fetched.errors == []
    assert fetched.requests_failed == 0
    assert run_scan(adapter).status == ScanStatus.SUCCESS


def test_full_scan_over_real_fixtures() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        fixture = STEAM if request.url.params["platform"] == "steam" else NONE
        return httpx.Response(200, json=load(fixture))

    result = run_scan(make_adapter(handler))
    assert result.status == ScanStatus.SUCCESS
    assert [p.title for p in result.items] == ["Dwarven Realms"]


def test_one_failing_platform_does_not_lose_the_others() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.params["platform"] == "gog":
            return httpx.Response(404)
        return httpx.Response(200, json=load(STEAM))

    result = run_scan(make_adapter(handler))
    assert result.status == ScanStatus.PARTIAL
    assert len(result.items) == 2  # steam + ubisoft responses both parsed
    assert any(error.startswith("gog:") for error in result.errors)


def test_all_platforms_failing_is_a_failed_scan() -> None:
    result = run_scan(make_adapter(lambda request: httpx.Response(500)))
    assert result.status == ScanStatus.FAILED


def test_unexpected_response_shape_is_a_failure_for_that_platform() -> None:
    adapter = make_adapter(
        lambda request: httpx.Response(200, json={"surprise": True}), platforms=("steam",)
    )
    assert run_scan(adapter).status == ScanStatus.FAILED


def test_malformed_item_is_dropped_but_valid_ones_survive() -> None:
    payload = [*load(STEAM), {"id": 1}]
    adapter = make_adapter(lambda request: httpx.Response(200, json=payload), platforms=("steam",))
    result = run_scan(adapter)
    assert result.status == ScanStatus.PARTIAL
    assert len(result.items) == 1
    assert result.dropped == 1


def test_item_pointing_at_an_unexpected_host_is_dropped_by_validation() -> None:
    item = {**load(STEAM)[0], "open_giveaway_url": "https://evil.example/claim"}
    adapter = make_adapter(lambda request: httpx.Response(200, json=[item]), platforms=("steam",))
    result = run_scan(adapter)
    assert result.items == []
    assert result.dropped == 1


def test_unknown_platform_is_rejected_at_construction() -> None:
    with pytest.raises(ValueError):
        make_adapter(lambda request: httpx.Response(200), platforms=("atari",))
