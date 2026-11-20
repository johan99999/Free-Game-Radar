from urllib.parse import urlparse

from app.adapters.models import NormalizedPromotion


def _url_problem(name: str, url: str, allowed_hosts: frozenset[str]) -> str | None:
    parsed = urlparse(url)
    if parsed.scheme != "https":
        return f"{name} must use https"
    if parsed.hostname not in allowed_hosts:
        return f"{name} host {parsed.hostname!r} is not allowed"
    return None


def validate_promotion(promo: NormalizedPromotion, allowed_hosts: frozenset[str]) -> list[str]:
    """Returns a list of problems; an empty list means the promotion is valid."""
    problems: list[str] = []
    if not promo.title.strip():
        problems.append("empty title")
    if not promo.platform_game_id.strip():
        problems.append("empty platform_game_id")

    for name, url in (
        ("store_url", promo.store_url),
        ("image_url", promo.image_url),
        ("source_url", promo.source_url),
    ):
        if url is not None and (problem := _url_problem(name, url, allowed_hosts)):
            problems.append(problem)

    for name, moment in (("start_date", promo.start_date), ("end_date", promo.end_date)):
        if moment is not None and moment.utcoffset() is None:
            problems.append(f"{name} is not timezone-aware")
    if (
        promo.start_date is not None
        and promo.end_date is not None
        and promo.end_date <= promo.start_date
    ):
        problems.append("end_date is not after start_date")

    for name, price in (
        ("original_price_minor", promo.original_price_minor),
        ("current_price_minor", promo.current_price_minor),
    ):
        if price is not None and price < 0:
            problems.append(f"{name} is negative")
    if promo.discount_percent is not None and not 0 <= promo.discount_percent <= 100:
        problems.append("discount_percent out of range")
    if promo.currency is not None and len(promo.currency) != 3:
        problems.append("currency must be a 3-letter code")
    if promo.region is not None and len(promo.region) != 2:
        problems.append("region must be a 2-letter code")
    if promo.is_free and promo.current_price_minor not in (None, 0):
        problems.append("free promotion has a non-zero price")
    return problems
