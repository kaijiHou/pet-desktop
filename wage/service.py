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
        self._legacy_migration_notice_pending = False
        self.settings = self._load_settings()
        self.calendar = WorkCalendarService(storage_path=self.data_dir / "work_calendar.json",
                                             holiday_data_path=self.data_dir / "holidays.json")
        self.records = self._load_records()
        # "稍后" dismissals are session-scoped on purpose: the prompt must
        # come back on the next launch until the day is truly resolved.
        self._missing_prompt_days = set()
        self._last_progress_slot = None
        self.on_progress = None

    def _load_settings(self):
        raw = load_json(self.settings_path, {})
        raw = raw if isinstance(raw, dict) else {}
        settings = WageSettings.from_dict(raw)
        # Persist the migration once so the old editable field is preserved as
        # audit data but can never silently influence payroll again.
        if raw.get("manual_workday_count") not in (None, "") and raw.get("legacy_manual_workday_count") in (None, ""):
            self._legacy_migration_notice_pending = True
            save_json_atomic(self.settings_path, settings.to_dict())
            LOGGER.info("migrated legacy manual_workday_count to audit field")
        return settings

    def consume_legacy_migration_notice(self) -> bool:
        pending = self._legacy_migration_notice_pending
        self._legacy_migration_notice_pending = False
        return pending

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
        if changes.get("manual_workday_count") not in (None, ""):
            changes["legacy_manual_workday_count"] = changes["manual_workday_count"]
            changes["manual_workday_count"] = None
            LOGGER.info("ignoring deprecated manual_workday_count for calculation")
        raw.update(changes)
        self.settings = WageSettings.from_dict(raw)
        save_json_atomic(self.settings_path, self.settings.to_dict())
        LOGGER.info("wage settings updated")
        return self.settings

    def calculator(self):
        return WageCalculator(self.settings, self.calendar)

    def status_for(self, day=None):
        day = day or self._now().date()
        if isinstance(day, datetime):
            day = day.date()
        record = self.records.get(day.isoformat())
        return record.workday_status if record else self.calendar.status_for(day)

    def record_for(self, day=None):
        day = day or self._now().date()
        if isinstance(day, datetime):
            day = day.date()
        return self.records.get(day.isoformat())

    def current_breakdown(self, when=None):
        when = when or self._now()
        prior = self.prior_overtime_minutes_before(when.date())
        return self.calculator().breakdown(when, self.record_for(when.date()), prior)

    snapshot = current_breakdown
    get_today_breakdown = current_breakdown

    def prior_overtime_minutes_before(self, day) -> int:
        """Month-to-date overtime strictly BEFORE *day* (historical backfills
        must never count later dates as prior — that shifted the 15/25 tier)."""
        if isinstance(day, datetime):
            day = day.date()
        key = day.isoformat()
        month_key = key[:7]
        return sum(r.overtime_minutes for k, r in self.records.items()
                   if k[:7] == month_key and k < key)

    def recalculate_month_records(self, year=None, month=None):
        """Recompute overtime minutes/pay and meal allowance for every record
        of the month in date order, so editing an early day re-tier the
        15/25 元 rates of all later days deterministically."""
        now = self._now()
        year, month = year or now.year, month or now.month
        month_key = f"{year:04d}-{month:02d}"
        calc = self.calculator()
        prior = 0
        touched = 0
        for key in sorted(k for k in self.records if k.startswith(month_key)):
            rec = self.records[key]
            overtime = calc.overtime_minutes(rec.actual_clock_out, rec) if rec.actual_clock_out else 0
            rec.overtime_minutes = overtime
            rec.overtime_pay = calc.overtime_pay(overtime, prior)
            rec.meal_allowance = calc.meal_allowance(rec.actual_clock_out, confirmed=True)
            prior += overtime
            touched += 1
        if touched:
            self._save_records()
            LOGGER.info("daily work record updated")
        return touched

    def set_day_status(self, day, status):
        """Update calendar override AND sync any existing WorkDayRecord."""
        if isinstance(day, datetime):
            day = day.date()
        self.calendar.set_override(day, status)
        rec = self.records.get(day.isoformat())
        if rec is not None:
            rec.workday_status = status
            rec.manual_override = True
            if status in ("rest", "leave", "sick"):
                rec.overtime_minutes = 0
                rec.overtime_pay = 0
                rec.meal_allowance = 0
            self.recalculate_month_records(day.year, day.month)
            self._save_records()
            LOGGER.info("day status override synced to record date=%s status=%s", day.isoformat(), status)

    def restore_day_status_auto(self, day):
        """Remove manual override and restore calendar auto + record sync."""
        if isinstance(day, datetime):
            day = day.date()
        self.calendar.restore_auto(day)
        rec = self.records.get(day.isoformat())
        if rec is not None:
            rec.workday_status = self.calendar.status_for(day)
            rec.manual_override = False
            self.recalculate_month_records(day.year, day.month)
            self._save_records()
            LOGGER.info("day status restored to auto date=%s", day.isoformat())

    def record_clock_out(self, actual_clock_out: datetime, day=None, note="") -> WorkDayRecord:
        if not isinstance(actual_clock_out, datetime):
            raise TypeError("actual_clock_out must be a datetime")
        day = day or actual_clock_out.date()
        if isinstance(day, datetime):
            day = day.date()
        status = self.status_for(day)
        calc = self.calculator()
        prior = self.prior_overtime_minutes_before(day)
        overtime = calc.overtime_minutes(actual_clock_out)
        rec = WorkDayRecord(day, status, actual_clock_out, overtime,
                            calc.overtime_pay(overtime, prior),
                            calc.meal_allowance(actual_clock_out, confirmed=True), note,
                            day.isoformat() in self.calendar.manual_overrides)
        self.records[day.isoformat()] = rec
        self.recalculate_month_records(day.year, day.month)
        LOGGER.info("daily work record updated date=%s", day.isoformat())
        return rec

    def edit_clock_out(self, day, actual_clock_out: datetime):
        if isinstance(day, datetime):
            day = day.date()
        elif not isinstance(day, date):
            day = date.fromisoformat(str(day))
        return self.record_clock_out(actual_clock_out, day)

    update_clock_out = edit_clock_out
    save_clock_out = record_clock_out

    def mark_no_overtime(self, day=None):
        """User explicitly said this day had no overtime (resolves the
        missing-clock-out prompt permanently for that day)."""
        day = day or self._now().date()
        rec = self.records.get(day.isoformat()) or WorkDayRecord(day, self.status_for(day))
        rec.actual_clock_out = None
        rec.overtime_minutes = 0
        rec.overtime_pay = rec.meal_allowance = rec.meal_allowance * 0
        rec.resolved_no_overtime = True
        self.records[day.isoformat()] = rec
        self.recalculate_month_records(day.year, day.month)
        LOGGER.info("daily work record updated date=%s", day.isoformat())
        return rec

    def missing_clockout_yesterday(self, when=None):
        """Yesterday's date when a workday was never closed out.

        Prompts on the FIRST launch after midnight — the old 17:30 gate made
        morning users miss the reminder for the whole day. Rest-day
        yesterday and already-resolved days never prompt.
        """
        when = when or self._now()
        yesterday = when.date().fromordinal(when.date().toordinal() - 1)
        key = yesterday.isoformat()
        if when.date() <= yesterday:
            return None
        if key in self._missing_prompt_days:
            return None
        if self.calendar.status_for(yesterday) not in {WORKDAY, ADJUSTED_WORKDAY}:
            return None
        rec = self.records.get(key)
        if rec is not None and (rec.actual_clock_out or rec.resolved_no_overtime):
            return None
        return yesterday

    def mark_missing_clockout_prompt(self, day):
        """Dismiss the prompt for this session only — a restart may ask
        again until the day is actually resolved (clock-out saved or
        explicit no-overtime)."""
        key = day.isoformat() if isinstance(day, date) else str(day)
        self._missing_prompt_days.add(key)

    def is_missing_clockout_resolved(self, day) -> bool:
        key = day.isoformat() if isinstance(day, date) else str(day)
        rec = self.records.get(key)
        return rec is not None and bool(rec.actual_clock_out or rec.resolved_no_overtime)

    def month_summary(self, year=None, month=None):
        now = self._now()
        year, month = year or now.year, month or now.month
        month_key = f"{year:04d}-{month:02d}"
        rows = [r for key, r in sorted(self.records.items()) if key.startswith(month_key)]
        calc = self.calculator()
        total_minutes = sum(r.overtime_minutes for r in rows)
        first_tier_minutes = min(total_minutes, 25 * 60)
        first_pay = calc.overtime_pay(first_tier_minutes, 0)
        second_pay = calc.overtime_pay(max(0, total_minutes - first_tier_minutes), first_tier_minutes)
        meal_total = sum((r.meal_allowance for r in rows), start=calc.MEAL_ALLOWANCE * 0)
        confirmed_overtime = sum((r.overtime_pay for r in rows), start=calc.MEAL_ALLOWANCE * 0)
        confirmed_meal = meal_total
        daily = calc.daily_salary(date(year, month, 1)) if self.settings.configured else calc.MEAL_ALLOWANCE * 0
        worked_base = sum((daily for r in rows
                           if r.workday_status in {WORKDAY, ADJUSTED_WORKDAY}
                           and (r.actual_clock_out or r.resolved_no_overtime)),
                          start=calc.MEAL_ALLOWANCE * 0)
        # Bug5: if querying current month, add today's real-time base/meal
        # (avoid double-counting if today already has a record)
        today_key = now.date().isoformat()
        today_rec = self.records.get(today_key)
        if now.year == year and now.month == month and today_rec is None:
            today_snap = self.current_breakdown(now)
            worked_base += today_snap.base_earned
            worked_value = worked_base + confirmed_overtime + confirmed_meal
        else:
            worked_value = worked_base + confirmed_overtime + confirmed_meal
        return {
            "workday_count": self.calendar.workday_count(year, month),
            "recorded_workdays": sum(1 for r in rows
                                     if r.workday_status in {WORKDAY, ADJUSTED_WORKDAY}
                                     and (r.actual_clock_out or r.resolved_no_overtime)),
            "monthly_salary": self.settings.monthly_salary,
            "overtime_minutes": total_minutes,
            "first_25h_pay": first_pay,
            "over_25h_pay": second_pay,
            "meal_count": sum(1 for r in rows if r.meal_allowance > 0),
            "meal_allowance": meal_total,
            "confirmed_overtime_pay": confirmed_overtime,
            "confirmed_meal_allowance": confirmed_meal,
            "worked_value_to_date": worked_value,
            "estimated_total": self.settings.monthly_salary + first_pay + second_pay + meal_total,
        }

    def maybe_emit_progress(self, when=None):
        when = when or self._now()
        interval = self.settings.income_interval_minutes
        if not self.configured or not interval or not self.on_progress:
            return False
        # Gate: only emit on workdays, during work hours, before clock-out
        status = self.status_for(when.date())
        if status not in (WORKDAY, ADJUSTED_WORKDAY):
            return False
        if hasattr(when, 'time') and when.time() < self.settings.work_start:
            return False
        rec = self.record_for(when.date())
        if rec and rec.actual_clock_out and when > rec.actual_clock_out:
            return False
        slot = int(when.timestamp() // (interval * 60))
        if slot == self._last_progress_slot:
            return False
        self._last_progress_slot = slot
        self.on_progress(self.current_breakdown(when))
        return True
