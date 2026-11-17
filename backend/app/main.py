import logging

from fastapi import FastAPI

from app import __version__
from app.api import health
from app.core.config import Settings, get_settings
from app.core.logging import configure_logging

logger = logging.getLogger(__name__)


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    configure_logging(settings.log_level)

    app = FastAPI(title="Free Game Radar", version=__version__)
    app.state.settings = settings
    app.include_router(health.router)

    logger.info("Free Game Radar %s starting (env=%s)", __version__, settings.app_env)
    return app


app = create_app()
