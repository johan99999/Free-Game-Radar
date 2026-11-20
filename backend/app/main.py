import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app import __version__
from app.api import health
from app.core.config import Settings, get_settings
from app.core.logging import configure_logging
from app.db.session import create_db_engine, create_session_factory, ensure_sqlite_directory

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    ensure_sqlite_directory(app.state.settings.database_url)
    yield
    app.state.engine.dispose()


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    configure_logging(settings.log_level)

    app = FastAPI(title="Free Game Radar", version=__version__, lifespan=lifespan)
    app.state.settings = settings
    app.state.engine = create_db_engine(settings.database_url)
    app.state.session_factory = create_session_factory(app.state.engine)
    app.include_router(health.router)

    logger.info("Free Game Radar %s starting (env=%s)", __version__, settings.app_env)
    return app


app = create_app()
