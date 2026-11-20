from datetime import UTC, datetime


def utcnow() -> datetime:
    """Current time as a timezone-aware UTC datetime. All stored times are UTC."""
    return datetime.now(UTC)
