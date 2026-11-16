"""
User-adjustable settings shared by the CLI (main.py) and the API (server.py).

They are stored in settings.json in the working directory. The file is not in
version control: it is created on the first save, and until then (or for any value
that is missing or out of range) the defaults from constants.py apply.
"""
import json
import logging
import os

from filelock import FileLock
from pydantic import BaseModel, Field, ValidationError

from constants import (
    DEFAULT_STABLE_COUNT,
    DEFAULT_VARIANCE_PERCENTILE,
    DEFAULT_VOLATILE_COUNT,
    PORTFOLIO_COUNT_MAX,
)

SETTINGS_FILE = "settings.json"


class SettingsModel(BaseModel):
    stable_count: int = Field(default=DEFAULT_STABLE_COUNT, gt=0, le=PORTFOLIO_COUNT_MAX)
    volatile_count: int = Field(default=DEFAULT_VOLATILE_COUNT, gt=0, le=PORTFOLIO_COUNT_MAX)
    # Share of the universe (lowest variance first) that forms the stable bucket
    variance_percentile: float = Field(default=DEFAULT_VARIANCE_PERCENTILE, gt=0, lt=100)


class SettingsUpdate(BaseModel):
    """A partial update: fields that are left out keep their stored value."""
    stable_count: int | None = Field(default=None, gt=0, le=PORTFOLIO_COUNT_MAX)
    volatile_count: int | None = Field(default=None, gt=0, le=PORTFOLIO_COUNT_MAX)
    variance_percentile: float | None = Field(default=None, gt=0, lt=100)


def _lock() -> FileLock:
    return FileLock(f"{SETTINGS_FILE}.lock")


def _read() -> SettingsModel:
    """Read the file without locking. Unusable values fall back to their defaults."""
    if not os.path.exists(SETTINGS_FILE):
        return SettingsModel()
    try:
        with open(SETTINGS_FILE, "r") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        logging.warning("Could not read %s (%s); using default settings", SETTINGS_FILE, e)
        return SettingsModel()
    if not isinstance(data, dict):
        logging.warning("%s does not contain an object; using default settings", SETTINGS_FILE)
        return SettingsModel()
    try:
        return SettingsModel(**data)
    except ValidationError as e:
        invalid = {error["loc"][0] for error in e.errors() if error["loc"]}
        logging.warning(
            "Ignoring invalid value(s) in %s for: %s", SETTINGS_FILE, ", ".join(sorted(map(str, invalid)))
        )
        return SettingsModel(**{key: value for key, value in data.items() if key not in invalid})


def _write(settings: SettingsModel) -> None:
    temp_path = f"{SETTINGS_FILE}.tmp"
    with open(temp_path, "w") as f:
        json.dump(settings.model_dump(), f, indent=2)
    os.replace(temp_path, SETTINGS_FILE)


def load_settings() -> SettingsModel:
    with _lock():
        return _read()


def update_settings(update: SettingsUpdate) -> SettingsModel:
    """Apply a partial update on top of the stored settings and persist the result."""
    changes = update.model_dump(exclude_none=True)
    with _lock():
        merged = SettingsModel(**{**_read().model_dump(), **changes})
        _write(merged)
    return merged
