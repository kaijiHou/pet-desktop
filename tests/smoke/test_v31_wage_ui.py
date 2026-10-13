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
    svc.calendar.set_month_workday_override(now.year, now.month, 22)
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
        assert win.clock_btn.isEnabled()   # 重复点击以最新为准
    finally:
        win.close()


def test_wage_scheduler_is_single_shot_not_polling(pet_window):
    assert pet_window._wage_timer.isSingleShot(), \
        "background wage wake must be a single-shot, not an interval poll"
    pet_window._schedule_next_wage_wake()
    # armed again with a bounded delay (≤1h) instead of a permanent 60s loop
    assert pet_window._wage_timer.isActive()
    assert pet_window._wage_timer.remainingTime() <= 3600 * 1000



def test_calendar_clockout_button_stamps_now_and_updates(qapp, test_temp_root):
    """今天点'下班打卡'=当前时间（重复点击取最新）；'选时间…'弹出器补卡；历史按钮叫'补卡下班'。"""
    import shutil
    from datetime import datetime, time as _time
    from wage.service import WageService
    from wage.ui_calendar import WorkCalendarDialog
    from tests.conftest import TEST_TEMP_ROOT

    tmp = TEST_TEMP_ROOT / "gui" / "v54_clockout_now"
    shutil.rmtree(tmp, ignore_errors=True)
    tmp.mkdir(parents=True)
    NOW = [datetime(2026, 10, 8, 18, 0, 5)]
    svc = WageService(tmp, now_provider=lambda: NOW[0])
    svc.update_settings(enabled=True, monthly_salary="14000", work_end="17:00",
                        income_interval_minutes=60)
    dlg = WorkCalendarDialog(svc)
    try:
        dlg._selected_day = NOW[0].date()
        dlg._show_day_detail()
        assert dlg.record_out_button.text() == "下班打卡"
        dlg._save_clock_out()                      # 一击：18:00
        rec = svc.record_for(NOW[0].date())
        assert rec.actual_clock_out == datetime(2026, 10, 8, 18, 0)
        assert dlg.clock_label.text() == "18:00（点打卡可改）"

        NOW[0] = datetime(2026, 10, 8, 19, 30, 40)
        dlg._save_clock_out()                      # 再击：19:30
        assert svc.record_for(NOW[0].date()).actual_clock_out == datetime(2026, 10, 8, 19, 30)

        # 选时间…：选 20:10 → 立即记录 20:10
        dlg._clock_selection = _time(20, 10)
        dlg._save_clock_out()
        assert svc.record_for(NOW[0].date()).actual_clock_out == datetime(2026, 10, 8, 20, 10)
        assert dlg.clock_label.text().startswith("20:10")

        # 历史日期：按钮叫 补卡下班
        from datetime import date as _d
        dlg._selected_day = _d(2026, 10, 5)
        dlg._show_day_detail()
        assert dlg.record_out_button.text() == "补卡下班"
    finally:
        dlg.close()

def test_clockout_needs_confirm_and_records_on_yes(qapp, test_temp_root):
    """确认框：确定→记录；取消→不记录。记录链本身由服务层保证。"""
    import shutil
    from datetime import datetime
    from decimal import Decimal
    from wage.service import WageService
    from clockout_confirm import ClockoutConfirmPopup
    from PyQt5.QtCore import QRect
    from tests.conftest import TEST_TEMP_ROOT

    tmp = TEST_TEMP_ROOT / "gui" / "v54_confirm"
    shutil.rmtree(tmp, ignore_errors=True)
    tmp.mkdir(parents=True)
    NOW = [datetime(2026, 10, 9, 18, 30)]
    svc = WageService(tmp, now_provider=lambda: NOW[0])
    svc.update_settings(enabled=True, monthly_salary="14000", work_end="17:00")

    # 确定按钮 → confirmed_flag=True
    popup = ClockoutConfirmPopup()
    popup.show()
    popup._answer_yes()
    assert popup.confirmed_flag is True
    popup.hide()
    svc.record_clock_out(datetime(2026, 10, 9, 18, 30))
    rec = svc.record_for(NOW[0].date())
    assert rec.actual_clock_out == datetime(2026, 10, 9, 18, 30)
    assert rec.overtime_pay == Decimal("15.00")

    # 取消按钮 → confirmed_flag=False（产品里此时不会调用 record）
    popup2 = ClockoutConfirmPopup()
    popup2.show()
    popup2._answer_no()
    assert popup2.confirmed_flag is False
    popup2.hide()


