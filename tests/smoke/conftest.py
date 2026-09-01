"""Smoke-test fixtures (Phase 2 + V4.5 dynamic production).

Native GUI tests run under Qt offscreen. Windows are constructed WITHOUT
show() and the tray icon is hidden. Config storage
is redirected into a per-module temp dir; the startup sound is silenced
(audio hardware side effect).

V4.5: Two fixture modes:
- pet_window (alias for pet_window_single) — legacy single-image tests
- pet_window_dynamic — production fresh-config dynamic tests
"""
import shutil
from pathlib import Path

import pytest

from tests.conftest import TEST_TEMP_ROOT


def _make_pet_window(qapp, character_mode="single", character_id=""):
    """Shared construction logic for PetWindow fixtures."""
    import config as config_mod
    import destinations
    import pet_window as pet_window_mod
    import pocket_service
    import reminder_service
    import sounds

    suffix = character_mode.replace("_", "-")
    tmp = TEST_TEMP_ROOT / "gui" / f"pet_window_{suffix}"
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
    cfg.set("character_mode", character_mode)
    cfg.set("selected_character_id", character_id)
    window = pet_window_mod.PetWindow(cfg)
    window.tray_icon.hide()

    return window, saved, saved_sound, config_mod, reminder_service, pocket_service, destinations, tmp


@pytest.fixture(scope="module")
def pet_window_dynamic(qapp):
    """Construct PetWindow with production Fresh DEFAULT_CONFIG (dynamic_pack).

    This fixture tests the actual production default: dynamic ghost character.
    """
    window, saved, saved_sound, config_mod, reminder_service, pocket_service, destinations, tmp = \
        _make_pet_window(qapp, "dynamic_pack", "default_dynamic_ghost")

    yield window

    try:
        window.file_watch.stop_all()
        window.close()
        window.tray_icon.hide()
    except Exception:
        pass
    import sounds as _sounds
    _sounds.play_startup = saved_sound
    (config_mod.CONFIG_DIR, config_mod.CONFIG_FILE,
     reminder_service.REMINDERS_FILE, pocket_service.POCKET_FILE,
     destinations.DESTINATIONS_FILE) = saved
    shutil.rmtree(tmp, ignore_errors=True)


@pytest.fixture(scope="module")
def pet_window_single(qapp):
    """Construct PetWindow with explicit single mode for legacy regression."""
    window, saved, saved_sound, config_mod, reminder_service, pocket_service, destinations, tmp = \
        _make_pet_window(qapp, "single", "")

    yield window

    try:
        window.file_watch.stop_all()
        window.close()
        window.tray_icon.hide()
    except Exception:
        pass
    import sounds as _sounds
    _sounds.play_startup = saved_sound
    (config_mod.CONFIG_DIR, config_mod.CONFIG_FILE,
     reminder_service.REMINDERS_FILE, pocket_service.POCKET_FILE,
     destinations.DESTINATIONS_FILE) = saved
    shutil.rmtree(tmp, ignore_errors=True)


@pytest.fixture(scope="module")
def pet_window(pet_window_single):
    """Legacy alias — existing tests use 'pet_window' which means single."""
    return pet_window_single
