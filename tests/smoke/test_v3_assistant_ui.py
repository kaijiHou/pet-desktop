"""V3 assistant UI + anchor regressions (task book §16 UI/Anchor lists).

Runs under Qt offscreen with the shared isolated ``pet_window`` fixture.
Wage data is pointed at a per-test temp dir via a fixed now provider, so
no wall clock and no real user wage data is involved.
"""

from datetime import datetime

import pytest
from PyQt5.QtCore import QPoint

from tests.conftest import TEST_TEMP_ROOT


def _iso_wage(privacy=False, now=None):
    """A configured WageService fully isolated from the real data dir."""
    import shutil
    from wage.service import WageService

    tmp = TEST_TEMP_ROOT / "gui" / "v3_assistant"
    shutil.rmtree(tmp, ignore_errors=True)
    tmp.mkdir(parents=True)
    svc = WageService(tmp, now_provider=lambda: now or datetime(2026, 8, 27, 10, 0))
    svc.update_settings(enabled=True, monthly_salary="22000", work_start="09:00",
                        lunch_start="12:00", lunch_end="13:00",
                        manual_workday_count=22, privacy_mode=privacy)
    svc.calendar.set_month_workday_override(svc._now().year, svc._now().month, 22)
    return svc


@pytest.fixture()
def isolated_wage(pet_window):
    original = pet_window.wage
    yield pet_window
    pet_window.wage = original


def _gap(bubble_geo, anchor):
    """Pixel distance between two rects that are expected to be adjacent."""
    if bubble_geo.bottom() < anchor.top():
        return anchor.top() - bubble_geo.bottom() - 1
    if bubble_geo.top() > anchor.bottom():
        return bubble_geo.top() - anchor.bottom() - 1
    if bubble_geo.left() > anchor.right():
        return bubble_geo.left() - anchor.right() - 1
    if bubble_geo.right() < anchor.left():
        return anchor.left() - bubble_geo.right() - 1
    return 0


# ── QuickPanel contents (§16 UI) ─────────────────────────────────────────

@pytest.mark.smoke
@pytest.mark.gui
def test_quick_panel_has_today_wage(pet_window, isolated_wage):
    pet_window.wage = _iso_wage()
    panel = pet_window._quick_panel
    if panel is None:
        from quick_panel import QuickPanel
        panel = QuickPanel(pet_window)
        pet_window._quick_panel = panel
    panel.refresh()
    assert "今日已赚" in panel.wage_amount.text()
    assert "¥" in panel.wage_amount.text()
    assert panel.wage_setup_btn.isHidden()
    panel.close()


@pytest.mark.smoke
@pytest.mark.gui
def test_quick_panel_has_pocket(pet_window, isolated_wage):
    pet_window.wage = _iso_wage()
    panel = pet_window._quick_panel
    if panel is None:
        from quick_panel import QuickPanel
        panel = QuickPanel(pet_window)
        pet_window._quick_panel = panel
    panel.refresh()
    assert panel.pocket_title.text() == "文件口袋"
    assert panel.pocket_count.text().isdigit()
    assert panel.open_pocket_btn.text() == "打开文件口袋"
    panel.close()


@pytest.mark.smoke
@pytest.mark.gui
def test_quick_panel_has_next_reminder(pet_window, isolated_wage):
    pet_window.wage = _iso_wage()
    panel = pet_window._quick_panel
    if panel is None:
        from quick_panel import QuickPanel
        panel = QuickPanel(pet_window)
        pet_window._quick_panel = panel
    from datetime import timedelta
    due = datetime(2026, 8, 27, 15, 30)
    pet_window.reminder.add_reminder("提交材料", due)
    try:
        panel.refresh()
        assert "提交材料" in panel.next_reminder_label.text()
        assert "15:30" in panel.next_reminder_label.text()
    finally:
        for rem in list(pet_window.reminder.list_reminders()):
            pet_window.reminder.remove_reminder(rem.id)
    panel.close()


