"""V4.7 production dynamic chain and dialog construction smoke tests."""
import pytest


@pytest.mark.smoke
@pytest.mark.gui
def test_dynamic_startup_uses_selected_pack(pet_window_dynamic):
    window = pet_window_dynamic
    assert window.dynamic_renderer is not None
    assert window.dynamic_renderer.is_loaded
    assert window.config.get("selected_character_id") == "default_dynamic_ghost"


@pytest.mark.smoke
@pytest.mark.gui
def test_settings_preview_and_reset_share_character_id(pet_window_dynamic):
    from pet_window import SettingsDialog
    dialog = SettingsDialog(pet_window_dynamic.config, pet_window_dynamic)
    try:
        assert dialog.preview_widget.character_id == "default_dynamic_ghost"
        dialog._work["selected_character_id"] = "default_dynamic_ghost"
        dialog._work["character_mode"] = "dynamic_pack"
        dialog._reset_image()
        assert dialog.preview_widget.character_id == "default_dynamic_ghost"
    finally:
        dialog.close()


@pytest.mark.smoke
@pytest.mark.gui
def test_dynamic_scale_semantics_and_dialogs(qapp, pet_window_dynamic):
    from PyQt5.QtCore import Qt
    from wage.ui_calendar import WorkCalendarDialog, ModernMonthCalendar
    from wage.ui_settings import WageSettingsDialog
    from character_gallery import CharacterGalleryDialog
    from character_v4.registry import CharacterRegistry
    from paths import ASSETS_DIR, DATA_DIR

    window = pet_window_dynamic
    old = window.config.get("pet_scale", 3)
    try:
        window._set_character_scale(2.5)
        assert window.dynamic_renderer.size() == (480, 520)
        window.play_semantic("GIVE_FILE")
        window.play_semantic("COPY_FILE")
        window.play_semantic("MOVE_FILE")
        window.play_semantic("MEAL_ALLOWANCE")
        assert window.dynamic_renderer._state_machine.current_state in {"GIVE_FILE", "COPY_FILE", "MOVE_FILE", "MEAL_ALLOWANCE"}
        calendar_dialog = WorkCalendarDialog(window.wage, window)
        wage_dialog = WageSettingsDialog(window.wage, window)
        gallery = CharacterGalleryDialog(CharacterRegistry(ASSETS_DIR, DATA_DIR), "default_dynamic_ghost", window)
        assert isinstance(calendar_dialog.calendar, ModernMonthCalendar)
        for dialog in (calendar_dialog, wage_dialog, gallery):
            assert dialog.windowFlags() & Qt.FramelessWindowHint
            dialog.close()
    finally:
        window._set_character_scale(old)
