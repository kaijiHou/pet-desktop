"""
Reminder Service — manages the legacy water reminder.
"""

from typing import Callable, Optional

from config import Config


class ReminderService:
    """Manages the tick-driven water reminder."""

    def __init__(self, config: Config):
        self.config = config

        # Callbacks
        self.on_water_reminder: Optional[Callable[[str], None]] = None

        # State
        self._water_timer = 0

    def tick(self, seconds: int = 5):
        """Called periodically by the main loop (every `seconds` seconds)."""
        self._check_water(seconds)

    def reset_water_timer(self):
        self._water_timer = 0

    def _check_water(self, elapsed: int):
        if not self.config.get("water_enabled", True):
            return

        interval_min = self.config.get("water_interval_min", 45)
        interval_sec = interval_min * 60
        self._water_timer += elapsed

        if self._water_timer >= interval_sec:
            self._water_timer = 0
            msg = self._get_water_message()
            if self.on_water_reminder:
                self.on_water_reminder(msg)

    def _get_water_message(self) -> str:
        """Generate a cute water reminder message."""
        messages = [
            "💧 Hayo minum air! Biar tetap segar kayak aku~",
            "🚰 Waktunya minum! Aku sudah isi gelasmu (secara virtual) 🐱",
            "💦 Minum dong! Jangan sampai dehidrasi nanti lemes~",
            "🥤 Clara... minum! Tanganmu sudah pegal ngetik? Istirahat bentar, minum dulu!",
            "🌊 Glug glug glug! Waktunya minum air putih! Aku temenin~",
        ]
        import random
        return random.choice(messages)

    def set_water_interval(self, minutes: int):
        self.config.set("water_interval_min", max(1, minutes))
        self._water_timer = 0

    def enable_water(self, enabled: bool):
        self.config.set("water_enabled", enabled)
        self._water_timer = 0
