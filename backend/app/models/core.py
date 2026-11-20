from datetime import datetime

from sqlalchemy import CheckConstraint, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.time import utcnow
from app.db.base import Base
from app.models.columns import enum_column
from app.models.enums import DevicePlatform, Platform, PromotionStatus, PromotionType


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    timezone: Mapped[str] = mapped_column(String(64), default="Asia/Jakarta")
    telegram_chat_id: Mapped[str | None] = mapped_column(String(64))
    steam_id: Mapped[str | None] = mapped_column(String(32))
    created_at: Mapped[datetime] = mapped_column(default=utcnow)


class UserDevice(Base):
    __tablename__ = "user_devices"
    __table_args__ = (
        UniqueConstraint("push_token", name="uq_user_devices_push_token"),
        Index("ix_user_devices_user_id", "user_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    push_token: Mapped[str] = mapped_column(String(512))
    platform: Mapped[DevicePlatform] = enum_column(DevicePlatform)
    created_at: Mapped[datetime] = mapped_column(default=utcnow)


class Game(Base):
    __tablename__ = "games"
    __table_args__ = (
        UniqueConstraint("platform", "platform_game_id", name="uq_games_platform_game"),
        Index("ix_games_title", "title"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    platform: Mapped[Platform] = enum_column(Platform)
    platform_game_id: Mapped[str] = mapped_column(String(128))
    title: Mapped[str] = mapped_column(String(300))
    store_url: Mapped[str | None] = mapped_column(String(1000))
    image_url: Mapped[str | None] = mapped_column(String(1000))
    created_at: Mapped[datetime] = mapped_column(default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(default=utcnow, onupdate=utcnow)


class Promotion(Base):
    __tablename__ = "promotions"
    __table_args__ = (
        UniqueConstraint("game_id", "dedupe_key", name="uq_promotions_game_dedupe"),
        Index("ix_promotions_status_end_date", "status", "end_date"),
        CheckConstraint("discount_percent BETWEEN 0 AND 100", name="discount_percent_range"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    game_id: Mapped[int] = mapped_column(ForeignKey("games.id", ondelete="CASCADE"))
    dedupe_key: Mapped[str] = mapped_column(String(200))
    promotion_type: Mapped[PromotionType] = enum_column(PromotionType)
    status: Mapped[PromotionStatus] = enum_column(PromotionStatus)
    is_free: Mapped[bool]
    start_date: Mapped[datetime | None]
    end_date: Mapped[datetime | None]
    original_price_minor: Mapped[int | None]
    current_price_minor: Mapped[int | None]
    currency: Mapped[str | None] = mapped_column(String(3))
    region: Mapped[str | None] = mapped_column(String(2))
    discount_percent: Mapped[int | None]
    source: Mapped[str] = mapped_column(String(50))
    source_url: Mapped[str | None] = mapped_column(String(1000))
    detected_at: Mapped[datetime] = mapped_column(default=utcnow)
    last_seen_at: Mapped[datetime] = mapped_column(default=utcnow)


class PriceHistory(Base):
    __tablename__ = "price_history"
    __table_args__ = (
        UniqueConstraint(
            "game_id",
            "currency",
            "region",
            "source",
            "observed_at",
            name="uq_price_history_observation",
        ),
        Index("ix_price_history_game_observed", "game_id", "observed_at"),
        CheckConstraint("price_minor >= 0", name="price_non_negative"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    game_id: Mapped[int] = mapped_column(ForeignKey("games.id", ondelete="CASCADE"))
    price_minor: Mapped[int]
    original_price_minor: Mapped[int | None]
    discount_percent: Mapped[int | None]
    currency: Mapped[str] = mapped_column(String(3))
    region: Mapped[str] = mapped_column(String(2))
    source: Mapped[str] = mapped_column(String(50))
    observed_at: Mapped[datetime]
