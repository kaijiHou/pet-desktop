"""V3.1 wage fixes: historical backfill tiers and missing clock-out flow."""

from datetime import date, datetime
from decimal import Decimal

from wage.service import WageService

DAY1 = date(2026, 8, 25)   # Tuesday
DAY3 = date(2026, 8, 27)   # Thursday
NOW = [datetime(2026, 8, 31, 12, 0)]


def _svc(tmp_path):
    svc = WageService(tmp_path, now_provider=lambda: NOW[0])
    svc.update_settings(enabled=True, monthly_salary="22000", work_start="09:00",
                        lunch_start="12:00", lunch_end="13:00", manual_workday_count=22)
    return svc


# ── historical backfill tier correctness ─────────────────────────────────

def test_historical_clockout_uses_only_prior_dates(test_temp_root):
    svc = _svc(test_temp_root)
    # A LATER day (the 28th) already has 25h+ of overtime on file.
    later = date(2026, 8, 28)
    svc.record_clock_out(datetime(2026, 8, 28, 18, 30), later)   # 60 min
    # Backfill the 27th: prior must be 0 — the 28th lies in its FUTURE and
    # must not be treated as already-accumulated overtime.
    rec = svc.record_clock_out(datetime(2026, 8, 27, 18, 30), DAY3)
    assert rec.overtime_minutes == 60
    assert rec.overtime_pay == Decimal("15.00")


def test_edit_earlier_day_recalculates_later_tier(test_temp_root):
    svc = _svc(test_temp_root)
    cal = svc.calendar
    from wage.model import ADJUSTED_WORKDAY
    days = [date(2026, 8, d) for d in (24, 25, 26, 27)]
    for d in days:
        if cal.status_for(d) not in {"workday"}:
            cal.set_override(d, ADJUSTED_WORKDAY)
        svc.record_clock_out(datetime(2026, 8, d.day, 23, 50), d)   # 385 min each
    last = date(2026, 8, 28)
    rec = svc.record_clock_out(datetime(2026, 8, 28, 19, 0), last)  # 90 min
    # prior = 4×385 = 1540 > 1500 → whole 90 min in the 25元 tier.
    assert rec.overtime_pay == Decimal("37.50")
    # Edit the EARLIEST day down to 90 min → prior 1245, tier1 has 255 left,
    # so the later day's 90 min re-tier into 15元/h.
    svc.edit_clock_out(days[0], datetime(2026, 8, 24, 19, 0))
    after = svc.record_for(last)
    assert after.overtime_pay == Decimal("22.50")


def test_month_records_recalculate_in_date_order(test_temp_root):
    svc = _svc(test_temp_root)
    # Insert out of order on purpose.
    svc.record_clock_out(datetime(2026, 8, 27, 19, 0), DAY3)          # 90 min
    svc.record_clock_out(datetime(2026, 8, 26, 20, 0), date(2026, 8, 26))  # 150 min
    svc.record_clock_out(datetime(2026, 8, 25, 23, 0), DAY1)          # 330 min
    svc.recalculate_month_records(2026, 8)
    r1 = svc.record_for(DAY1)
    r2 = svc.record_for(date(2026, 8, 26))
    r3 = svc.record_for(DAY3)
    assert r1.overtime_pay == Decimal("82.50")   # prior 0   → 330×15/60
    assert r2.overtime_pay == Decimal("37.50")   # prior 330 → 150×15/60
    assert r3.overtime_pay == Decimal("22.50")   # prior 480 → 90×15/60


def test_month_total_stable_after_recalculation(test_temp_root):
    svc = _svc(test_temp_root)
    svc.record_clock_out(datetime(2026, 8, 27, 19, 0), DAY3)
    before = svc.month_summary(2026, 8)
    svc.recalculate_month_records(2026, 8)
    after = svc.month_summary(2026, 8)
    assert before["overtime_minutes"] == after["overtime_minutes"]
    assert before["first_25h_pay"] == after["first_25h_pay"]
    assert before["over_25h_pay"] == after["over_25h_pay"]


# ── missing clock-out flow ───────────────────────────────────────────────

def test_missing_clockout_prompts_next_morning(test_temp_root):
    NOW[0] = datetime(2026, 8, 26, 8, 30)   # morning after the 25th
    svc = _svc(test_temp_root)
    assert svc.missing_clockout_yesterday() == DAY1
    NOW[0] = datetime(2026, 8, 26, 7, 0)    # the old 17:30 gate blocked this
    assert svc.missing_clockout_yesterday() == DAY1


def test_missing_clockout_not_for_rest_day(test_temp_root):
    NOW[0] = datetime(2026, 8, 30, 9, 0)    # Sunday, "yesterday" = Saturday
    svc = _svc(test_temp_root)
    assert svc.missing_clockout_yesterday() is None


def test_mark_no_overtime_resolves_prompt(test_temp_root):
    NOW[0] = datetime(2026, 8, 26, 8, 30)
    svc = _svc(test_temp_root)
    svc.mark_no_overtime(DAY1)
    assert svc.missing_clockout_yesterday() is None
    assert svc.is_missing_clockout_resolved(DAY1)


def test_recording_clockout_resolves_prompt(test_temp_root):
    NOW[0] = datetime(2026, 8, 26, 8, 30)
    svc = _svc(test_temp_root)
    svc.record_clock_out(datetime(2026, 8, 25, 20, 13), DAY1)
    assert svc.missing_clockout_yesterday() is None


def test_snooze_does_not_permanently_resolve(test_temp_root):
    NOW[0] = datetime(2026, 8, 26, 8, 30)
    svc = _svc(test_temp_root)
    day = svc.missing_clockout_yesterday()
    svc.mark_missing_clockout_prompt(day)               # 稍后
    assert svc.missing_clockout_yesterday() is None     # silent this session
    fresh = WageService(test_temp_root, now_provider=lambda: NOW[0])
    assert fresh.missing_clockout_yesterday() == DAY1   # next launch asks again
