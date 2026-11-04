"""QuickPanel 提醒行标注：今天到期高亮、重复类型（每天/每周/每月/单次）、已过期。"""
from datetime import datetime, timedelta

from quick_panel import QuickPanel


class FakeReminder:
    def __init__(self, rid, due, content, recurrence="", interval_minutes=0):
        self.id, self.due_at, self.content = rid, due, content
        self.recurrence, self.interval_minutes = recurrence, interval_minutes


class Pet:
    wage = type("W", (), {"configured": False})()
    destination_service = type("D", (), {"list_favorites": staticmethod(lambda: [])})()

    class pocket:
        list_items = staticmethod(lambda: [])

    reminder = None  # set per test


def _rows(panel):
    rows = [panel.next_reminder_label.text()]
    rows += [panel.remind_items_layout.itemAt(i).widget().text()
             for i in range(panel.remind_items_layout.count())]
    return rows


def test_markers_today_recurrence_and_single(qapp, test_temp_root, monkeypatch):
    import ui_skin
    monkeypatch.setattr(ui_skin, "_active_id", "sakura")
    now = datetime(2026, 11, 4, 16, 0)
    pet = Pet()
    pet.reminder = type("R", (), {"list_reminders": staticmethod(lambda: [
        FakeReminder("1", now.replace(hour=18), "今晚的事", "daily"),
        FakeReminder("2", now + timedelta(days=25), "续费 Codex 会员", "monthly"),
        FakeReminder("3", now + timedelta(days=3), "周会", "weekly"),
    ])})()
    panel = QuickPanel(pet)
    try:
        rows = "\n".join(_rows(panel))
        assert "【今天】" in rows and "· 每天" in rows
        assert "续费 Codex 会员 · 每月" in rows
        assert "周会 · 每周" in rows
    finally:
        panel.close()


def test_single_reminder_marked(qapp, test_temp_root, monkeypatch):
    import ui_skin
    monkeypatch.setattr(ui_skin, "_active_id", "sakura")
    now = datetime(2026, 11, 4, 16, 0)
    pet = Pet()
    pet.reminder = type("R", (), {"list_reminders": staticmethod(lambda: [
        FakeReminder("1", now + timedelta(days=3), "取快递"),
    ])})()
    panel = QuickPanel(pet)
    try:
        assert "取快递 · 单次" in _rows(panel)[0]
    finally:
        panel.close()


def test_overdue_row_marked(qapp, test_temp_root, monkeypatch):
    import ui_skin
    monkeypatch.setattr(ui_skin, "_active_id", "sakura")
    now = datetime(2026, 11, 4, 16, 0)
    pet = Pet()
    pet.reminder = type("R", (), {"list_reminders": staticmethod(lambda: [
        FakeReminder("1", now - timedelta(hours=2), "该打卡了"),
    ])})()
    panel = QuickPanel(pet)
    try:
        assert "【已过期】" in _rows(panel)[0]
    finally:
        panel.close()
