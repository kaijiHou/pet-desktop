"""V3 wage rules — task-book named regression tests (§15/§16).

Every time-dependent test uses a fixed now_provider; no wall-clock reads.
Amounts are Decimal and asserted to the cent.
"""

from datetime import date, datetime
from decimal import Decimal

from wage.model import WageSettings, WORKDAY, REST, ADJUSTED_WORKDAY, LEAVE, money
from wage.calendar_service import WorkCalendarService
from wage.calculator import WageCalculator
from wage.service import WageService

DAY = date(2026, 8, 27)  # a Thursday
NOON_NOW = [datetime(2026, 8, 27, 12, 0)]


def _calc(tmp_path, **kwargs):
    settings = WageSettings(enabled=True, monthly_salary="22000", work_start="09:00",
                            lunch_start="12:00", lunch_end="13:00",
                            manual_workday_count=22, **kwargs)
    cal = WorkCalendarService(tmp_path / "calendar.json", tmp_path / "none.json")
    cal.set_month_workday_override(2026, 8, 22)
    return WageCalculator(settings, cal), cal


def _dt(h, m):
    return datetime(2026, 8, 27, h, m)


# ── base income ──────────────────────────────────────────────────────────

def test_regular_income_after_lunch(test_temp_root):
    calc, _ = _calc(test_temp_root)
    # 13:30 = 4.5h elapsed minus 1h lunch = 3.5h (210 min) of 7.5h regular day.
    assert calc.paid_regular_minutes(_dt(13, 30)) == 210
    assert calc.base_earned(_dt(13, 30)) == Decimal("466.67")


def test_rest_day_base_income_zero(test_temp_root):
    calc, cal = _calc(test_temp_root)
    cal.set_override(DAY, REST)
    assert calc.base_earned(_dt(15, 0), REST) == Decimal("0.00")


def test_adjusted_workday_counts_as_workday(test_temp_root):
    calc, cal = _calc(test_temp_root)
    saturday = date(2026, 8, 29)
    cal.set_override(saturday, ADJUSTED_WORKDAY)
    assert cal.status_for(saturday) == ADJUSTED_WORKDAY
    assert calc.base_earned(datetime(2026, 8, 29, 17, 30)) == Decimal("1000.00")


def test_manual_calendar_override_wins(test_temp_root):
    calc, cal = _calc(test_temp_root)
    cal.set_override(DAY, LEAVE)
    assert cal.status_for(DAY) == LEAVE
    assert calc.base_earned(_dt(15, 0)) == Decimal("0.00")


def test_manual_workday_count_override(test_temp_root):
    calc, cal = _calc(test_temp_root)
    # An explicit per-month override is the only supported manual count.
    assert cal.workday_count(2026, 8) == 22
    calc.settings.manual_workday_count = 20
    assert calc.salary_workday_count(DAY) == 22
    assert calc.daily_salary(DAY) == Decimal("1000.00")


def test_missing_wage_settings_unconfigured(test_temp_root):
    svc = WageService(test_temp_root, now_provider=lambda: NOON_NOW[0])
    assert svc.configured is False
    snap = svc.current_breakdown()
    assert snap.configured is False
    assert snap.total_earned == Decimal("0.00")


def test_decimal_rounding_to_cent(test_temp_root):
    calc, _ = _calc(test_temp_root)
    # 22000/22 = 1000/day; 7.5h day → 133.33... per hour must quantize HALF_UP.
    assert money("133.335") == Decimal("133.34")
    assert calc.base_earned(_dt(10, 0)) == Decimal("133.33")
    assert str(calc.base_earned(_dt(10, 0))).split(".")[1].__len__() == 2


def test_corrupt_wage_data_safe_fallback(test_temp_root):
    current = [NOON_NOW[0]]
    svc = WageService(test_temp_root, now_provider=lambda: current[0])
    svc.update_settings(enabled=True, monthly_salary="22000", manual_workday_count=22)
    (test_temp_root / "wage_records.json").write_text("{broken", encoding="utf-8")
    (test_temp_root / "work_calendar.json").write_text(str([1, 2, 3]), encoding="utf-8")
    (test_temp_root / "wage_prompts.json").write_text("null", encoding="utf-8")
    reloaded = WageService(test_temp_root, now_provider=lambda: current[0])
    assert reloaded.records == {}
    assert reloaded.configured is True
    # Corrupt side files must not crash or corrupt the math: 12:00 noon is
    # 180 paid minutes of 450 using August's automatic 21-day calendar.
    assert reloaded.current_breakdown().total_earned == Decimal("419.05")


# ── overtime ─────────────────────────────────────────────────────────────

def test_overtime_zero_at_1730(test_temp_root):
    calc, _ = _calc(test_temp_root)
    assert calc.overtime_minutes(_dt(17, 30)) == 0
    assert calc.overtime_pay(0) == Decimal("0.00")


def test_overtime_first_25_hours_rate_15(test_temp_root):
    calc, _ = _calc(test_temp_root)
    assert calc.overtime_pay(25 * 60, 0) == Decimal("375.00")
    assert calc.overtime_pay(60, 0) == Decimal("15.00")


def test_overtime_above_25_hours_rate_25(test_temp_root):
    calc, _ = _calc(test_temp_root)
    assert calc.overtime_pay(26 * 60, 0) == Decimal("400.00")
    assert calc.overtime_pay(60, 25 * 60) == Decimal("25.00")


