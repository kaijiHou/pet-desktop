"""Serializable domain objects used by the local wage calculator."""

from dataclasses import dataclass, field
from datetime import date, datetime, time
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional


WORKDAY = "workday"
REST = "rest"
ADJUSTED_WORKDAY = "adjusted_workday"
LEAVE = "leave"
VALID_STATUSES = {WORKDAY, REST, ADJUSTED_WORKDAY, LEAVE}


def money(value) -> Decimal:
    """Convert user/storage values to cents-safe Decimal values."""
    if isinstance(value, Decimal):
        return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return Decimal(str(value or "0")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def parse_time(value, default: time) -> time:
    if isinstance(value, time):
        return value.replace(second=0, microsecond=0)
    if isinstance(value, str):
        try:
            parts = value.split(":")
            return time(int(parts[0]), int(parts[1]), int(parts[2]) if len(parts) > 2 else 0)
        except (ValueError, IndexError):
            pass
    return default


@dataclass
class WageSettings:
    enabled: bool = False
    monthly_salary: Decimal = Decimal("0.00")
    work_start: time = time(9, 0)
    lunch_start: time = time(12, 0)
    lunch_end: time = time(13, 0)
    income_interval_minutes: int = 0
    privacy_mode: bool = False
    manual_workday_count: Optional[int] = None
    overtime_start: time = time(17, 30)
    meal_allowance_time: time = time(20, 0)

    def __post_init__(self):
        self.monthly_salary = money(self.monthly_salary)
        self.work_start = parse_time(self.work_start, time(9, 0))
        self.lunch_start = parse_time(self.lunch_start, time(12, 0))
        self.lunch_end = parse_time(self.lunch_end, time(13, 0))
        self.overtime_start = parse_time(self.overtime_start, time(17, 30))
        self.meal_allowance_time = parse_time(self.meal_allowance_time, time(20, 0))
        self.income_interval_minutes = int(self.income_interval_minutes or 0)
        if self.income_interval_minutes not in {0, 10, 30, 60, 120}:
            self.income_interval_minutes = 0
        if self.manual_workday_count is not None:
            self.manual_workday_count = max(1, int(self.manual_workday_count))

    @property
    def configured(self) -> bool:
        return self.enabled and self.monthly_salary > 0 and self.work_start < self.overtime_start

    def to_dict(self) -> dict:
        return {
            "enabled": self.enabled,
            "monthly_salary": str(self.monthly_salary),
            "work_start": self.work_start.strftime("%H:%M"),
            "lunch_start": self.lunch_start.strftime("%H:%M"),
            "lunch_end": self.lunch_end.strftime("%H:%M"),
            "income_interval_minutes": self.income_interval_minutes,
            "privacy_mode": self.privacy_mode,
            "manual_workday_count": self.manual_workday_count,
            "overtime_start": self.overtime_start.strftime("%H:%M"),
            "meal_allowance_time": self.meal_allowance_time.strftime("%H:%M"),
        }

    @classmethod
    def from_dict(cls, raw: dict):
        if not isinstance(raw, dict):
            return cls()
        return cls(
            enabled=bool(raw.get("enabled", False)),
            monthly_salary=raw.get("monthly_salary", "0"),
            work_start=raw.get("work_start", "09:00"),
            lunch_start=raw.get("lunch_start", "12:00"),
            lunch_end=raw.get("lunch_end", "13:00"),
            income_interval_minutes=raw.get("income_interval_minutes", 0),
            privacy_mode=bool(raw.get("privacy_mode", False)),
            manual_workday_count=raw.get("manual_workday_count"),
            overtime_start=raw.get("overtime_start", "17:30"),
            meal_allowance_time=raw.get("meal_allowance_time", "20:00"),
        )


@dataclass
class WorkDayRecord:
    date: date
    workday_status: str = WORKDAY
    actual_clock_out: Optional[datetime] = None
    overtime_minutes: int = 0
    overtime_pay: Decimal = Decimal("0.00")
    meal_allowance: Decimal = Decimal("0.00")
    note: str = ""
    manual_override: bool = False

    def __post_init__(self):
        if isinstance(self.date, str):
            self.date = date.fromisoformat(self.date)
        if self.workday_status not in VALID_STATUSES:
            self.workday_status = WORKDAY
        if isinstance(self.actual_clock_out, str):
            self.actual_clock_out = datetime.fromisoformat(self.actual_clock_out)
        self.overtime_minutes = max(0, int(self.overtime_minutes or 0))
        self.overtime_pay = money(self.overtime_pay)
        self.meal_allowance = money(self.meal_allowance)

    def to_dict(self) -> dict:
        return {
            "date": self.date.isoformat(),
            "workday_status": self.workday_status,
            "actual_clock_out": self.actual_clock_out.isoformat(timespec="seconds") if self.actual_clock_out else None,
            "overtime_minutes": self.overtime_minutes,
            "overtime_pay": str(self.overtime_pay),
            "meal_allowance": str(self.meal_allowance),
            "note": self.note,
            "manual_override": self.manual_override,
        }

    @classmethod
    def from_dict(cls, raw: dict):
        return cls(
            date=raw["date"],
            workday_status=raw.get("workday_status", WORKDAY),
            actual_clock_out=raw.get("actual_clock_out"),
            overtime_minutes=raw.get("overtime_minutes", 0),
            overtime_pay=raw.get("overtime_pay", "0"),
            meal_allowance=raw.get("meal_allowance", "0"),
            note=str(raw.get("note", "")),
            manual_override=bool(raw.get("manual_override", False)),
        )


@dataclass
class WageBreakdown:
    date: date
    status: str
    configured: bool
    daily_salary: Decimal = Decimal("0.00")
    regular_minutes: int = 0
    paid_regular_minutes: int = 0
    base_earned: Decimal = Decimal("0.00")
    overtime_minutes: int = 0
    overtime_pay: Decimal = Decimal("0.00")
    confirmed_meal_allowance: Decimal = Decimal("0.00")
    expected_meal_allowance: Decimal = Decimal("0.00")
    progress: int = 0

    @property
    def total_earned(self):
        return money(self.base_earned + self.overtime_pay + self.confirmed_meal_allowance)

