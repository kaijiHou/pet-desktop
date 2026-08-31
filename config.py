"""
Configuration manager for Desktop Pet.
Saves/loads user preferences as JSON.
"""

import json
from paths import CONFIG_DIR

CONFIG_FILE = CONFIG_DIR / "config.json"


DEFAULT_CONFIG = {
    # Pet settings
    "pet_scale": 3.0,
    "pet_x": -1,  # -1 = default position
    "pet_y": -1,

    # Character (V2): "single" = one transparent PNG (default buddy when unset),
    # "sheet" = legacy sprite sheet mode.
    "character_mode": "single",
    "character_image": "",      # file name inside assets/, "" = built-in buddy

    # Behavior (V2)
    "always_on_top": True,
    "wheel_zoom_enabled": True,          # plain wheel zooms; Ctrl+wheel always zooms
    "idle_animations_enabled": False, # sheet-mode variety clips; single mode stays still
    "file_event_animations_enabled": True,
    "show_pet_name": False,           # permanent name label under the pet: off
    "pocket_badge_enabled": True,

    # Reminders (V2)
    "reminder_sound_enabled": True,
    "reminder_bubble_enabled": True,

    # First-run onboarding (shown once, then cleared)
    "show_welcome": True,

    # Character name (tooltip / optional label)
    "pet_name": "小助手",
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
LEGACY_CALENDAR_KEYS = {
    "calendar_enabled",
    "calendar_check_interval_min",
    "calendar_reminder_minutes_before",
}
LEGACY_WATER_KEYS = {"water_interval_min", "water_enabled"}


class Config:
    def __init__(self):
        self.data = dict(DEFAULT_CONFIG)
        self._load()
        self._migrate_v31_scale_defaults()

    def _migrate_v31_scale_defaults(self):
        """One-shot: re-enable plain-wheel zoom on V2-era machines.

        V2 builds saved ``wheel_zoom_enabled: false`` (the default of that
        era's settings dialog), which silently disabled plain-wheel zoom on
        every machine that ever opened Settings. V3.1 restores wheel zoom as
        the default interaction; the marker below guarantees this migration
        runs exactly once, afterwards the Settings checkbox governs.
        """
        if self.data.get("v31_wheel_migration_done"):
            return
        self.data["wheel_zoom_enabled"] = True
        self.data["v31_wheel_migration_done"] = True
        self.save()

    def _load(self):
        if CONFIG_FILE.exists():
            try:
                with open(CONFIG_FILE, "r") as f:
                    loaded = json.load(f)
                    had_legacy_ai_settings = bool(LEGACY_AI_KEYS.intersection(loaded))
                    had_legacy_calendar_settings = bool(LEGACY_CALENDAR_KEYS.intersection(loaded))
                    had_legacy_water_settings = bool(LEGACY_WATER_KEYS.intersection(loaded))
                    had_legacy_pet_name = LEGACY_PET_NAME_KEY in loaded
                    if had_legacy_pet_name and "pet_name" not in loaded:
                        loaded["pet_name"] = loaded[LEGACY_PET_NAME_KEY]
                    loaded.pop(LEGACY_PET_NAME_KEY, None)
                    for key in LEGACY_AI_KEYS:
                        loaded.pop(key, None)
                    for key in LEGACY_CALENDAR_KEYS:
                        loaded.pop(key, None)
                    for key in LEGACY_WATER_KEYS:
                        loaded.pop(key, None)
                    self.data.update(loaded)
                    if (had_legacy_ai_settings or had_legacy_calendar_settings
                            or had_legacy_water_settings or had_legacy_pet_name):
                        self.save()
            except (json.JSONDecodeError, OSError):
                pass

    def save(self):
        for key in LEGACY_AI_KEYS | LEGACY_CALENDAR_KEYS | LEGACY_WATER_KEYS | {LEGACY_PET_NAME_KEY}:
            self.data.pop(key, None)
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        with open(CONFIG_FILE, "w") as f:
            json.dump(self.data, f, indent=2)

    def get(self, key, default=None):
        return self.data.get(key, default)

    def set(self, key, value):
        if key in LEGACY_AI_KEYS | LEGACY_CALENDAR_KEYS | LEGACY_WATER_KEYS | {LEGACY_PET_NAME_KEY}:
            return
        self.data[key] = value
        self.save()

    @property
    def pet_name(self) -> str:
        return self.data.get("pet_name", "小助手")
