from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.time import utcnow
from app.models import NotificationLog, NotificationPreference, PriceAlert
from app.models.enums import (
    AlertType,
    NotificationChannel,
    NotificationStatus,
    NotificationType,
)


class NotificationLogRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def add(
        self,
        user_id: int,
        dedupe_key: str,
        notification_type: NotificationType,
        channel: NotificationChannel,
        status: NotificationStatus,
        error: str | None = None,
        now: datetime | None = None,
    ) -> NotificationLog:
        log = NotificationLog(
            user_id=user_id,
            dedupe_key=dedupe_key,
            notification_type=notification_type,
            channel=channel,
            status=status,
            error=error,
            created_at=now or utcnow(),
        )
        self.session.add(log)
        self.session.flush()
        return log

    def was_sent(self, dedupe_key: str, channel: NotificationChannel) -> bool:
        stmt = (
            select(NotificationLog.id)
            .where(
                NotificationLog.dedupe_key == dedupe_key,
                NotificationLog.channel == channel,
                NotificationLog.status == NotificationStatus.SENT,
            )
            .limit(1)
        )
        return self.session.scalars(stmt).first() is not None


class PreferenceRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def _get(
        self, user_id: int, notification_type: NotificationType, channel: NotificationChannel
    ) -> NotificationPreference | None:
        stmt = select(NotificationPreference).where(
            NotificationPreference.user_id == user_id,
            NotificationPreference.notification_type == notification_type,
            NotificationPreference.channel == channel,
        )
        return self.session.scalars(stmt).first()

    def is_enabled(
        self, user_id: int, notification_type: NotificationType, channel: NotificationChannel
    ) -> bool:
        """Notifications are on unless the user switched them off."""
        pref = self._get(user_id, notification_type, channel)
        return True if pref is None else pref.enabled

    def set_enabled(
        self,
        user_id: int,
        notification_type: NotificationType,
        channel: NotificationChannel,
        enabled: bool,
    ) -> NotificationPreference:
        pref = self._get(user_id, notification_type, channel)
        if pref is None:
            pref = NotificationPreference(
                user_id=user_id,
                notification_type=notification_type,
                channel=channel,
                enabled=enabled,
            )
            self.session.add(pref)
        else:
            pref.enabled = enabled
        self.session.flush()
        return pref


class PriceAlertRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def record_if_new(
        self, wishlist_item_id: int, alert_type: AlertType, dedupe_key: str
    ) -> tuple[PriceAlert | None, bool]:
        """Returns (alert, True) if recorded now, or (None, False) if already recorded."""
        stmt = select(PriceAlert).where(
            PriceAlert.wishlist_item_id == wishlist_item_id, PriceAlert.dedupe_key == dedupe_key
        )
        if self.session.scalars(stmt).first() is not None:
            return None, False
        alert = PriceAlert(
            wishlist_item_id=wishlist_item_id, alert_type=alert_type, dedupe_key=dedupe_key
        )
        self.session.add(alert)
        self.session.flush()
        return alert, True
