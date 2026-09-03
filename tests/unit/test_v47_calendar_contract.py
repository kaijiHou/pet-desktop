"""V4.7 calendar authority and holiday metadata contract."""
from datetime import date

from wage.calendar_service import WorkCalendarService
from wage.calculator import WageCalculator
from wage.model import ADJUSTED_WORKDAY, REST, WORKDAY, WageSettings


def test_2026_statutory_counts_and_metadata(test_temp_root):
    cal = WorkCalendarService(test_temp_root / "calendar.json", test_temp_root / "none.json")
    assert cal.workday_count(2026, 9) == 22
    assert cal.workday_count(2026, 10) == 18
    sep20 = cal.status_detail_for(date(2026, 9, 20))
    assert sep20["status"] == ADJUSTED_WORKDAY
    assert sep20["holiday_name"] == "国庆节"
    assert sep20["display_label"] == "国庆补班"
    assert sep20["source"] == "official"
    assert sep20["paper_url"].startswith("https://")
    assert cal.status_detail_for(date(2026, 9, 25))["status"] == REST
    assert cal.status_detail_for(date(2026, 10, 10))["status"] == ADJUSTED_WORKDAY


def test_manual_day_override_changes_count_and_restores(test_temp_root):
    cal = WorkCalendarService(test_temp_root / "calendar.json", test_temp_root / "none.json")
    day = date(2026, 9, 25)
    cal.set_override(day, WORKDAY)
    assert cal.workday_count(2026, 9) == 23
    assert cal.status_detail_for(day)["is_manual"] is True
    cal.restore_auto(day)
    assert cal.workday_count(2026, 9) == 22


def test_calculator_ignores_deprecated_settings_count(test_temp_root):
    cal = WorkCalendarService(test_temp_root / "calendar.json", test_temp_root / "none.json")
    settings = WageSettings(enabled=True, monthly_salary="22000", manual_workday_count=99)
    calc = WageCalculator(settings, cal)
    assert calc.salary_workday_count(date(2026, 9, 1)) == 22


def test_per_month_override_is_explicit_and_persistent(test_temp_root):
    path = test_temp_root / "calendar.json"
    cal = WorkCalendarService(path, test_temp_root / "none.json")
    cal.set_month_workday_override(2026, 9, 23)
    assert cal.workday_count(2026, 9) == 23
    restored = WorkCalendarService(path, test_temp_root / "none.json")
    assert restored.workday_count(2026, 9) == 23


def test_legacy_settings_count_is_migrated_to_audit_only(test_temp_root):
    settings_path = test_temp_root / "wage_settings.json"
    settings_path.write_text('{"enabled":true,"monthly_salary":"22000","manual_workday_count":99}', encoding="utf-8")
    from wage.service import WageService
    service = WageService(test_temp_root, now_provider=lambda: __import__("datetime").datetime(2026, 9, 1, 9, 0))
    assert service.settings.legacy_manual_workday_count == 99
    assert service.calculator().salary_workday_count(date(2026, 9, 1)) == 22
    assert service.consume_legacy_migration_notice() is True
    assert service.consume_legacy_migration_notice() is False


def test_legacy_calendar_count_does_not_survive_as_active_authority(test_temp_root):
    path = test_temp_root / "work_calendar.json"
    path.write_text('{"manual_workday_count":3}', encoding="utf-8")
    cal = WorkCalendarService(path, test_temp_root / "none.json")
    assert cal.legacy_manual_workday_count == 3
    assert cal.workday_count(2026, 9) == 22
