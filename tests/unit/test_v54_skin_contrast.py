"""Readable skin colors and a character-free QuickPanel switch check."""

import pytest
from PyQt5.QtGui import QPalette

import ui_skin


@pytest.mark.parametrize("skin_id", [*ui_skin.PRESETS, "custom_light", "custom_dark", "custom_pale_saved"])
def test_skin_contrast(skin_id, monkeypatch):
    if skin_id.startswith("custom"):
        accent, bg = (("#FFFFFF", "#FFFFFF") if skin_id == "custom_light"
                      else ("#171717", "#171717"))
        colors = ui_skin.build_custom_colors(accent, bg)
        if skin_id == "custom_pale_saved":
            colors.update(text="#DADADA", muted="#DDDDDD")
        monkeypatch.setattr(ui_skin, "all_skins", lambda: {skin_id: (skin_id, colors)})
    monkeypatch.setattr(ui_skin, "_active_id", skin_id)
    p = ui_skin.palette()
    assert ui_skin._contrast(p["muted"], p["card"]) >= 4.5
    assert ui_skin._contrast(p["text_soft"], p["section_bg"]) >= 4.5
    assert ui_skin._contrast(p["text_soft"], p["tint_light"]) >= 4.5
    assert ui_skin._contrast(p["amount"], p["section_bg"]) >= 4.5
    assert ui_skin._contrast("#FFFFFF", p["action_bg"]) >= 4.5
    assert ui_skin._contrast("#FFFFFF", p["action_hover"]) >= 4.5
    assert p["section_bg"] == ui_skin._tint(p["accent"], p["card"], 0.10)
    assert p["tint_light"] == ui_skin._tint(p["accent"], "#FFFFFF", 0.12)


def test_quick_panel_switch_recolors_visible_captions(qapp, test_temp_root, monkeypatch):
    import config
    import theme
    from quick_panel import QuickPanel

    monkeypatch.setattr(config, "CONFIG_DIR", test_temp_root)
    monkeypatch.setattr(config, "CONFIG_FILE", test_temp_root / "config.json")
    monkeypatch.setattr(ui_skin, "SKINS_FILE", test_temp_root / "skins.json")
    monkeypatch.setattr(ui_skin, "_active_id", "sakura")
    ui_skin.initialize()
    theme.apply(qapp)

    class Empty:
        configured = False

        def list_items(self):
            return []

        def list_reminders(self):
            return []

        def list_favorites(self):
            return []

    class Pet:
        wage = pocket = reminder = destination_service = Empty()

    panel = QuickPanel(Pet())
    try:
        for skin_id in ("sakura", "mint", "cream"):
            assert ui_skin.set_skin(skin_id)
            panel.ensurePolished()
            qapp.processEvents()
            p = ui_skin.palette()
            assert p["section_bg"] in panel._card.styleSheet()
            assert p["action_bg"] in panel._card.styleSheet()
            for label in (panel.wage_status, panel.wage_detail):
                assert label.palette().color(QPalette.WindowText).name() == p["text_soft"]
            for label in (panel.favorite_empty, panel.empty_label, panel.no_remind_label):
                assert label.palette().color(QPalette.WindowText).name() == p["muted"].lower()
            assert not panel.clock_out_btn.isEnabled()
            assert panel.clock_out_btn.palette().color(QPalette.ButtonText).name() == p["text_soft"]
    finally:
        panel.close()
        ui_skin.set_skin("sakura")
