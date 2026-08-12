"""Application events and deterministic animation fallback."""

from dataclasses import dataclass

from PyQt5.QtCore import QObject, pyqtSignal


@dataclass(frozen=True)
class AppEvent:
    category: str
    action: str
    detail: object = None


class EventDispatcher(QObject):
    """Thread-safe Qt signal boundary for background and UI producers."""

    event_received = pyqtSignal(object)

    def dispatch(self, event: AppEvent):
        self.event_received.emit(event)


class AnimationController:
    MAPPING = {
        ("reminder", "due"): "Alert",
        ("pocket", "receive"): "Save",
        ("file_operation", "copy"): "Print",
        ("file_operation", "move"): "SendMail",
        ("windows", "added"): "Show",
        ("windows", "removed"): "EmptyTrash",
        ("windows", "modified"): "Writing",
        ("windows", "renamed_from"): "Searching",
        ("windows", "renamed_to"): "Save",
    }
    GENERIC = {
        "reminder": "Alert",
        "pocket": "Save",
        "file_operation": "Processing",
        "windows": "GetAttention",
    }

    def __init__(self, available_animations):
        self.available = set(available_animations)

    def resolve(self, event: AppEvent):
        for candidate in (
            self.MAPPING.get((event.category, event.action)),
            self.GENERIC.get(event.category),
            "RestPose",
        ):
            if candidate and candidate in self.available:
                return candidate
        return None
