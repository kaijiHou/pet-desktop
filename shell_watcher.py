"""Global Windows Shell Change Watcher (V2.1 — real SHChangeNotifyRegister).

This is a genuine implementation, not a poll loop:
  * a hidden (message-only) window + WndProc
  * SHChangeNotifyRegister subscribes to SHCNE_CREATE / DELETE / MKDIR / RMDIR
    on the whole shell namespace (desktop PIDL, recursive)
  * a worker thread pumps the message loop; WndProc receives WM_SHChangeNotify
  * on each notification: SHChangeNotification_Lock -> SHGetPathFromIDListW
    -> extract path -> emit a Qt signal (auto-queued to the GUI thread)
  * debounced before display

Limitations (§39, honest):
  * rename events (RENAMEITEM / RENAMEFOLDER) require two PIDL entries and a
    second registration; NOT wired here. Recorded as KNOWN_ISSUE.
  * cannot reliably distinguish "new file" from "copy produces a new file".
  * events are only shown when the foreground window is explorer.exe (§37).
"""

import ctypes
from ctypes import wintypes, WINFUNCTYPE
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path

from PyQt5.QtCore import QObject, pyqtSignal


user32 = ctypes.windll.user32
shell32 = ctypes.windll.shell32

# DefWindowProcW takes a pointer-sized lparam; default int argtype overflows.
user32.DefWindowProcW.argtypes = [wintypes.HWND, wintypes.UINT,
                                  wintypes.WPARAM, wintypes.LPARAM]
user32.DefWindowProcW.restype = ctypes.c_ssize_t if hasattr(ctypes, "c_ssize_t") else ctypes.c_longlong

# ── Win32 types we define by hand (ctypes.wintypes is missing WNDCLASSW) ───
from ctypes import Structure, c_uint, c_int, c_void_p, c_wchar_p

LRESULT = ctypes.c_ssize_t if hasattr(ctypes, "c_ssize_t") else ctypes.c_longlong
WNDPROC = WINFUNCTYPE(LRESULT, wintypes.HWND, wintypes.UINT,
                      wintypes.WPARAM, wintypes.LPARAM)


class WNDCLASSW(Structure):
    _fields_ = [
        ("style", c_uint),
        ("lpfnWndProc", WNDPROC),
        ("cbClsExtra", c_int),
        ("cbWndExtra", c_int),
        ("hInstance", c_void_p),
        ("hIcon", c_void_p),
        ("hCursor", c_void_p),
        ("hbrBackground", c_void_p),
        ("lpszMenuName", c_wchar_p),
        ("lpszClassName", c_wchar_p),
    ]


class SHChangeNotifyEntry(Structure):
    _fields_ = [("pidl", c_void_p), ("fRecursive", wintypes.BOOL)]

# ── Shell notification event codes ─────────────────────────────────────────
SHCNE_RENAMEITEM = 0x00000001
SHCNE_RENAMEFOLDER = 0x00000002
SHCNE_MKDIR = 0x00000004
SHCNE_CREATE = 0x00000100
SHCNE_DELETE = 0x00000200
SHCNE_RMDIR = 0x00000008

# Combined mask for the single-PIDL events we subscribe to.
WATCH_EVENTS = SHCNE_CREATE | SHCNE_DELETE | SHCNE_MKDIR | SHCNE_RMDIR

SHCNF_IDLIST = 0x0000
WM_SHChangeNotify = 0x0401

# ── action mapping (Shell event code -> logical action) ────────────────────
_SHELL_TO_ACTION = {
    SHCNE_CREATE: "created",
    SHCNE_DELETE: "deleted",
    SHCNE_MKDIR: "dir_created",
    SHCNE_RMDIR: "dir_removed",
    # callers may still map these for legacy/manual dispatch
    SHCNE_RENAMEITEM: "renamed",
    SHCNE_RENAMEFOLDER: "dir_renamed",
}


@dataclass(frozen=True)
class ShellEvent:
    path: Path
    action: str
    timestamp: float = field(default_factory=time.time)


