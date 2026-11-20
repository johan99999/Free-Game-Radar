import logging
from datetime import UTC, datetime

from fastapi import APIRouter, Request, Response
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app import __version__

logger = logging.getLogger(__name__)

router = APIRouter(tags=["health"])


class HealthResponse(BaseModel):
    status: str
    app: str
    version: str
    environment: str
    database: str
    time_utc: datetime


@router.get("/health", response_model=HealthResponse)
def health(request: Request, response: Response) -> HealthResponse:
    """Liveness plus a database connectivity check (503 if the database is unreachable)."""
    database_ok = True
    try:
        with request.app.state.engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except SQLAlchemyError:
        logger.exception("Database health check failed")
        database_ok = False
        response.status_code = 503
    return HealthResponse(
        status="ok" if database_ok else "degraded",
        app="free-game-radar",
        version=__version__,
        environment=request.app.state.settings.app_env,
        database="ok" if database_ok else "error",
        time_utc=datetime.now(UTC),
    )
