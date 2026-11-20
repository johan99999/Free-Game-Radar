from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import PriceHistory, WishlistItem
from app.models.enums import (
    AlertType,
    NotificationChannel,
    NotificationStatus,
    NotificationType,
    Platform,
    PromotionStatus,
    PromotionType,
    ReminderStatus,
    ScanStatus,
)
from app.repositories.games import GameRepository
from app.repositories.notifications import (
    NotificationLogRepository,
    PreferenceRepository,
    PriceAlertRepository,
)
from app.repositories.price_history import PriceHistoryRepository
from app.repositories.promotions import PromotionData, PromotionRepository
from app.repositories.reminders import ReminderRepository
from app.repositories.scan_logs import ScanLogRepository
from app.repositories.users import UserRepository
from app.repositories.wishlist import WishlistRepository

NOW = datetime(2026, 11, 20, 12, 0, tzinfo=UTC)


def make_game(session: Session, platform_game_id: str = "730"):
    game, _ = GameRepository(session).upsert(Platform.STEAM, platform_game_id, "Game")
    return game


# ---- users ----


def test_default_user_is_created_once(session: Session) -> None:
    repo = UserRepository(session)
    first = repo.get_or_create_default()
    second = repo.get_or_create_default()
    assert first.id == second.id
    assert first.timezone == "Asia/Jakarta"


# ---- price history ----


def test_price_history_preserves_currency_region_source_and_time(session: Session) -> None:
    game = make_game(session)
    repo = PriceHistoryRepository(session)
    repo.add(
        game.id,
        price_minor=150000,
        currency="idr",
        region="id",
        source="steam",
        observed_at=NOW,
        original_price_minor=300000,
        discount_percent=50,
    )
    [row] = repo.list_for_game(game.id)
    assert (row.price_minor, row.currency, row.region, row.source) == (150000, "IDR", "ID", "steam")
    assert row.observed_at == NOW
    assert (row.original_price_minor, row.discount_percent) == (300000, 50)


def test_price_history_lists_newest_first_and_filters(session: Session) -> None:
    game = make_game(session)
    repo = PriceHistoryRepository(session)
    repo.add(game.id, 100, "IDR", "ID", "steam", NOW - timedelta(days=2))
    repo.add(game.id, 90, "IDR", "ID", "steam", NOW - timedelta(days=1))
    repo.add(game.id, 5, "USD", "US", "steam", NOW)
    idr = repo.list_for_game(game.id, currency="IDR", region="ID")
    assert [r.price_minor for r in idr] == [90, 100]
    assert len(repo.list_for_game(game.id)) == 3


def test_recorded_low_never_mixes_currencies(session: Session) -> None:
    game = make_game(session)
    repo = PriceHistoryRepository(session)
    repo.add(game.id, 150000, "IDR", "ID", "steam", NOW - timedelta(days=3))
    repo.add(game.id, 99000, "IDR", "ID", "steam", NOW - timedelta(days=2))
    repo.add(game.id, 120000, "IDR", "ID", "steam", NOW - timedelta(days=1))
    repo.add(game.id, 5, "USD", "US", "steam", NOW)  # numerically lower, different currency
    low = repo.recorded_low(game.id, "IDR", "ID")
    assert low is not None
    assert low.price_minor == 99000
    assert repo.recorded_low(game.id, "EUR", "DE") is None


def test_price_history_rejects_duplicate_observation_and_negative_price(session: Session) -> None:
    game = make_game(session)
    repo = PriceHistoryRepository(session)
    repo.add(game.id, 100, "IDR", "ID", "steam", NOW)
    with pytest.raises(IntegrityError):
        repo.add(game.id, 100, "IDR", "ID", "steam", NOW)
    session.rollback()


def test_price_history_rejects_negative_price(session: Session) -> None:
    game = make_game(session)
    with pytest.raises(IntegrityError):
        PriceHistoryRepository(session).add(game.id, -1, "IDR", "ID", "steam", NOW)


# ---- wishlist ----


def test_wishlist_add_is_idempotent(session: Session) -> None:
    user = UserRepository(session).get_or_create_default()
    game = make_game(session)
    repo = WishlistRepository(session)
    item, created = repo.add(user.id, game.id, steam_app_id="730", target_price_minor=100000)
    again, created_again = repo.add(user.id, game.id)
    assert created is True
    assert created_again is False
    assert again.id == item.id
    assert len(repo.list_for_user(user.id)) == 1


def test_wishlist_update_and_remove(session: Session) -> None:
    user = UserRepository(session).get_or_create_default()
    game = make_game(session)
    repo = WishlistRepository(session)
    item, _ = repo.add(user.id, game.id)
    repo.set_target_price(item, 50000)
    assert repo.get(user.id, game.id) is item
    assert item.target_price_minor == 50000
    assert repo.remove(user.id, game.id) is True
    assert repo.get(user.id, game.id) is None
    assert repo.remove(user.id, game.id) is False


def test_deleting_user_cascades_to_wishlist(session: Session) -> None:
    user = UserRepository(session).get_or_create_default()
    game = make_game(session)
    WishlistRepository(session).add(user.id, game.id)
    session.delete(user)
    session.flush()
    assert session.scalars(select(WishlistItem)).all() == []


def test_wishlist_requires_existing_game(session: Session) -> None:
    user = UserRepository(session).get_or_create_default()
    with pytest.raises(IntegrityError):
        WishlistRepository(session).add(user.id, 999)


