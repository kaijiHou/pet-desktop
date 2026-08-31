"""Shell watcher tests (V3.2 — queue-based cross-thread delivery).

Two layers:
  1. unit: debounce / stop / action mapping
  2. integration: registration + real shell broadcast reaches callback
"""
import time
import pytest
from shell_watcher import ShellWatcher, ShellEvent, _SHELL_TO_ACTION


@pytest.mark.unit
def test_dispatch_calls_callback():
    events = []
    w = ShellWatcher(debounce_ms=0)
    w.start(lambda e: events.append(e))
    # dispatch puts event in queue; poll_events delivers it
    w.dispatch(ShellEvent(path="/test/file.txt", action="created"))
    w._poll_events()
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
    w.dispatch(ShellEvent(path="/b.txt", action="deleted"))
    w._poll_events()
    time.sleep(0.6)
    w.dispatch(ShellEvent(path="/a.txt", action="deleted"))
    w._poll_events()
    w.stop()
    assert len(events) == 3


@pytest.mark.unit
def test_stop_prevents_further_dispatch():
    events = []
    w = ShellWatcher()
    w.start(lambda e: events.append(e))
    w.stop()
    w.dispatch(ShellEvent(path="/x.txt", action="created"))
    w._poll_events()
    assert len(events) == 0


@pytest.mark.unit
def test_shell_action_mapping():
    assert _SHELL_TO_ACTION[0x00000100] == "created"
    assert _SHELL_TO_ACTION[0x00000200] == "deleted"
    assert _SHELL_TO_ACTION[0x00000001] == "renamed"


@pytest.mark.integration
def test_registration_id_is_nonzero(qapp):
    """ShellWatcher must register with SHChangeNotifyRegister."""
    import sys
    if not sys.platform.startswith("win"):
        pytest.skip("Windows-only")
    w = ShellWatcher()
    w.start()
    assert w.registered, "SHChangeNotifyRegister must return nonzero id"
    w.stop()


@pytest.mark.integration
def test_real_shell_broadcast_reaches_callback(qapp, test_temp_root):
    """Real SHChangeNotify broadcast must reach the callback via queue."""
    import sys, ctypes, os
    if not sys.platform.startswith("win"):
        pytest.skip("Windows-only")

    shell32 = ctypes.windll.shell32
    w = ShellWatcher(debounce_ms=0)
    got = []
    w.start(lambda e: got.append((e.action, str(e.path))))
    assert w.registered

    # broadcast a real SHCNE_CREATE
    p = test_temp_root / "shell_test.txt"
    p.write_text("x")
    pidl = ctypes.c_void_p()
    attr = ctypes.c_ulong()
    shell32.SHParseDisplayName.restype = ctypes.c_long
    shell32.SHParseDisplayName.argtypes = [ctypes.c_wchar_p, ctypes.c_void_p,
                                           ctypes.POINTER(ctypes.c_void_p),
                                           ctypes.c_ulong, ctypes.POINTER(ctypes.c_ulong)]
    shell32.SHParseDisplayName(str(p), None, ctypes.byref(pidl), 0, ctypes.byref(attr))
    shell32.SHChangeNotify.restype = None
    shell32.SHChangeNotify.argtypes = [ctypes.c_ulong, ctypes.c_uint,
                                       ctypes.c_void_p, ctypes.c_void_p]
    shell32.SHChangeNotify(0x100, 0, pidl, None)  # SHCNE_CREATE, SHCNF_IDLIST

    # poll for delivery
    result = {}
    def check():
        w._poll_events()
        result["got"] = list(got)
        w.stop()
        p.unlink(missing_ok=True)
        qapp.exit()

    from PyQt5.QtCore import QTimer
    QTimer.singleShot(1500, check)
    qapp.exec_()
    assert any(e[0] == "created" for e in result.get("got", [])), \
        "real shell create event must reach callback"

@pytest.mark.unit
def test_shell_delete_dispatches_even_when_pidl_path_decode_fails():
    """P0: Shell event must dispatch action even if PIDL path decode fails."""
    events = []
    w = ShellWatcher(debounce_ms=0)
    w.start(lambda e: events.append(e))
    # Simulate: action decoded but path unknown (pidl decode failed)
    w.dispatch(ShellEvent(action="deleted", path=None))
    w._poll_events()
    w.stop()
    assert len(events) == 1
    assert events[0].action == "deleted"
    assert events[0].path is None


@pytest.mark.unit
def test_shell_create_dispatches_even_when_path_unknown():
    events = []
    w = ShellWatcher(debounce_ms=0)
    w.start(lambda e: events.append(e))
    w.dispatch(ShellEvent(action="created", path=None))
    w._poll_events()
    w.stop()
    assert len(events) == 1
    assert events[0].action == "created"


@pytest.mark.unit
def test_debounce_aggregates_unknown_path_events():
    """Multiple delete events with path=None should be debounced."""
    events = []
    w = ShellWatcher(debounce_ms=500)
    w.start(lambda e: events.append(e))
    w.dispatch(ShellEvent(action="deleted", path=None))
    w.dispatch(ShellEvent(action="deleted", path=None))  # suppressed
    w.dispatch(ShellEvent(action="deleted", path=None))  # suppressed
    w._poll_events()
    w.stop()
    assert len(events) == 1  # only one delivered due to debounce
