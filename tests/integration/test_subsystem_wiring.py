"""Integration tests: real subsystems wired together (Phase 2).

Everything is local and real: Config persistence, ReminderService logic, and
HTML-source animation metadata.
"""

import json
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
ANIMS_JSON = PROJECT_ROOT / "assets" / "animations.json"


@pytest.mark.integration
class TestReminderConfigPersistence:
    def test_reminder_survives_service_reload_and_fires_once(self, test_temp_root):
        from reminder_service import ReminderService
        from datetime import datetime, timedelta

        now = [datetime(2026, 8, 12, 12, 0, 0)]
        storage = test_temp_root / "reminders.json"
        svc = ReminderService(storage_path=storage, now_provider=lambda: now[0])
        created = svc.add_reminder("Integration", now[0] + timedelta(minutes=5))

        restarted = ReminderService(storage_path=storage, now_provider=lambda: now[0])
        assert restarted.list_reminders()[0].id == created.id

        fired = []
        restarted.on_reminder_due = fired.append
        now[0] += timedelta(minutes=5)
        restarted.check_due()
        restarted.check_due()
        assert [r.content for r in fired] == ["Integration"]


@pytest.mark.integration
class TestAnimationMetadataConsistency:
    def test_native_loader_uses_tracked_json_catalog(self):
        from pet_sprite import ANIMATIONS
        exported = json.loads(ANIMS_JSON.read_text(encoding="utf-8"))
        assert ANIMATIONS == exported
