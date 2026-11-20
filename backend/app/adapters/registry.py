from app.adapters.models import PlatformInfo, SupportStatus
from app.models.enums import Platform, PromotionType

_GP = "gamerpower"
_NO_FIRST_PARTY = "No first-party source found."


def describe_platforms() -> list[PlatformInfo]:
    """Honest, static support table (feeds GET /api/platforms in Phase 7).

    Nothing is SUPPORTED until a first-party source has been tested against real responses.
    """
    return [
        PlatformInfo(
            Platform.EPIC,
            "epic (adapter not written yet)",
            SupportStatus.UNSUPPORTED,
            (PromotionType.FREE_TO_KEEP,),
            "Planned first-party adapter; waiting for a real response to verify the format.",
        ),
        PlatformInfo(
            Platform.STEAM,
            _GP,
            SupportStatus.PARTIAL,
            (PromotionType.FREE_TO_KEEP,),
            "Third-party aggregator; verified 2026-11-20 (1 giveaway returned). "
            "No first-party Steam giveaway feed. End dates may be missing.",
        ),
        PlatformInfo(
            Platform.GOG,
            _GP,
            SupportStatus.PARTIAL,
            (PromotionType.FREE_TO_KEEP,),
            "Third-party aggregator; endpoint answered 2026-11-20 but listed no giveaways, "
            "so item parsing for GOG is untested against real data.",
        ),
        PlatformInfo(
            Platform.UBISOFT,
            _GP,
            SupportStatus.PARTIAL,
            (PromotionType.FREE_TO_KEEP,),
            "Third-party aggregator; endpoint answered 2026-11-20 but listed no giveaways, "
            "so item parsing for Ubisoft is untested against real data.",
        ),
        PlatformInfo(
            Platform.EA,
            _GP,
            SupportStatus.UNSUPPORTED,
            (),
            "GamerPower platform name ('origin') not yet confirmed against a real response.",
        ),
        PlatformInfo(
            Platform.OTHER,
            "rockstar",
            SupportStatus.UNSUPPORTED,
            (),
            f"Rockstar: {_NO_FIRST_PARTY} Not covered by GamerPower's platform list.",
        ),
    ]
