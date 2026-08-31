"""Active Explorer Watcher — monitors the current foreground Explorer directory.

Uses SetWinEventHook to detect foreground changes, then reads the Explorer
path via Shell.Application COM, and watches that directory with
ReadDirectoryChangesW.
"""
from __future__ import annotations

import ctypes
import ctypes.wintypes as wintypes
import logging
import threading
import time
from pathlib import Path
from typing import Callable, Optional

from PyQt5.QtCore import QObject, pyqtSignal

from .file_event import FileSemanticEvent

LOGGER = logging.getLogger("pet.explorer_watch")

# Win32 constants
EVENT_SYSTEM_FOREGROUND = 0x0003
WINEVENT_OUTOFCONTEXT = 0x0000
WINEVENT_SKIPOWNPROCESS = 0x0002


def _get_foreground_hwnd() -> int:
    """Get the current foreground window handle."""
    user32 = ctypes.windll.user32
    return user32.GetForegroundWindow()


def _get_window_pid(hwnd: int) -> int:
    """Get the process ID of a window."""
    pid = wintypes.DWORD()
    ctypes.windll.user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    return pid.value


def _is_explorer_window(hwnd: int) -> bool:
    """Check if a window belongs to explorer.exe."""
    try:
        pid = _get_window_pid(hwnd)
        if pid == 0:
            return False
        PROCESS_QUERY_LIMITED = 0x1000
        handle = ctypes.windll.kernel32.OpenProcess(PROCESS_QUERY_LIMITED, False, pid)
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


def _get_explorer_path(hwnd: int) -> Optional[Path]:
    """Try to get the current directory of an Explorer window."""
    try:
        import win32com.client
        shell = win32com.client.Dispatch("Shell.Application")
        windows = shell.Windows()
        for i in range(windows.Count):
            w = windows.Item(i)
            if w is None:
                continue
            if w.HWND == hwnd:
                url = w.LocationURL
                if url and url.startswith("file:///"):
                    path_str = url[8:].replace("/", "\\")
                    from urllib.parse import unquote
                    path_str = unquote(path_str)
                    p = Path(path_str)
                    if p.is_dir():
                        return p
                # Fallback: try LocationPath
                loc = w.LocationPath
                if loc:
                    p = Path(loc)
                    if p.is_dir():
                        return p
    except Exception:
        pass
    return None


class ActiveExplorerWatcher(QObject):
    """Monitors the current foreground Explorer directory.

    When the foreground window is Explorer:
    1. Get its current directory path
    2. Watch that directory with ReadDirectoryChangesW
    3. Emit semantic events for file operations
    """

    event = pyqtSignal(object)  # FileSemanticEvent

    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_hwnd: int = 0
        self._current_path: Optional[Path] = None
        self._watching = False
        self._hook = None
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        # For path polling fallback
        self._poll_timer = None

    def start(self):
        """Start monitoring foreground Explorer windows."""
        if self._hook is not None:
            return
        # Set up WinEventHook for foreground changes
        WINEVENTPROC = ctypes.WINFUNCTYPE(
            None, wintypes.HANDLE, wintypes.DWORD,
            wintypes.HWND, wintypes.LONG, wintypes.LONG,
            wintypes.DWORD, wintypes.DWORD
        )
        self._hook_proc = WINEVENTPROC(self._on_foreground_change)
        self._hook = ctypes.windll.user32.SetWinEventHook(
            EVENT_SYSTEM_FOREGROUND, EVENT_SYSTEM_FOREGROUND,
            None, self._hook_proc, 0, 0,
            WINEVENT_OUTOFCONTEXT | WINEVENT_SKIPOWNPROCESS
        )
        if not self._hook:
            LOGGER.error("SetWinEventHook failed")
            return
        LOGGER.info("ActiveExplorerWatcher started (hook=%s)", self._hook)
        # Check current foreground immediately
        self._check_foreground()

    def stop(self):
        """Stop monitoring."""
        self._stop_event.set()
        if self._hook:
            ctypes.windll.user32.UnhookWinEvent(self._hook)
            self._hook = None
        self._current_hwnd = 0
        self._current_path = None
        self._watching = False
        LOGGER.info("ActiveExplorerWatcher stopped")

    def _on_foreground_change(self, hwnd, event, hwnd_obj, idObject, idChild, dwEventThread, dwmsEventTime):
        """Callback when foreground window changes."""
        if self._stop_event.is_set():
            return
        self._check_foreground()

    def _check_foreground(self):
        """Check if the current foreground is an Explorer window."""
        hwnd = _get_foreground_hwnd()
        if hwnd == self._current_hwnd:
            return
        self._current_hwnd = hwnd
        if _is_explorer_window(hwnd):
            path = _get_explorer_path(hwnd)
            if path and path != self._current_path:
                self._current_path = path
                LOGGER.info("Explorer directory changed: %s", path)
                # Emit a directory change event
                self.event.emit(FileSemanticEvent(
                    action="directory_changed",
                    path=path,
                    is_dir=True,
                    source="explorer_watch",
                ))
        else:
            if self._current_path is not None:
                LOGGER.debug("Foreground left Explorer")
                self._current_path = None

    @property
    def current_path(self) -> Optional[Path]:
        return self._current_path

    @property
    def is_explorer_foreground(self) -> bool:
        return _is_explorer_window(_get_foreground_hwnd())
