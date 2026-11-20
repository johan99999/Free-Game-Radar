from datetime import UTC, datetime, timedelta

from app.adapters.models import AdapterFetch, NormalizedPromotion, SupportStatus
from app.adapters.runner import run_all, run_scan
from app.adapters.validation import validate_promotion
from app.models.enums import Platform, PromotionStatus, PromotionType, ScanStatus

HOSTS = frozenset({"www.gamerpower.com"})
NOW = datetime(2026, 11, 20, 12, 0, tzinfo=UTC)


def promo(**overrides: object) -> NormalizedPromotion:
    fields: dict[str, object] = {
        "platform": Platform.STEAM,
        "platform_game_id": "gamerpower-1",
        "title": "Some Game",
        "promotion_type": PromotionType.FREE_TO_KEEP,
        "status": PromotionStatus.ACTIVE,
        "is_free": True,
        "source": "gamerpower",
        "store_url": "https://www.gamerpower.com/open/x",
        "current_price_minor": 0,
    }
    fields.update(overrides)
    return NormalizedPromotion(**fields)  # type: ignore[arg-type]


def test_valid_promotion_has_no_problems() -> None:
    assert validate_promotion(promo(), HOSTS) == []


def test_rejects_bad_urls() -> None:
    assert validate_promotion(promo(store_url="http://www.gamerpower.com/x"), HOSTS)
    assert validate_promotion(promo(store_url="https://evil.example/x"), HOSTS)
    assert validate_promotion(promo(image_url="https://evil.example/i.jpg"), HOSTS)


def test_rejects_bad_dates() -> None:
    assert validate_promotion(promo(end_date=datetime(2026, 1, 1)), HOSTS)  # naive
    assert validate_promotion(promo(start_date=NOW, end_date=NOW - timedelta(days=1)), HOSTS)


def test_rejects_bad_numbers_and_empty_fields() -> None:
    assert validate_promotion(promo(title="  "), HOSTS)
    assert validate_promotion(promo(platform_game_id=""), HOSTS)
    assert validate_promotion(promo(original_price_minor=-1), HOSTS)
    assert validate_promotion(promo(discount_percent=150), HOSTS)
    assert validate_promotion(promo(currency="US"), HOSTS)
    assert validate_promotion(promo(current_price_minor=500), HOSTS)  # "free" but priced


class FakeAdapter:
    allowed_hosts = HOSTS
    support_status = SupportStatus.PARTIAL

    def __init__(self, source: str, fetch: AdapterFetch | Exception) -> None:
        self.source = source
        self._fetch = fetch

    def fetch_free_games(self) -> AdapterFetch:
        if isinstance(self._fetch, Exception):
            raise self._fetch
        return self._fetch


def test_successful_scan() -> None:
    adapter = FakeAdapter("a", AdapterFetch(items=[promo()], requests_total=1))
    result = run_scan(adapter, clock=lambda: NOW)
    assert result.status == ScanStatus.SUCCESS
    assert len(result.items) == 1
    assert result.error_text is None


def test_invalid_items_are_dropped_and_scan_is_partial() -> None:
    adapter = FakeAdapter(
        "a",
        AdapterFetch(items=[promo(), promo(title="")], requests_total=1),
    )
    result = run_scan(adapter, clock=lambda: NOW)
    assert result.status == ScanStatus.PARTIAL
    assert len(result.items) == 1
    assert result.dropped == 1


def test_all_requests_failing_is_a_failed_scan() -> None:
    fetch = AdapterFetch(requests_total=2, requests_failed=2, errors=["x: boom"])
    assert run_scan(FakeAdapter("a", fetch), clock=lambda: NOW).status == ScanStatus.FAILED


def test_empty_but_healthy_scan_is_a_success() -> None:
    fetch = AdapterFetch(requests_total=3)
    result = run_scan(FakeAdapter("a", fetch), clock=lambda: NOW)
    assert result.status == ScanStatus.SUCCESS
    assert result.items == []


def test_crashing_adapter_never_propagates_and_does_not_block_others() -> None:
    adapters = [
        FakeAdapter("crashy", RuntimeError("boom")),
        FakeAdapter("fine", AdapterFetch(items=[promo()], requests_total=1)),
    ]
    results = run_all(adapters)
    assert [r.source for r in results] == ["crashy", "fine"]
    assert results[0].status == ScanStatus.FAILED
    assert "boom" in (results[0].error_text or "")
    assert results[1].status == ScanStatus.SUCCESS
