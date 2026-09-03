"""Pure, deterministic wage calculations. No timers and no wall-clock state."""

from datetime import date, datetime, time, timedelta
from decimal import Decimal, ROUND_HALF_UP
from typing import Iterable, Optional

from .model import WageSettings, WorkDayRecord, WageBreakdown, WORKDAY, ADJUSTED_WORKDAY, money


CENT = Decimal("0.01")


def _decimal(value):
    return Decimal(str(value))


class WageCalculator:
    OVERTIME_TIER_1_MINUTES = 25 * 60
    OVERTIME_RATE_1 = Decimal("15")
    OVERTIME_RATE_2 = Decimal("25")
    MEAL_ALLOWANCE = Decimal("30")

    def __init__(self, settings: WageSettings, calendar=None):
        self.settings = settings if isinstance(settings, WageSettings) else WageSettings.from_dict(settings or {})
        self.calendar = calendar

    def salary_workday_count(self, day: Optional[date] = None) -> int:
        day = day or date.today()
        if self.calendar is not None:
            return max(1, int(self.calendar.workday_count(day.year, day.month)))
        return 22

    def daily_salary(self, day: Optional[date] = None) -> Decimal:
        return money(self.settings.monthly_salary / Decimal(self.salary_workday_count(day)))

    @staticmethod
    def _minutes_between(start: time, end: time) -> int:
        return max(0, (end.hour * 60 + end.minute) - (start.hour * 60 + start.minute))

    def regular_minutes_per_day(self) -> int:
        start = self.settings.work_start
        cutoff = self.settings.overtime_start
        total = self._minutes_between(start, cutoff)
        lunch_start = max(start, self.settings.lunch_start)
        lunch_end = min(cutoff, self.settings.lunch_end)
        return max(0, total - self._minutes_between(lunch_start, lunch_end))

    def paid_regular_minutes(self, when: datetime) -> int:
        start = datetime.combine(when.date(), self.settings.work_start)
        cutoff = datetime.combine(when.date(), self.settings.overtime_start)
        if when <= start:
            return 0
        end = min(when, cutoff)
        minutes = max(0, int((end - start).total_seconds() // 60))
        lunch_start = datetime.combine(when.date(), self.settings.lunch_start)
        lunch_end = datetime.combine(when.date(), self.settings.lunch_end)
        overlap_start = max(start, lunch_start)
        overlap_end = min(end, lunch_end)
        if overlap_end > overlap_start:
            minutes -= int((overlap_end - overlap_start).total_seconds() // 60)
        return max(0, min(self.regular_minutes_per_day(), minutes))

    def base_earned(self, when: datetime, status: Optional[str] = None) -> Decimal:
        status = status or (self.calendar.status_for(when.date()) if self.calendar else WORKDAY)
        if status not in {WORKDAY, ADJUSTED_WORKDAY} or not self.settings.configured:
            return Decimal("0.00")
        regular = self.regular_minutes_per_day()
        if regular <= 0:
            return Decimal("0.00")
        return money(self.daily_salary(when.date()) * Decimal(self.paid_regular_minutes(when)) / Decimal(regular))

    regular_income = base_earned
    calculate_regular_income = base_earned

    def overtime_minutes(self, when: datetime, record: Optional[WorkDayRecord] = None) -> int:
        status = record.workday_status if record else (self.calendar.status_for(when.date()) if self.calendar else WORKDAY)
        if status not in {WORKDAY, ADJUSTED_WORKDAY}:
            return 0
        if record and record.actual_clock_out:
            end = record.actual_clock_out
        else:
            end = when
        start = datetime.combine(end.date(), self.settings.overtime_start)
        if end <= start:
            return 0
        return int((end - start).total_seconds() // 60)

    def overtime_pay(self, overtime_minutes: int, prior_overtime_minutes: int = 0) -> Decimal:
        remaining = max(0, int(overtime_minutes))
        prior = max(0, int(prior_overtime_minutes))
        tier1_left = max(0, self.OVERTIME_TIER_1_MINUTES - prior)
        first = min(remaining, tier1_left)
        second = remaining - first
        # Divide by 60 only at the end so a 30-minute boundary is exact.
        amount = (Decimal(first) / Decimal(60) * self.OVERTIME_RATE_1
                  + Decimal(second) / Decimal(60) * self.OVERTIME_RATE_2)
        return money(amount)

    calculate_overtime_pay = overtime_pay
    calculate_overtime = overtime_pay

    def meal_allowance(self, clock_out: Optional[datetime], confirmed: bool = False) -> Decimal:
        if not confirmed or not clock_out:
            return Decimal("0.00")
        threshold = datetime.combine(clock_out.date(), self.settings.meal_allowance_time)
        return self.MEAL_ALLOWANCE if clock_out >= threshold else Decimal("0.00")

    calculate_meal_allowance = meal_allowance

    def expected_meal_allowance(self, when: datetime, clock_out: Optional[datetime] = None) -> Decimal:
        point = clock_out or when
        threshold = datetime.combine(point.date(), self.settings.meal_allowance_time)
        return self.MEAL_ALLOWANCE if point >= threshold and not clock_out else Decimal("0.00")

    def breakdown(self, when: datetime, record: Optional[WorkDayRecord] = None,
                  prior_overtime_minutes: int = 0) -> WageBreakdown:
        day = when.date()
        status = record.workday_status if record else (self.calendar.status_for(day) if self.calendar else WORKDAY)
        configured = self.settings.configured
        daily = self.daily_salary(day) if configured else Decimal("0.00")
        regular = self.regular_minutes_per_day() if configured else 0
        paid = self.paid_regular_minutes(when) if configured else 0
        base = self.base_earned(when, status)
        overtime = self.overtime_minutes(when, record) if configured else 0
        overtime_value = self.overtime_pay(overtime, prior_overtime_minutes) if configured else Decimal("0.00")
        confirmed_meal = self.meal_allowance(record.actual_clock_out, confirmed=True) if record else Decimal("0.00")
        expected = self.expected_meal_allowance(when) if not record or not record.actual_clock_out else Decimal("0.00")
        progress = round(100 * paid / regular) if regular else 0
        return WageBreakdown(day, status, configured, daily, regular, paid, base,
                             overtime, overtime_value, confirmed_meal, expected,
                             max(0, min(100, progress)))
