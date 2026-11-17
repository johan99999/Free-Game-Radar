from datetime import UTC, datetime

from fastapi import APIRouter, Request
from pydantic import BaseModel

from app import __version__

router = APIRouter(tags=["health"])


class HealthResponse(BaseModel):
    status: str
    app: str
    version: str
    environment: str
    time_utc: datetime


@router.get("/health", response_model=HealthResponse)
def health(request: Request) -> HealthResponse:
    """Liveness check. A database check is added in Phase 2."""
    return HealthResponse(
        status="ok",
        app="free-game-radar",
        version=__version__,
        environment=request.app.state.settings.app_env,
        time_utc=datetime.now(UTC),
    )
