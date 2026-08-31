"""Shell watcher tests (V3.5 — Windows SDK contract-correct constants).

CRITICAL: Tests assert against Windows SDK values, NOT against production
code constants. This prevents "wrong code + wrong test = false PASS".

Source: Microsoft Learn "SHChangeNotify" / "SHCNE" constants
"""
import time
import pytest
from shell_watcher import ShellWatcher, ShellEvent, _SHELL_TO_ACTION


# ── Windows SDK contract tests ──────────────────────────────────────────────
# These must match the Microsoft documentation exactly.

def test_shell_constants_match_windows_sdk():
    """SHCNE values MUST match Windows SDK. Do NOT import from production code."""
    from shell_watcher import (
        SHCNE_RENAMEITEM, SHCNE_CREATE, SHCNE_DELETE,
        SHCNE_MKDIR, SHCNE_RMDIR, SHCNE_RENAMEFOLDER,
    )
    assert SHCNE_RENAMEITEM   == 0x00000001  # Microsoft Learn
    assert SHCNE_CREATE       == 0x00000002  # Microsoft Learn
    assert SHCNE_DELETE       == 0x00000004  # Microsoft Learn
    assert SHCNE_MKDIR        == 0x00000008  # Microsoft Learn
    assert SHCNE_RMDIR        == 0x00000010  # Microsoft Learn
    assert SHCNE_RENAMEFOLDER == 0x00020000  # Microsoft Learn


def test_shell_action_mapping_matches_sdk():
    """Action mapping must use correct SDK values."""
    from shell_watcher import (
        SHCNE_CREATE, SHCNE_DELETE, SHCNE_MKDIR,
        SHCNE_RMDIR, SHCNE_RENAMEITEM, SHCNE_RENAMEFOLDER,
    )
    assert _SHELL_TO_ACTION[SHCNE_CREATE] == "created"
    assert _SHELL_TO_ACTION[SHCNE_DELETE] == "deleted"
    assert _SHELL_TO_ACTION[SHCNE_MKDIR] == "dir_created"
    assert _SHELL_TO_ACTION[SHCNE_RMDIR] == "dir_removed"
    assert _SHELL_TO_ACTION[SHCNE_RENAMEITEM] == "renamed"
    assert _SHELL_TO_ACTION[SHCNE_RENAMEFOLDER] == "dir_renamed"


# ── unit tests ──────────────────────────────────────────────────────────────

@pytest.mark.unit
def test_dispatch_calls_callback():
    events = []
    w = ShellWatcher(debounce_ms=0)
    w.start(lambda e: events.append(e))
    w.dispatch(ShellEvent(action="created", path="/test/file.txt"))
    w._poll_events()
    w.stop()
    assert len(events) == 1
    assert events[0].action == "created"


@pytest.mark.unit
def test_debounce_suppresses_duplicates():
    events = []
    w = ShellWatcher(debounce_ms=500)
    w.start(lambda e: events.append(e))
    w.dispatch(ShellEvent(action="deleted", path="/a.txt"))
    w.dispatch(ShellEvent(action="deleted", path="/a.txt"))
    w.dispatch(ShellEvent(action="deleted", path="/b.txt"))
    w._poll_events()
    time.sleep(0.6)
    w.dispatch(ShellEvent(action="deleted", path="/a.txt"))
    w._poll_events()
    w.stop()
    assert len(events) == 3


@pytest.mark.unit
def test_stop_prevents_further_dispatch():
    events = []
    w = ShellWatcher()
    w.start(lambda e: events.append(e))
    w.stop()
    w.dispatch(ShellEvent(action="created", path="/x.txt"))
    w._poll_events()
    assert len(events) == 0


@pytest.mark.unit
def test_shell_delete_dispatches_even_when_pidl_path_decode_fails():
    """P0: Shell event must dispatch action even if PIDL path decode fails."""
    events = []
    w = ShellWatcher(debounce_ms=0)
    w.start(lambda e: events.append(e))
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
    w.dispatch(ShellEvent(action="deleted", path=None))
    w.dispatch(ShellEvent(action="deleted", path=None))
    w._poll_events()
    w.stop()
    assert len(events) == 1


# ── integration tests ───────────────────────────────────────────────────────

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
def test_real_shell_create_broadcast(qapp, test_temp_root):
    """Real SHCNE_CREATE broadcast must reach callback."""
    import sys, ctypes, os, time
    if not sys.platform.startswith("win"):
        pytest.skip("Windows-only")
    from shell_watcher import SHCNE_CREATE
    shell32 = ctypes.windll.shell32
    # Retry up to 3 times to handle RegisterClassW resource contention
    for attempt in range(3):
        w = ShellWatcher(debounce_ms=0)
        got = []
        w.start(lambda e: got.append((e.action, str(e.path) if e.path else None)))
        if w.registered:
            break
        w.stop()
        time.sleep(0.2)
    assert w.registered, "Failed to register after 3 attempts"
    p = test_temp_root / "shell_create_test.txt"
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
    shell32.SHChangeNotify(SHCNE_CREATE, 0, pidl, None)
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
        "real SHCNE_CREATE must reach callback"


