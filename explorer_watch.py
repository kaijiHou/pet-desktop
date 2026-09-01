"""Active Explorer Watcher — monitors the current foreground Explorer directory.

Uses SetWinEventHook for foreground changes and a QTimer to poll the
active Explorer HWND path every 1s via a single long-lived COM session.
"""
from __future__ import annotations

import ctypes
import ctypes.wintypes as wintypes
import logging
import subprocess
import threading
import time
from pathlib import Path
from typing import Optional

from PyQt5.QtCore import QObject, QTimer, pyqtSignal

from file_event import FileSemanticEvent

LOGGER = logging.getLogger("pet.explorer_watch")

EVENT_SYSTEM_FOREGROUND = 0x0003
WINEVENT_OUTOFCONTEXT = 0x0000
WINEVENT_SKIPOWNPROCESS = 0x0002


def _get_foreground_hwnd() -> int:
    return ctypes.windll.user32.GetForegroundWindow()


def _get_window_pid(hwnd: int) -> int:
    pid = wintypes.DWORD()
    ctypes.windll.user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    return pid.value


def _is_explorer_window(hwnd: int) -> bool:
    try:
        pid = _get_window_pid(hwnd)
        if pid == 0:
            return False
        handle = ctypes.windll.kernel32.OpenProcess(0x1000, False, pid)
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


# Cached: last Explorer HWND and path
_cached_explorer_hwnd: int = 0
_cached_explorer_path: Optional[Path] = None
_ps_last_result: str = ""
_ps_last_hwnd: int = 0


def _get_explorer_path_ps(hwnd: int) -> Optional[Path]:
    """Resolve Explorer HWND to filesystem path via a single PowerShell call."""
    global _cached_explorer_hwnd, _cached_explorer_path, _ps_last_result, _ps_last_hwnd
    # Cache: same HWND → same result within 1s (polling handles this)
    if hwnd == _ps_last_hwnd and _cached_explorer_path is not None:
        return _cached_explorer_path
    try:
        ps_cmd = (
            f"$s = New-Object -ComObject Shell.Application; "
            f"$w = $s.Windows(); "
            f"foreach ($i in $w) {{ if ($i.HWND -eq {hwnd}) {{ $p = $i.LocationPath; if ($p) {{ Write-Output $p; break }} }} }}"
        )
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command", ps_cmd],
            capture_output=True, text=True, timeout=3,
            creationflags=0x08000000  # CREATE_NO_WINDOW
        )
        _ps_last_hwnd = hwnd
        if result.returncode == 0 and result.stdout.strip():
            p = Path(result.stdout.strip())
            if p.is_dir():
                _cached_explorer_path = p
                return p
        _cached_explorer_path = None
    except Exception as exc:
        LOGGER.debug("Explorer path resolve failed: %s", exc)
    return None


class ActiveExplorerWatcher(QObject):
    """Monitors the current foreground Explorer directory.

    Emits directory_changed events when the active Explorer window
    navigates to a different directory.
    """
    event = pyqtSignal(object)  # FileSemanticEvent

    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_hwnd: int = 0
        self._current_path: Optional[Path] = None
        self._hook = None
        self._hook_proc = None
        self._poll_timer = QTimer(self)
        self._poll_timer.timeout.connect(self._poll_explorer_path)

    def start(self):
        """Start monitoring foreground Explorer windows."""
        if self._hook is not None:
            return
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
        self._poll_timer.start(1000)
        LOGGER.info("ActiveExplorerWatcher started")

    def stop(self):
        if self._hook:
            ctypes.windll.user32.UnhookWinEvent(self._hook)
            self._hook = None
        self._poll_timer.stop()
        self._current_hwnd = 0
        self._current_path = None
        LOGGER.info("ActiveExplorerWatcher stopped")

    def _on_foreground_change(self, hwnd, event, hwnd_obj, idObject, idChild, dwEventThread, dwmsEventTime):
        self._check_foreground()

    def _check_foreground(self):
        hwnd = _get_foreground_hwnd()
        if hwnd == self._current_hwnd:
            return
        self._current_hwnd = hwnd
        if not _is_explorer_window(hwnd):
            if self._current_path is not None:
                self._current_path = None

    def _poll_explorer_path(self):
        """Poll the current Explorer HWND for path changes."""
        hwnd = _get_foreground_hwnd()
        if not _is_explorer_window(hwnd):
            return
        path = _get_explorer_path_ps(hwnd)
        if path and path != self._current_path:
            self._current_path = path
            LOGGER.info("Explorer directory: %s", path)
            self.event.emit(FileSemanticEvent(
                action="directory_changed",
                path=path,
                is_dir=True,
                source="explorer_watch",
            ))

    @property
    def current_path(self) -> Optional[Path]:
        return self._current_path

    @property
    def is_explorer_foreground(self) -> bool:
        return _is_explorer_window(_get_foreground_hwnd())
