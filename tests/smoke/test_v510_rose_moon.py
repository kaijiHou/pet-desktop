"""V5.10 玫瑰月夜可爱风: the 4 raw assets are wired into the QuickPanel.

Covers: asset registration + fixed sizes, icon-sheet splits, themed render
(avatar / hero art / pocket banner / sheet icons replacing emoji), real
controls still clickable with real data, theme switching persistence, and
the no-paintEvent IME red line. All data surfaces are sandboxed.
"""

import shutil
from pathlib import Path

import pytest


ASSETS = Path(__file__).resolve().parents[2] / "assets" / "ui_themes" / "rose_moon"
EXPECTED_SIZES = {
    "avatar.png": (1254, 1254),
    "hero_scene.png": (1672, 941),
    "pocket_banner.png": (2172, 724),
    "icon_sheet.png": (2172, 724),
}
ICON_NAMES = ("close", "plus", "folder", "pocket", "bell", "calendar", "clock", "rose")


def test_four_raw_assets_wired_verbatim():
    from PIL import Image
    for name, size in EXPECTED_SIZES.items():
        path = ASSETS / name
        assert path.exists(), f"missing asset {name}"
        im = Image.open(path)
        assert im.size == size, f"{name} must keep the fixed source size {size}, got {im.size}"
        assert im.mode == "RGBA", f"{name} must stay a transparent PNG"


def test_icon_sheet_split_into_standalone_icons():
    from PIL import Image
    for name in ICON_NAMES:
        path = ASSETS / "icons" / f"{name}.png"
        assert path.exists(), f"missing split icon {name}"
        im = Image.open(path).convert("RGBA")
        alpha = im.getchannel("A")
        assert alpha.getbbox() is not None, f"icon {name} is blank"


def test_rose_moon_registered_as_dark_cute_theme(theme_env):
    name, colors = theme_env.PRESETS["rose_moon"]
    assert name == "玫瑰月夜"
    assert colors["category"] == "cute" and colors["dark"] is True
    for key in theme_env.SKIN_KEYS:
        assert key in colors
    assert theme_env.theme_asset("hero_scene", "rose_moon") is not None
    assert theme_env.theme_asset("avatar", "no_such_skin") is None


@pytest.fixture()
def rose_panel(theme_env, qapp, monkeypatch):
    import theme
    from quick_panel import QuickPanel

    class FakeItem:
        def __init__(self, name):
            self.name, self.exists = name, True

    class FakeReminder:
        def __init__(self, when, content):
            self.due_at, self.content = when, content

    from datetime import datetime

    class Pet:
        wage = type("W", (), {"configured": False})()
        destination_service = type("D", (), {"list_favorites": staticmethod(lambda: [])})()

        class pocket:
            list_items = staticmethod(lambda: [FakeItem("需求文档 v3.docx")])

        class reminder:
            list_reminders = staticmethod(
                lambda: [FakeReminder(datetime(2026, 10, 29, 9, 0), "续费 Codex 会员")])

    monkeypatch.setattr(theme_env, "_active_id", "rose_moon")
    theme_env.initialize()
    theme.apply(qapp)
    panel = QuickPanel(Pet())
    panel.ensurePolished()
    qapp.processEvents()
    yield panel
    panel.close()


def test_panel_uses_the_four_assets(rose_panel):
    assert not rose_panel._mark.pixmap().isNull(), "header avatar must be the asset image"
    assert not rose_panel._wage_bg.pixmap().isNull(), "wage hero card must carry hero_scene"
    assert not rose_panel._wage_bg.isHidden(), "hero art layer must be visible"
    assert rose_panel.wage_decor.isHidden(), "emoji decor must yield to the art"
    assert rose_panel._pocket_bg is not None and not rose_panel._pocket_bg.pixmap().isNull(), \
        "pocket banner must carry pocket_banner art"
    # sheet icons replace emoji on actions
    for btn in (rose_panel.clock_out_btn, rose_panel.calendar_btn,
                rose_panel.open_reminders_btn, rose_panel.panel_close_btn,
                rose_panel.remind_btn):
        assert not btn.icon().isNull()
    assert rose_panel.clock_out_btn.icon().availableSizes(), "clock icon must have sizes"
    # section headers carry sheet icons, not emoji text
    assert not rose_panel._favorite_icon.pixmap().isNull()
    assert rose_panel._favorite_icon.text() == ""
    assert not rose_panel._favorite_rose.pixmap().isNull()


def test_panel_controls_click_and_real_data_show(rose_panel):
    opened = []
    rose_panel.pet._open_calendar = lambda: opened.append("calendar")
    rose_panel.pet._open_pocket = lambda: opened.append("pocket")
    rose_panel.calendar_btn.click()
    rose_panel.open_pocket_btn.click()
    assert opened == ["calendar", "pocket"], "real buttons must stay clickable"
    # real data rendered by controls (not baked into art)
    rows = [rose_panel.pocket_items_layout.itemAt(i).widget() for i in range(rose_panel.pocket_items_layout.count())]
    assert any("需求文档 v3.docx" in w.text() for w in rows), "pocket item must render as real text"
    # first reminder renders as the chip row (next_reminder_label)
    assert "续费 Codex 会员" in rose_panel.next_reminder_label.text()


def test_rose_moon_switch_persists(theme_env):
    assert theme_env.set_skin("rose_moon")
    import config as config_mod
    import json
    stored = json.loads(config_mod.CONFIG_FILE.read_text(encoding="utf-8"))
    assert stored["ui_skin"] == "rose_moon"
    assert theme_env.active_id() == "rose_moon"


def test_other_themes_keep_emoji_fallback(theme_env, qapp, monkeypatch):
    """Skins without assets keep the V5.8 gradient/emoji panel, unchanged."""
    import theme
    from quick_panel import QuickPanel

    class Pet:
        wage = type("W", (), {"configured": False})()
        destination_service = type("D", (), {"list_favorites": staticmethod(lambda: [])})()

        class pocket:
            list_items = staticmethod(lambda: [])

        class reminder:
            list_reminders = staticmethod(lambda: [])

    monkeypatch.setattr(theme_env, "_active_id", "sakura")
    theme_env.initialize()
    theme.apply(qapp)
    panel = QuickPanel(Pet())
    try:
        assert panel._mark.pixmap() is None or panel._mark.pixmap().isNull()
        assert panel._mark.text() == "🌸"
        assert panel._wage_bg.isHidden() and not panel.wage_decor.isHidden()
        assert panel._pocket_bg is None
        assert panel.open_pocket_btn.objectName() == "panelPrimary"
        assert panel.panel_close_btn.text() == "×"
    finally:
        panel.close()


def test_no_paint_event_redline_rose_moon():
    from PyQt5.QtWidgets import QWidget
    from quick_panel import QuickPanel
    assert "paintEvent" not in vars(QuickPanel), "art layers must stay QLabel/QSS"
