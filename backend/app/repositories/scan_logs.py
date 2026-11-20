from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import PlatformScanLog
from app.models.enums import ScanStatus


class ScanLogRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def start(self, source: str, now: datetime) -> PlatformScanLog:
        log = PlatformScanLog(source=source, started_at=now, status=ScanStatus.FAILED)
        self.session.add(log)
        self.session.flush()
        return log

    def finish(
        self,
        log: PlatformScanLog,
        status: ScanStatus,
        now: datetime,
        items_found: int = 0,
        error: str | None = None,
    ) -> None:
        log.status = status
        log.finished_at = now
        log.items_found = items_found
        log.error = error
        self.session.flush()

    def latest_success(self, source: str) -> PlatformScanLog | None:
        stmt = (
            select(PlatformScanLog)
            .where(PlatformScanLog.source == source, PlatformScanLog.status == ScanStatus.SUCCESS)
            .order_by(PlatformScanLog.started_at.desc(), PlatformScanLog.id.desc())
            .limit(1)
        )
        return self.session.scalars(stmt).first()
