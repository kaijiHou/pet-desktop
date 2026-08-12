"""Characterization tests for reminder_service.ReminderService (Phase 2).

ReminderService is tick-driven (PetWindow calls tick(5) from a QTimer), so
time is injected directly via tick(elapsed) — no sleeps, no event loops, and
no production refactoring needed. Phase 5 will rewrite Reminder; these tests
pin the OLD behavior first so regressions during removal are detectable.

The only mocked collaborator is a fake CalendarService (external Google API);
Config is the real class with isolated storage.
"""

import pytest

import config as config_mod
from reminder_service import ReminderService


class FakeCalendar:
    """Stands in for CalendarService — the only external (network) boundary."""

    def __init__(self, events=None, raise_exc=None):
        self.events = events or []
        self.raise_exc = raise_exc
        self.calls = 0
        self.last_minutes_before = None

    def check_events_to_remind(self, minutes_before):
        self.calls += 1
        self.last_minutes_before = minutes_before
        if self.raise_exc:
            raise self.raise_exc
        return self.events


@pytest.fixture
def water_cfg(isolated_config):
    return isolated_config


# ── Init / defaults ────────────────────────────────────────────────────────

@pytest.mark.unit
class TestReminderInit:
    def test_water_timer_starts_at_zero(self, water_cfg):
        svc = ReminderService(water_cfg)
        assert svc._water_timer == 0

    def test_callbacks_start_unset(self, water_cfg):
        svc = ReminderService(water_cfg)
        assert svc.on_water_reminder is None
        assert svc.on_meeting_reminder is None

    def test_effective_water_interval_is_config_default_30min(self, water_cfg):
        # Characterized via _check_water threshold: DEFAULT_CONFIG carries
        # water_interval_min=30 (config.py), so the trigger point is 1800s.
        assert water_cfg.get("water_interval_min") == 30


# ── Water reminder trigger condition ──────────────────────────────────────

@pytest.mark.unit
class TestWaterTrigger:
    def test_no_trigger_before_interval(self, water_cfg):
        svc = ReminderService(water_cfg)
        fired = []
        svc.on_water_reminder = fired.append

        svc.tick(30 * 60 - 1)  # one second short of 30 min

        assert fired == []

    def test_triggers_exactly_at_interval(self, water_cfg):
        svc = ReminderService(water_cfg)
        fired = []
        svc.on_water_reminder = fired.append

        svc.tick(30 * 60)

        assert len(fired) == 1
        assert isinstance(fired[0], str) and fired[0]  # non-empty message

    def test_trigger_resets_timer_so_next_fire_needs_full_interval(self, water_cfg):
        svc = ReminderService(water_cfg)
        fired = []
        svc.on_water_reminder = fired.append

        svc.tick(30 * 60)
        assert len(fired) == 1
        assert svc._water_timer == 0  # reset after firing

        svc.tick(30 * 60 - 1)
        assert len(fired) == 1  # not enough elapsed since reset

        svc.tick(1)
        assert len(fired) == 2

    def test_disabled_water_never_fires(self, water_cfg):
        water_cfg.set("water_enabled", False)
        svc = ReminderService(water_cfg)
        fired = []
        svc.on_water_reminder = fired.append

        svc.tick(30 * 60)

        assert fired == []

    def test_reset_water_timer_restarts_countdown(self, water_cfg):
        svc = ReminderService(water_cfg)
        svc.tick(30 * 60 - 5)  # nearly there
        svc.reset_water_timer()

        fired = []
        svc.on_water_reminder = fired.append
        svc.tick(30 * 60 - 5)

        assert fired == []  # countdown restarted from zero

    def test_set_water_interval_clamps_to_minimum_one_minute(self, water_cfg):
        svc = ReminderService(water_cfg)
        svc.set_water_interval(0)
        assert water_cfg.get("water_interval_min") == 1

    def test_set_water_interval_resets_pending_timer(self, water_cfg):
        svc = ReminderService(water_cfg)
        svc.tick(100)
        svc.set_water_interval(5)
        assert svc._water_timer == 0

    def test_enable_water_writes_config_and_resets(self, water_cfg):
        svc = ReminderService(water_cfg)
        svc.tick(100)
        svc.enable_water(False)
        assert water_cfg.get("water_enabled") is False
        assert svc._water_timer == 0


# ── Calendar reminder branch ───────────────────────────────────────────────

@pytest.mark.unit
class TestCalendarReminder:
    def test_no_calendar_object_means_no_check(self, water_cfg):
        svc = ReminderService(water_cfg, calendar=None)
        water_cfg.set("calendar_enabled", True)
        # Must not raise despite calendar being None.
        svc.tick(15 * 60)

    def test_disabled_calendar_never_checks(self, water_cfg):
        cal = FakeCalendar(events=[{"id": "e1", "summary": "Standup"}])
        svc = ReminderService(water_cfg, calendar=cal)
        water_cfg.set("calendar_enabled", False)

        svc.tick(15 * 60)

        assert cal.calls == 0

    def test_check_runs_at_default_15min_interval(self, water_cfg):
        cal = FakeCalendar(events=[])
        svc = ReminderService(water_cfg, calendar=cal)
        water_cfg.set("calendar_enabled", True)

        svc.tick(15 * 60 - 1)
        assert cal.calls == 0
        svc.tick(1)
        assert cal.calls == 1

    def test_meeting_reminder_fires_with_formatted_message(self, water_cfg):
        cal = FakeCalendar(events=[{"id": "e1", "summary": "Standup"}])
        svc = ReminderService(water_cfg, calendar=cal)
        water_cfg.set("calendar_enabled", True)
        fired = []
        svc.on_meeting_reminder = fired.append

        svc.tick(15 * 60)

        assert cal.last_minutes_before == 10  # DEFAULT minutes_before
        assert len(fired) == 1
        assert "Standup" in fired[0]
        assert fired[0].startswith("📅")

    def test_same_event_id_notified_only_once(self, water_cfg):
        cal = FakeCalendar(events=[{"id": "e1", "summary": "Standup"}])
        svc = ReminderService(water_cfg, calendar=cal)
        water_cfg.set("calendar_enabled", True)
        fired = []
        svc.on_meeting_reminder = fired.append

        svc.tick(15 * 60)
        svc.tick(15 * 60)  # second check cycle, same event id

        assert len(fired) == 1

    def test_calendar_errors_are_swallowed(self, water_cfg):
        # Upstream wraps meeting checks in try/except Exception: pass.
        # Characterized — a flaky calendar must not crash the pet loop.
        cal = FakeCalendar(raise_exc=RuntimeError("api down"))
        svc = ReminderService(water_cfg, calendar=cal)
        water_cfg.set("calendar_enabled", True)

        svc.tick(15 * 60)  # must not raise

        assert cal.calls == 1
