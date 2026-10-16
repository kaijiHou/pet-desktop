"""V5.12/V5.13 asset themes (cyber_night / spring_study / aurora_cyber /
sea_salt_pearl) — parametrized pipeline contract: fixed-size assets, icon
splits, themed QuickPanel render, switching, zero paintEvent."""

from datetime import datetime
from pathlib import Path

import pytest

ASSETS = Path(__file__).resolve().parents[2] / "assets" / "ui_themes"
SIZES = {"avatar.png": (1254, 1254), "hero_scene.png": (1672, 941),
         "pocket_banner.png": (2172, 724), "icon_sheet.png": (2172, 724)}
# per-theme icon files that must exist after the sheet split
ICONS = {
    "cyber_night": ("close", "plus", "folder", "pocket", "bell", "calendar", "clock", "rose"),
    "spring_study": ("clock", "calendar", "bell", "folder", "pocket", "gear", "rose"),
    "aurora_cyber": ("clock", "calendar", "bell", "folder", "pocket", "gear", "rose"),
    "sea_salt_pearl": ("close", "plus", "folder", "pocket", "bell", "calendar", "clock",
                       "star", "gear", "rose"),
}


@pytest.mark.parametrize("skin", sorted(ICONS))
def test_assets_and_icons_wired(skin):
    from PIL import Image
    d = ASSETS / skin
    for name, size in SIZES.items():
        assert (d / name).exists(), f"{skin}: missing {name}"
        assert Image.open(d / name).size == size, f"{skin}: {name} wrong size"
    for icon in ICONS[skin]:
        path = d / "icons" / f"{icon}.png"
        assert path.exists(), f"{skin}: missing icon {icon}"
        assert Image.open(path).convert("RGBA").getchannel("A").getbbox() is not None


@pytest.mark.parametrize("skin", sorted(ICONS))
def test_registered_and_panel_renders(theme_env, qapp, monkeypatch, skin):
    import theme
    from quick_panel import QuickPanel

    class FakeItem:
        def __init__(self, name):
            self.name, self.exists = name, True

    class Pet:
        wage = type("W", (), {"configured": False})()
        destination_service = type("D", (), {"list_favorites": staticmethod(lambda: [])})()

        class pocket:
            list_items = staticmethod(lambda: [FakeItem("报表.xlsx")])

        class reminder:
            list_reminders = staticmethod(
                lambda: [type("R", (), {"due_at": datetime(2026, 10, 29, 9, 0),
                                        "content": "续费 Codex 会员"})()])

    monkeypatch.setattr(theme_env, "_active_id", skin)
    theme_env.initialize()
    theme.apply(qapp)
    assert theme_env.active_id() == skin
    panel = QuickPanel(Pet())
    try:
        assert not panel._mark.pixmap().isNull(), f"{skin}: avatar art missing"
        assert not panel._wage_bg.pixmap().isNull(), f"{skin}: hero art missing"
        assert not panel._wage_bg.isHidden()
        assert panel._pocket_bg is not None and not panel._pocket_bg.pixmap().isNull()
        assert not panel.clock_out_btn.icon().isNull()
        rows = [panel.pocket_items_layout.itemAt(i).widget()
                for i in range(panel.pocket_items_layout.count())]
        assert any("报表.xlsx" in w.text() for w in rows), "real data must render"
    finally:
        panel.close()
        assert "paintEvent" not in vars(QuickPanel)
