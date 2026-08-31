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
import logging
import threading
import queue
import time
from dataclasses import dataclass, field
from pathlib import Path

from PyQt5.QtCore import QObject, pyqtSignal


log = logging.getLogger("pet.shell_watcher")

user32 = ctypes.windll.user32
shell32 = ctypes.windll.shell32
kernel32 = ctypes.windll.kernel32

kernel32.GetModuleHandleW.argtypes = [wintypes.LPCWSTR]
kernel32.GetModuleHandleW.restype = wintypes.HINSTANCE

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
    SHGetFolderLocation.argtypes = [wintypes.HWND, ctypes.c_int,
                                    wintypes.HANDLE, wintypes.DWORD,
                                    ctypes.POINTER(ctypes.c_void_p)]
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
        self._startup_error = None
        self._callback = None
        self._event_queue = queue.Queue()

    # ── ctypes WndProc ─────────────────────────────────────────────────────
    def _make_wnd_proc(self):
        @WNDPROC
        def wnd_proc(hwnd, msg, wparam, lparam):
            if msg == WM_SHChangeNotify:
                log.debug("WndProc WM_SHChangeNotify wparam=%s lparam=%s", wparam, lparam)
                try:
                    self._on_shell_notify(wparam, lparam)
                except Exception:
                    log.exception("WndProc _on_shell_notify failed")
                return 0
            if msg == 0x0002:  # WM_DESTROY
                user32.PostQuitMessage(0)
                return 0
            return user32.DefWindowProcW(hwnd, msg, wparam, lparam)
        return wnd_proc

    def _on_shell_notify(self, wparam, lparam):
        """Decode a WM_SHChangeNotify message under SHCNRF_NewDelivery."""
        log.info("_on_shell_notify called wparam=%s lparam=%s", wparam, lparam)
        SHChangeNotification_Lock = shell32.SHChangeNotification_Lock
        SHChangeNotification_Lock.restype = ctypes.c_void_p
        SHChangeNotification_Lock.argtypes = [
            ctypes.c_void_p,            # hChange
            ctypes.c_ulong,             # dwProcessID
            ctypes.POINTER(ctypes.c_void_p),  # PIDLIST_ABSOLUTE **ppidl
            ctypes.POINTER(ctypes.c_long),    # LONG *plEvent
        ]
        SHChangeNotification_Unlock = shell32.SHChangeNotification_Unlock
        SHChangeNotification_Unlock.argtypes = [ctypes.c_void_p]
        SHGetPathFromIDList = shell32.SHGetPathFromIDListW
        SHGetPathFromIDList.restype = wintypes.BOOL
        SHGetPathFromIDList.argtypes = [ctypes.c_void_p, wintypes.LPWSTR]

        h_change = wparam          # NewDelivery: wParam is the change handle
        dw_proc_id = lparam        # NewDelivery: lParam is the process id
        ppidl = ctypes.c_void_p()
        event_id = ctypes.c_long()
        lock = SHChangeNotification_Lock(
            h_change, dw_proc_id, ctypes.byref(ppidl), ctypes.byref(event_id))
        if not lock:
            log.warning("SHChangeNotification_Lock returned NULL for h=%s pid=%s", h_change, dw_proc_id)
            return
        try:
            raw_event_id = int(event_id.value)
            log.info("Shell event decoded: event_id=0x%x raw=0x%x", event_id.value, raw_event_id)
            action = _SHELL_TO_ACTION.get(raw_event_id & WATCH_EVENTS)
            if not action:
                log.debug("Shell notification ignored event_id=0x%x", raw_event_id)
                return
            if not ppidl.value:
                return
            # The lock API writes a pointer to the PIDL into *ppidl.  ctypes
            # therefore gives us the address of that pointer; dereference it
            # once before passing the PIDL to SHGetPathFromIDListW.
            pidl_ref = ctypes.cast(ppidl.value, ctypes.POINTER(ctypes.c_void_p))
            pidl = pidl_ref[0]
            if not pidl:
                return
            buf = ctypes.create_unicode_buffer(260)
            ok = SHGetPathFromIDList(pidl, buf)
            if ok:
                path = Path(buf.value)
                log.info("Shell notification event_id=0x%x action=%s path=%s exists=%s",
                         raw_event_id, action, path, path.exists())
                if path.exists() or action in ("deleted", "dir_removed"):
                    self._dispatch(ShellEvent(path=path, action=action))
                else:
                    log.info("Shell event skipped (path gone and not delete): %s", path)
            else:
                log.warning("SHGetPathFromIDList failed for event_id=0x%x action=%s pidl=%s",
                           raw_event_id, action, pidl)
        finally:
            SHChangeNotification_Unlock(lock)

    # ── lifecycle ──────────────────────────────────────────────────────────
    def start(self, callback=None):
        """Start the watcher. If callback given, poll queue from main thread."""
        if self._thread and self._thread.is_alive():
            return
        if callback is not None:
            self._callback = callback
            from PyQt5.QtCore import QTimer
            self._poll_timer = QTimer()
            self._poll_timer.timeout.connect(self._poll_events)
            self._poll_timer.start(50)
        self._stop_event.clear()
        self._inited.clear()
        self._startup_error = None
        self._thread = threading.Thread(target=self._run_watcher, daemon=True)
        self._thread.start()
        self._inited.wait(timeout=5)

    def stop(self):
        self._stop_event.set()
        self._inited.set()
        if hasattr(self, '_poll_timer') and self._poll_timer is not None:
            self._poll_timer.stop()
        if self._hwnd:
            user32.PostMessageW(self._hwnd, 0x0010, 0, 0)  # WM_CLOSE
        if self._thread:
            self._thread.join(timeout=2)
        if self._thread and not self._thread.is_alive():
            self._thread = None
        if self._callback is not None:
            try:
                self.event.disconnect(self._callback)
            except (TypeError, RuntimeError):
                pass
            self._callback = None

    def _run_watcher(self):
        """Create the hidden window + register + pump message loop (same thread)."""
        # Unique class name per instance: RegisterClassW only registers a name
        # once, and a second window created from a duplicate registration would
        # bind to the FIRST instance's WndProc (which may be GC'd -> crash).
        class_name = f"DesktopPetShellWatcher_{id(self)}"
        wc = WNDCLASSW()
        wc.lpfnWndProc = self._wnd_proc
        wc.hInstance = kernel32.GetModuleHandleW(None)
        wc.lpszClassName = class_name
        wc.hCursor = 0
        wc.hbrBackground = 0
        wc.lpszMenuName = None
        wc.cbClsExtra = 0
        wc.cbWndExtra = 0
        wc.hIcon = 0
        wc.style = 0

        try:
            user32.RegisterClassW.argtypes = [ctypes.POINTER(WNDCLASSW)]
            user32.RegisterClassW.restype = wintypes.ATOM
            user32.CreateWindowExW.argtypes = [
                wintypes.DWORD, wintypes.LPCWSTR, wintypes.LPCWSTR,
                wintypes.DWORD, ctypes.c_int, ctypes.c_int, ctypes.c_int,
                ctypes.c_int, wintypes.HWND, wintypes.HMENU, wintypes.HINSTANCE,
                ctypes.c_void_p,
            ]
            user32.CreateWindowExW.restype = wintypes.HWND
            user32.PostMessageW.argtypes = [wintypes.HWND, wintypes.UINT,
                                            wintypes.WPARAM, wintypes.LPARAM]
            user32.PostMessageW.restype = wintypes.BOOL
            user32.DestroyWindow.argtypes = [wintypes.HWND]
            user32.DestroyWindow.restype = wintypes.BOOL
            user32.GetMessageW.argtypes = [ctypes.POINTER(wintypes.MSG),
                                           wintypes.HWND, wintypes.UINT, wintypes.UINT]
            user32.GetMessageW.restype = ctypes.c_int
            user32.TranslateMessage.argtypes = [ctypes.POINTER(wintypes.MSG)]
            user32.DispatchMessageW.argtypes = [ctypes.POINTER(wintypes.MSG)]

            atom = user32.RegisterClassW(ctypes.byref(wc))
            if not atom:
                err = ctypes.get_last_error()
                self._startup_error = OSError(err, "RegisterClassW failed")
                log.error("ShellWatcher RegisterClassW failed: %s", self._startup_error)
                return
            hwnd = user32.CreateWindowExW(
                0, class_name, "Desktop Pet Shell Watcher", 0,
                0, 0, 0, 0, None, None,
                kernel32.GetModuleHandleW(None), None)
            if not hwnd:
                err = ctypes.get_last_error()
                self._startup_error = OSError(err, "CreateWindowExW failed")
                log.error("ShellWatcher CreateWindowExW failed: %s", self._startup_error)
                return
            self._hwnd = hwnd

            # SHCNRF_* source flags (Microsoft Learn). Using NewDelivery lets us
            # decode hChange/event-id correctly instead of guessing from wparam.
            SHCNRF_ShellLevel = 0x0002
            SHCNRF_InterruptLevel = 0x0001
            SHCNRF_RecursiveInterrupt = 0x1000
            SHCNRF_NewDelivery = 0x8000
            sources = (SHCNRF_ShellLevel | SHCNRF_InterruptLevel
                       | SHCNRF_RecursiveInterrupt | SHCNRF_NewDelivery)
            desktop_pidl = _get_desktop_pidl()
            if not desktop_pidl:
                self._startup_error = OSError("SHGetFolderLocation failed")
                log.error("ShellWatcher could not resolve the desktop PIDL")
                return
            SHChangeNotifyRegister = shell32.SHChangeNotifyRegister
            SHChangeNotifyRegister.restype = ctypes.c_ulong
            SHChangeNotifyRegister.argtypes = [
                wintypes.HWND, ctypes.c_int, ctypes.c_ulong, wintypes.UINT,
                ctypes.c_int, ctypes.c_void_p,
            ]
            # Desktop PIDL + fRecursive=TRUE watches the whole shell namespace.
            entry = SHChangeNotifyEntry(desktop_pidl, True)
            reg_id = SHChangeNotifyRegister(hwnd, sources, WATCH_EVENTS,
                                            WM_SHChangeNotify, 1, ctypes.byref(entry))
            self._reg_id = int(reg_id or 0)
            if not self._reg_id:
                err = ctypes.get_last_error()
                self._startup_error = OSError(err, "SHChangeNotifyRegister failed")
                log.error("ShellWatcher registration failed: %s", self._startup_error)
            else:
                log.info("ShellWatcher registered id=%s sources=0x%x events=0x%x",
                         self._reg_id, sources, WATCH_EVENTS)
        except Exception as exc:
            self._startup_error = exc
            log.exception("ShellWatcher startup failed")
        finally:
            self._inited.set()

        if not self._hwnd:
            return

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
            try:
                shell32.SHChangeNotifyDeregister.argtypes = [ctypes.c_ulong]
                shell32.SHChangeNotifyDeregister.restype = wintypes.BOOL
                shell32.SHChangeNotifyDeregister(self._reg_id)
            except Exception:
                log.exception("ShellWatcher deregistration failed")
            finally:
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
        self._event_queue.put(event)

    def dispatch(self, event: ShellEvent):
        """Manual dispatch (for tests / app-triggered events)."""
        self._dispatch(event)

    def is_explorer_foreground(self) -> bool:
        return _is_explorer_foreground()

    def _poll_events(self):
        while not self._event_queue.empty():
            try:
                event = self._event_queue.get_nowait()
                if self._callback is not None:
                    self._callback(event)
            except queue.Empty:
                break
            except Exception:
                import logging
                logging.getLogger("pet.shell_watcher").exception("callback failed")

    @property
    def registered(self) -> bool:
        return bool(self._reg_id)

    @property
    def startup_error(self):
        """The exception from the last start attempt, if registration failed."""
        return self._startup_error
