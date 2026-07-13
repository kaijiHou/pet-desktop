"""
Reminder Service — manages water drinking and meeting reminders.
"""

import datetime
from typing import Callable, Optional

from config import Config
from calendar_service import CalendarService


class ReminderService:
    """Manages timed reminders (water, meetings)."""

    def __init__(self, config: Config, calendar: Optional[CalendarService] = None):
        self.config = config
        self.calendar = calendar

        # Callbacks
        self.on_water_reminder: Optional[Callable[[str], None]] = None
        self.on_meeting_reminder: Optional[Callable[[str], None]] = None

        # State
        self._water_timer = 0
        self._calendar_timer = 0
        self._last_checked_events = []
        self._notified_event_ids = set()

    def tick(self, seconds: int = 5):
        """Called periodically by the main loop (every `seconds` seconds)."""
        self._check_water(seconds)
        self._check_calendar(seconds)

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

    def _check_calendar(self, elapsed: int):
        if not self.config.get("calendar_enabled", False) or not self.calendar:
            return

        check_interval = self.config.get("calendar_check_interval_min", 15)
        self._calendar_timer += elapsed

        if self._calendar_timer >= check_interval * 60:
            self._calendar_timer = 0
            self._check_upcoming_meetings()

    def _check_upcoming_meetings(self):
        try:
            minutes_before = self.config.get("calendar_reminder_minutes_before", 10)
            events = self.calendar.check_events_to_remind(minutes_before)
            for event in events:
                event_id = event.get("id", "")
                if event_id and event_id not in self._notified_event_ids:
                    self._notified_event_ids.add(event_id)
                    summary = event.get("summary", "Meeting")
                    msg = f"📅 **{summary}** akan mulai dalam beberapa menit! Siap-siap ya~"
                    if self.on_meeting_reminder:
                        self.on_meeting_reminder(msg)
        except Exception:
            pass

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

    def enable_calendar(self, enabled: bool):
        self.config.set("calendar_enabled", enabled)
