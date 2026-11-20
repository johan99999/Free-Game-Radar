from enum import StrEnum


class Platform(StrEnum):
    EPIC = "EPIC"
    STEAM = "STEAM"
    GOG = "GOG"
    UBISOFT = "UBISOFT"
    EA = "EA"
    OTHER = "OTHER"


class PromotionType(StrEnum):
    FREE_TO_KEEP = "FREE_TO_KEEP"
    FREE_WEEKEND = "FREE_WEEKEND"
    FREE_TO_PLAY = "FREE_TO_PLAY"
    DISCOUNT = "DISCOUNT"
    UNKNOWN = "UNKNOWN"


class PromotionStatus(StrEnum):
    UPCOMING = "UPCOMING"
    ACTIVE = "ACTIVE"
    EXPIRED = "EXPIRED"


class ReminderStatus(StrEnum):
    PENDING = "PENDING"
    SENT = "SENT"
    SKIPPED = "SKIPPED"
    FAILED = "FAILED"


class NotificationChannel(StrEnum):
    TELEGRAM = "TELEGRAM"
    FCM = "FCM"


class NotificationType(StrEnum):
    NEW_GIVEAWAY = "NEW_GIVEAWAY"
    GIVEAWAY_REMINDER = "GIVEAWAY_REMINDER"
    PRICE_DROP = "PRICE_DROP"
    TARGET_PRICE = "TARGET_PRICE"
    RECORDED_LOW = "RECORDED_LOW"


class NotificationStatus(StrEnum):
    SENT = "SENT"
    FAILED = "FAILED"


class AlertType(StrEnum):
    DISCOUNT_STARTED = "DISCOUNT_STARTED"
    PRICE_DROPPED = "PRICE_DROPPED"
    RECORDED_LOW = "RECORDED_LOW"
    EXTERNAL_LOW = "EXTERNAL_LOW"
    TARGET_PRICE = "TARGET_PRICE"


class ScanStatus(StrEnum):
    SUCCESS = "SUCCESS"
    PARTIAL = "PARTIAL"
    FAILED = "FAILED"


class DevicePlatform(StrEnum):
    ANDROID = "ANDROID"
    IOS = "IOS"
    WINDOWS = "WINDOWS"
