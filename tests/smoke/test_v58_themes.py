"""V5.8 theme system: 16 presets (cute/cool), dark-aware derivation,
theme picker, and themed renders of QuickPanel / WorkCalendarDialog.

Data discipline: every test redirects ALL five user data surfaces (config,
reminders, pocket, destinations, wage) into the per-test temp root before
any widget/service is constructed.
"""

import json
from datetime import date, datetime

import pytest


@pytest.fixture()
def theme_env(test_temp_root, monkeypatch):
    """Redirect every user data surface; return the touched modules."""
    import config as config_mod
    import reminder_service
    import pocket_service
    import destinations
    import ui_skin

    cfg_dir = test_temp_root / "cfg"
    cfg_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(config_mod, "CONFIG_DIR", cfg_dir)
    monkeypatch.setattr(config_mod, "CONFIG_FILE", cfg_dir / "config.json")
    monkeypatch.setattr(reminder_service, "REMINDERS_FILE", test_temp_root / "reminders.json")
    monkeypatch.setattr(pocket_service, "POCKET_FILE", test_temp_root / "pocket.json")
    monkeypatch.setattr(destinations, "DESTINATIONS_FILE", test_temp_root / "destinations.json")
    monkeypatch.setattr(ui_skin, "SKINS_FILE", test_temp_root / "ui_skins.json")
    monkeypatch.setattr(ui_skin, "_active_id", None)
    return ui_skin


CUTE = ("sakura", "garden", "taro", "sky", "cream", "forest", "mint", "berry_night")
COOL = ("cyber_night", "deep_pulse", "ember_tech", "aurora_pulse", "titanium",
        "obsidian_gold", "storm_volt", "midnight_neon")


def test_sixteen_presets_eight_per_category(theme_env):
    skins = theme_env.PRESETS
    assert len(skins) == 16
    cute = [sid for sid, (_, c) in skins.items() if c.get("category") == "cute"]
    cool = [sid for sid, (_, c) in skins.items() if c.get("category") == "cool"]
    assert cute == list(CUTE)
    assert cool == list(COOL)


def test_cool_presets_dark_with_flavor_keys(theme_env):
    for sid, (name, colors) in theme_env.PRESETS.items():
        for key in theme_env.SKIN_KEYS:
            assert key in colors, f"{sid} missing {key}"
        assert colors.get("deco"), f"{sid} missing theme emoji"
    assert all(theme_env.PRESETS[sid][1].get("dark") for sid in COOL)
    assert not any(theme_env.PRESETS[sid][1].get("dark") for sid in CUTE if sid != "berry_night")
    assert theme_env.PRESETS["berry_night"][1].get("dark") is True


def test_every_preset_switches_persists_and_bridges(theme_env):
    import theme
    import config as config_mod
    for sid, (name, colors) in theme_env.PRESETS.items():
        assert theme_env.set_skin(sid)
        p = theme_env.palette()
        assert theme.ACCENT == p["accent"] == colors["accent"]
        stored = json.loads(config_mod.CONFIG_FILE.read_text(encoding="utf-8"))
        assert stored["ui_skin"] == sid


def test_quick_panel_renders_under_every_theme(theme_env, qapp, monkeypatch):
    import theme
    from quick_panel import QuickPanel

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

    for sid in theme_env.PRESETS:
        monkeypatch.setattr(theme_env, "_active_id", sid)
        theme_env.initialize()
        theme.apply(qapp)
        panel = QuickPanel(Pet())
        try:
            qss = panel._card.styleSheet()
            p = theme_env.palette()
            assert p["action_bg"] in qss, f"{sid}: panel must follow action colour"
            assert p["hero_top"] in qss, f"{sid}: panel must paint the hero gradient"
            assert panel._mark.text() == p["deco"]
        finally:
            panel.close()


def test_calendar_dialog_renders_under_every_theme(theme_env, qapp, monkeypatch):
    import theme
    from wage.service import WageService
    from wage.ui_calendar import WorkCalendarDialog

    wage_dir = theme_env.SKINS_FILE.parent / "wage"
    wage_dir.mkdir(exist_ok=True)
    service = WageService(wage_dir, now_provider=lambda: datetime(2026, 10, 14, 15, 0))
    for sid in theme_env.PRESETS:
        monkeypatch.setattr(theme_env, "_active_id", sid)
        theme_env.initialize()
        theme.apply(qapp)
        dialog = WorkCalendarDialog(service, None)
        try:
            assert len(dialog.calendar.cells) == 42
            assert dialog.record_out_button.objectName() == "primary"
            assert "小周上班" in dialog.legend_label.text()
            assert "20 天" in dialog.stat_cards["workdays"].value.text()
            today_cell = next(c for c in dialog.calendar.cells if c.is_today)
            assert theme_env.palette()["accent"] in today_cell.styleSheet()
        finally:
            dialog.close()


def test_theme_picker_tabs_cards_and_switch(theme_env, qapp):
    from ui_theme_picker import ThemePickerDialog

    dialog = ThemePickerDialog()
    try:
        assert [k for k, _ in dialog._categories] == ["cute", "cool"]
        dialog._show_category("cute")
        assert dialog.grid.count() == 8
        dialog._show_category("cool")
        assert dialog.grid.count() == 8
        card = dialog.grid.itemAt(3).widget()
        dialog._pick("storm_volt")
        assert theme_env.active_id() == "storm_volt"
        assert card is not None
    finally:
        dialog.close()


def test_popup_surfaces_stay_python_paintevent_free():
    """IME red line: translucent frameless surfaces must be QLabel/QSS only."""
    from PyQt5.QtWidgets import QWidget, QFrame, QDialog
    from quick_panel import QuickPanel
    from ui_theme_picker import ThemePickerDialog, ThemeCard
    from wage.ui_calendar import CalendarDayCell, ModernMonthCalendar

    for cls, base in ((QuickPanel, QWidget), (CalendarDayCell, QFrame),
                      (ModernMonthCalendar, QWidget), (ThemeCard, QFrame),
                      (ThemePickerDialog, QDialog)):
        assert "paintEvent" not in vars(cls), f"{cls.__name__} defines a custom paintEvent"


def test_calendar_status_colors_follow_skin(theme_env, monkeypatch):
    from wage.service import WageService

    wage_dir = theme_env.SKINS_FILE.parent / "wage2"
    wage_dir.mkdir(exist_ok=True)
    service = WageService(wage_dir, now_provider=lambda: datetime(2026, 10, 14, 15, 0))
    monkeypatch.setattr(theme_env, "_active_id", "sakura")
    rest_sakura = service.calendar.status_detail_for(date(2026, 10, 24))
    assert rest_sakura["status"] == "rest"
    cell_day = next(d for d in (date(2026, 10, 24),))
    from wage.ui_calendar import CalendarDayCell
    cell = CalendarDayCell(cell_day, rest_sakura, None, True, None)
    sakura_qss = cell.styleSheet()
    monkeypatch.setattr(theme_env, "_active_id", "storm_volt")
    cell._apply_style(False)
    assert cell.styleSheet() != sakura_qss, "cell must re-skin when the theme changes"
