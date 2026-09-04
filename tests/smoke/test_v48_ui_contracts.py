"""V4.8 UI contracts: behavior and hierarchy, not pixel-perfect snapshots."""
from datetime import datetime


def test_modern_dialog_resizable_flag_and_minimum_size(qapp):
    from ui.modern import ModernDialog
    dialog = ModernDialog("测试", resizable=True, min_width=320, min_height=210)
    try:
        assert dialog.resizable is True
        dialog.resize(40, 40)
        assert dialog.width() >= 320 and dialog.height() >= 210
        assert dialog._cursor_for(dialog._hit_test(dialog.rect().bottomRight()))
    finally:
        dialog.close()


def test_work_calendar_is_resizable_and_has_rules_entry(qapp, test_temp_root):
    from wage.service import WageService
    from wage.ui_calendar import WorkCalendarDialog
    svc = WageService(test_temp_root, now_provider=lambda: datetime(2032, 2, 10, 12, 0))
    dialog = WorkCalendarDialog(svc)
    try:
        assert dialog.resizable is True
        assert dialog.rules_button.text() == "⋯"
        dialog._toggle_rules()
        assert dialog._rules_expanded
        dialog._toggle_rules()
        assert not dialog._rules_expanded
        assert "周一至周五" in dialog.warning_banner.label.text()
    finally:
        dialog.close()


def test_settings_uses_cards_and_chinese_role_actions(pet_window):
    from PyQt5.QtWidgets import QGroupBox
    from pet_window import SettingsDialog
    dialog = SettingsDialog(pet_window.config, pet_window)
    try:
        assert not dialog.findChildren(QGroupBox)
        assert dialog.gallery_button.text() == "管理角色"
        assert dialog.import_button.text() == "导入单图"
        assert "..." not in " ".join(button.text() for button in dialog.findChildren(type(dialog.gallery_button)))
    finally:
        dialog.close()


def test_wage_manual_badge_tracks_month_override(qapp, test_temp_root):
    from wage.service import WageService
    from wage.ui_settings import WageSettingsDialog
    svc = WageService(test_temp_root, now_provider=lambda: datetime(2026, 9, 3, 12, 0))
    dialog = WageSettingsDialog(svc)
    try:
        assert dialog.auto_badge.text() == "自动"
        svc.calendar.set_month_workday_override(2026, 9, 23)
        dialog._refresh_workdays()
        assert dialog.workdays_label.text() == "23 天"
        assert dialog.auto_badge.text() == "手动"
    finally:
        dialog.close()


def test_single_image_import_is_portable(test_temp_root, tmp_path):
    from PIL import Image
    from character_import import SingleCharacterImportService
    image = tmp_path / "sample.jpg"
    Image.new("RGB", (24, 32), (20, 40, 80)).save(image)
    service = SingleCharacterImportService(test_temp_root)
    stored = service.import_image(image)
    assert stored.parent == test_temp_root / "character_images"
    assert service.relative_path(stored) == "character_images/sample.png"
    assert service.resolve("character_images/sample.png") == stored


def test_character_controller_reads_portable_image_path(test_temp_root, isolated_config, monkeypatch):
    from PIL import Image
    import character as character_mod
    image_dir = test_temp_root / "character_images"; image_dir.mkdir()
    Image.new("RGBA", (24, 32), (20, 40, 80, 255)).save(image_dir / "portable.png")
    monkeypatch.setattr(character_mod, "DATA_DIR", test_temp_root)
    isolated_config.set("character_image", "character_images/portable.png")
    isolated_config.set("character_mode", "single")
    controller = character_mod.CharacterController(isolated_config)
    assert controller.using_builtin_default is False
    assert controller.get_single_frame().size == (24, 32)
