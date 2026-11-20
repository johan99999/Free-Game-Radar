"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-11-18
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _id() -> sa.Column[int]:
    return sa.Column("id", sa.Integer(), nullable=False)


def upgrade() -> None:
    op.create_table(
        "users",
        _id(),
        sa.Column("timezone", sa.String(length=64), nullable=False),
        sa.Column("telegram_chat_id", sa.String(length=64), nullable=True),
        sa.Column("steam_id", sa.String(length=32), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_users")),
    )

    op.create_table(
        "user_devices",
        _id(),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("push_token", sa.String(length=512), nullable=False),
        sa.Column("platform", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_user_devices_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_user_devices")),
        sa.UniqueConstraint("push_token", name=op.f("uq_user_devices_push_token")),
    )
    op.create_index(op.f("ix_user_devices_user_id"), "user_devices", ["user_id"])

    op.create_table(
        "games",
        _id(),
        sa.Column("platform", sa.String(length=32), nullable=False),
        sa.Column("platform_game_id", sa.String(length=128), nullable=False),
        sa.Column("title", sa.String(length=300), nullable=False),
        sa.Column("store_url", sa.String(length=1000), nullable=True),
        sa.Column("image_url", sa.String(length=1000), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_games")),
        sa.UniqueConstraint("platform", "platform_game_id", name=op.f("uq_games_platform_game")),
    )
    op.create_index(op.f("ix_games_title"), "games", ["title"])

    op.create_table(
        "promotions",
        _id(),
        sa.Column("game_id", sa.Integer(), nullable=False),
        sa.Column("dedupe_key", sa.String(length=200), nullable=False),
        sa.Column("promotion_type", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("is_free", sa.Boolean(), nullable=False),
        sa.Column("start_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("end_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("original_price_minor", sa.Integer(), nullable=True),
        sa.Column("current_price_minor", sa.Integer(), nullable=True),
        sa.Column("currency", sa.String(length=3), nullable=True),
        sa.Column("region", sa.String(length=2), nullable=True),
        sa.Column("discount_percent", sa.Integer(), nullable=True),
        sa.Column("source", sa.String(length=50), nullable=False),
        sa.Column("source_url", sa.String(length=1000), nullable=True),
        sa.Column("detected_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "discount_percent BETWEEN 0 AND 100",
            name=op.f("ck_promotions_discount_percent_range"),
        ),
        sa.ForeignKeyConstraint(
            ["game_id"], ["games.id"], name=op.f("fk_promotions_game_id_games"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_promotions")),
        sa.UniqueConstraint("game_id", "dedupe_key", name=op.f("uq_promotions_game_dedupe")),
    )
    op.create_index(op.f("ix_promotions_status_end_date"), "promotions", ["status", "end_date"])

    op.create_table(
        "price_history",
        _id(),
        sa.Column("game_id", sa.Integer(), nullable=False),
        sa.Column("price_minor", sa.Integer(), nullable=False),
        sa.Column("original_price_minor", sa.Integer(), nullable=True),
        sa.Column("discount_percent", sa.Integer(), nullable=True),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("region", sa.String(length=2), nullable=False),
        sa.Column("source", sa.String(length=50), nullable=False),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("price_minor >= 0", name=op.f("ck_price_history_price_non_negative")),
        sa.ForeignKeyConstraint(
            ["game_id"],
            ["games.id"],
            name=op.f("fk_price_history_game_id_games"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_price_history")),
        sa.UniqueConstraint(
            "game_id",
            "currency",
            "region",
            "source",
            "observed_at",
            name=op.f("uq_price_history_observation"),
        ),
    )
    op.create_index(
        op.f("ix_price_history_game_observed"), "price_history", ["game_id", "observed_at"]
    )

    op.create_table(
        "wishlist_items",
        _id(),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("game_id", sa.Integer(), nullable=False),
        sa.Column("steam_app_id", sa.String(length=32), nullable=True),
        sa.Column("target_price_minor", sa.Integer(), nullable=True),
        sa.Column("notification_enabled", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["game_id"],
            ["games.id"],
            name=op.f("fk_wishlist_items_game_id_games"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_wishlist_items_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_wishlist_items")),
        sa.UniqueConstraint("user_id", "game_id", name=op.f("uq_wishlist_items_user_game")),
    )
    op.create_index(op.f("ix_wishlist_items_game_id"), "wishlist_items", ["game_id"])

    op.create_table(
        "price_alerts",
        _id(),
        sa.Column("wishlist_item_id", sa.Integer(), nullable=False),
        sa.Column("alert_type", sa.String(length=32), nullable=False),
        sa.Column("dedupe_key", sa.String(length=200), nullable=False),
        sa.Column("triggered_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["wishlist_item_id"],
            ["wishlist_items.id"],
            name=op.f("fk_price_alerts_wishlist_item_id_wishlist_items"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_price_alerts")),
        sa.UniqueConstraint(
            "wishlist_item_id", "dedupe_key", name=op.f("uq_price_alerts_item_dedupe")
        ),
    )

    op.create_table(
        "giveaway_reminders",
        _id(),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("promotion_id", sa.Integer(), nullable=False),
        sa.Column("offset_minutes", sa.Integer(), nullable=False),
        sa.Column("scheduled_for", sa.DateTime(timezone=True), nullable=False),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.ForeignKeyConstraint(
            ["promotion_id"],
            ["promotions.id"],
            name=op.f("fk_giveaway_reminders_promotion_id_promotions"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_giveaway_reminders_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_giveaway_reminders")),
        sa.UniqueConstraint(
            "user_id",
            "promotion_id",
            "offset_minutes",
            name=op.f("uq_giveaway_reminders_offset"),
        ),
    )
    op.create_index(
        op.f("ix_giveaway_reminders_promotion_id"), "giveaway_reminders", ["promotion_id"]
    )
    op.create_index(
        op.f("ix_giveaway_reminders_status_scheduled"),
        "giveaway_reminders",
        ["status", "scheduled_for"],
    )

    op.create_table(
        "notification_preferences",
        _id(),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("notification_type", sa.String(length=32), nullable=False),
        sa.Column("channel", sa.String(length=32), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("platform_filter", sa.String(length=32), nullable=True),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_notification_preferences_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_notification_preferences")),
        sa.UniqueConstraint(
            "user_id",
            "notification_type",
            "channel",
            name=op.f("uq_notification_preferences_key"),
        ),
    )

    op.create_table(
        "notification_logs",
        _id(),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("dedupe_key", sa.String(length=200), nullable=False),
        sa.Column("notification_type", sa.String(length=32), nullable=False),
        sa.Column("channel", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_notification_logs_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_notification_logs")),
    )
    op.create_index(
        op.f("ix_notification_logs_dedupe"), "notification_logs", ["dedupe_key", "channel"]
    )
    op.create_index(
        op.f("ix_notification_logs_user_created"), "notification_logs", ["user_id", "created_at"]
    )

    op.create_table(
        "platform_scan_logs",
        _id(),
        sa.Column("source", sa.String(length=50), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("items_found", sa.Integer(), nullable=False),
        sa.Column("error", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_platform_scan_logs")),
    )
    op.create_index(
        op.f("ix_platform_scan_logs_source_started"),
        "platform_scan_logs",
        ["source", "started_at"],
    )


def downgrade() -> None:
    for table in (
        "platform_scan_logs",
        "notification_logs",
        "notification_preferences",
        "giveaway_reminders",
        "price_alerts",
        "wishlist_items",
        "price_history",
        "promotions",
        "games",
        "user_devices",
        "users",
    ):
        op.drop_table(table)
