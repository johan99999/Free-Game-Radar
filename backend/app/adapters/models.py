from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum

from app.models.enums import Platform, PromotionStatus, PromotionType, ScanStatus


class SupportStatus(StrEnum):
    SUPPORTED = "SUPPORTED"  # first-party source, tested against real responses
    PARTIAL = "PARTIAL"  # third-party source or incomplete data
    UNSUPPORTED = "UNSUPPORTED"  # no usable source


@dataclass(frozen=True)
class NormalizedPromotion:
    """What every adapter produces, whatever the source looks like."""

    platform: Platform
    platform_game_id: str
    title: str
    promotion_type: PromotionType
    status: PromotionStatus
    is_free: bool
    source: str
    store_url: str | None = None
    image_url: str | None = None
    source_url: str | None = None
    start_date: datetime | None = None
    end_date: datetime | None = None
    original_price_minor: int | None = None
    current_price_minor: int | None = None
    currency: str | None = None
    region: str | None = None
    discount_percent: int | None = None


@dataclass
class AdapterFetch:
    """Raw adapter output, before validation."""

    items: list[NormalizedPromotion] = field(default_factory=list)
    dropped: int = 0  # items that could not be normalized
    errors: list[str] = field(default_factory=list)
    requests_total: int = 0
    requests_failed: int = 0


@dataclass
class ScanResult:
    source: str
    status: ScanStatus
    started_at: datetime
    finished_at: datetime
    items: list[NormalizedPromotion] = field(default_factory=list)
    dropped: int = 0
    errors: list[str] = field(default_factory=list)

    @property
    def error_text(self) -> str | None:
        return "; ".join(self.errors) if self.errors else None


@dataclass(frozen=True)
class PlatformInfo:
    platform: Platform
    source: str
    status: SupportStatus
    promotion_types: tuple[PromotionType, ...]
    notes: str
