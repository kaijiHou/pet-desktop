"""Shell watcher tests (V2.2 — real SHChangeNotifyRegister).

Two layers:
  1. unit: debounce / stop / action mapping (no Windows messaging needed)
  2. integration: registration id != 0 + real shell broadcast reaches the
     Qt signal via NewDelivery decode (requires GUI event loop)
"""
import time
from pathlib import Path
import pytest
from shell_watcher import ShellWatcher, ShellEvent, _SHELL_TO_ACTION


@pytest.mark.unit
def test_dispatch_calls_callback():
    events = []
    w = ShellWatcher(debounce_ms=0)
    w.event.connect(lambda e: events.append(e))
    w.start()
    w.dispatch(ShellEvent(path="/test/file.txt", action="created"))
    w.stop()
    assert len(events) == 1
    assert events[0].action == "created"


@pytest.mark.unit
def test_debounce_suppresses_duplicates():
    events = []
    w = ShellWatcher(debounce_ms=500)
    w.event.connect(lambda e: events.append(e))
    w.start()
    w.dispatch(ShellEvent(path="/a.txt", action="deleted"))
    w.dispatch(ShellEvent(path="/a.txt", action="deleted"))  # suppressed
    w.dispatch(ShellEvent(path="/b.txt", action="deleted"))
    time.sleep(0.6)
    w.dispatch(ShellEvent(path="/a.txt", action="deleted"))
    w.stop()
    assert len(events) == 3


@pytest.mark.unit
def test_stop_prevents_further_dispatch():
    events = []
    w = ShellWatcher()
    w.event.connect(lambda e: events.append(e))
    w.start()
    w.stop()
    w.dispatch(ShellEvent(path="/x.txt", action="created"))
    assert len(events) == 0


@pytest.mark.unit
def test_shell_action_mapping():
    assert _SHELL_TO_ACTION[0x00000100] == "created"
    assert _SHELL_TO_ACTION[0x00000200] == "deleted"
    assert _SHELL_TO_ACTION[0x00000001] == "renamed"


@pytest.mark.integration
def test_registration_id_is_nonzero_and_real_event_reaches_signal(qapp, test_temp_root):
    """Real SHChangeNotifyRegister + a real SHCNE broadcast.

    This is the crux of Bug3: registration must actually subscribe (reg_id
    nonzero) and a real Explorer-style change must decode and reach the Qt
    signal. Dropping the earlier Test P0 (register with SHCNRF_* + NewDelivery).
    """
    import ctypes, os
    from PyQt5.QtCore import QTimer

    shell32 = ctypes.windll.shell32
    w = ShellWatcher(debounce_ms=0)
    got = []
    w.event.connect(lambda e: got.append((e.action, str(e.path))))
    w.start()
    assert w.registered, "SHChangeNotifyRegister must return a nonzero id (Bug3)"

    # broadcast a real SHCNE_CREATE to all registered shell watchers
    p = test_temp_root / "delete-me.txt"
    p.write_text("x")
    pidl = ctypes.c_void_p(); attr = ctypes.c_ulong()
    shell32.SHParseDisplayName.restype = ctypes.c_long
    shell32.SHParseDisplayName.argtypes = [ctypes.c_wchar_p, ctypes.c_void_p,
                                           ctypes.POINTER(ctypes.c_void_p),
                                           ctypes.c_ulong, ctypes.POINTER(ctypes.c_ulong)]
    shell32.SHParseDisplayName(str(p), None, ctypes.byref(pidl), 0, ctypes.byref(attr))
    assert pidl.value

    result = {}
    def deliver():
        shell32.SHChangeNotify.restype = None
        shell32.SHChangeNotify.argtypes = [ctypes.c_ulong, ctypes.c_uint,
                                           ctypes.c_void_p, ctypes.c_void_p]
        shell32.SHChangeNotify(0x100, 0, pidl, None)  # SHCNE_CREATE, SHCNF_IDLIST
        QTimer.singleShot(1000, check)

    def check():
        result["got"] = list(got)
        try:
            w.stop()
        finally:
            p.unlink(missing_ok=True)
            app = qapp
            app.exit()

    QTimer.singleShot(0, deliver)
    qapp.exec_()
    assert any(e[0] == "created" and Path(e[1]) == p.resolve() for e in result.get("got", [])), \
        "real shell create event must decode to the correct path"


@pytest.mark.integration
def test_registration_id_is_zero_marked_failed_if_unsupported(qapp):
    # On non-Windows / failure it must at least not crash; on Windows we expect
    # a real registration. (Skip silently on non-Windows.)
    import sys
    if not sys.platform.startswith("win"):
        pytest.skip("Windows-only")
    w = ShellWatcher()
    w.start()
    assert w.registered
    w.stop()
