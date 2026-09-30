"""V5.4 skin system contracts: presets, switching, persistence, custom skins."""

import json

import pytest


@pytest.fixture()
def skin_env(test_temp_root, monkeypatch):
    import config as config_mod
    import ui_skin
    cfg_dir = test_temp_root / "cfg"
    cfg_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(config_mod, "CONFIG_DIR", cfg_dir)
    monkeypatch.setattr(config_mod, "CONFIG_FILE", cfg_dir / "config.json")
    monkeypatch.setattr(ui_skin, "SKINS_FILE", test_temp_root / "ui_skins.json")
    monkeypatch.setattr(ui_skin, "_active_id", None)
    return ui_skin


def test_five_presets_exist(skin_env):
    skins = skin_env.all_skins()
    for expected in ("sakura", "cream", "mint", "sky", "taro"):
        assert expected in skins, f"missing preset {expected}"
        name, colors = skins[expected]
        for key in skin_env.SKIN_KEYS:
            assert key in colors, f"{expected} missing {key}"


def test_set_skin_mutates_legacy_globals_and_persists(skin_env, monkeypatch):
    import theme
    import ui.modern.tokens as tokens
    monkeypatch.setattr(skin_env, "_active_id", None)
    assert skin_env.set_skin("mint")
    p = skin_env.palette()
    assert theme.ACCENT == p["accent"] == "#34B78F"
    assert tokens.PRIMARY == p["accent"]
    assert theme.MENU_BG == p["menu_bg"]
    # persisted for next startup
    import config as config_mod
    stored = json.loads((config_mod.CONFIG_FILE).read_text(encoding="utf-8"))
    assert stored["ui_skin"] == "mint"


def test_switch_back_to_sakura_restores_pink(skin_env, monkeypatch):
    import theme
    monkeypatch.setattr(skin_env, "_active_id", None)
    skin_env.set_skin("sky")
    skin_env.set_skin("sakura")
    assert theme.ACCENT == "#F27BA7"
    p = skin_env.palette()
    assert p["menu_bg"] == "#FFF5F9"


def test_custom_skin_roundtrip(skin_env, monkeypatch):
    monkeypatch.setattr(skin_env, "_active_id", None)
    colors = skin_env.build_custom_colors("#FF8800", "#FFF8EF")
    for key in skin_env.SKIN_KEYS:
        assert key in colors
    skin_id = skin_env.save_custom_skin("蜜桃乌龙", colors)
    assert skin_id in skin_env.all_skins()
    assert skin_env.set_skin(skin_id)
    import theme
    assert theme.ACCENT == colors["accent"]
    # persisted to ui_skins.json
    doc = json.loads(skin_env.SKINS_FILE.read_text(encoding="utf-8"))
    assert any(s["id"] == skin_id for s in doc["skins"])


def test_unknown_skin_rejected(skin_env):
    before = skin_env.active_id()
    assert skin_env.set_skin("no_such_skin") is False
    assert skin_env.active_id() == before


def test_quick_panel_repaints_on_skin_change(pet_window, monkeypatch):
    import ui_skin
    panel = pet_window._quick_panel
    if panel is None:
        from quick_panel import QuickPanel
        panel = QuickPanel(pet_window)
        pet_window._quick_panel = panel
    monkeypatch.setattr(ui_skin, "_active_id", None)
    ui_skin.set_skin("mint")
    qss_mint = panel._card.styleSheet().lower()
    # The panel follows the skin's derived action colour (contrast-darkened
    # accent, lowercase from QColor.name()).
    assert ui_skin.palette()["action_bg"].lower() in qss_mint, \
        "panel stylesheet must follow the mint action colour"
    ui_skin.set_skin("sakura")
    qss_sakura = panel._card.styleSheet().lower()
    assert ui_skin.palette()["action_bg"].lower() in qss_sakura
    assert qss_mint != qss_sakura
