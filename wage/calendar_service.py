"""Offline Chinese work calendar with one authoritative resolution chain."""

from __future__ import annotations

import calendar as _calendar
import logging
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Optional

from paths import BUNDLE_ROOT, DATA_DIR
from .model import WORKDAY, REST, ADJUSTED_WORKDAY, LEAVE, VALID_STATUSES
from .storage import load_json, save_json_atomic

LOGGER = logging.getLogger("pet.wage.calendar")
STATUS_LABELS = {WORKDAY: "工作日", REST: "休息日", ADJUSTED_WORKDAY: "调休上班", LEAVE: "请假"}
PAPER_URL_FALLBACK = "https://www.gov.cn/"


@dataclass(frozen=True)
class HolidayInfo:
    date: date
    name: str = ""
    status: str = REST
    is_off_day: bool = True
    source: str = "weekday_fallback"
    official_year: Optional[int] = None
    paper_url: str = PAPER_URL_FALLBACK

    @property
    def likely_paper_url(self):
        return self.paper_url


def bundled_holiday_dir() -> Path:
    return BUNDLE_ROOT / "assets" / "holiday_cn"


def _short_name(name: str) -> str:
    name = (name or "").strip()
    return name[:-1] if name.endswith("节") and len(name) > 2 else name


class WorkCalendarService:
    """Resolve statutory status and metadata without network access."""

    def __init__(self, storage_path: Optional[Path] = None, holiday_data_path: Optional[Path] = None):
        self.storage_path = Path(storage_path) if storage_path else DATA_DIR / "work_calendar.json"
        self.holiday_data_path = Path(holiday_data_path) if holiday_data_path else DATA_DIR / "holidays.json"
        self.manual_overrides: dict[str, str] = {}
        self.workday_count_overrides: dict[str, int] = {}
        self.legacy_manual_workday_count: Optional[int] = None
        self._compat_manual_count: Optional[int] = None
        self.holidays: dict[str, str] = {}
        self.holiday_info: dict[str, HolidayInfo] = {}
        self._user_holiday_years: set[int] = set()
        self._official_years: set[int] = set()
        self._load()

    def _load(self):
        raw = load_json(self.storage_path, {})
        if isinstance(raw, dict):
            overrides = raw.get("manual_overrides", {})
            if isinstance(overrides, dict):
                self.manual_overrides = {str(k): v for k, v in overrides.items() if v in VALID_STATUSES}
            month_overrides = raw.get("workday_count_overrides", {})
            if isinstance(month_overrides, dict):
                for key, value in month_overrides.items():
                    try:
                        if len(str(key)) == 7 and int(value) > 0:
                            self.workday_count_overrides[str(key)] = max(1, int(value))
                    except (TypeError, ValueError):
                        continue
            legacy = raw.get("legacy_manual_workday_count")
            if legacy in (None, ""):
                legacy = raw.get("manual_workday_count")
            if legacy not in (None, ""):
                try:
                    self.legacy_manual_workday_count = max(1, int(legacy))
                except (TypeError, ValueError):
                    pass
        self._merge_holiday_payload(load_json(self.holiday_data_path, {}), source="user")
        bundle_dir = bundled_holiday_dir()
        if bundle_dir.is_dir():
            for path in sorted(bundle_dir.glob("*.json")):
                year = int(path.stem) if path.stem.isdigit() else None
                if year:
                    self._official_years.add(year)
                payload = load_json(path, {})
                self._merge_holiday_payload(payload, source="official", official_year=year,
                                            paper_url=(payload.get("papers") or [None])[0] if isinstance(payload, dict) else None)

    def _merge_holiday_payload(self, holiday_raw, *, source="user", official_year=None, paper_url=None):
        if not isinstance(holiday_raw, dict):
            return
        payload_year = holiday_raw.get("year") or official_year
        try:
            payload_year = int(payload_year) if payload_year else None
        except (TypeError, ValueError):
            payload_year = official_year
        source_data = holiday_raw.get("holidays", holiday_raw.get("days", holiday_raw))
        if isinstance(source_data, dict):
            for key, value in source_data.items():
                if isinstance(value, list):
                    self._merge_holiday_payload({"days": value}, source=source, official_year=payload_year, paper_url=paper_url)
                else:
                    self._merge_one(str(key), value, source, payload_year, paper_url)
        elif isinstance(source_data, list):
            for item in source_data:
                if isinstance(item, dict) and item.get("date"):
                    self._merge_one(str(item["date"]), item, source, payload_year, paper_url)

    def _merge_one(self, key, value, source, official_year, paper_url=None):
        try:
            parsed = date.fromisoformat(key)
        except ValueError:
            return
        status = self._status_from_holiday(value)
        if not status:
            return
        name = value.get("name", "") if isinstance(value, dict) else ""
        is_off = bool(value.get("isOffDay")) if isinstance(value, dict) and "isOffDay" in value else status == REST
        paper_url = paper_url or PAPER_URL_FALLBACK
        if isinstance(value, dict):
            paper_url = str(value.get("paperUrl", value.get("url", paper_url)) or paper_url)
        info = HolidayInfo(parsed, str(name or ""), status, is_off, source, official_year, paper_url)
        if key not in self.holidays:
            self.holidays[key] = status
            self.holiday_info[key] = info
        if source == "user":
            self._user_holiday_years.add(parsed.year)

    @staticmethod
    def _status_from_holiday(value):
        if isinstance(value, str) and value in VALID_STATUSES:
            return value
        if isinstance(value, dict):
            status = value.get("status")
            if status in VALID_STATUSES:
                return status
            if value.get("isWorkday") is True or value.get("workday") is True:
                return ADJUSTED_WORKDAY
            if value.get("isOffDay") is True or value.get("holiday") is True or value.get("isHoliday") is True:
                return REST
            if value.get("isOffDay") is False and value.get("date"):
                return ADJUSTED_WORKDAY
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

    get_status = status_for
    status = status_for

    def status_detail_for(self, day) -> dict:
        key = self._key(day)
        day_obj = date.fromisoformat(key)
        status = self.status_for(day_obj)
        manual = key in self.manual_overrides
        info = self.holiday_info.get(key)
        if manual:
            source, name = "manual", info.name if info else ""
            year, paper, off = info.official_year if info else None, info.paper_url if info else PAPER_URL_FALLBACK, status == REST
        elif info:
            source, name, year, paper, off = info.source, info.name, info.official_year, info.paper_url, info.is_off_day
        else:
            source, name, year, paper, off = "weekday_fallback", "", None, PAPER_URL_FALLBACK, status == REST
        label = STATUS_LABELS.get(status, status)
        if status == ADJUSTED_WORKDAY and name:
            display = f"{_short_name(name)}补班"
        elif name and status == REST:
            display = f"{name} · 休息"
        else:
            display = label
        return {"date": day_obj, "status": status, "label": label, "holiday_name": name,
                "display_label": display, "source": source, "is_manual": manual,
                "is_off_day": off, "official_year": year, "paper_url": paper,
                "likely_paper_url": paper, "source_label": source}

    def holiday_info_for(self, day) -> Optional[HolidayInfo]:
        return self.holiday_info.get(self._key(day))

    get_holiday_info = holiday_info_for

    def holiday_data_status(self, year: int) -> str:
        if year in self._official_years:
            return "official"
        if year in self._user_holiday_years:
            return "user"
        return "weekday_fallback"

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
    clear_override = restore_auto

    def set_month_workday_override(self, year: int, month: int, count: Optional[int]) -> None:
        key = f"{int(year):04d}-{int(month):02d}"
        if count in (None, "", 0):
            self.workday_count_overrides.pop(key, None)
        else:
            self.workday_count_overrides[key] = max(1, int(count))
        self.save()

    def month_days(self, year: int, month: int):
        last = _calendar.monthrange(year, month)[1]
        return [date(year, month, day) for day in range(1, last + 1)]

    def workday_count(self, year: int, month: int) -> int:
        key = f"{int(year):04d}-{int(month):02d}"
        if key in self.workday_count_overrides:
            return self.workday_count_overrides[key]
        # V3 compatibility for callers that explicitly invoked the old API.
        # Settings/UI never call this method, so normal payroll remains fully
        # statutory and per-month override based.
        if self._compat_manual_count is not None:
            return self._compat_manual_count
        return sum(self.is_workday(day) for day in self.month_days(year, month))

    count_workdays = workday_count

    # Deprecated compatibility API.  It records audit data only; normal
    # calculation never consults this value.
    def set_manual_workday_count(self, count: Optional[int]) -> None:
        self.legacy_manual_workday_count = None if count in (None, "") else max(1, int(count))
        self._compat_manual_count = self.legacy_manual_workday_count
        self.save()

    @property
    def manual_workday_count(self):
        return self.legacy_manual_workday_count

    def save(self):
        save_json_atomic(self.storage_path, {
            "manual_overrides": dict(sorted(self.manual_overrides.items())),
            "workday_count_overrides": dict(sorted(self.workday_count_overrides.items())),
            "legacy_manual_workday_count": self.legacy_manual_workday_count,
        })


WorkCalendar = WorkCalendarService