def test_deleting_game_cascades_to_price_history(session: Session) -> None:
    game = make_game(session)
    PriceHistoryRepository(session).add(game.id, 100, "IDR", "ID", "steam", NOW)
    GameRepository(session).delete(game.id)
    assert session.scalars(select(PriceHistory)).all() == []


# ---- reminders ----


def make_promotion(session: Session):
    game = make_game(session, "epic-game")
    promo, _ = PromotionRepository(session).upsert(
        game.id,
        PromotionData(
            promotion_type=PromotionType.FREE_TO_KEEP,
            source="epic",
            is_free=True,
            status=PromotionStatus.ACTIVE,
            end_date=NOW + timedelta(days=1),
        ),
        now=NOW,
    )
    return promo


def test_reminder_add_is_idempotent(session: Session) -> None:
    user = UserRepository(session).get_or_create_default()
    promo = make_promotion(session)
    repo = ReminderRepository(session)
    first, created = repo.add_if_missing(user.id, promo.id, 60, NOW)
    second, created_again = repo.add_if_missing(user.id, promo.id, 60, NOW)
    assert created is True
    assert created_again is False
    assert second.id == first.id
    assert first.status == ReminderStatus.PENDING


def test_due_returns_only_pending_reminders_scheduled_in_the_past(session: Session) -> None:
    user = UserRepository(session).get_or_create_default()
    promo = make_promotion(session)
    repo = ReminderRepository(session)
    due, _ = repo.add_if_missing(user.id, promo.id, 1440, NOW - timedelta(minutes=5))
    repo.add_if_missing(user.id, promo.id, 30, NOW + timedelta(hours=1))
    done, _ = repo.add_if_missing(user.id, promo.id, 360, NOW - timedelta(hours=1))
    assert repo.mark_sent(done.id, NOW) is True
    assert [r.id for r in repo.due(NOW)] == [due.id]


def test_mark_sent_can_only_succeed_once(session: Session) -> None:
    user = UserRepository(session).get_or_create_default()
    promo = make_promotion(session)
    repo = ReminderRepository(session)
    reminder, _ = repo.add_if_missing(user.id, promo.id, 60, NOW)
    assert repo.mark_sent(reminder.id, NOW) is True
    assert repo.mark_sent(reminder.id, NOW) is False
    assert reminder.status == ReminderStatus.SENT
    assert reminder.sent_at == NOW


def test_skip_pending_for_promotion(session: Session) -> None:
    user = UserRepository(session).get_or_create_default()
    promo = make_promotion(session)
    repo = ReminderRepository(session)
    repo.add_if_missing(user.id, promo.id, 60, NOW)
    repo.add_if_missing(user.id, promo.id, 30, NOW)
    assert repo.skip_pending_for_promotion(promo.id) == 2
    assert repo.due(NOW + timedelta(days=1)) == []


# ---- scan logs ----


def test_scan_log_lifecycle(session: Session) -> None:
    repo = ScanLogRepository(session)
    assert repo.latest_success("epic") is None
    failed = repo.start("epic", NOW)
    repo.finish(failed, ScanStatus.FAILED, NOW, error="timeout")
    assert repo.latest_success("epic") is None
    ok = repo.start("epic", NOW + timedelta(minutes=30))
    repo.finish(ok, ScanStatus.SUCCESS, NOW + timedelta(minutes=31), items_found=2)
    latest = repo.latest_success("epic")
    assert latest is not None
    assert (latest.id, latest.items_found) == (ok.id, 2)
    assert repo.latest_success("gamerpower") is None


# ---- notifications ----


def test_preferences_default_to_enabled_and_can_be_switched_off(session: Session) -> None:
    user = UserRepository(session).get_or_create_default()
    repo = PreferenceRepository(session)
    kind, channel = NotificationType.PRICE_DROP, NotificationChannel.TELEGRAM
    assert repo.is_enabled(user.id, kind, channel) is True
    repo.set_enabled(user.id, kind, channel, False)
    assert repo.is_enabled(user.id, kind, channel) is False
    repo.set_enabled(user.id, kind, channel, True)
    assert repo.is_enabled(user.id, kind, channel) is True


def test_notification_log_tracks_sent_only(session: Session) -> None:
    user = UserRepository(session).get_or_create_default()
    repo = NotificationLogRepository(session)
    kind, channel = NotificationType.GIVEAWAY_REMINDER, NotificationChannel.TELEGRAM
    repo.add(user.id, "k1", kind, channel, NotificationStatus.FAILED, error="network")
    assert repo.was_sent("k1", channel) is False
    repo.add(user.id, "k1", kind, channel, NotificationStatus.SENT)
    assert repo.was_sent("k1", channel) is True
    assert repo.was_sent("k1", NotificationChannel.FCM) is False


def test_price_alert_is_recorded_once(session: Session) -> None:
    user = UserRepository(session).get_or_create_default()
    game = make_game(session)
    item, _ = WishlistRepository(session).add(user.id, game.id)
    repo = PriceAlertRepository(session)
    alert, recorded = repo.record_if_new(item.id, AlertType.TARGET_PRICE, "730:99000:target")
    again, recorded_again = repo.record_if_new(item.id, AlertType.TARGET_PRICE, "730:99000:target")
    assert recorded is True
    assert alert is not None
    assert (again, recorded_again) == (None, False)
