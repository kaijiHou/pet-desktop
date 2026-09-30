"""V5.4 animation speed setting contracts."""

import pytest


def test_player_speed_scales_frame_interval(qapp):
    from character_v4.animation import AnimationPlayer
    from character_v4.atlas import SpritesheetAtlas
    from character_v4.manifest import CodexPetManifest
    from paths import ASSETS_DIR
    from pathlib import Path

    root = ASSETS_DIR / "default_dynamic_ghost"
    manifest = CodexPetManifest.load(root)
    atlas = SpritesheetAtlas(manifest, root)
    assert atlas.load()
    player = AnimationPlayer(atlas)
    player.set_speed(1.0)
    player.play("idle")
    base = player._current_interval_ms()
    assert base == 200

    player.set_speed(2.0)
    assert player._current_interval_ms() == 100, "2x speed halves the interval"
    assert player._timer.isActive() and player._timer.remainingTime() <= 120, \
        "speed change applies to the RUNNING animation immediately"

    player.set_speed(0.5)
    assert player._current_interval_ms() == 400
    player.set_speed(99)          # clamped
    assert player._current_interval_ms() == 50
    player.set_speed(0.01)        # clamped
    assert player._current_interval_ms() == 800


def test_renderer_speed_delegates_to_player(qapp):
    from character_v4.renderer import DynamicPackRenderer
    from paths import ASSETS_DIR
    from pathlib import Path

    renderer = DynamicPackRenderer(ASSETS_DIR / "default_dynamic_ghost", scale=1.0)
    assert renderer.load()
    renderer.set_speed(1.5)
    assert renderer.speed == 1.5
    assert renderer._player._speed == 1.5


def test_settings_persist_and_apply(pet_window, isolated_config):
    pet = pet_window
    pet.config.set("animation_speed", 2.0)
    assert pet._animation_speed() == 2.0
    pet._apply_animation_speed()
    if pet.dynamic_renderer is not None:
        assert pet.dynamic_renderer.speed == 2.0
    # invalid values fall back to 1.0
    pet.config.set("animation_speed", "not-a-number")
    assert pet._animation_speed() == 1.0


def test_settings_dialog_speed_combo_roundtrip(pet_window):
    from pet_window import SettingsDialog
    dlg = SettingsDialog(pet_window.config, pet_window)
    try:
        # default 正常
        assert float(dlg.speed_combo.currentData()) == 1.0
        dlg.speed_combo.setCurrentIndex(0)          # 慢
        dlg._save()
        assert float(pet_window.config.get("animation_speed")) == 0.6
        # reopening shows the persisted option closest to the stored factor
        dlg2 = SettingsDialog(pet_window.config, pet_window)
        try:
            assert float(dlg2.speed_combo.currentData()) == 0.6
        finally:
            dlg2.close()
    finally:
        dlg.close()
        pet_window.config.set("animation_speed", 1.0)
