"""Boot autostart (HKCU Run key) and single-instance guard.

Windows-only helpers; no-ops elsewhere so tests on any platform import fine.
"""

import logging
import sys

LOGGER = logging.getLogger("pet.autostart")

RUN_KEY_PATH = r"Software\Microsoft\Windows\CurrentVersion\Run"
VALUE_NAME = "DesktopPet"


def _command() -> str:
    if getattr(sys, "frozen", False):
        return f'"{sys.executable}"'
    from paths import PROJECT_ROOT
    pythonw = PROJECT_ROOT / ".venv" / "Scripts" / "pythonw.exe"
    return f'"{pythonw}" "{PROJECT_ROOT / "main.py"}"'


def is_enabled() -> bool:
    if sys.platform != "win32":
        return False
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY_PATH) as key:
            value, _type = winreg.QueryValueEx(key, VALUE_NAME)
            return bool(value)
    except OSError:
        return False


def set_enabled(on: bool) -> bool:
    if sys.platform != "win32":
        return False
    import winreg
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY_PATH, 0,
                            winreg.KEY_SET_VALUE) as key:
            if on:
                winreg.SetValueEx(key, VALUE_NAME, 0, winreg.REG_SZ, _command())
            else:
                try:
                    winreg.DeleteValue(key, VALUE_NAME)
                except FileNotFoundError:
                    pass
        LOGGER.info("autostart %s", "enabled" if on else "disabled")
        return True
    except OSError:
        LOGGER.exception("autostart toggle failed")
        return False


def acquire_single_instance_mutex() -> bool:
    """Create the process-wide mutex; False when another instance holds it.

    Two instances both write data/*.json — the last writer silently wipes
    the other's additions (user-reported favorites loss).
    """
    if sys.platform != "win32":
        return True
    import ctypes
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.CreateMutexW(None, False, "DesktopPet.SingleInstance")
    return ctypes.get_last_error() != 183  # ERROR_ALREADY_EXISTS
