"""Application-facing facade combining settings, calendar, records and calculator."""

from datetime import date, datetime, time
from pathlib import Path
from typing import Callable, Optional
import logging

from paths import DATA_DIR
from .model import WageSettings, WorkDayRecord, WORKDAY, REST, ADJUSTED_WORKDAY, LEAVE
from .storage import load_json, save_json_atomic
from .calendar_service import WorkCalendarService
from .calculator import WageCalculator

LOGGER = logging.getLogger("pet.wage")


class WageService:
    def __init__(self, data_dir: Optional[Path] = None, now_provider: Optional[Callable[[], datetime]] = None):
        self.data_dir = Path(data_dir) if data_dir else DATA_DIR
        self.settings_path = self.data_dir / "wage_settings.json"
        self.records_path = self.data_dir / "wage_records.json"
        self.prompt_path = self.data_dir / "wage_prompts.json"
        self._now = now_provider or datetime.now
        self.settings = self._load_settings()
        self.calendar = WorkCalendarService(storage_path=self.data_dir / "work_calendar.json",
                                             holiday_data_path=self.data_dir / "holidays.json")
        self.records = self._load_records()
        raw_prompts = load_json(self.prompt_path, {})
        self._missing_prompt_days = set(raw_prompts.get("missing_clockout", [])) if isinstance(raw_prompts, dict) else set()
        self._last_progress_slot = None
        self.on_progress = None

    def _load_settings(self):
        raw = load_json(self.settings_path, {})
        return WageSettings.from_dict(raw if isinstance(raw, dict) else {})

    def _load_records(self):
        raw = load_json(self.records_path, {})
        out = {}
        source = raw.get("records", raw) if isinstance(raw, dict) else {}
        if isinstance(source, dict):
            for key, value in source.items():
                try:
                    out[str(key)] = WorkDayRecord.from_dict(value)
                except (KeyError, TypeError, ValueError):
                    continue
        return out

    def _save_records(self):
        save_json_atomic(self.records_path, {"records": {k: v.to_dict() for k, v in sorted(self.records.items())}})

    @property
    def configured(self):
        return self.settings.configured

    def update_settings(self, **changes):
        raw = self.settings.to_dict()
        raw.update(changes)
        self.settings = WageSettings.from_dict(raw)
        save_json_atomic(self.settings_path, self.settings.to_dict())
        LOGGER.info("wage settings updated")
        return self.settings

    def calculator(self):
        return WageCalculator(self.settings, self.calendar)

    def status_for(self, day=None):
        day = day or self._now().date()
        record = self.records.get(day.isoformat())
        return record.workday_status if record else self.calendar.status_for(day)

    def record_for(self, day=None):
        day = day or self._now().date()
        return self.records.get(day.isoformat())

    def current_breakdown(self, when=None):
        when = when or self._now()
        prior = sum(r.overtime_minutes for key, r in self.records.items()
                    if key[:7] == when.date().isoformat()[:7] and key != when.date().isoformat())
        return self.calculator().breakdown(when, self.record_for(when.date()), prior)

    snapshot = current_breakdown

    def record_clock_out(self, actual_clock_out: datetime, day=None, note="") -> WorkDayRecord:
        if not isinstance(actual_clock_out, datetime):
            raise TypeError("actual_clock_out must be a datetime")
        day = day or actual_clock_out.date()
        if isinstance(day, datetime):
            day = day.date()
        status = self.status_for(day)
        calc = self.calculator()
        prior = sum(r.overtime_minutes for key, r in self.records.items()
                    if key[:7] == day.isoformat()[:7] and key != day.isoformat())
        overtime = calc.overtime_minutes(actual_clock_out)
        rec = WorkDayRecord(day, status, actual_clock_out, overtime,
                            calc.overtime_pay(overtime, prior),
                            calc.meal_allowance(actual_clock_out, confirmed=True), note,
                            day.isoformat() in self.calendar.manual_overrides)
        self.records[day.isoformat()] = rec
        self._save_records()
        LOGGER.info("daily work record updated date=%s", day.isoformat())
        return rec

    def edit_clock_out(self, day, actual_clock_out: datetime):
        if isinstance(day, datetime):
            day = day.date()
        elif not isinstance(day, date):
            day = date.fromisoformat(str(day))
        return self.record_clock_out(actual_clock_out, day)

    def mark_no_overtime(self, day=None):
        day = day or self._now().date()
        rec = self.records.get(day.isoformat()) or WorkDayRecord(day, self.status_for(day))
        rec.actual_clock_out = None
        rec.overtime_minutes = 0
        rec.overtime_pay = rec.meal_allowance = rec.meal_allowance * 0
        self.records[day.isoformat()] = rec
        self._save_records()
        LOGGER.info("daily work record updated date=%s", day.isoformat())
        return rec

    def missing_clockout_yesterday(self, when=None):
        """Return yesterday's date once when a workday was never closed out."""
        when = when or self._now()
        yesterday = when.date().fromordinal(when.date().toordinal() - 1)
        key = yesterday.isoformat()
        if key in self._missing_prompt_days or key in self.records:
            return None
        if self.calendar.status_for(yesterday) not in {WORKDAY, ADJUSTED_WORKDAY}:
            return None
        if when < datetime.combine(when.date(), self.settings.overtime_start):
            return None
        return yesterday

    def mark_missing_clockout_prompt(self, day):
        key = day.isoformat() if isinstance(day, date) else str(day)
        self._missing_prompt_days.add(key)
        save_json_atomic(self.prompt_path, {"missing_clockout": sorted(self._missing_prompt_days)})

    def month_summary(self, year=None, month=None):
        now = self._now()
        year, month = year or now.year, month or now.month
        month_key = f"{year:04d}-{month:02d}"
        rows = [r for key, r in self.records.items() if key.startswith(month_key)]
        calc = self.calculator()
        first_tier_minutes = min(sum(r.overtime_minutes for r in rows), 25 * 60)
        total_minutes = sum(r.overtime_minutes for r in rows)
        first_pay = calc.overtime_pay(first_tier_minutes, 0)
        second_pay = calc.overtime_pay(max(0, total_minutes - first_tier_minutes), first_tier_minutes)
        return {
            "workday_count": self.calendar.workday_count(year, month),
            "monthly_salary": self.settings.monthly_salary,
            "overtime_minutes": total_minutes,
            "first_25h_pay": first_pay,
            "over_25h_pay": second_pay,
            "meal_allowance": sum((r.meal_allowance for r in rows), start=calc.MEAL_ALLOWANCE * 0),
            "estimated_total": self.settings.monthly_salary + first_pay + second_pay + sum((r.meal_allowance for r in rows), start=calc.MEAL_ALLOWANCE * 0),
        }

    def maybe_emit_progress(self, when=None):
        when = when or self._now()
        interval = self.settings.income_interval_minutes
        if not self.configured or not interval or not self.on_progress:
            return False
        slot = int(when.timestamp() // (interval * 60))
        if slot == self._last_progress_slot:
            return False
        self._last_progress_slot = slot
        self.on_progress(self.current_breakdown(when))
        return True
