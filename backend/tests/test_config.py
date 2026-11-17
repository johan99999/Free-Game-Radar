import pytest
from pydantic import ValidationError

from app.core.config import Settings


def make(**overrides: object) -> Settings:
    return Settings(_env_file=None, **overrides)  # type: ignore[arg-type]


def test_defaults_match_phase0_plan() -> None:
    s = make()
    assert s.default_timezone == "Asia/Jakarta"
    assert s.steam_region == "ID"
    assert s.steam_currency == "IDR"
    assert s.giveaway_scan_interval_minutes == 30
    assert s.reminder_offsets_minutes == [1440, 360, 60, 30]


def test_reminder_offsets_parsed_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("REMINDER_OFFSETS_MINUTES", "60, 30,1440,60")
    assert make().reminder_offsets_minutes == [1440, 60, 30]


def test_empty_env_value_is_treated_as_unset(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "")
    assert make().telegram_bot_token is None


def test_invalid_timezone_rejected() -> None:
    with pytest.raises(ValidationError):
        make(default_timezone="Mars/Olympus")


def test_non_positive_interval_rejected() -> None:
    with pytest.raises(ValidationError):
        make(giveaway_scan_interval_minutes=0)


def test_negative_reminder_offset_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("REMINDER_OFFSETS_MINUTES", "60,-5")
    with pytest.raises(ValidationError):
        make()


def test_production_requires_real_api_token() -> None:
    with pytest.raises(ValidationError):
        make(app_env="production")
    with pytest.raises(ValidationError):
        make(app_env="production", api_token="change-me")
    assert make(app_env="production", api_token="x" * 32).app_env == "production"


def test_secrets_are_not_leaked_in_repr() -> None:
    assert "supersecret" not in repr(make(telegram_bot_token="supersecret"))
