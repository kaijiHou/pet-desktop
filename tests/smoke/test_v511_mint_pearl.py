"""V5.11 薄荷珍珠 (mint_pearl): the second asset theme wired via the pipeline.

Same contract as V5.10 rose_moon — 4 raw assets at fixed sizes, 10-icon
sheet split (5x2), themed QuickPanel render, switching, data isolation.
"""

from pathlib import Path

from datetime import datetime

import pytest


ASSETS = Path(__file__).resolve().parents[2] / "assets" / "ui_themes" / "mint_pearl"
EXPECTED_SIZES = {
    "avatar.png": (1254, 1254),
    "hero_scene.png": (1672, 941),
    "pocket_banner.png": (2172, 724),
    "icon_sheet.png": (2172, 724),
}


def test_four_raw_assets_wired():
    from PIL import Image
    for name, size in EXPECTED_SIZES.items():
        path = ASSETS / name
        assert path.exists(), f"missing asset {name}"
        assert Image.open(path).size == size, f"{name} must keep fixed size {size}"


def test_ten_icons_split_from_5x2_sheet():
    from PIL import Image
    for name in ("close", "plus", "folder", "pocket", "bell",
                 "calendar", "clock", "star", "gear", "rose"):
        path = ASSETS / "icons" / f"{name}.png"
        assert path.exists(), f"missing split icon {name}"
        assert Image.open(path).convert("RGBA").getchannel("A").getbbox() is not None


def test_mint_pearl_registered_as_light_asset_theme(theme_env):
    name, colors = theme_env.PRESETS["mint_pearl"]
    assert name == "薄荷珍珠"
    assert colors.get("dark", False) is False
    for key in theme_env.SKIN_KEYS:
        assert key in colors
    assert theme_env.theme_asset("hero_scene", "mint_pearl") is not None
    assert theme_env.theme_asset("icons/gear", "mint_pearl") is not None


@pytest.fixture()
def pearl_panel(theme_env, qapp, monkeypatch):
    import theme
    from quick_panel import QuickPanel

    class FakeItem:
        def __init__(self, name):
            self.name, self.exists = name, True

    class FakeReminder:
        def __init__(self, when, content):
            self.due_at, self.content = when, content

    class Pet:
        wage = type("W", (), {"configured": False})()
        destination_service = type("D", (), {"list_favorites": staticmethod(lambda: [])})()

        class pocket:
            list_items = staticmethod(lambda: [FakeItem("需求文档 v3.docx")])

        class reminder:
            list_reminders = staticmethod(
                lambda: [FakeReminder(datetime(2026, 10, 29, 9, 0), "续费 Codex 会员")])

    monkeypatch.setattr(theme_env, "_active_id", "mint_pearl")
    theme_env.initialize()
    theme.apply(qapp)
    panel = QuickPanel(Pet())
    panel.ensurePolished()
    qapp.processEvents()
    yield panel
    panel.close()


def test_panel_uses_the_four_assets(pearl_panel):
    assert not pearl_panel._mark.pixmap().isNull(), "header avatar must be the asset image"
    assert not pearl_panel._wage_bg.pixmap().isNull(), "wage hero card must carry hero_scene"
    assert not pearl_panel._wage_bg.isHidden()
    assert pearl_panel._pocket_bg is not None and not pearl_panel._pocket_bg.pixmap().isNull()
    for btn in (pearl_panel.clock_out_btn, pearl_panel.calendar_btn,
                pearl_panel.open_reminders_btn, pearl_panel.panel_close_btn):
        assert not btn.icon().isNull()
    assert not pearl_panel._favorite_icon.pixmap().isNull()
    assert not pearl_panel._favorite_rose.pixmap().isNull(), "shell accent must decorate sections"


def test_panel_click_and_real_data(pearl_panel):
    opened = []
    pearl_panel.pet._open_calendar = lambda: opened.append("calendar")
    pearl_panel.pet._open_pocket = lambda: opened.append("pocket")
    pearl_panel.calendar_btn.click()
    pearl_panel.open_pocket_btn.click()
    assert opened == ["calendar", "pocket"]
    rows = [pearl_panel.pocket_items_layout.itemAt(i).widget()
            for i in range(pearl_panel.pocket_items_layout.count())]
    assert any("需求文档 v3.docx" in w.text() for w in rows)
    assert "续费 Codex 会员" in pearl_panel.next_reminder_label.text()


def test_switch_persists(theme_env):
    assert theme_env.set_skin("mint_pearl")
    import json
    import config as config_mod
    stored = json.loads(config_mod.CONFIG_FILE.read_text(encoding="utf-8"))
    assert stored["ui_skin"] == "mint_pearl"


def test_no_paint_event():
    from quick_panel import QuickPanel
    assert "paintEvent" not in vars(QuickPanel)
