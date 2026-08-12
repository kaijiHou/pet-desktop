"""Read the current directory of the foreground Windows Explorer window."""

import ctypes
from pathlib import Path
import subprocess


class ExplorerService:
    """Query Shell.Application without guessing a fallback directory."""

    def __init__(self, runner=None, foreground_hwnd_provider=None):
        self._runner = runner or subprocess.run
        self._foreground_hwnd = foreground_hwnd_provider or self._get_foreground_hwnd

    @staticmethod
    def _get_foreground_hwnd():
        try:
            return int(ctypes.windll.user32.GetForegroundWindow())
        except (AttributeError, OSError):
            return 0

    def current_directory(self):
        hwnd = self._foreground_hwnd()
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
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=5,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
        except (OSError, subprocess.SubprocessError):
            return None
        if result.returncode != 0 or not result.stdout.strip():
            return None
        path = Path(result.stdout.strip()).expanduser().resolve()
        return path if path.is_dir() else None
