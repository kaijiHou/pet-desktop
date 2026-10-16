"""V5.14-V5.18 asset themes (autumn_lantern / snowy_starlight /
sakura_lantern / moonlit_coast) — these packs ship PRE-SPLIT icons, so the
contract covers the name-mapped icon copies instead of sheet re-splitting."""

from datetime import datetime
from pathlib import Path

import pytest

ASSETS = Path(__file__).resolve().parents[2] / "assets" / "ui_themes"
SIZES = {"avatar.png": (1254, 1254), "hero_scene.png": (1672, 941),
         "pocket_banner.png": (2172, 724), "icon_sheet.png": (2172, 724)}
ICONS = {
    "autumn_lantern": ("bell", "calendar", "clock", "folder", "pocket", "rose", "settings"),
    "snowy_starlight": ("bell", "calendar", "clock", "folder", "pocket", "rose", "settings"),
    "sakura_lantern": ("bell", "calendar", "clock", "folder", "notes", "pocket",
                       "rose", "settings", "star", "statistics"),
    "moonlit_coast": ("bell", "calendar", "clock", "close", "folder", "plus", "pocket",
                      "rose", "settings", "star"),
}
DISPLAY_NAMES = {"autumn_lantern": "枫叶暖灯书房", "snowy_starlight": "雪夜星灯小屋",
                 "sakura_lantern": "樱花灯影书阁", "moonlit_coast": "月夜海城"}


@pytest.mark.parametrize("skin", sorted(ICONS))
def test_assets_and_icon_copies_wired(skin):
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
    assert theme_env.PRESETS[skin][0] == DISPLAY_NAMES[skin]
    assert theme_env.active_id() == skin
    panel = QuickPanel(Pet())
    try:
        assert not panel._mark.pixmap().isNull(), f"{skin}: avatar art missing"
        assert not panel._wage_bg.pixmap().isNull(), f"{skin}: hero art missing"
        assert panel._pocket_bg is not None and not panel._pocket_bg.pixmap().isNull()
        assert not panel.clock_out_btn.icon().isNull()
        rows = [panel.pocket_items_layout.itemAt(i).widget()
                for i in range(panel.pocket_items_layout.count())]
        assert any("报表.xlsx" in w.text() for w in rows)
    finally:
        panel.close()
        assert "paintEvent" not in vars(QuickPanel)


def test_light_skins_use_weak_scrim(theme_env):
    """User-reported: a near-opaque light scrim read as a white blob over art."""
    dark_p = theme_env.resolve_palette(theme_env.PRESETS["moonlit_coast"][1])
    light_p = theme_env.resolve_palette(theme_env.PRESETS["sea_salt_pearl"][1])
    import re
    a = lambda v: int(re.search(r"rgba\(\d+,\d+,\d+,(\d+)\)", v).group(1))
    assert a(dark_p["scrim_left"]) > a(light_p["scrim_left"])
    assert a(light_p["scrim_left"]) <= 100
