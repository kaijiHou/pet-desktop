"""V5.4 work-schedule rules: paid time ends at work_end; 17:00-17:30 unpaid."""

from datetime import date, datetime
from decimal import Decimal

from wage.model import WageSettings
from wage.calculator import WageCalculator

DAY = date(2026, 10, 8)


def _calc(**overrides):
    """Calendar-driven workday count (V5.3+ contract): October 2026 = 20 days
    via the service's own month override, so daily = 14000/20 = 700."""
    import tempfile
    from pathlib import Path
    from wage.calendar_service import WorkCalendarService
    tmp = Path(tempfile.mkdtemp())
    cal = WorkCalendarService(tmp / "c.json", tmp / "none.json")
    cal.set_month_workday_override(2026, 10, 20)
    overrides.setdefault("work_end", "17:00")
    settings = WageSettings(enabled=True, monthly_salary="14000", work_start="09:00",
                            lunch_start="12:00", lunch_end="13:00",
                            overtime_start="17:30", **overrides)
    return WageCalculator(settings, cal)


def _dt(h, m):
    return datetime(2026, 10, 8, h, m)


def test_paid_time_ends_at_work_end():
    calc = _calc()
    assert calc.regular_minutes_per_day() == 420       # 09:00-17:00 minus 1h lunch
    assert calc.paid_regular_minutes(_dt(16, 59)) == 419
    assert calc.paid_regular_minutes(_dt(17, 0)) == 420
    assert calc.paid_regular_minutes(_dt(17, 29)) == 420
    assert calc.paid_regular_minutes(_dt(17, 30)) == 420
    assert calc.base_earned(_dt(17, 0)) == Decimal("700.00")
    assert calc.base_earned(_dt(17, 29)) == Decimal("700.00")


def test_unpaid_gap_before_overtime():
    calc = _calc()
    # 17:00-17:30 accrues nothing and is not overtime either.
    assert calc.overtime_minutes(_dt(17, 29)) == 0
    assert calc.overtime_minutes(_dt(17, 30)) == 0
    assert calc.overtime_minutes(_dt(18, 30)) == 60
    base_1730 = calc.base_earned(_dt(17, 30))
    assert base_1730 == calc.base_earned(_dt(17, 0))


def test_custom_work_end_scales_rate():
    calc = _calc(work_end="16:30")
    assert calc.regular_minutes_per_day() == 390       # 09:00-16:30 minus 1h lunch
    assert calc.base_earned(_dt(16, 30)) == Decimal("700.00")
    assert calc.base_earned(_dt(15, 30)) == Decimal("592.31")   # 700×330/390


def test_work_end_roundtrips_through_storage():
    settings = WageSettings(enabled=True, monthly_salary="14000", work_end="17:30")
    restored = WageSettings.from_dict(settings.to_dict())
    assert restored.work_end.hour == 17 and restored.work_end.minute == 30
    legacy = WageSettings.from_dict({"enabled": True, "monthly_salary": "14000"})
    assert legacy.work_end == __import__("datetime").time(17, 0)


def test_base_income_stops_at_clock_out(test_temp_root):
    """打卡后正常工资停在离开时间：11:00 下班，后面不再涨到 17:00。"""
    from datetime import datetime
    from wage.service import WageService
    from wage.calendar_service import WorkCalendarService
    cal = WorkCalendarService(test_temp_root / "cal.json", test_temp_root / "h.json")
    cal.set_month_workday_override(2026, 10, 20)
    svc = WageService(test_temp_root / "wage.json",
                      now_provider=lambda: datetime(2026, 10, 8, 15, 0))
    svc.calendar = cal
    svc.update_settings(enabled=True, monthly_salary="14000", work_end="17:00")
    svc.record_clock_out(datetime(2026, 10, 8, 11, 0))   # 上午就走了
    snap = svc.current_breakdown()
    # 120 分钟计薪（09:00-11:00），之后冻结
    assert snap.paid_regular_minutes == 120
    assert snap.base_earned == _expected(120)
    # 时间继续走（15:00）金额不变
    svc2 = WageService(test_temp_root / "wage.json",
                       now_provider=lambda: datetime(2026, 10, 8, 16, 30))
    svc2.calendar = cal
    svc2.records = svc.records
    snap2 = svc2.current_breakdown()
    assert snap2.base_earned == snap.base_earned


def _expected(paid_minutes):
    from decimal import Decimal
    return (Decimal("14000") / 20 * Decimal(paid_minutes) / 420).quantize(Decimal("0.01"))
