"""V3.1: bundled statutory holiday data drives the work calendar offline."""

from datetime import date
from pathlib import Path

import pytest

from paths import BUNDLE_ROOT
from wage.calendar_service import WorkCalendarService, bundled_holiday_dir
from wage.model import WORKDAY, REST, ADJUSTED_WORKDAY, LEAVE


@pytest.fixture()
def statutory_calendar(test_temp_root):
    """Service backed ONLY by the bundled holiday-cn data (offline check)."""
    return WorkCalendarService(test_temp_root / "c.json", test_temp_root / "none.json")


def test_bundled_data_is_shipped_and_loadable():
    d = bundled_holiday_dir()
    assert d == BUNDLE_ROOT / "assets" / "holiday_cn"
    years = sorted(p.stem for p in d.glob("*.json"))
    assert "2025" in years and "2026" in years   # current years covered


def test_statutory_holiday_overrides_weekday(statutory_calendar):
    # 2026-10-01 国庆 falls on a Thursday: Mon-Fri fallback must lose.
    assert statutory_calendar.status_for(date(2026, 10, 1)) == REST
    assert statutory_calendar.status_for(date(2026, 10, 2)) == REST


def test_spring_festival_span(statutory_calendar):
    # 2026 春节 statutory break per State Council paper.
    assert statutory_calendar.status_for(date(2026, 2, 15)) == REST
    assert statutory_calendar.status_for(date(2026, 2, 16)) == REST
    assert statutory_calendar.status_for(date(2026, 2, 23)) == REST


def test_tiaoxiu_workday_overrides_weekend(statutory_calendar):
    # 2026-09-20 is a Sunday but a statutory 调休补班 day for 国庆.
    assert date(2026, 9, 20).weekday() == 6
    assert statutory_calendar.status_for(date(2026, 9, 20)) == ADJUSTED_WORKDAY
    assert statutory_calendar.is_workday(date(2026, 9, 20))


def test_normal_weekend_and_weekday_unchanged(statutory_calendar):
    assert statutory_calendar.status_for(date(2026, 9, 21)) == WORKDAY    # Monday
    assert statutory_calendar.status_for(date(2026, 9, 26)) == REST      # Saturday


def test_manual_override_beats_statutory_data(statutory_calendar):
    day = date(2026, 10, 1)
    assert statutory_calendar.status_for(day) == REST       # statutory
    statutory_calendar.set_override(day, ADJUSTED_WORKDAY)  # company says come in
    assert statutory_calendar.status_for(day) == ADJUSTED_WORKDAY
    statutory_calendar.restore_auto(day)
    assert statutory_calendar.status_for(day) == REST       # back to statutory


def test_user_holiday_file_beats_bundled_data(test_temp_root):
    user = test_temp_root / "holidays.json"
    user.write_text('{"2026-10-01": "adjusted_workday"}', encoding="utf-8")
    cal = WorkCalendarService(test_temp_root / "c.json", user)
    assert cal.status_for(date(2026, 10, 1)) == ADJUSTED_WORKDAY


def test_workday_count_uses_statutory_calendar(statutory_calendar):
    # August 2026 has no statutory adjustments: 21 Mon–Fri workdays.
    assert statutory_calendar.workday_count(2026, 8) == 21
