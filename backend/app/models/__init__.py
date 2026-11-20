"""Importing this package registers every model on Base.metadata."""

from app.models.core import Game, PriceHistory, Promotion, User, UserDevice
from app.models.tracking import (
    GiveawayReminder,
    NotificationLog,
    NotificationPreference,
    PlatformScanLog,
    PriceAlert,
    WishlistItem,
)

__all__ = [
    "Game",
    "GiveawayReminder",
    "NotificationLog",
    "NotificationPreference",
    "PlatformScanLog",
    "PriceAlert",
    "PriceHistory",
    "Promotion",
    "User",
    "UserDevice",
    "WishlistItem",
]
