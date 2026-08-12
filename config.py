"""
Configuration manager for Desktop Pet.
Saves/loads user preferences as JSON.
"""

import json
import os
from pathlib import Path


CONFIG_DIR = Path.home() / "desktop-pet"
CONFIG_FILE = CONFIG_DIR / "config.json"
OAUTH_FILE = CONFIG_DIR / "credentials" / "token.json"
CREDENTIALS_FILE = CONFIG_DIR / "credentials" / "credentials.json"


DEFAULT_CONFIG = {
    # Pet settings
    "pet_scale": 3.0,
    "pet_x": -1,  # -1 = center
    "pet_y": -1,

    # Water reminder (minutes)
    "water_interval_min": 30,
    "water_enabled": True,

    # Google Calendar
    "calendar_enabled": True,
    "calendar_check_interval_min": 15,
    "calendar_reminder_minutes_before": 10,

    # Character name
    "pet_name": "Clippy",
}


# Phase 3 migration: old local config files may still contain credentials and
# chat-only settings.  Never load them back into memory or write them again.
LEGACY_AI_KEYS = {
    "openai_api_key",
    "openai_model",
    "openai_base_url",
    "ai_personality",
}
LEGACY_PET_NAME_KEY = "ai_name"


class Config:
    def __init__(self):
        self.data = dict(DEFAULT_CONFIG)
        self._load()

    def _load(self):
        if CONFIG_FILE.exists():
            try:
                with open(CONFIG_FILE, "r") as f:
                    loaded = json.load(f)
                    had_legacy_ai_settings = bool(LEGACY_AI_KEYS.intersection(loaded))
                    had_legacy_pet_name = LEGACY_PET_NAME_KEY in loaded
                    if had_legacy_pet_name and "pet_name" not in loaded:
                        loaded["pet_name"] = loaded[LEGACY_PET_NAME_KEY]
                    loaded.pop(LEGACY_PET_NAME_KEY, None)
                    for key in LEGACY_AI_KEYS:
                        loaded.pop(key, None)
                    self.data.update(loaded)
                    if had_legacy_ai_settings or had_legacy_pet_name:
                        self.save()
            except (json.JSONDecodeError, OSError):
                pass

    def save(self):
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        with open(CONFIG_FILE, "w") as f:
            json.dump(self.data, f, indent=2)

    def get(self, key, default=None):
        return self.data.get(key, default)

    def set(self, key, value):
        self.data[key] = value
        self.save()

    @property
    def pet_name(self) -> str:
        return self.data.get("pet_name", "Mochi")
