from app.adapters.models import SupportStatus
from app.adapters.registry import describe_platforms
from app.models.enums import Platform


def test_every_platform_has_an_explanation() -> None:
    assert all(info.notes for info in describe_platforms())


def test_nothing_is_claimed_as_fully_supported_without_first_party_verification() -> None:
    assert all(info.status != SupportStatus.SUPPORTED for info in describe_platforms())


def test_rockstar_is_unsupported() -> None:
    rockstar = next(i for i in describe_platforms() if i.source == "rockstar")
    assert rockstar.platform == Platform.OTHER
    assert rockstar.status == SupportStatus.UNSUPPORTED