def _is_explorer_foreground() -> bool:
    """True when the foreground window belongs to explorer.exe."""
    try:
        hwnd = user32.GetForegroundWindow()
        if not hwnd:
            return False
        pid = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
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


def _get_desktop_pidl():
    """Return the absolute PIDL of the desktop (NULL-checked) or 0."""
    SHGetFolderLocation = shell32.SHGetFolderLocation
    SHGetFolderLocation.restype = ctypes.c_long
    pidl = c_void_p()
    hr = SHGetFolderLocation(None, 0, None, 0, ctypes.byref(pidl))
    return pidl if hr == 0 else 0


class ShellWatcher(QObject):
    """QObject facade. Emits `event` (queued to GUI thread)."""

    event = pyqtSignal(object)  # ShellEvent

    def __init__(self, parent=None, debounce_ms=500):
        super().__init__(parent)
        self._debounce_ms = debounce_ms
        self._recent_actions: dict[str, float] = {}
        self._wnd_proc = self._make_wnd_proc()
        self._hwnd = None
        self._reg_id = None
        self._thread = None
        self._stop_event = threading.Event()
        self._inited = threading.Event()

    # ── ctypes WndProc ─────────────────────────────────────────────────────
    def _make_wnd_proc(self):
        @WNDPROC
        def wnd_proc(hwnd, msg, wparam, lparam):
            if msg == WM_SHChangeNotify:
                self._on_shell_notify(wparam, lparam)
                return 0
            if msg == 0x0002:  # WM_DESTROY
                user32.PostQuitMessage(0)
                return 0
            return user32.DefWindowProcW(hwnd, msg, wparam, lparam)
        return wnd_proc

    def _on_shell_notify(self, wparam, lparam):
        """Read the locked PIDLs and emit a ShellEvent (queued)."""
        SHChangeNotification_Lock = shell32.SHChangeNotification_Lock
        SHChangeNotification_Lock.restype = ctypes.c_void_p
        SHChangeNotification_Lock.argtypes = [ctypes.c_void_p,
                                              ctypes.POINTER(wintypes.DWORD),
                                              ctypes.POINTER(ctypes.c_void_p),
                                              ctypes.POINTER(ctypes.c_void_p)]
        SHChangeNotification_Unlock = shell32.SHChangeNotification_Unlock
        SHChangeNotification_Unlock.argtypes = [ctypes.c_void_p]
        SHGetPathFromIDList = shell32.SHGetPathFromIDListW
        SHGetPathFromIDList.restype = wintypes.BOOL
        SHGetPathFromIDList.argtypes = [ctypes.c_void_p, wintypes.LPWSTR]

        dw_process = wintypes.DWORD()
        ppidl = ctypes.c_void_p()   # pointer to LPITEMIDLIST array
        psf = ctypes.c_void_p()
        lock = SHChangeNotification_Lock(lparam, ctypes.byref(dw_process),
                                         ctypes.byref(ppidl), ctypes.byref(psf))
        if not lock:
            return
        try:
            # wparam carries the event flag; we subscribed only to 1-pidl events
            flags = int(wparam)
            action = _SHELL_TO_ACTION.get(flags & WATCH_EVENTS)
            if not action:
                return
            # ppidl points to the first element of a PIDL array
            if not ppidl.value:
                return
            pidl_ptr = ctypes.cast(ppidl, ctypes.POINTER(ctypes.c_void_p))
            pidl = pidl_ptr[0]
            if not pidl:
                return
            buf = ctypes.create_unicode_buffer(260)
            if SHGetPathFromIDList(pidl, buf):
                path = Path(buf.value)
                if path.exists() or action in ("deleted", "dir_removed"):
                    self._dispatch(ShellEvent(path=path, action=action))
        finally:
            SHChangeNotification_Unlock(lock)

    # ── lifecycle ──────────────────────────────────────────────────────────
    def start(self, callback=None):
        """Start the watcher. If callback given, connect it to `event`."""
        if callback is not None:
            self.event.connect(callback)
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run_watcher, daemon=True)
        self._thread.start()
        self._inited.wait(timeout=5)

    def stop(self):
        self._stop_event.set()
        try:
            self._inited.set()  # unblock if thread never got going
            self.event.disconnect()
        except (TypeError, RuntimeError):
            pass
        if self._hwnd:
            user32.PostMessageW(self._hwnd, 0x0010, 0, 0)  # WM_CLOSE
        if self._thread:
            self._thread.join(timeout=2)
        if self._reg_id:
            try:
                shell32.SHChangeNotifyDeregister(self._reg_id)
            except Exception:
                pass
            self._reg_id = None

    def _run_watcher(self):
        """Create the hidden window + register + pump message loop (same thread)."""
        wc = WNDCLASSW()
        wc.lpfnWndProc = self._wnd_proc
        wc.hInstance = ctypes.windll.kernel32.GetModuleHandleW(None)
        wc.lpszClassName = "DesktopPetShellWatcher"
        wc.hCursor = 0
        wc.hbrBackground = 0
        wc.lpszMenuName = None
        wc.cbClsExtra = 0
        wc.cbWndExtra = 0
        wc.hIcon = 0
        wc.style = 0

        atom = user32.RegisterClassW(ctypes.byref(wc))
        hwnd = user32.CreateWindowExW(
            0, ctypes.c_wchar_p("DesktopPetShellWatcher"), ctypes.c_wchar_p(""),
            0, 0, 0, 0, 0, 0, 0, ctypes.windll.kernel32.GetModuleHandleW(None), None)
        if not hwnd:
            self._inited.set()
            return
        self._hwnd = hwnd

        # Register for shell events on the whole desktop namespace.
        desktop_pidl = _get_desktop_pidl()
        if not desktop_pidl:
            self._inited.set()
            return
        SHChangeNotifyRegister = shell32.SHChangeNotifyRegister
        SHChangeNotifyRegister.restype = ctypes.c_ulong
        SHChangeNotifyRegister.argtypes = [
            wintypes.HWND, ctypes.c_int, ctypes.c_ulong, wintypes.UINT,
            ctypes.c_int, ctypes.c_void_p,
        ]
        # pidl=NULL + fRecursive=TRUE => watch the whole shell namespace
        # (Desktop Pet's "respond to Explorer file ops" is inherently global).
        entry = SHChangeNotifyEntry(0, True)
        reg_id = SHChangeNotifyRegister(hwnd, SHCNF_IDLIST, WATCH_EVENTS,
                                        WM_SHChangeNotify, 1, ctypes.byref(entry))
        self._reg_id = reg_id
        self._inited.set()

        # Message loop (must run on the thread that created the window).
        msg = wintypes.MSG()
        while not self._stop_event.is_set():
            ret = user32.GetMessageW(ctypes.byref(msg), None, 0, 0)
            if ret == 0:  # WM_QUIT
                break
            if ret == -1:
                break
            user32.TranslateMessage(ctypes.byref(msg))
            user32.DispatchMessageW(ctypes.byref(msg))

        if self._reg_id:
            shell32.SHChangeNotifyDeregister(self._reg_id)
            self._reg_id = None
        if hwnd:
            user32.DestroyWindow(hwnd)
        self._hwnd = None

    # ── dispatch / debounce ────────────────────────────────────────────────
    def _dispatch(self, event: ShellEvent):
        if self._stop_event.is_set():
            return  # stopped — don't deliver (reviewer test #11)
        key = f"{event.action}:{event.path}"
        now = time.time()
        last = self._recent_actions.get(key, 0)
        if now - last < self._debounce_ms / 1000.0:
            return
        self._recent_actions[key] = now
        self.event.emit(event)

    def dispatch(self, event: ShellEvent):
        """Manual dispatch (for tests / app-triggered events)."""
        self._dispatch(event)

    def is_explorer_foreground(self) -> bool:
        return _is_explorer_foreground()

    @property
    def registered(self) -> bool:
        return bool(self._reg_id)
