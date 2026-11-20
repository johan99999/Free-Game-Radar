from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import PriceHistory


class PriceHistoryRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def add(
        self,
        game_id: int,
        price_minor: int,
        currency: str,
        region: str,
        source: str,
        observed_at: datetime,
        original_price_minor: int | None = None,
        discount_percent: int | None = None,
    ) -> PriceHistory:
        row = PriceHistory(
            game_id=game_id,
            price_minor=price_minor,
            original_price_minor=original_price_minor,
            discount_percent=discount_percent,
            currency=currency.upper(),
            region=region.upper(),
            source=source,
            observed_at=observed_at,
        )
        self.session.add(row)
        self.session.flush()
        return row

    def list_for_game(
        self,
        game_id: int,
        currency: str | None = None,
        region: str | None = None,
        limit: int = 200,
    ) -> list[PriceHistory]:
        """Newest first."""
        stmt = select(PriceHistory).where(PriceHistory.game_id == game_id)
        if currency is not None:
            stmt = stmt.where(PriceHistory.currency == currency.upper())
        if region is not None:
            stmt = stmt.where(PriceHistory.region == region.upper())
        stmt = stmt.order_by(PriceHistory.observed_at.desc(), PriceHistory.id.desc()).limit(limit)
        return list(self.session.scalars(stmt))

    def recorded_low(self, game_id: int, currency: str, region: str) -> PriceHistory | None:
        """Lowest price WE observed. Prices are never compared across currency or region."""
        stmt = (
            select(PriceHistory)
            .where(
                PriceHistory.game_id == game_id,
                PriceHistory.currency == currency.upper(),
                PriceHistory.region == region.upper(),
            )
            .order_by(PriceHistory.price_minor, PriceHistory.observed_at)
            .limit(1)
        )
        return self.session.scalars(stmt).first()
