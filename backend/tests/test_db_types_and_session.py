from datetime import UTC, datetime, timedelta, timezone

import pytest
from sqlalchemy import Engine, select
from sqlalchemy.dialects import sqlite
from sqlalchemy.orm import Session

from app.db.session import create_session_factory, session_scope
from app.db.types import UTCDateTime
from app.models import Game, Promotion
from app.models.enums import Platform, PromotionStatus, PromotionType
from app.repositories.games import GameRepository
from app.repositories.promotions import PromotionData, PromotionRepository


def test_naive_datetime_is_rejected() -> None:
    with pytest.raises(ValueError):
        UTCDateTime().process_bind_param(datetime(2026, 1, 1), sqlite.dialect())


def test_datetime_roundtrips_as_utc(session: Session) -> None:
    game, _ = GameRepository(session).upsert(Platform.EPIC, "g1", "Game")
    jakarta = timezone(timedelta(hours=7))
    end = datetime(2026, 11, 20, 22, 0, tzinfo=jakarta)
    promo, _ = PromotionRepository(session).upsert(
        game.id,
        PromotionData(
            promotion_type=PromotionType.FREE_TO_KEEP,
            source="epic",
            is_free=True,
            status=PromotionStatus.ACTIVE,
            end_date=end,
        ),
    )
    session.expire(promo)  # force a re-read from the database
    assert promo.end_date == end
    assert promo.end_date is not None
    assert promo.end_date.utcoffset() == timedelta(0)
    assert promo.end_date.hour == 15  # 22:00 at +07:00 is 15:00 UTC


def test_session_scope_commits_on_success(engine: Engine) -> None:
    factory = create_session_factory(engine)
    with session_scope(factory) as db:
        db.add(Game(platform=Platform.GOG, platform_game_id="a", title="A"))
    with factory() as db:
        assert db.scalars(select(Game)).all() != []


def test_session_scope_rolls_back_on_error(engine: Engine) -> None:
    factory = create_session_factory(engine)
    with pytest.raises(RuntimeError), session_scope(factory) as db:
        db.add(Game(platform=Platform.GOG, platform_game_id="a", title="A"))
        db.flush()
        raise RuntimeError("boom")
    with factory() as db:
        assert db.scalars(select(Game)).all() == []


def test_promotion_datetimes_default_to_utc_aware(session: Session) -> None:
    game, _ = GameRepository(session).upsert(Platform.EPIC, "g2", "Game 2")
    promo = Promotion(
        game_id=game.id,
        dedupe_key="k",
        promotion_type=PromotionType.UNKNOWN,
        status=PromotionStatus.ACTIVE,
        is_free=True,
        source="epic",
    )
    session.add(promo)
    session.flush()
    session.expire(promo)
    assert promo.detected_at.tzinfo is not None
    assert abs(datetime.now(UTC) - promo.detected_at) < timedelta(minutes=1)
