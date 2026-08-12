"""Unit tests for the Phase 5 local reminder service."""

from datetime import datetime, timedelta
import json

import pytest

from reminder_service import ReminderService


@pytest.fixture
def clock():
    current = [datetime(2026, 8, 12, 9, 0, 0)]
    return current, lambda: current[0]


@pytest.fixture
def service(test_temp_root, clock):
    current, now = clock
    storage = test_temp_root / "reminders.json"
    return ReminderService(storage_path=storage, now_provider=now), storage, current


@pytest.mark.unit
class TestReminderCrud:
    def test_starts_empty_when_storage_is_missing(self, service):
        svc, storage, _ = service
        assert svc.list_reminders() == []
        assert not storage.exists()

    def test_add_persists_content_due_time_and_id(self, service):
        svc, storage, current = service
        reminder = svc.add_reminder("Submit report", current[0] + timedelta(hours=2))

        assert reminder.id
        assert reminder.content == "Submit report"
        assert reminder.status == "pending"
        saved = json.loads(storage.read_text(encoding="utf-8"))
        assert saved[0]["id"] == reminder.id
        assert saved[0]["due_at"] == "2026-08-12T11:00:00"

    def test_add_rejects_blank_content(self, service):
        svc, _, current = service
        with pytest.raises(ValueError, match="content"):
            svc.add_reminder("   ", current[0] + timedelta(minutes=5))

    def test_add_rejects_non_datetime_due_time(self, service):
        svc, _, _ = service
        with pytest.raises(TypeError, match="datetime"):
            svc.add_reminder("Bad", "2026-08-12 10:00")

    def test_list_is_sorted_by_due_time(self, service):
        svc, _, current = service
        svc.add_reminder("Later", current[0] + timedelta(hours=2))
        svc.add_reminder("Sooner", current[0] + timedelta(minutes=10))
        assert [r.content for r in svc.list_reminders()] == ["Sooner", "Later"]

    def test_remove_existing_and_missing_reminder(self, service):
        svc, storage, current = service
        reminder = svc.add_reminder("Delete me", current[0] + timedelta(hours=1))
        assert svc.remove_reminder(reminder.id) is True
        assert svc.remove_reminder("missing") is False
        assert json.loads(storage.read_text(encoding="utf-8")) == []


@pytest.mark.unit
class TestReminderPersistence:
    def test_pending_reminders_survive_service_restart(self, service, clock):
        svc, storage, current = service
        created = svc.add_reminder("Persistent", current[0] + timedelta(days=1))

        restarted = ReminderService(storage_path=storage, now_provider=clock[1])
        loaded = restarted.list_reminders()

        assert len(loaded) == 1
        assert loaded[0].id == created.id
        assert loaded[0].content == "Persistent"

    def test_corrupt_storage_falls_back_to_empty_without_crashing(self, service, clock):
        _, storage, _ = service
        storage.write_text("not json", encoding="utf-8")
        restarted = ReminderService(storage_path=storage, now_provider=clock[1])
        assert restarted.list_reminders() == []

    def test_invalid_entries_are_skipped_while_valid_entries_load(self, service, clock):
        _, storage, current = service
        valid_due = (current[0] + timedelta(hours=1)).isoformat(timespec="seconds")
        storage.write_text(json.dumps([
            {"id": "ok", "content": "Valid", "due_at": valid_due,
             "created_at": current[0].isoformat(timespec="seconds"), "status": "pending"},
            {"id": "bad", "content": "Broken", "due_at": "not-a-date"},
        ]), encoding="utf-8")

        restarted = ReminderService(storage_path=storage, now_provider=clock[1])
        assert [r.id for r in restarted.list_reminders()] == ["ok"]


@pytest.mark.unit
class TestReminderDueSemantics:
    def test_next_due_returns_earliest_pending_time(self, service):
        svc, _, current = service
        later = current[0] + timedelta(hours=2)
        sooner = current[0] + timedelta(minutes=5)
        svc.add_reminder("Later", later)
        svc.add_reminder("Sooner", sooner)
        assert svc.next_due_at() == sooner

    def test_check_due_does_nothing_before_due_time(self, service):
        svc, _, current = service
        svc.add_reminder("Not yet", current[0] + timedelta(minutes=1))
        fired = []
        svc.on_reminder_due = fired.append
        assert svc.check_due() == []
        assert fired == []

    def test_check_due_fires_and_completes_all_overdue_reminders_once(self, service):
        svc, storage, current = service
        first = svc.add_reminder("First", current[0] + timedelta(minutes=1))
        second = svc.add_reminder("Second", current[0] + timedelta(minutes=2))
        fired = []
        svc.on_reminder_due = fired.append
        current[0] += timedelta(minutes=3)

        due = svc.check_due()

        assert [r.id for r in due] == [first.id, second.id]
        assert [r.content for r in fired] == ["First", "Second"]
        assert svc.list_reminders() == []
        assert all(item["status"] == "completed" for item in json.loads(storage.read_text()))
        assert svc.check_due() == []
        assert len(fired) == 2

    def test_restart_does_not_refire_completed_reminder(self, service, clock):
        svc, storage, current = service
        svc.add_reminder("Once", current[0])
        svc.check_due()

        restarted = ReminderService(storage_path=storage, now_provider=clock[1])
        fired = []
        restarted.on_reminder_due = fired.append
        assert restarted.check_due() == []
        assert fired == []

    def test_snooze_returns_completed_reminder_to_pending(self, service):
        svc, _, current = service
        reminder = svc.add_reminder("Snooze", current[0])
        svc.check_due()
        snoozed = svc.snooze_reminder(reminder.id, 10)
        assert snoozed.status == "pending"
        assert snoozed.due_at == current[0] + timedelta(minutes=10)