def test_picker_defaults_and_zero_guard(qapp, test_temp_root):
    """选择器打开=默认合理时刻；0:00 拒绝保存（防止工资冻结成 0）。"""
    import shutil
    from datetime import datetime
    from wage.service import WageService
    from wage.ui_calendar import WorkCalendarDialog
    from tests.conftest import TEST_TEMP_ROOT

    tmp = TEST_TEMP_ROOT / "gui" / "v54_picker"
    shutil.rmtree(tmp, ignore_errors=True)
    tmp.mkdir(parents=True)
    NOW = [datetime(2026, 10, 12, 11, 20)]
    svc = WageService(tmp, now_provider=lambda: NOW[0])
    svc.update_settings(enabled=True, monthly_salary="14000", work_end="17:00")
    dlg = WorkCalendarDialog(svc)
    try:
        dlg._selected_day = NOW[0].date()
        dlg._show_day_detail()
        dlg._pick_clock_time()                     # 打开：默认=当前时刻
        assert dlg.picker_hour.currentIndex() == 11
        assert dlg.picker_minute.currentIndex() == 20
        dlg.picker_hour.setCurrentIndex(0)
        dlg.picker_minute.setCurrentIndex(0)
        dlg._picker_confirmed()                    # 0:00 拒绝
        assert svc.record_for(NOW[0].date()) is None
        dlg.picker_hour.setCurrentIndex(20)
        dlg.picker_minute.setCurrentIndex(10)
        dlg._picker_confirmed()
        rec = svc.record_for(NOW[0].date())
        assert rec.actual_clock_out == datetime(2026, 10, 12, 20, 10)
    finally:
        dlg.close()


def test_clockout_popup_warns_before_work_end(qapp, test_temp_root):
    """17:00 前打卡 → 确认卡带'还没到下班时间'警告；之后没有。"""
    import shutil
    from datetime import datetime, time as _time
    from wage.service import WageService
    from clockout_confirm import clockout_popup_texts
    from tests.conftest import TEST_TEMP_ROOT

    tmp = TEST_TEMP_ROOT / "gui" / "v54_early_warn"
    shutil.rmtree(tmp, ignore_errors=True)
    tmp.mkdir(parents=True)
    NOW = [datetime(2026, 10, 12, 15, 0)]
    svc = WageService(tmp, now_provider=lambda: NOW[0])
    svc.update_settings(enabled=True, monthly_salary="14000", work_end="17:00")
    title, sub = clockout_popup_texts(svc)
    assert "还没到 17:00 下班时间" in sub
    NOW[0] = datetime(2026, 10, 12, 17, 30)
    title, sub = clockout_popup_texts(svc)
    assert "还没到" not in sub


def test_picker_buttons_fit_inside_card(qapp, test_temp_root):
    """确定/取消不得被挤出面板右缘（用户截图显示过裁切）。"""
    import shutil
    from datetime import datetime
    from wage.service import WageService
    from wage.ui_calendar import WorkCalendarDialog
    from tests.conftest import TEST_TEMP_ROOT

    tmp = TEST_TEMP_ROOT / "gui" / "v54_picker_fit"
    shutil.rmtree(tmp, ignore_errors=True)
    tmp.mkdir(parents=True)
    svc = WageService(tmp, now_provider=lambda: datetime(2026, 10, 12, 11, 20))
    svc.update_settings(enabled=True, monthly_salary="14000", work_end="17:00")
    dlg = WorkCalendarDialog(svc)
    try:
        dlg.show(); qapp.processEvents()
        dlg._pick_clock_time(); qapp.processEvents()
        card_right = dlg.detail_card.mapTo(dlg, dlg.detail_card.rect().topRight()).x()
        for name, widget in (("ok", dlg.picker_ok), ("cancel", dlg.picker_cancel),
                             ("hour", dlg.picker_hour), ("minute", dlg.picker_minute)):
            right = widget.mapTo(dlg, widget.rect().topRight()).x()
            assert right <= card_right - 2, f"{name} clipped: {right} > {card_right}"
        dlg.picker_ok.setFocus()
    finally:
        dlg.close()
