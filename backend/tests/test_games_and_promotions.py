from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import Game, Promotion
from app.models.enums import Platform, PromotionStatus, PromotionType
from app.repositories.games import GameRepository
from app.repositories.promotions import PromotionData, PromotionRepository, make_dedupe_key

NOW = datetime(2026, 11, 20, 12, 0, tzinfo=UTC)


def make_game(session: Session, platform_game_id: str = "g1", platform: Platform = Platform.EPIC):
    game, _ = GameRepository(session).upsert(platform, platform_game_id, f"Game {platform_game_id}")
    return game


def free_data(**overrides: object) -> PromotionData:
    fields: dict[str, object] = {
        "promotion_type": PromotionType.FREE_TO_KEEP,
        "source": "epic",
        "is_free": True,
        "status": PromotionStatus.ACTIVE,
        "start_date": NOW - timedelta(days=1),
        "end_date": NOW + timedelta(days=6),
    }
    fields.update(overrides)
    return PromotionData(**fields)  # type: ignore[arg-type]


# ---- games ----


def test_game_insert_and_retrieve(session: Session) -> None:
    repo = GameRepository(session)
    game, created = repo.upsert(Platform.STEAM, "730", "Counter-Strike 2", store_url="https://x")
    assert created is True
    assert repo.get(game.id) is game
    found = repo.get_by_platform_id(Platform.STEAM, "730")
    assert found is not None
    assert found.title == "Counter-Strike 2"
    assert found.store_url == "https://x"


def test_game_upsert_updates_instead_of_duplicating(session: Session) -> None:
    repo = GameRepository(session)
    first, _ = repo.upsert(Platform.STEAM, "730", "Old title")
    second, created = repo.upsert(Platform.STEAM, "730", "New title", image_url="https://img")
    assert created is False
    assert second.id == first.id
    assert second.title == "New title"
    assert second.image_url == "https://img"
    assert len(repo.list_games()) == 1


def test_same_id_on_different_platforms_is_allowed(session: Session) -> None:
    repo = GameRepository(session)
    repo.upsert(Platform.STEAM, "1", "A")
    repo.upsert(Platform.EPIC, "1", "A")
    assert len(repo.list_games()) == 2


def test_database_rejects_duplicate_game(session: Session) -> None:
    session.add(Game(platform=Platform.GOG, platform_game_id="x", title="One"))
    session.add(Game(platform=Platform.GOG, platform_game_id="x", title="Two"))
    with pytest.raises(IntegrityError):
        session.flush()


def test_list_games_filters_by_platform_and_paginates(session: Session) -> None:
    repo = GameRepository(session)
    for i in range(3):
        repo.upsert(Platform.EPIC, f"e{i}", f"E{i}")
    repo.upsert(Platform.GOG, "g0", "G0")
    assert len(repo.list_games(platform=Platform.EPIC)) == 3
    assert len(repo.list_games(limit=2)) == 2
    assert len(repo.list_games(limit=10, offset=3)) == 1


def test_game_delete(session: Session) -> None:
    repo = GameRepository(session)
    game, _ = repo.upsert(Platform.EPIC, "g", "G")
    assert repo.delete(game.id) is True
    assert repo.get(game.id) is None
    assert repo.delete(game.id) is False


# ---- promotions ----


def test_promotion_insert_and_retrieve(session: Session) -> None:
    game = make_game(session)
    repo = PromotionRepository(session)
    promo, created = repo.upsert(game.id, free_data(), now=NOW)
    assert created is True
    assert promo.detected_at == NOW
    assert promo.last_seen_at == NOW
    assert promo.dedupe_key == make_dedupe_key("epic", PromotionType.FREE_TO_KEEP, promo.start_date)
    assert repo.get(promo.id) is promo


def test_promotion_upsert_updates_end_date_without_duplicating(session: Session) -> None:
    game = make_game(session)
    repo = PromotionRepository(session)
    first, _ = repo.upsert(game.id, free_data(), now=NOW)
    later = NOW + timedelta(hours=1)
    new_end = NOW + timedelta(days=9)
    second, created = repo.upsert(game.id, free_data(end_date=new_end), now=later)
    assert created is False
    assert second.id == first.id
    assert second.end_date == new_end
    assert second.detected_at == NOW  # first detection time is preserved
    assert second.last_seen_at == later
    assert len(session.scalars(select(Promotion)).all()) == 1


def test_promotion_with_unknown_start_date_does_not_duplicate(session: Session) -> None:
    game = make_game(session)
    repo = PromotionRepository(session)
    repo.upsert(game.id, free_data(start_date=None), now=NOW)
    _, created = repo.upsert(game.id, free_data(start_date=None), now=NOW)
    assert created is False


def test_promotion_requires_existing_game(session: Session) -> None:
    session.add(
        Promotion(
            game_id=999,
            dedupe_key="k",
            promotion_type=PromotionType.UNKNOWN,
            status=PromotionStatus.ACTIVE,
            is_free=True,
            source="epic",
        )
    )
    with pytest.raises(IntegrityError):
        session.flush()


def test_deleting_game_cascades_to_promotions(session: Session) -> None:
    game = make_game(session)
    PromotionRepository(session).upsert(game.id, free_data(), now=NOW)
    GameRepository(session).delete(game.id)
    assert session.scalars(select(Promotion)).all() == []


def test_discount_percent_must_be_between_0_and_100(session: Session) -> None:
    game = make_game(session)
    with pytest.raises(IntegrityError):
        PromotionRepository(session).upsert(game.id, free_data(discount_percent=150), now=NOW)


def test_list_active_only_returns_running_promotions(session: Session) -> None:
    repo = PromotionRepository(session)
    active = make_game(session, "active")
    unknown_end = make_game(session, "unknown")
    expired = make_game(session, "expired")
    upcoming = make_game(session, "upcoming")
    stale = make_game(session, "stale")  # status ACTIVE but end date already passed

    repo.upsert(active.id, free_data(), now=NOW)
    repo.upsert(unknown_end.id, free_data(end_date=None), now=NOW)
    repo.upsert(expired.id, free_data(status=PromotionStatus.EXPIRED), now=NOW)
    repo.upsert(upcoming.id, free_data(status=PromotionStatus.UPCOMING), now=NOW)
    repo.upsert(stale.id, free_data(end_date=NOW - timedelta(hours=1)), now=NOW)

    result = repo.list_active(NOW)
    assert [p.game_id for p in result] == [active.id, unknown_end.id]  # unknown end last


def test_list_active_filters_by_platform(session: Session) -> None:
    repo = PromotionRepository(session)
    epic = make_game(session, "e", Platform.EPIC)
    steam = make_game(session, "s", Platform.STEAM)
    repo.upsert(epic.id, free_data(), now=NOW)
    repo.upsert(steam.id, free_data(source="gamerpower"), now=NOW)
    result = repo.list_active(NOW, platform=Platform.STEAM)
    assert [p.game_id for p in result] == [steam.id]


def test_expire_due_marks_ended_promotions(session: Session) -> None:
    repo = PromotionRepository(session)
    ended = make_game(session, "ended")
    running = make_game(session, "running")
    ended_promo, _ = repo.upsert(ended.id, free_data(end_date=NOW - timedelta(minutes=1)), now=NOW)
    running_promo, _ = repo.upsert(running.id, free_data(), now=NOW)

    assert repo.expire_due(NOW) == 1
    assert ended_promo.status == PromotionStatus.EXPIRED
    assert running_promo.status == PromotionStatus.ACTIVE
    assert repo.expire_due(NOW) == 0  # nothing left to expire
