from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from sqlalchemy import Engine, create_engine, event
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool


def _enable_sqlite_foreign_keys(dbapi_connection: Any, _record: Any) -> None:
    # SQLite ignores foreign keys unless this is switched on for every connection.
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


def create_db_engine(url: str) -> Engine:
    parsed = make_url(url)
    kwargs: dict[str, Any] = {}
    is_sqlite = parsed.get_backend_name() == "sqlite"
    if is_sqlite:
        # The API serves requests from a thread pool.
        kwargs["connect_args"] = {"check_same_thread": False}
        if parsed.database in (None, "", ":memory:"):
            # One shared connection, otherwise every connection gets its own empty database.
            kwargs["poolclass"] = StaticPool
    engine = create_engine(url, **kwargs)
    if is_sqlite:
        event.listen(engine, "connect", _enable_sqlite_foreign_keys)
    return engine


def ensure_sqlite_directory(url: str) -> None:
    """Create the folder for a file-based SQLite database (e.g. ./data)."""
    parsed = make_url(url)
    if parsed.get_backend_name() != "sqlite":
        return
    if parsed.database in (None, "", ":memory:"):
        return
    Path(parsed.database).parent.mkdir(parents=True, exist_ok=True)


def create_session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, expire_on_commit=False)


@contextmanager
def session_scope(factory: sessionmaker[Session]) -> Iterator[Session]:
    """One transaction: commit if the block succeeds, roll back if it raises."""
    session = factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
