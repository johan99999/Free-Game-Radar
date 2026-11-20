import httpx
import pytest

from app.adapters.http import FetchError, Throttle, get_json

URL = "https://example.test/api"


def client_for(handler) -> httpx.Client:
    return httpx.Client(transport=httpx.MockTransport(handler))


def test_returns_json_on_success() -> None:
    client = client_for(lambda request: httpx.Response(200, json={"ok": True}))
    assert get_json(client, URL) == {"ok": True}


def test_retries_server_errors_then_succeeds() -> None:
    calls: list[int] = []
    sleeps: list[float] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(1)
        return httpx.Response(503) if len(calls) < 3 else httpx.Response(200, json=[1])

    result = get_json(client_for(handler), URL, backoff_base=1.0, sleep=sleeps.append)
    assert result == [1]
    assert len(calls) == 3
    assert sleeps == [1.0, 2.0]  # exponential backoff


def test_gives_up_after_max_attempts() -> None:
    calls: list[int] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(1)
        return httpx.Response(500)

    with pytest.raises(FetchError, match="failed after 3 attempts"):
        get_json(client_for(handler), URL, max_attempts=3, sleep=lambda _: None)
    assert len(calls) == 3


def test_client_errors_are_not_retried() -> None:
    calls: list[int] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(1)
        return httpx.Response(404)

    with pytest.raises(FetchError, match="HTTP 404"):
        get_json(client_for(handler), URL, sleep=lambda _: None)
    assert len(calls) == 1


def test_rate_limit_honours_retry_after() -> None:
    sleeps: list[float] = []
    responses = [httpx.Response(429, headers={"Retry-After": "7"}), httpx.Response(200, json=1)]

    result = get_json(client_for(lambda request: responses.pop(0)), URL, sleep=sleeps.append)
    assert result == 1
    assert sleeps == [7.0]


def test_retry_after_is_capped() -> None:
    sleeps: list[float] = []
    responses = [httpx.Response(429, headers={"Retry-After": "99999"}), httpx.Response(200, json=1)]
    get_json(client_for(lambda request: responses.pop(0)), URL, sleep=sleeps.append)
    assert sleeps == [60.0]


def test_timeouts_are_retried() -> None:
    attempts: list[int] = []

    def handler(request: httpx.Request) -> httpx.Response:
        attempts.append(1)
        if len(attempts) == 1:
            raise httpx.ConnectTimeout("slow", request=request)
        return httpx.Response(200, json="fine")

    assert get_json(client_for(handler), URL, sleep=lambda _: None) == "fine"


def test_invalid_json_is_a_fetch_error() -> None:
    client = client_for(lambda request: httpx.Response(200, text="<html>not json</html>"))
    with pytest.raises(FetchError, match="invalid JSON"):
        get_json(client, URL)


def test_throttle_enforces_minimum_gap() -> None:
    now = [100.0]
    sleeps: list[float] = []
    throttle = Throttle(1.0, clock=lambda: now[0], sleep=sleeps.append)
    throttle.wait()  # first call never waits
    now[0] = 100.25
    throttle.wait()
    assert sleeps == [pytest.approx(0.75)]
