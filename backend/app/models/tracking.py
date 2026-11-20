from datetime import datetime

from sqlalchemy import ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.time import utcnow
from app.db.base import Base
from app.models.columns import enum_column
from app.models.enums import (
    AlertType,
    NotificationChannel,
    NotificationStatus,
    NotificationType,
    ReminderStatus,
    ScanStatus,
)


class WishlistItem(Base):
    __tablename__ = "wishlist_items"
    __table_args__ = (
        UniqueConstraint("user_id", "game_id", name="uq_wishlist_items_user_game"),
        Index("ix_wishlist_items_game_id", "game_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    game_id: Mapped[int] = mapped_column(ForeignKey("games.id", ondelete="CASCADE"))
    steam_app_id: Mapped[str | None] = mapped_column(String(32))
    target_price_minor: Mapped[int | None]
    notification_enabled: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(default=utcnow)


class PriceAlert(Base):
    __tablename__ = "price_alerts"
    __table_args__ = (
        UniqueConstraint("wishlist_item_id", "dedupe_key", name="uq_price_alerts_item_dedupe"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    wishlist_item_id: Mapped[int] = mapped_column(
        ForeignKey("wishlist_items.id", ondelete="CASCADE")
    )
    alert_type: Mapped[AlertType] = enum_column(AlertType)
    dedupe_key: Mapped[str] = mapped_column(String(200))
    triggered_at: Mapped[datetime] = mapped_column(default=utcnow)


class GiveawayReminder(Base):
    __tablename__ = "giveaway_reminders"
    __table_args__ = (
        UniqueConstraint(
            "user_id", "promotion_id", "offset_minutes", name="uq_giveaway_reminders_offset"
        ),
        Index("ix_giveaway_reminders_promotion_id", "promotion_id"),
        Index("ix_giveaway_reminders_status_scheduled", "status", "scheduled_for"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    promotion_id: Mapped[int] = mapped_column(ForeignKey("promotions.id", ondelete="CASCADE"))
    offset_minutes: Mapped[int]
    scheduled_for: Mapped[datetime]
    sent_at: Mapped[datetime | None]
    status: Mapped[ReminderStatus] = enum_column(ReminderStatus, default=ReminderStatus.PENDING)


class NotificationPreference(Base):
    __tablename__ = "notification_preferences"
    __table_args__ = (
        UniqueConstraint(
            "user_id", "notification_type", "channel", name="uq_notification_preferences_key"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    notification_type: Mapped[NotificationType] = enum_column(NotificationType)
    channel: Mapped[NotificationChannel] = enum_column(NotificationChannel)
    enabled: Mapped[bool] = mapped_column(default=True)
    platform_filter: Mapped[str | None] = mapped_column(String(32))


class NotificationLog(Base):
    __tablename__ = "notification_logs"
    __table_args__ = (
        Index("ix_notification_logs_dedupe", "dedupe_key", "channel"),
        Index("ix_notification_logs_user_created", "user_id", "created_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    dedupe_key: Mapped[str] = mapped_column(String(200))
    notification_type: Mapped[NotificationType] = enum_column(NotificationType)
    channel: Mapped[NotificationChannel] = enum_column(NotificationChannel)
    status: Mapped[NotificationStatus] = enum_column(NotificationStatus)
    error: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(default=utcnow)


class PlatformScanLog(Base):
    __tablename__ = "platform_scan_logs"
    __table_args__ = (Index("ix_platform_scan_logs_source_started", "source", "started_at"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    source: Mapped[str] = mapped_column(String(50))
    started_at: Mapped[datetime]
    finished_at: Mapped[datetime | None]
    status: Mapped[ScanStatus] = enum_column(ScanStatus)
    items_found: Mapped[int] = mapped_column(default=0)
    error: Mapped[str | None] = mapped_column(Text)
