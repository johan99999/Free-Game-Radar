from fastapi.testclient import TestClient

from app import __version__
from app.core.config import Settings
from app.main import create_app


def make_client(database_url: str = "sqlite://") -> TestClient:
    settings = Settings(_env_file=None, app_env="test", database_url=database_url)
    return TestClient(create_app(settings))


def test_health_returns_ok() -> None:
    response = make_client().get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["app"] == "free-game-radar"
    assert body["version"] == __version__
    assert body["environment"] == "test"
    assert body["database"] == "ok"
    assert body["time_utc"].endswith(("Z", "+00:00"))


def test_health_reports_database_failure_with_503() -> None:
    response = make_client("sqlite:////nonexistent_dir_for_fgr_tests/x.db").get("/health")
    assert response.status_code == 503
    body = response.json()
    assert body["status"] == "degraded"
    assert body["database"] == "error"


def test_unknown_route_is_404() -> None:
    assert make_client().get("/nope").status_code == 404
