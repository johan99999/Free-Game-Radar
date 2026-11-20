import logging
import time
from collections.abc import Callable
from typing import Any

import httpx

logger = logging.getLogger(__name__)

MAX_RETRY_AFTER_SECONDS = 60.0


class FetchError(Exception):
    """A request failed for good (after any retries)."""


class Throttle:
    """Keeps a minimum gap between requests to the same source (politeness)."""

    def __init__(
        self,
        min_interval: float,
        clock: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self._min_interval = min_interval
        self._clock = clock
        self._sleep = sleep
        self._last: float | None = None

    def wait(self) -> None:
        if self._last is not None:
            remaining = self._last + self._min_interval - self._clock()
            if remaining > 0:
                self._sleep(remaining)
        self._last = self._clock()


def make_client(timeout_seconds: float, user_agent: str) -> httpx.Client:
    return httpx.Client(timeout=timeout_seconds, headers={"User-Agent": user_agent})


def _retry_after(response: httpx.Response) -> float | None:
    value = response.headers.get("Retry-After")
    if value is None:
        return None
    try:
        return min(max(float(value), 0.0), MAX_RETRY_AFTER_SECONDS)
    except ValueError:
        return None  # HTTP-date form is ignored; normal backoff applies


def get_json(
    client: httpx.Client,
    url: str,
    params: dict[str, str] | None = None,
    max_attempts: int = 3,
    backoff_base: float = 1.0,
    sleep: Callable[[float], None] = time.sleep,
) -> Any:
    """GET and decode JSON. Retries timeouts, connection errors, 429 and 5xx with exponential
    backoff (honouring Retry-After); other 4xx errors fail immediately."""
    last_problem = "no attempt made"
    for attempt in range(1, max_attempts + 1):
        delay = backoff_base * 2 ** (attempt - 1)
        try:
            response = client.get(url, params=params)
        except httpx.TransportError as exc:
            last_problem = f"{type(exc).__name__}: {exc}"
        else:
            status = response.status_code
            if status == 429 or status >= 500:
                last_problem = f"HTTP {status}"
                delay = _retry_after(response) or delay
            elif status >= 400:
                raise FetchError(f"HTTP {status} from {url}")
            else:
                try:
                    return response.json()
                except ValueError as exc:
                    raise FetchError(f"invalid JSON from {url}") from exc
        if attempt < max_attempts:
            logger.warning(
                "Request to %s failed (%s), attempt %d/%d, retrying in %.1fs",
                url,
                last_problem,
                attempt,
                max_attempts,
                delay,
            )
            sleep(delay)
    raise FetchError(f"{url} failed after {max_attempts} attempts: {last_problem}")
