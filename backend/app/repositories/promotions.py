from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, cast

from sqlalchemy import or_, select, update
from sqlalchemy.engine import CursorResult
from sqlalchemy.orm import Session

from app.core.time import utcnow
from app.models import Game, Promotion
from app.models.enums import Platform, PromotionStatus, PromotionType


@dataclass(frozen=True)
class PromotionData:
    promotion_type: PromotionType
    source: str
    is_free: bool
    status: PromotionStatus
    start_date: datetime | None = None
    end_date: datetime | None = None
    original_price_minor: int | None = None
    current_price_minor: int | None = None
    currency: str | None = None
    region: str | None = None
    discount_percent: int | None = None
    source_url: str | None = None


def make_dedupe_key(source: str, promotion_type: PromotionType, start_date: datetime | None) -> str:
    """Identity of one promotion window. The end date is NOT part of it, so an extended
    giveaway updates the same row instead of creating a new one."""
    start = start_date.astimezone(UTC).strftime("%Y%m%dT%H%M%SZ") if start_date else "unknown"
    return f"{source}|{promotion_type.value}|{start}"


class PromotionRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get(self, promotion_id: int) -> Promotion | None:
        return self.session.get(Promotion, promotion_id)

    def upsert(
        self, game_id: int, data: PromotionData, now: datetime | None = None
    ) -> tuple[Promotion, bool]:
        """Insert or update one promotion. Returns (promotion, created)."""
        now = now or utcnow()
        key = make_dedupe_key(data.source, data.promotion_type, data.start_date)
        stmt = select(Promotion).where(Promotion.game_id == game_id, Promotion.dedupe_key == key)
        promo = self.session.scalars(stmt).first()
        created = promo is None
        if promo is None:
            promo = Promotion(
                game_id=game_id,
                dedupe_key=key,
                promotion_type=data.promotion_type,
                source=data.source,
                start_date=data.start_date,
                detected_at=now,
            )
            self.session.add(promo)
        promo.status = data.status
        promo.is_free = data.is_free
        promo.end_date = data.end_date
        promo.original_price_minor = data.original_price_minor
        promo.current_price_minor = data.current_price_minor
        promo.currency = data.currency
        promo.region = data.region
        promo.discount_percent = data.discount_percent
        promo.source_url = data.source_url
        promo.last_seen_at = now
        self.session.flush()
        return promo, created

    def list_active(
        self,
        now: datetime,
        platform: Platform | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Promotion]:
        """ACTIVE promotions that have not ended. A missing end date means 'unknown', and
        such promotions are included (soonest-ending first, unknown last)."""
        stmt = (
            select(Promotion)
            .where(
                Promotion.status == PromotionStatus.ACTIVE,
                or_(Promotion.end_date.is_(None), Promotion.end_date > now),
            )
            .order_by(Promotion.end_date.is_(None), Promotion.end_date, Promotion.id)
            .limit(limit)
            .offset(offset)
        )
        if platform is not None:
            stmt = stmt.join(Game, Game.id == Promotion.game_id).where(Game.platform == platform)
        return list(self.session.scalars(stmt))

    def expire_due(self, now: datetime) -> int:
        """Mark UPCOMING/ACTIVE promotions whose end date has passed as EXPIRED."""
        stmt = (
            update(Promotion)
            .where(
                Promotion.status.in_([PromotionStatus.ACTIVE, PromotionStatus.UPCOMING]),
                Promotion.end_date.is_not(None),
                Promotion.end_date <= now,
            )
            .values(status=PromotionStatus.EXPIRED)
        )
        result = cast("CursorResult[Any]", self.session.execute(stmt))
        self.session.expire_all()
        return result.rowcount
