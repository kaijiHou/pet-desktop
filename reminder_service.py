"""Persistent, local-only reminders for the desktop pet."""

from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
import json
import logging
from pathlib import Path
from typing import Callable, Optional
from uuid import uuid4

from paths import DATA_DIR


LOGGER = logging.getLogger("pet.reminder")
REMINDERS_FILE = DATA_DIR / "reminders.json"


@dataclass
class Reminder:
    """A single reminder stored entirely on the local machine."""

    id: str
    content: str
    due_at: datetime
    created_at: datetime
    status: str = "pending"

    def to_dict(self) -> dict:
        data = asdict(self)
        data["due_at"] = self.due_at.isoformat(timespec="seconds")
        data["created_at"] = self.created_at.isoformat(timespec="seconds")
        return data


class ReminderService:
    """Create, persist, and deliver one-time local reminders."""

    def __init__(
        self,
        storage_path: Optional[Path] = None,
        now_provider: Optional[Callable[[], datetime]] = None,
    ):
        self.storage_path = Path(storage_path) if storage_path else REMINDERS_FILE
        self._now = now_provider or datetime.now
        self.on_reminder_due: Optional[Callable[[Reminder], None]] = None
        self._reminders = self._load()

    def add_reminder(self, content: str, due_at: datetime) -> Reminder:
        if not isinstance(due_at, datetime):
            raise TypeError("due_at must be a datetime")
        content = content.strip()
        if not content:
            raise ValueError("reminder content cannot be blank")

        reminder = Reminder(
            id=uuid4().hex,
            content=content,
            due_at=due_at.replace(microsecond=0),
            created_at=self._now().replace(microsecond=0),
        )
        self._reminders.append(reminder)
        self._save()
        LOGGER.info("Reminder created id=%s due_at=%s", reminder.id, reminder.due_at.isoformat())
        return reminder

    def list_reminders(self) -> list[Reminder]:
        return sorted(
            (item for item in self._reminders if item.status == "pending"),
            key=lambda item: item.due_at,
        )

    def remove_reminder(self, reminder_id: str) -> bool:
        original_count = len(self._reminders)
        self._reminders = [item for item in self._reminders if item.id != reminder_id]
        if len(self._reminders) == original_count:
            return False
        self._save()
        LOGGER.info("Reminder removed id=%s", reminder_id)
        return True

    def next_due_at(self) -> Optional[datetime]:
        pending = self.list_reminders()
        return pending[0].due_at if pending else None

    def check_due(self) -> list[Reminder]:
        now = self._now()
        due = [item for item in self.list_reminders() if item.due_at <= now]
        if not due:
            return []

        for reminder in due:
            reminder.status = "completed"
        self._save()

        for reminder in due:
            LOGGER.info("Reminder triggered id=%s", reminder.id)
            if self.on_reminder_due:
                self.on_reminder_due(reminder)
        return due

    def snooze_reminder(self, reminder_id: str, minutes: int = 10) -> Reminder:
        if minutes < 1:
            raise ValueError("snooze minutes must be at least 1")
        reminder = self._find(reminder_id)
        if reminder is None:
            raise KeyError(reminder_id)
        reminder.status = "pending"
        reminder.due_at = (self._now() + timedelta(minutes=minutes)).replace(microsecond=0)
        self._save()
        LOGGER.info("Reminder snoozed id=%s minutes=%s", reminder.id, minutes)
        return reminder

    def _find(self, reminder_id: str) -> Optional[Reminder]:
        return next((item for item in self._reminders if item.id == reminder_id), None)

    def _load(self) -> list[Reminder]:
        if not self.storage_path.exists():
            return []
        try:
            raw_items = json.loads(self.storage_path.read_text(encoding="utf-8"))
            if not isinstance(raw_items, list):
                return []
        except (OSError, json.JSONDecodeError):
            LOGGER.warning("Could not read reminder storage; starting empty")
            return []

        reminders = []
        for item in raw_items:
            try:
                reminder = Reminder(
                    id=str(item["id"]),
                    content=str(item["content"]).strip(),
                    due_at=datetime.fromisoformat(item["due_at"]),
                    created_at=datetime.fromisoformat(item["created_at"]),
                    status=str(item.get("status", "pending")),
                )
                if not reminder.content or reminder.status not in {"pending", "completed"}:
                    raise ValueError
                reminders.append(reminder)
            except (KeyError, TypeError, ValueError):
                LOGGER.warning("Skipping invalid reminder entry")
        return reminders

    def _save(self) -> None:
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.storage_path.with_suffix(self.storage_path.suffix + ".tmp")
        temporary.write_text(
            json.dumps([item.to_dict() for item in self._reminders], indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        temporary.replace(self.storage_path)
