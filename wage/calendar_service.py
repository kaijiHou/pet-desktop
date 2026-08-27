"""Offline work calendar with manual overrides taking precedence."""

import calendar as _calendar
from datetime import date
from pathlib import Path
from typing import Optional

from paths import DATA_DIR
from .model import WORKDAY, REST, ADJUSTED_WORKDAY, LEAVE, VALID_STATUSES
from .storage import load_json, save_json_atomic


class WorkCalendarService:
    """Resolve a date as work/rest using manual > holiday data > weekday rules."""

    def __init__(self, storage_path: Optional[Path] = None, holiday_data_path: Optional[Path] = None):
        self.storage_path = Path(storage_path) if storage_path else DATA_DIR / "work_calendar.json"
        self.holiday_data_path = Path(holiday_data_path) if holiday_data_path else DATA_DIR / "holidays.json"
        self.manual_overrides = {}
        self._manual_workday_count = None
        self.holidays = {}
        self._load()

    def _load(self):
        raw = load_json(self.storage_path, {})
        if isinstance(raw, dict):
            self.manual_overrides = {str(k): v for k, v in raw.get("manual_overrides", {}).items()
                                     if v in VALID_STATUSES}
            count = raw.get("manual_workday_count")
            self._manual_workday_count = int(count) if count not in (None, "") else None
        holiday_raw = load_json(self.holiday_data_path, {})
        if isinstance(holiday_raw, dict):
            # Accept {"2026-10-01": "rest"}, {date: {"status": ...}},
            # and the common {"holidays": [...]} export shape.
            source = holiday_raw.get("holidays", holiday_raw)
            if isinstance(source, dict):
                for key, value in source.items():
                    status = self._status_from_holiday(value)
                    if status:
                        self.holidays[str(key)] = status
            elif isinstance(source, list):
                for item in source:
                    if isinstance(item, dict) and item.get("date"):
                        status = self._status_from_holiday(item)
                        if status:
                            self.holidays[str(item["date"])] = status

    @staticmethod
    def _status_from_holiday(value):
        if isinstance(value, str) and value in VALID_STATUSES:
            return value
        if isinstance(value, dict):
            status = value.get("status")
            if status in VALID_STATUSES:
                return status
            # Common data sets use isOffDay / isHoliday or workday booleans.
            if value.get("isWorkday") is True or value.get("workday") is True:
                return ADJUSTED_WORKDAY
            if value.get("isOffDay") is True or value.get("holiday") is True or value.get("isHoliday") is True:
                return REST
        return None

    def _key(self, day) -> str:
        return day.isoformat() if isinstance(day, date) else date.fromisoformat(str(day)).isoformat()

    def status_for(self, day) -> str:
        key = self._key(day)
        if key in self.manual_overrides:
            return self.manual_overrides[key]
        if key in self.holidays:
            return self.holidays[key]
        day_obj = date.fromisoformat(key)
        return WORKDAY if day_obj.weekday() < 5 else REST

    # Friendly aliases used by UI/tests.
    get_status = status_for
    status = status_for

    def is_workday(self, day) -> bool:
        return self.status_for(day) in {WORKDAY, ADJUSTED_WORKDAY}

    def set_override(self, day, status: str) -> None:
        if status not in VALID_STATUSES:
            raise ValueError(f"unknown workday status: {status}")
        self.manual_overrides[self._key(day)] = status
        self.save()

    set_manual_override = set_override

    def restore_auto(self, day) -> None:
        self.manual_overrides.pop(self._key(day), None)
        self.save()

    restore_automatic = restore_auto

    def clear_override(self, day) -> None:
        self.restore_auto(day)

    def set_manual_workday_count(self, count: Optional[int]) -> None:
        self._manual_workday_count = None if count in (None, "") else max(1, int(count))
        self.save()

    @property
    def manual_workday_count(self):
        return self._manual_workday_count

    def month_days(self, year: int, month: int):
        last = _calendar.monthrange(year, month)[1]
        return [date(year, month, day) for day in range(1, last + 1)]

    def workday_count(self, year: int, month: int) -> int:
        if self._manual_workday_count is not None:
            return self._manual_workday_count
        return sum(self.status_for(day) in {WORKDAY, ADJUSTED_WORKDAY}
                   for day in self.month_days(year, month))

    count_workdays = workday_count

    def save(self):
        save_json_atomic(self.storage_path, {
            "manual_overrides": dict(sorted(self.manual_overrides.items())),
            "manual_workday_count": self._manual_workday_count,
        })


# Short name is useful to consumers and keeps the suggested module API.
WorkCalendar = WorkCalendarService