def test_overtime_crosses_25_hour_boundary_precisely(test_temp_root):
    calc, _ = _calc(test_temp_root)
    # Prior month-to-date 24h30m; today 17:30→19:30 adds 2h:
    # 0.5h × 15 + 1.5h × 25 = 7.5 + 37.5 = 45.00 — never one flat tier.
    assert calc.overtime_pay(120, 24 * 60 + 30) == Decimal("45.00")


# ── meal allowance ───────────────────────────────────────────────────────

def test_meal_allowance_before_2000_zero(test_temp_root):
    calc, _ = _calc(test_temp_root)
    assert calc.meal_allowance(_dt(19, 59), confirmed=True) == Decimal("0.00")


def test_meal_allowance_at_2000(test_temp_root):
    calc, _ = _calc(test_temp_root)
    assert calc.meal_allowance(_dt(20, 0), confirmed=True) == Decimal("30.00")


def test_meal_allowance_after_2000(test_temp_root):
    calc, _ = _calc(test_temp_root)
    assert calc.meal_allowance(_dt(21, 15), confirmed=True) == Decimal("30.00")


def test_meal_allowance_requires_clock_out_confirmation(test_temp_root):
    calc, _ = _calc(test_temp_root)
    assert calc.meal_allowance(_dt(20, 1), confirmed=False) == Decimal("0.00")
    assert calc.meal_allowance(None, confirmed=True) == Decimal("0.00")


# ── calendar (§16) ───────────────────────────────────────────────────────

def test_month_workday_count(test_temp_root):
    cal = WorkCalendarService(test_temp_root / "c.json", test_temp_root / "h.json")
    # Aug 2026: 31 days, weekends 1/2/8/9/15/16/22/23/29/30 → 21 workdays.
    assert cal.workday_count(2026, 8) == 21


def test_weekend_default_rest(test_temp_root):
    cal = WorkCalendarService(test_temp_root / "c.json", test_temp_root / "h.json")
    assert cal.status_for(date(2026, 8, 29)) == REST  # Saturday


def test_weekday_default_work(test_temp_root):
    cal = WorkCalendarService(test_temp_root / "c.json", test_temp_root / "h.json")
    assert cal.status_for(DAY) == WORKDAY  # Thursday


def test_holiday_override(test_temp_root):
    holiday = test_temp_root / "h.json"
    holiday.write_text('{"2026-08-27": "rest"}', encoding="utf-8")
    cal = WorkCalendarService(test_temp_root / "c.json", holiday)
    assert cal.status_for(DAY) == REST


def test_record_clock_out(test_temp_root):
    current = [datetime(2026, 8, 27, 20, 13)]
    svc = WageService(test_temp_root, now_provider=lambda: current[0])
    svc.update_settings(enabled=True, monthly_salary="22000", manual_workday_count=22)
    rec = svc.record_clock_out(current[0])
    assert rec.actual_clock_out == current[0]
    assert rec.overtime_minutes == 163
    assert rec.overtime_pay == Decimal("40.75")  # 163min × 15/h
    assert rec.meal_allowance == Decimal("30.00")


def test_edit_clock_out(test_temp_root):
    current = [datetime(2026, 8, 27, 21, 15)]
    svc = WageService(test_temp_root, now_provider=lambda: current[0])
    svc.update_settings(enabled=True, monthly_salary="22000", manual_workday_count=22)
    svc.record_clock_out(datetime(2026, 8, 27, 20, 13))
    edited = svc.edit_clock_out(DAY, datetime(2026, 8, 27, 19, 0))
    assert edited.overtime_minutes == 90
    assert edited.overtime_pay == Decimal("22.50")
    assert edited.meal_allowance == Decimal("0.00")


def test_month_overtime_sum(test_temp_root):
    current = [datetime(2026, 8, 27, 12, 0)]
    svc = WageService(test_temp_root, now_provider=lambda: current[0])
    svc.update_settings(enabled=True, monthly_salary="22000", manual_workday_count=22)
    svc.record_clock_out(datetime(2026, 8, 25, 19, 0))   # 90 min
    svc.record_clock_out(datetime(2026, 8, 26, 20, 0))   # 150 min
    summary = svc.month_summary(2026, 8)
    assert summary["overtime_minutes"] == 240
    assert summary["first_25h_pay"] == Decimal("60.00")


def test_meal_allowance_sum(test_temp_root):
    current = [datetime(2026, 8, 27, 12, 0)]
    svc = WageService(test_temp_root, now_provider=lambda: current[0])
    svc.update_settings(enabled=True, monthly_salary="22000", manual_workday_count=22)
    svc.record_clock_out(datetime(2026, 8, 25, 19, 0))   # no meal
    svc.record_clock_out(datetime(2026, 8, 26, 20, 0))   # +30
    svc.record_clock_out(datetime(2026, 8, 27, 21, 0))   # +30
    summary = svc.month_summary(2026, 8)
    assert summary["meal_allowance"] == Decimal("60.00")
    # overtime 90+150+210=450min → all in first tier: 450/60×15 = 112.50
    assert summary["first_25h_pay"] == Decimal("112.50")
    # estimated = salary + first-tier pay + meals
    assert summary["estimated_total"] == Decimal("22000") + Decimal("112.50") + Decimal("60.00")
