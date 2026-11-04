"""weekly 重复：到期触发一次并顺延恰好 7 天。"""
from datetime import datetime
from pathlib import Path

from reminder_service import ReminderService


def test_weekly_fires_and_advances_seven_days(tmp_path):
    svc = ReminderService(tmp_path / "reminders.json",
                          now_provider=lambda: datetime(2026, 11, 4, 15, 12))
    fired = []
    svc.on_reminder_due = lambda r: fired.append(r.content)
    svc.add_reminder("周会", datetime(2026, 11, 2, 10, 0), recurrence="weekly")
    fired_list = svc.check_due()
    assert [r.content for r in fired_list] == ["周会"]
    assert fired == ["周会"]
    pending = svc.list_reminders()[0]
    assert pending.due_at == datetime(2026, 11, 9, 10, 0)   # 恰好 +7 天
    assert pending.status == "pending"
