from pathlib import Path

from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.migration import MigrationContext
from sqlalchemy import create_engine, inspect

import app.models  # noqa: F401  (registers all models on Base.metadata)
from app.db.base import Base

ROOT = Path(__file__).resolve().parents[2]

EXPECTED_TABLES = {
    "users",
    "user_devices",
    "games",
    "promotions",
    "price_history",
    "wishlist_items",
    "price_alerts",
    "giveaway_reminders",
    "notification_preferences",
    "notification_logs",
    "platform_scan_logs",
}


def alembic_config(url: str) -> Config:
    config = Config(str(ROOT / "alembic.ini"))
    config.set_main_option("script_location", (ROOT / "backend" / "migrations").as_posix())
    config.set_main_option("sqlalchemy.url", url)
    return config


def sqlite_url(tmp_path: Path) -> str:
    return f"sqlite:///{(tmp_path / 'migrate.db').as_posix()}"


def table_names(url: str) -> set[str]:
    engine = create_engine(url)
    try:
        return set(inspect(engine).get_table_names())
    finally:
        engine.dispose()


def test_upgrade_creates_all_tables_and_downgrade_removes_them(tmp_path: Path) -> None:
    url = sqlite_url(tmp_path)
    config = alembic_config(url)

    command.upgrade(config, "head")
    assert table_names(url) == EXPECTED_TABLES | {"alembic_version"}

    command.downgrade(config, "base")
    assert table_names(url) == {"alembic_version"}


def test_migration_matches_models(tmp_path: Path) -> None:
    """If a model changes without a new migration, this fails."""
    url = sqlite_url(tmp_path)
    command.upgrade(alembic_config(url), "head")

    engine = create_engine(url)
    try:
        with engine.connect() as connection:
            context = MigrationContext.configure(connection, opts={"compare_type": False})
            differences = compare_metadata(context, Base.metadata)
    finally:
        engine.dispose()

    unexpected = [
        diff
        for diff in differences
        if not (
            isinstance(diff, tuple)
            and diff[0] == "remove_table"
            and diff[1].name == "alembic_version"
        )
    ]
    assert unexpected == []
