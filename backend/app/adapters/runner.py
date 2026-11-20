import logging
from collections.abc import Callable, Iterable
from datetime import datetime

from app.adapters.base import PlatformAdapter
from app.adapters.models import ScanResult
from app.adapters.validation import validate_promotion
from app.core.time import utcnow
from app.models.enums import ScanStatus

logger = logging.getLogger(__name__)


def run_scan(adapter: PlatformAdapter, clock: Callable[[], datetime] = utcnow) -> ScanResult:
    """Run one adapter. Never raises: any failure becomes a FAILED result."""
    started = clock()
    try:
        fetched = adapter.fetch_free_games()
    except Exception as exc:  # one broken source must never take the app down
        logger.exception("Adapter %s crashed", adapter.source)
        return ScanResult(
            source=adapter.source,
            status=ScanStatus.FAILED,
            started_at=started,
            finished_at=clock(),
            errors=[f"{type(exc).__name__}: {exc}"],
        )

    valid = []
    dropped = fetched.dropped
    errors = list(fetched.errors)
    for promo in fetched.items:
        problems = validate_promotion(promo, adapter.allowed_hosts)
        if problems:
            dropped += 1
            errors.append(f"dropped {promo.platform_game_id}: {', '.join(problems)}")
        else:
            valid.append(promo)

    all_requests_failed = fetched.requests_total > 0 and (
        fetched.requests_failed == fetched.requests_total
    )
    if all_requests_failed:
        status = ScanStatus.FAILED
    elif errors or dropped:
        status = ScanStatus.PARTIAL
    else:
        status = ScanStatus.SUCCESS
    return ScanResult(
        source=adapter.source,
        status=status,
        started_at=started,
        finished_at=clock(),
        items=valid,
        dropped=dropped,
        errors=errors,
    )


def run_all(adapters: Iterable[PlatformAdapter]) -> list[ScanResult]:
    return [run_scan(adapter) for adapter in adapters]
