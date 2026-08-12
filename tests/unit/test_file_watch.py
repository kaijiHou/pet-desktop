"""Phase 14 event-driven file watcher tests."""

import struct
import time

import pytest

from file_watch import FileWatchService, parse_notifications


def notification(action, name):
    encoded = name.encode("utf-16-le")
    return struct.pack("<III", 0, action, len(encoded)) + encoded


@pytest.mark.unit
def test_parse_windows_notification_actions(test_temp_root):
    for code, expected in ((1, "added"), (2, "removed"), (3, "modified"),
                           (4, "renamed_from"), (5, "renamed_to")):
        event = parse_notifications(notification(code, "item.txt"), test_temp_root)[0]
        assert event.action == expected
        assert event.path == test_temp_root / "item.txt"


@pytest.mark.unit
def test_service_watches_only_explicit_existing_directories(test_temp_root):
    class Backend:
        def watch(self, directory, stop):
            yield notification(1, "new.txt")
    service = FileWatchService(Backend())
    events = []
    service.on_change = events.append
    assert service.watch(test_temp_root) is True
    assert service.watch(test_temp_root) is False
    for _ in range(50):
        if events: break
        time.sleep(0.01)
    assert events[0].action == "added"
    with pytest.raises(NotADirectoryError): service.watch(test_temp_root / "missing")
    service.stop_all()


@pytest.mark.unit
def test_implementation_is_event_driven_not_polling():
    from pathlib import Path
    source = (Path(__file__).resolve().parents[2] / "file_watch.py").read_text(encoding="utf-8")
    assert "ReadDirectoryChangesW" in source
    assert "time.sleep" not in source
