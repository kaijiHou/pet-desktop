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
    # Semantic animation names — mode-independent; PetWindow translates
    # to concrete (sheet or single-image) names at playback time.
    MAPPING = {
        ("reminder", "due"): "REMINDER",
        ("pocket", "receive"): "RECEIVE_FILE",
        ("pocket", "give"): "GIVE_FILE",
        ("file_operation", "copy"): "COPY_FILE",
        ("file_operation", "move"): "MOVE_FILE",
        ("windows", "added"): "CREATE_FILE",
        ("windows", "removed"): "DELETE_FILE",
        ("windows", "renamed_to"): "RENAME_FILE",
    }
    GENERIC = {
        "reminder": "REMINDER",
        "pocket": "RECEIVE_FILE",
        "file_operation": "COPY_FILE",
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
