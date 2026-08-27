from datetime import date, datetime, time
from decimal import Decimal

from wage.model import WageSettings, WORKDAY, REST, ADJUSTED_WORKDAY
from wage.calendar_service import WorkCalendarService
from wage.calculator import WageCalculator
from wage.service import WageService


def _calculator(tmp_path, **kwargs):
    settings = WageSettings(enabled=True, monthly_salary="22000", work_start="09:00", lunch_start="12:00", lunch_end="13:00", **kwargs)
    cal = WorkCalendarService(tmp_path / "calendar.json", tmp_path / "none.json")
    cal.set_manual_workday_count(22)
    return WageCalculator(settings, cal), cal


def test_daily_salary_from_monthly_salary_and_workdays(test_temp_root):
    calc, _ = _calculator(test_temp_root)
    assert calc.daily_salary(date(2026, 8, 27)) == Decimal("1000.00")


def test_regular_income_before_work_and_morning(test_temp_root):
    calc, _ = _calculator(test_temp_root)
    assert calc.base_earned(datetime(2026, 8, 27, 8, 59)) == Decimal("0.00")
    assert calc.paid_regular_minutes(datetime(2026, 8, 27, 10, 0)) == 60
    assert calc.base_earned(datetime(2026, 8, 27, 10, 0)) == Decimal("133.33")


def test_lunch_does_not_accrue_and_caps_at_1730(test_temp_root):
    calc, _ = _calculator(test_temp_root)
    assert calc.paid_regular_minutes(datetime(2026, 8, 27, 12, 30)) == 180
    assert calc.paid_regular_minutes(datetime(2026, 8, 27, 13, 30)) == 210
    assert calc.base_earned(datetime(2026, 8, 27, 17, 30)) == Decimal("1000.00")
    assert calc.base_earned(datetime(2026, 8, 27, 18, 30)) == Decimal("1000.00")


def test_overtime_tiers_and_cross_boundary(test_temp_root):
    calc, _ = _calculator(test_temp_root)
    assert calc.overtime_pay(25 * 60) == Decimal("375.00")
    assert calc.overtime_pay(120, 24 * 60 + 30) == Decimal("45.00")


def test_meal_allowance_requires_confirmed_clock_out(test_temp_root):
    calc, _ = _calculator(test_temp_root)
    assert calc.meal_allowance(datetime(2026, 8, 27, 19, 59), True) == Decimal("0.00")
    assert calc.meal_allowance(datetime(2026, 8, 27, 20, 0), True) == Decimal("30.00")
    assert calc.meal_allowance(datetime(2026, 8, 27, 20, 1), False) == Decimal("0.00")


def test_calendar_priority_and_restore(test_temp_root):
    holiday = test_temp_root / "holidays.json"
    holiday.write_text('{"2026-08-27": "rest"}', encoding="utf-8")
    cal = WorkCalendarService(test_temp_root / "calendar.json", holiday)
    day = date(2026, 8, 27)
    assert cal.status_for(day) == REST
    cal.set_override(day, ADJUSTED_WORKDAY)
    assert cal.status_for(day) == ADJUSTED_WORKDAY
    cal.restore_auto(day)
    assert cal.status_for(day) == REST


def test_service_record_clock_out_and_corrupt_fallback(test_temp_root):
    current = [datetime(2026, 8, 27, 20, 13)]
    svc = WageService(test_temp_root, now_provider=lambda: current[0])
    svc.update_settings(enabled=True, monthly_salary="22000", work_start="09:00", lunch_start="12:00", lunch_end="13:00", manual_workday_count=22)
    rec = svc.record_clock_out(current[0])
    assert rec.overtime_minutes == 163
    assert rec.meal_allowance == Decimal("30.00")
    svc.settings_path.write_text("not json", encoding="utf-8")
    assert WageService(test_temp_root, now_provider=lambda: current[0]).settings.configured is False
