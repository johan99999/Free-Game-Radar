from collections.abc import Iterator

import pytest
from sqlalchemy import Engine
from sqlalchemy.orm import Session

import app.models  # noqa: F401  (registers all models on Base.metadata)
from app.db.base import Base
from app.db.session import create_db_engine, create_session_factory


@pytest.fixture
def engine() -> Iterator[Engine]:
    engine = create_db_engine("sqlite://")  # in-memory, foreign keys enabled
    Base.metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture
def session(engine: Engine) -> Iterator[Session]:
    with create_session_factory(engine)() as db_session:
        yield db_session
