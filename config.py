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
    # OpenAI
    "openai_api_key": "",
    "openai_model": "gpt-4o-mini",
    "openai_base_url": "",  # optional custom endpoint

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

    # AI personality
    "ai_name": "Clippy",
    "ai_personality": (
        "Kamu adalah Mochi, seekor kucing chibi imut yang tinggal di desktop "
        "laptop Clara. Kamu membantu Clara dengan ingatan jadwal, minum air, "
        "dan ngobrol santai. Kamu lucu, suka pake bahasa campuran Indonesia-Inggris "
        "(Indoglish), kadang nge-meme, dan suka pakai emoticon. "
        "Jawab dengan hangat dan natural."
    ),
}


class Config:
    def __init__(self):
        self.data = dict(DEFAULT_CONFIG)
        self._load()

    def _load(self):
        if CONFIG_FILE.exists():
            try:
                with open(CONFIG_FILE, "r") as f:
                    loaded = json.load(f)
                    self.data.update(loaded)
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
    def api_key(self) -> str:
        return self.data.get("openai_api_key", "")

    @property
    def has_api_key(self) -> bool:
        return bool(self.data.get("openai_api_key", ""))

    @property
    def api_model(self) -> str:
        return self.data.get("openai_model", "gpt-4o-mini")

    @property
    def pet_name(self) -> str:
        return self.data.get("ai_name", "Mochi")
