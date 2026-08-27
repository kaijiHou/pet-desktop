"""Read the current/last-active directory of a Windows Explorer window.

V2.1 fix (reviewer #2): the D1 bug came from matching ONLY the foreground
window against Shell.Windows(). In practice the user clicks the pet, the
QuickPanel, or the Pocket window first, so the foreground is no longer
Explorer and `current_directory()` returned None — breaking the primary
"复制/移动到当前文件夹" action.

This version keeps a `last_active` directory: whenever the foreground
window is Explorer, we cache its directory. `current_directory()` returns
the *most recent* Explorer directory (falling back to the cached one), so
opening the Pocket panel after focusing Explorer C still targets C.
"""

import ctypes
from pathlib import Path
import subprocess
import time


class ExplorerService:
    """Query Shell.Application, tracking the last-active Explorer folder."""

    def __init__(self, runner=None, foreground_hwnd_provider=None):
        self._runner = runner or subprocess.run
        self._foreground_hwnd = foreground_hwnd_provider or self._get_foreground_hwnd
        # (directory, timestamp) cached whenever Explorer is foreground
        self._last_active: tuple[Path, float] | None = None

    @staticmethod
    def _get_foreground_hwnd():
        try:
            return int(ctypes.windll.user32.GetForegroundWindow())
        except (AttributeError, OSError):
            return 0

    def _foreground_is_explorer(self, hwnd: int) -> bool:
        """Check whether a given HWND belongs to explorer.exe."""
        if not hwnd:
            return False
        try:
            pid = ctypes.wintypes.DWORD()
            ctypes.windll.user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
            if pid.value == 0:
                return False
            PROCESS_QUERY_LIMITED = 0x1000
            handle = ctypes.windll.kernel32.OpenProcess(PROCESS_QUERY_LIMITED, False, pid.value)
            if not handle:
                return False
            try:
                buf = ctypes.create_unicode_buffer(260)
                size = ctypes.wintypes.DWORD(260)
                if ctypes.windll.kernel32.QueryFullProcessNameW(handle, 0, buf, ctypes.byref(size)):
                    return buf.value.lower().endswith("\\explorer.exe")
            finally:
                ctypes.windll.kernel32.CloseHandle(handle)
        except (AttributeError, OSError):
            return False
        return False

    def _directory_for_hwnd(self, hwnd: int):
        """Resolve a foreground Explorer HWND to its directory, or None."""
        if not hwnd:
            return None
        script = (
            "[Console]::OutputEncoding=[Text.UTF8Encoding]::new();"
            f"$fg=[int64]{hwnd};"
            "$shell=New-Object -ComObject Shell.Application;"
            "$window=$shell.Windows() | Where-Object {[int64]$_.HWND -eq $fg} | Select-Object -First 1;"
            "if($window){$path=$window.Document.Folder.Self.Path;"
            "if($path){[Console]::Write($path)}}"
        )
        try:
            result = self._runner(
                ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", script],
                capture_output=True, text=True, encoding="utf-8", errors="replace",
                timeout=5, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
        except (OSError, subprocess.SubprocessError):
            return None
        if result.returncode != 0 or not result.stdout.strip():
            return None
        path = Path(result.stdout.strip()).expanduser().resolve()
        return path if path.is_dir() else None

    def current_directory(self):
        """Return the most-recently-active Explorer directory.

        Resolve the foreground window's directory first (if any). Cache it as
        the last-active Explorer folder **only** when that foreground window is
        actually explorer.exe. When the foreground is something else (e.g. the
        pet / quick panel / pocket panel — the D1 bug), fall back to the cached
        last-active Explorer folder, so the primary "复制/移动到当前文件夹"
        action still targets the folder the user was just working in.
        """
        hwnd = self._foreground_hwnd()
        if hwnd:
            directory = self._directory_for_hwnd(hwnd)
            if directory is not None:
                if self._foreground_is_explorer(hwnd):
                    self._last_active = (directory, time.time())
                return directory
        # Fall back to cached last-active Explorer folder.
        if self._last_active is not None:
            directory, _ = self._last_active
            if directory.is_dir():
                return directory
        return None

    def set_last_active(self, directory):
        """Allow the UI to explicitly record a known Explorer folder."""
        path = Path(directory).expanduser().resolve()
        if path.is_dir():
            self._last_active = (path, time.time())
