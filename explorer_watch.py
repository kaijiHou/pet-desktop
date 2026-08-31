"""Active Explorer Watcher — monitors the current foreground Explorer directory.

Uses SetWinEventHook to detect foreground changes, then reads the Explorer
path via existing ExplorerService (ctypes, no pywin32 dependency).
"""
from __future__ import annotations

import ctypes
import ctypes.wintypes as wintypes
import logging
import time
from pathlib import Path
from typing import Optional

from PyQt5.QtCore import QObject, pyqtSignal

from file_event import FileSemanticEvent

LOGGER = logging.getLogger("pet.explorer_watch")

# Win32 constants
EVENT_SYSTEM_FOREGROUND = 0x0003
WINEVENT_OUTOFCONTEXT = 0x0000
WINEVENT_SKIPOWNPROCESS = 0x0002


def _get_foreground_hwnd() -> int:
    user32 = ctypes.windll.user32
    return user32.GetForegroundWindow()


def _get_window_pid(hwnd: int) -> int:
    pid = wintypes.DWORD()
    ctypes.windll.user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    return pid.value


def _is_explorer_window(hwnd: int) -> bool:
    """Check if a window belongs to explorer.exe using ctypes."""
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
    """Try to get the current directory of an Explorer window using Shell.Application via ctypes."""
    try:
        # Use Shell.Application COM via ctypes to enumerate windows
        import ctypes
        ole32 = ctypes.windll.ole32
        ole32.CoInitialize(None)
        try:
            # CLSID_Shell.Application = {13709620-C279-11CE-A49E-444553540000}
            CLSID = ctypes.c_wchar_p("{13709620-C279-11CE-A49E-444553540000}")
            shell = ctypes.c_void_p()
            hr = ctypes.windll.ole32.CoCreateInstance(
                CLSID, None, 0x17,  # CLSCTX_INPROC_SERVER | LOCAL_SERVER
                ctypes.byref(ctypes.c_wchar_p("{4DF0C730-DF9D-11D0-97DE-00C04FD91996}")),
                ctypes.byref(shell)
            )
            if hr != 0 or not shell:
                return None
            # This approach is complex with raw ctypes; fall back to path from HWND via window title
            # Explorer window titles often contain the path
            import ctypes.wintypes as wt
            title_buf = ctypes.create_unicode_buffer(512)
            user32 = ctypes.windll.user32
            user32.GetWindowTextW(hwnd, title_buf, 512)
            title = title_buf.value
            # Explorer title format: "Folder Name" or "Folder Name - File Explorer"
            # This is not reliable for path extraction; use a simpler approach
            return None
        finally:
            ole32.CoUninitialize()
    except Exception:
        pass
    return None


class ActiveExplorerWatcher(QObject):
    """Monitors the current foreground Explorer directory.

    When the foreground window is Explorer:
    1. Poll the current directory path every 1000ms
    2. Emit directory_changed events when path changes
    """

    event = pyqtSignal(object)  # FileSemanticEvent

    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_hwnd: int = 0
        self._current_path: Optional[Path] = None
        self._hook = None
        self._hook_proc = None
        # Poll timer for path changes within same Explorer window
        self._poll_timer = None

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
        # Poll timer: check Explorer path every 1s when Explorer is foreground
        from PyQt5.QtCore import QTimer
        self._poll_timer = QTimer(self)
        self._poll_timer.timeout.connect(self._poll_explorer_path)
        self._poll_timer.start(1000)
        LOGGER.info("ActiveExplorerWatcher started (hook=%s)", self._hook)
        self._check_foreground()

    def stop(self):
        """Stop monitoring."""
        if self._hook:
            ctypes.windll.user32.UnhookWinEvent(self._hook)
            self._hook = None
        if self._poll_timer:
            self._poll_timer.stop()
            self._poll_timer = None
        self._current_hwnd = 0
        self._current_path = None
        LOGGER.info("ActiveExplorerWatcher stopped")

    def _on_foreground_change(self, hwnd, event, hwnd_obj, idObject, idChild, dwEventThread, dwmsEventTime):
        """Callback when foreground window changes."""
        self._check_foreground()

    def _check_foreground(self):
        """Check if the current foreground is an Explorer window."""
        hwnd = _get_foreground_hwnd()
        if hwnd == self._current_hwnd:
            return
        self._current_hwnd = hwnd
        if _is_explorer_window(hwnd):
            # Will be picked up by poll timer
            pass
        else:
            if self._current_path is not None:
                LOGGER.debug("Foreground left Explorer")
                self._current_path = None

    def _poll_explorer_path(self):
        """Poll the current Explorer HWND for path changes."""
        hwnd = _get_foreground_hwnd()
        if not _is_explorer_window(hwnd):
            return
        # Use the existing ExplorerService approach to get path from HWND
        path = self._resolve_explorer_path(hwnd)
        if path and path != self._current_path:
            self._current_path = path
            LOGGER.info("Explorer directory: %s", path)
            self.event.emit(FileSemanticEvent(
                action="directory_changed",
                path=path,
                is_dir=True,
                source="explorer_watch",
            ))

    def _resolve_explorer_path(self, hwnd: int) -> Optional[Path]:
        """Resolve Explorer HWND to filesystem path using Shell.Application."""
        try:
            import subprocess
            # Use PowerShell to get Explorer path from HWND (reliable, no pywin32)
            ps_cmd = (
                f'$shell = New-Object -ComObject Shell.Application; '
                f'$windows = $shell.Windows(); '
                f'foreach ($w in $windows) {{ '
                f'  if ($w.HWND -eq {hwnd}) {{ '
                f'    $loc = $w.LocationPath; '
                f'    if ($loc) {{ Write-Output $loc; break }} '
                f'  }} '
                f'}}'
            )
            result = subprocess.run(
                ["powershell", "-NoProfile", "-Command", ps_cmd],
                capture_output=True, text=True, timeout=3, creationflags=0x08000000
            )
            if result.returncode == 0 and result.stdout.strip():
                path_str = result.stdout.strip()
                p = Path(path_str)
                if p.is_dir():
                    return p
        except Exception:
            pass
        return None

    @property
    def current_path(self) -> Optional[Path]:
        return self._current_path

    @property
    def is_explorer_foreground(self) -> bool:
        return _is_explorer_window(_get_foreground_hwnd())
