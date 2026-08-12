"""Smoke-test fixtures (Phase 2).

Native GUI tests run under Qt offscreen. Windows are constructed WITHOUT
show() and the tray icon is hidden. Config storage
is redirected into a per-module temp dir; the startup sound is silenced
(audio hardware side effect).
"""

import shutil
from pathlib import Path

import pytest

from tests.conftest import TEST_TEMP_ROOT


@pytest.fixture(scope="module")
def pet_window(qapp):
    """Construct the real PetWindow once per module, fully isolated.

    Behavior-preserving isolation (no production change):
      * config.CONFIG_DIR/CONFIG_FILE patched to a temp dir
      * sounds.play_startup silenced (audio is an external side effect)
    """
    import config as config_mod
    import destinations
    import pet_window as pet_window_mod
    import pocket_service
    import reminder_service
    import sounds

    tmp = TEST_TEMP_ROOT / "gui" / "pet_window"
    if tmp.exists():
        shutil.rmtree(tmp)
    cfg_dir = tmp / "desktop-pet"
    cfg_dir.mkdir(parents=True)

    saved = (
        config_mod.CONFIG_DIR,
        config_mod.CONFIG_FILE,
        reminder_service.REMINDERS_FILE,
        pocket_service.POCKET_FILE,
        destinations.DESTINATIONS_FILE,
    )
    config_mod.CONFIG_DIR = cfg_dir
    config_mod.CONFIG_FILE = cfg_dir / "config.json"
    reminder_service.REMINDERS_FILE = tmp / "reminders.json"
    pocket_service.POCKET_FILE = tmp / "pocket.json"
    destinations.DESTINATIONS_FILE = tmp / "destinations.json"
    saved_sound = sounds.play_startup
    sounds.play_startup = lambda: None

    cfg = config_mod.Config()
    window = pet_window_mod.PetWindow(cfg)
    window.tray_icon.hide()

    yield window

    # teardown
    try:
        window.file_watch.stop_all()
        window.close()
        window.tray_icon.hide()
    except Exception:
        pass
    sounds.play_startup = saved_sound
    (config_mod.CONFIG_DIR, config_mod.CONFIG_FILE,
     reminder_service.REMINDERS_FILE, pocket_service.POCKET_FILE,
     destinations.DESTINATIONS_FILE) = saved
    shutil.rmtree(tmp, ignore_errors=True)