@pytest.mark.integration
def test_real_shell_delete_broadcast(qapp, test_temp_root):
    """Real SHCNE_DELETE broadcast must reach callback."""
    import sys, ctypes, os, time
    if not sys.platform.startswith("win"):
        pytest.skip("Windows-only")
    from shell_watcher import SHCNE_DELETE
    shell32 = ctypes.windll.shell32
    for attempt in range(3):
        w = ShellWatcher(debounce_ms=0)
        got = []
        w.start(lambda e: got.append((e.action, str(e.path) if e.path else None)))
        if w.registered:
            break
        w.stop()
        time.sleep(0.2)
    assert w.registered, "Failed to register after 3 attempts"
    p = test_temp_root / "shell_delete_test.txt"
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
    shell32.SHChangeNotify(SHCNE_DELETE, 0, pidl, None)
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
    assert any(e[0] == "deleted" for e in result.get("got", [])), \
        "real SHCNE_DELETE must reach callback"


@pytest.mark.integration
def test_real_shell_mkdir_broadcast(qapp, test_temp_root):
    """Real SHCNE_MKDIR broadcast must reach callback."""
    import sys, ctypes, os, time
    if not sys.platform.startswith("win"):
        pytest.skip("Windows-only")
    from shell_watcher import SHCNE_MKDIR
    shell32 = ctypes.windll.shell32
    for attempt in range(3):
        w = ShellWatcher(debounce_ms=0)
        got = []
        w.start(lambda e: got.append((e.action, str(e.path) if e.path else None)))
        if w.registered:
            break
        w.stop()
        time.sleep(0.2)
    assert w.registered, "Failed to register after 3 attempts"
    # Create a directory to get a PIDL
    d = test_temp_root / "shell_mkdir_test"
    d.mkdir()
    pidl = ctypes.c_void_p()
    attr = ctypes.c_ulong()
    shell32.SHParseDisplayName.restype = ctypes.c_long
    shell32.SHParseDisplayName.argtypes = [ctypes.c_wchar_p, ctypes.c_void_p,
                                           ctypes.POINTER(ctypes.c_void_p),
                                           ctypes.c_ulong, ctypes.POINTER(ctypes.c_ulong)]
    shell32.SHParseDisplayName(str(d), None, ctypes.byref(pidl), 0, ctypes.byref(attr))
    shell32.SHChangeNotify.restype = None
    shell32.SHChangeNotify.argtypes = [ctypes.c_ulong, ctypes.c_uint,
                                       ctypes.c_void_p, ctypes.c_void_p]
    shell32.SHChangeNotify(SHCNE_MKDIR, 0, pidl, None)
    result = {}
    def check():
        w._poll_events()
        result["got"] = list(got)
        w.stop()
        d.rmdir()
        qapp.exit()
    from PyQt5.QtCore import QTimer
    QTimer.singleShot(1500, check)
    qapp.exec_()
    assert any(e[0] == "dir_created" for e in result.get("got", [])), \
        "real SHCNE_MKDIR must reach callback as dir_created"


@pytest.mark.integration
def test_real_shell_rmdir_broadcast(qapp, test_temp_root):
    """Real SHCNE_RMDIR broadcast must reach callback."""
    import sys, ctypes, os, time
    if not sys.platform.startswith("win"):
        pytest.skip("Windows-only")
    from shell_watcher import SHCNE_RMDIR
    shell32 = ctypes.windll.shell32
    for attempt in range(3):
        w = ShellWatcher(debounce_ms=0)
        got = []
        w.start(lambda e: got.append((e.action, str(e.path) if e.path else None)))
        if w.registered:
            break
        w.stop()
        time.sleep(0.2)
    assert w.registered, "Failed to register after 3 attempts"
    # Create and then remove a directory
    d = test_temp_root / "shell_rmdir_test"
    d.mkdir()
    pidl = ctypes.c_void_p()
    attr = ctypes.c_ulong()
    shell32.SHParseDisplayName.restype = ctypes.c_long
    shell32.SHParseDisplayName.argtypes = [ctypes.c_wchar_p, ctypes.c_void_p,
                                           ctypes.POINTER(ctypes.c_void_p),
                                           ctypes.c_ulong, ctypes.POINTER(ctypes.c_ulong)]
    shell32.SHParseDisplayName(str(d), None, ctypes.byref(pidl), 0, ctypes.byref(attr))
    shell32.SHChangeNotify.restype = None
    shell32.SHChangeNotify.argtypes = [ctypes.c_ulong, ctypes.c_uint,
                                       ctypes.c_void_p, ctypes.c_void_p]
    shell32.SHChangeNotify(SHCNE_RMDIR, 0, pidl, None)
    result = {}
    def check():
        w._poll_events()
        result["got"] = list(got)
        w.stop()
        qapp.exit()
    from PyQt5.QtCore import QTimer
    QTimer.singleShot(1500, check)
    qapp.exec_()
    assert any(e[0] == "dir_removed" for e in result.get("got", [])), \
        "real SHCNE_RMDIR must reach callback as dir_removed"
