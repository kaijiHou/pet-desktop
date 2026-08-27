"""Shell watcher unit tests (V2 Phase 5)."""
import time
import pytest
from shell_watcher import ShellWatcher, ShellEvent, _SHELL_TO_ACTION


@pytest.mark.unit
def test_dispatch_calls_callback():
    events = []
    w = ShellWatcher(debounce_ms=0)
    w.start(lambda e: events.append(e))
    w.dispatch(ShellEvent(path="/test/file.txt", action="created"))
    w.stop()
    assert len(events) == 1
    assert events[0].action == "created"


@pytest.mark.unit
def test_debounce_suppresses_duplicates():
    events = []
    w = ShellWatcher(debounce_ms=500)
    w.start(lambda e: events.append(e))
    w.dispatch(ShellEvent(path="/a.txt", action="deleted"))
    w.dispatch(ShellEvent(path="/a.txt", action="deleted"))  # suppressed
    w.dispatch(ShellEvent(path="/b.txt", action="deleted"))  # different path
    time.sleep(0.6)
    w.dispatch(ShellEvent(path="/a.txt", action="deleted"))  # after debounce
    w.stop()
    assert len(events) == 3  # /a first, /b, /a after debounce


@pytest.mark.unit
def test_stop_prevents_further_dispatch():
    events = []
    w = ShellWatcher()
    w.start(lambda e: events.append(e))
    w.stop()
    w.dispatch(ShellEvent(path="/x.txt", action="created"))
    assert len(events) == 0


@pytest.mark.unit
def test_shell_action_mapping():
    assert _SHELL_TO_ACTION[0x00000100] == "created"
    assert _SHELL_TO_ACTION[0x00000200] == "deleted"
    assert _SHELL_TO_ACTION[0x00000001] == "renamed"
