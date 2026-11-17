from fastapi.testclient import TestClient

from app import __version__
from app.core.config import Settings
from app.main import create_app


def make_client() -> TestClient:
    return TestClient(create_app(Settings(_env_file=None, app_env="test")))


def test_health_returns_ok() -> None:
    response = make_client().get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["app"] == "free-game-radar"
    assert body["version"] == __version__
    assert body["environment"] == "test"
    assert body["time_utc"].endswith(("Z", "+00:00"))


def test_unknown_route_is_404() -> None:
    assert make_client().get("/nope").status_code == 404
