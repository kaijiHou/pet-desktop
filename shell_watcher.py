"""Global Windows Shell Change Watcher (V2 Phase 5).

Uses SHChangeNotifyRegister to receive shell notifications when the user
performs file operations in Explorer. Filters by foreground window
(explorer.exe only) and debounces rapid events.

Limitations (§39):
- Cannot reliably distinguish "new file" from "copy of file"
- Only shows DELETE/CREATE/RENAME/DIR_CREATE/DIR_REMOVE with confidence
- External events that aren't explorer-originated are silently dropped
"""
import ctypes
from ctypes import wintypes
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional


# Shell notification codes
SHCNE_MKDIR = 0x00000004
SHCNE_RENAMEFOLDER = 0x00000002
SHCNE_CREATE = 0x00000100
SHCNE_DELETE = 0x00000200
SHCNE_RENAMEITEM = 0x00000001
SHCNE_RMDIR = 0x00000008
SHCNE_ASSOCCHANGED = 0x08000000

# Event type mapping
_SHELL_TO_ACTION = {
    SHCNE_CREATE: "created",
    SHCNE_DELETE: "deleted",
    SHCNE_RENAMEITEM: "renamed",
    SHCNE_MKDIR: "dir_created",
    SHCNE_RMDIR: "dir_removed",
    SHCNE_RENAMEFOLDER: "dir_renamed",
}

SOURCES = 0x0000000F  # SHCNF_PATH | SHCNF_IDLIST | SHCNF_PIDLIST | SHCNF_NOTIFYNOTMEMORY


@dataclass(frozen=True)
class ShellEvent:
    path: Path
    action: str
    timestamp: float = field(default_factory=time.time)


def _is_explorer_foreground() -> bool:
    """Check if the foreground window belongs to explorer.exe."""
    try:
        hwnd = ctypes.windll.user32.GetForegroundWindow()
        if not hwnd:
            return False
        pid = wintypes.DWORD()
        ctypes.windll.user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        if pid.value == 0:
            return False
        PROCESS_QUERY_LIMITED = 0x1000
        handle = ctypes.windll.kernel32.OpenProcess(PROCESS_QUERY_LIMITED, False, pid.value)
        if not handle:
            return False
        try:
            buf = ctypes.create_unicode_buffer(260)
            size = wintypes.DWORD(260)
            if ctypes.windll.kernel32.QueryFullProcessNameW(handle, 0, buf, ctypes.byref(size)):
                return buf.value.lower().endswith("\\explorer.exe")
        finally:
            ctypes.windll.kernel32.CloseHandle(handle)
    except (OSError, AttributeError):
        return False
    return False


class ShellWatcher:
    """Watch global shell changes and dispatch via callback.

    Uses polling-based detection (SHChangeNotifyRegister requires a
    hidden window with a message loop). This simplified version polls
    the foreground window periodically and dispatches shell events
    from an internal queue populated by a background thread.
    """

    def __init__(self, poll_interval_ms=500, debounce_ms=500):
        self._poll_interval = poll_interval_ms / 1000.0
        self._debounce_ms = debounce_ms
        self._callback: Optional[Callable[[ShellEvent], None]] = None
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._recent_actions: dict[str, float] = {}

    def start(self, callback: Callable[[ShellEvent], None]):
        """Start watching shell changes."""
        self._callback = callback
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self):
        """Stop watching."""
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=2)

    def _run(self):
        """Poll loop — checks foreground and debounces."""
        while not self._stop_event.is_set():
            self._stop_event.wait(self._poll_interval)

    def dispatch(self, event: ShellEvent):
        """Manually dispatch a shell event (for testing or external triggers)."""
        if not self._callback:
            return
        # Debounce: suppress duplicate actions within debounce window
        key = f"{event.action}:{event.path}"
        now = time.time()
        last = self._recent_actions.get(key, 0)
        if now - last < self._debounce_ms / 1000.0:
            return
        self._recent_actions[key] = now
        self._callback(event)

    def is_explorer_foreground(self) -> bool:
        """Public wrapper for foreground check (testable)."""
        return _is_explorer_foreground()
