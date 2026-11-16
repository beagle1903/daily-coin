import json

import pytest
from pydantic import ValidationError

import settings
from constants import (
    DEFAULT_STABLE_COUNT,
    DEFAULT_VARIANCE_PERCENTILE,
    DEFAULT_VOLATILE_COUNT,
    PORTFOLIO_COUNT_MAX,
)
from settings import SettingsModel, SettingsUpdate, load_settings, update_settings


@pytest.fixture
def settings_file(tmp_path, monkeypatch):
    path = tmp_path / "settings.json"
    monkeypatch.setattr(settings, "SETTINGS_FILE", str(path))
    return path


def test_defaults_come_from_constants_when_file_is_missing(settings_file):
    loaded = load_settings()

    assert loaded.stable_count == DEFAULT_STABLE_COUNT
    assert loaded.volatile_count == DEFAULT_VOLATILE_COUNT
    assert loaded.variance_percentile == DEFAULT_VARIANCE_PERCENTILE
    assert not settings_file.exists()


def test_loading_does_not_create_the_file(settings_file):
    load_settings()
    assert not settings_file.exists()


def test_first_update_creates_the_file(settings_file):
    update_settings(SettingsUpdate(stable_count=4))

    assert json.loads(settings_file.read_text()) == {
        "stable_count": 4,
        "volatile_count": DEFAULT_VOLATILE_COUNT,
        "variance_percentile": DEFAULT_VARIANCE_PERCENTILE,
    }


def test_partial_update_keeps_fields_that_are_not_sent(settings_file):
    settings_file.write_text(json.dumps(
        {"stable_count": 2, "volatile_count": 4, "variance_percentile": 45.0}
    ))

    result = update_settings(SettingsUpdate(stable_count=5, volatile_count=10))

    assert result == SettingsModel(stable_count=5, volatile_count=10, variance_percentile=45.0)
    assert load_settings().variance_percentile == 45.0


def test_update_can_change_variance_percentile_alone(settings_file):
    settings_file.write_text(json.dumps({"stable_count": 2, "volatile_count": 4}))

    result = update_settings(SettingsUpdate(variance_percentile=20.0))

    assert result == SettingsModel(stable_count=2, volatile_count=4, variance_percentile=20.0)


@pytest.mark.parametrize("value", [0, -5, 100, 150])
def test_variance_percentile_must_be_between_0_and_100(value):
    with pytest.raises(ValidationError):
        SettingsModel(variance_percentile=value)
    with pytest.raises(ValidationError):
        SettingsUpdate(variance_percentile=value)


@pytest.mark.parametrize("value", [0, -1, PORTFOLIO_COUNT_MAX + 1])
def test_counts_are_bounded(value):
    with pytest.raises(ValidationError):
        SettingsModel(stable_count=value)
    with pytest.raises(ValidationError):
        SettingsUpdate(volatile_count=value)


def test_invalid_stored_value_falls_back_to_its_default_only(settings_file):
    settings_file.write_text(json.dumps(
        {"stable_count": 7, "volatile_count": 9, "variance_percentile": 500}
    ))

    loaded = load_settings()

    assert loaded.stable_count == 7
    assert loaded.volatile_count == 9
    assert loaded.variance_percentile == DEFAULT_VARIANCE_PERCENTILE


@pytest.mark.parametrize("content", ["not json", "[1, 2, 3]", ""])
def test_unreadable_file_falls_back_to_defaults(settings_file, content):
    settings_file.write_text(content)

    assert load_settings() == SettingsModel()
