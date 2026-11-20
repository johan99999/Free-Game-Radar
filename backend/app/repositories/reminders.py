from datetime import datetime
from typing import Any, cast

from sqlalchemy import select, update
from sqlalchemy.engine import CursorResult
from sqlalchemy.orm import Session

from app.models import GiveawayReminder
from app.models.enums import ReminderStatus


class ReminderRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def add_if_missing(
        self, user_id: int, promotion_id: int, offset_minutes: int, scheduled_for: datetime
    ) -> tuple[GiveawayReminder, bool]:
        """Idempotent. Returns (reminder, created)."""
        stmt = select(GiveawayReminder).where(
            GiveawayReminder.user_id == user_id,
            GiveawayReminder.promotion_id == promotion_id,
            GiveawayReminder.offset_minutes == offset_minutes,
        )
        existing = self.session.scalars(stmt).first()
        if existing is not None:
            return existing, False
        reminder = GiveawayReminder(
            user_id=user_id,
            promotion_id=promotion_id,
            offset_minutes=offset_minutes,
            scheduled_for=scheduled_for,
        )
        self.session.add(reminder)
        self.session.flush()
        return reminder, True

    def due(self, now: datetime, limit: int = 100) -> list[GiveawayReminder]:
        stmt = (
            select(GiveawayReminder)
            .where(
                GiveawayReminder.status == ReminderStatus.PENDING,
                GiveawayReminder.scheduled_for <= now,
            )
            .order_by(GiveawayReminder.scheduled_for, GiveawayReminder.id)
            .limit(limit)
        )
        return list(self.session.scalars(stmt))

    def mark_sent(self, reminder_id: int, now: datetime) -> bool:
        """Atomic PENDING -> SENT. True only for the caller that wins, so a reminder can
        never be claimed twice."""
        stmt = (
            update(GiveawayReminder)
            .where(
                GiveawayReminder.id == reminder_id,
                GiveawayReminder.status == ReminderStatus.PENDING,
            )
            .values(status=ReminderStatus.SENT, sent_at=now)
        )
        result = cast("CursorResult[Any]", self.session.execute(stmt))
        self.session.expire_all()
        return result.rowcount == 1

    def skip_pending_for_promotion(self, promotion_id: int) -> int:
        stmt = (
            update(GiveawayReminder)
            .where(
                GiveawayReminder.promotion_id == promotion_id,
                GiveawayReminder.status == ReminderStatus.PENDING,
            )
            .values(status=ReminderStatus.SKIPPED)
        )
        result = cast("CursorResult[Any]", self.session.execute(stmt))
        self.session.expire_all()
        return result.rowcount