@pytest.mark.smoke
@pytest.mark.gui
def test_privacy_mode_hides_amount(pet_window, isolated_wage):
    pet_window.wage = _iso_wage(privacy=True)
    panel = pet_window._quick_panel
    if panel is None:
        from quick_panel import QuickPanel
        panel = QuickPanel(pet_window)
        pet_window._quick_panel = panel
    panel.refresh()
    assert "¥" not in panel.wage_amount.text()
    assert "¥" not in panel.wage_detail.text()
    assert "今日进度" in panel.wage_amount.text()
    panel.close()


@pytest.mark.smoke
@pytest.mark.gui
def test_normal_mode_shows_amount(pet_window, isolated_wage):
    pet_window.wage = _iso_wage(privacy=False)
    panel = pet_window._quick_panel
    if panel is None:
        from quick_panel import QuickPanel
        panel = QuickPanel(pet_window)
        pet_window._quick_panel = panel
    panel.refresh()
    assert "¥" in panel.wage_amount.text()
    assert "133.33" in panel.wage_detail.text()
    panel.close()


@pytest.mark.smoke
@pytest.mark.gui
def test_today_wage_temp_reveal_respects_privacy(pet_window, isolated_wage):
    from wage.ui_today import TodayWageWindow

    pet_window.wage = _iso_wage(privacy=True)
    win = TodayWageWindow(pet_window.wage, pet_window)
    try:
        win.refresh()
        assert "¥" not in win.amount.text()
        win._toggle_reveal()
        assert "¥" in win.amount.text()
        win._toggle_reveal()
        assert "¥" not in win.amount.text()
    finally:
        win.close()


# ── anchors (§16 Anchor) ─────────────────────────────────────────────────

@pytest.mark.smoke
@pytest.mark.gui
def test_bubble_gap_near_visible_pet(pet_window):
    pet_window.show()
    pet_window.show_bubble("今天已赚 ¥238.46")
    anchor = pet_window.visible_pet_global_rect()
    gap = _gap(pet_window._bubble_window.geometry(), anchor)
    assert 4 <= gap <= 12, f"bubble gap {gap}px outside 4..10 target (7px nominal)"
    pet_window._bubble_hide()


@pytest.mark.smoke
@pytest.mark.gui
def test_bubble_reanchors_after_scale(pet_window):
    original = pet_window.character.scale
    try:
        pet_window.show()
        pet_window.show_bubble("scale test")
        before_pos = pet_window._bubble_window.pos()
        pet_window._change_scale(0.5)   # _resize_to_character repositions bubble
        anchor = pet_window.visible_pet_global_rect()
        gap = _gap(pet_window._bubble_window.geometry(), anchor)
        assert 4 <= gap <= 12
        assert pet_window._bubble_window.pos() != before_pos
    finally:
        pet_window.character.set_scale(original)
        pet_window._resize_to_character()
        pet_window._bubble_hide()


@pytest.mark.smoke
@pytest.mark.gui
def test_bubble_reanchors_after_move(pet_window):
    pet_window.show()
    pet_window.show_bubble("move test")
    before_pos = pet_window._bubble_window.pos()
    pet_window.move(pet_window.pos() + QPoint(90, 40))
    after_pos = pet_window._bubble_window.pos()
    assert after_pos != before_pos
    anchor = pet_window.visible_pet_global_rect()
    assert 4 <= _gap(pet_window._bubble_window.geometry(), anchor) <= 12
    pet_window._bubble_hide()


@pytest.mark.smoke
@pytest.mark.gui
def test_panel_reanchors_after_pet_move(pet_window, isolated_wage):
    from PyQt5.QtCore import QPoint

    from quick_panel import QuickPanel

    pet_window.wage = _iso_wage()
    pet_window.show()
    panel = QuickPanel(pet_window)
    pet_window._quick_panel = panel
    try:
        panel.showNear(pet_window)
        old_pos = panel.pos()
        pet_window.move(pet_window.pos() + QPoint(70, 25))
        assert panel.isVisible() and panel.pos() != old_pos
        anchor = pet_window.visible_pet_global_rect()
        gap = _gap(panel.geometry(), anchor)
        assert 8 <= gap <= 12, f"panel gap {gap}px outside 8..12 target"
    finally:
        panel.close()
        pet_window._quick_panel = None
