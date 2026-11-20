from typing import Protocol

from app.adapters.models import AdapterFetch, SupportStatus


class PlatformAdapter(Protocol):
    """One implementation per data source. Adapters do no database access.

    Flow: raw response -> normalize (inside the adapter) -> validate (runner) -> result.
    Each adapter decides how it collects data; nothing forces the same logic on all of them.
    """

    source: str
    support_status: SupportStatus
    allowed_hosts: frozenset[str]  # hosts a stored URL is allowed to point at

    def fetch_free_games(self) -> AdapterFetch: ...
