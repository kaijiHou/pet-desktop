"""V3.1 wage UI regressions: real month grid, complete stats, tier hints,
expected meal hint and the single-shot background scheduler."""

from datetime import date, datetime

import pytest

from tests.conftest import TEST_TEMP_ROOT

DAY = date(2026, 8, 27)


def _svc(now, privacy=False):
    import shutil
    from wage.service import WageService
    tmp = TEST_TEMP_ROOT / "gui" / "v31_wage_ui"
    shutil.rmtree(tmp, ignore_errors=True)
    tmp.mkdir(parents=True)
    svc = WageService(tmp, now_provider=lambda: now)
    svc.update_settings(enabled=True, monthly_salary="22000", work_start="09:00",
                        lunch_start="12:00", lunch_end="13:00",
                        manual_workday_count=22, privacy_mode=privacy)
    return svc


def test_month_summary_stats_complete(test_temp_root):
    now = datetime(2026, 8, 27, 20, 13)
    svc = _svc(now)
    svc.record_clock_out(now)
    s = svc.month_summary(2026, 8)
    for key in ("workday_count", "recorded_workdays", "overtime_minutes",
                "first_25h_pay", "over_25h_pay", "meal_count", "meal_allowance",
                "monthly_salary", "worked_value_to_date", "confirmed_overtime_pay",
                "confirmed_meal_allowance", "estimated_total"):
        assert key in s, f"month summary missing {key}"
    assert s["recorded_workdays"] == 1
    assert s["meal_count"] == 1
    # worked value = 1 day base (1000) + overtime (163min×15/h=40.75) + meal 30
    from decimal import Decimal
    assert s["worked_value_to_date"] == Decimal("1070.75")


def test_calendar_dialog_is_real_month_grid(qapp, test_temp_root):
    from wage.ui_calendar import WorkCalendarDialog
    svc = _svc(datetime(2026, 8, 27, 12, 0))
    dlg = WorkCalendarDialog(svc)
    try:
        from PyQt5.QtWidgets import QCalendarWidget
        grids = dlg.findChildren(QCalendarWidget)
        assert len(grids) == 1, "calendar dialog must embed a real month grid"
        # Month may change depending on when tests run; just verify grid is present
        text = dlg.summary.toPlainText()
        assert "月度统计" in text
        assert "应出勤" in text
        assert "前25h加班费" in text
        assert "预计本月总收入" in text
        dlg._go_today()
        assert dlg._selected_day == DAY
    finally:
        dlg.close()


def test_calendar_dialog_privacy_hides_amounts(qapp, test_temp_root):
    from wage.ui_calendar import WorkCalendarDialog
    svc = _svc(datetime(2026, 8, 27, 20, 13), privacy=True)
    svc.record_clock_out(datetime(2026, 8, 27, 20, 13))
    dlg = WorkCalendarDialog(svc)
    try:
        body = dlg.summary.toPlainText() + dlg.detail.toPlainText()
        assert "¥" not in body
        assert "已隐藏" in body
    finally:
        dlg.close()


def test_today_wage_shows_tier_hint_during_overtime(qapp, test_temp_root):
    from wage.ui_today import TodayWageWindow
    win = TodayWageWindow(_svc(datetime(2026, 8, 27, 18, 30)), None)
    try:
        win.refresh()
        assert "已加班 1h00m" in win.detail.text()
        assert "15元/h" in win.detail.text()
        assert "距 25元/h 档还差 24h00m 加班" in win.detail.text()
    finally:
        win.close()


def test_today_wage_expected_meal_hint_before_clockout(qapp, test_temp_root):
    from wage.ui_today import TodayWageWindow
    win = TodayWageWindow(_svc(datetime(2026, 8, 27, 20, 1)), None)
    try:
        win.refresh()
        assert "餐补预计 +¥30" in win.detail.text()
        assert win.clock_btn.isEnabled()
    finally:
        win.close()


def test_today_wage_clocked_out_summary(qapp, test_temp_root):
    from wage.ui_today import TodayWageWindow
    svc = _svc(datetime(2026, 8, 27, 20, 13))
    svc.record_clock_out(datetime(2026, 8, 27, 20, 13))
    win = TodayWageWindow(svc, None)
    try:
        win.refresh()
        assert "20:13 下班" in win.amount.text()
        assert "今日加班 2h43m" in win.detail.text()
        assert "本月累计 2h43m" in win.detail.text()
        assert not win.clock_btn.isEnabled()
    finally:
        win.close()


def test_wage_scheduler_is_single_shot_not_polling(pet_window):
    assert pet_window._wage_timer.isSingleShot(), \
        "background wage wake must be a single-shot, not an interval poll"
    pet_window._schedule_next_wage_wake()
    # armed again with a bounded delay (≤1h) instead of a permanent 60s loop
    assert pet_window._wage_timer.isActive()
    assert pet_window._wage_timer.remainingTime() <= 3600 * 1000
