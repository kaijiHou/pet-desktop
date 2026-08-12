"""GUI construction smoke tests (Phase 2).

Runs on the REAL platform (offscreen segfaults QWebEngineView.page()).
Windows/dialogs are constructed but never shown.
"""

import pytest

import pet_window_web


@pytest.mark.smoke
@pytest.mark.gui
class TestGuiConstruction:
    def test_qapplication_exists(self, qapp):
        from PyQt5.QtWidgets import QApplication
        assert QApplication.instance() is qapp

    def test_pet_window_constructed(self, pet_window):
        w = pet_window
        assert w is not None
        assert w.width() > 0 and w.height() > 0
        # never shown on screen
        assert not w.isVisible()

    def test_pet_window_initial_state_is_idle(self, pet_window):
        assert pet_window._state == pet_window.STATE_IDLE

    def test_pet_window_owns_services(self, pet_window):
        w = pet_window
        assert w.reminder is not None
        assert not hasattr(w, "ai_engine")
        assert not hasattr(w, "calendar")

    def test_settings_dialog_constructs(self, pet_window):
        d = pet_window_web.SettingsDialog(pet_window.config, pet_window)
        assert d is not None
        assert d.minimumWidth() >= 420
        d.close()

    def test_settings_dialog_reflects_config_values(self, pet_window):
        d = pet_window_web.SettingsDialog(pet_window.config, pet_window)
        assert d.water_interval.value() == pet_window.config.get("water_interval_min")
        assert d.water_enabled.isChecked() == pet_window.config.get("water_enabled")
        d.close()

    def test_settings_dialog_has_no_openai_controls(self, pet_window):
        d = pet_window_web.SettingsDialog(pet_window.config, pet_window)
        assert not hasattr(d, "api_key_input")
        assert not hasattr(d, "model_input")
        assert not hasattr(d, "cal_enabled")
        assert not hasattr(d, "cal_remind_before")
        d.close()

    def test_context_menu_items_are_constructed(self, pet_window, monkeypatch, qapp):
        # Intercept the blocking QMenu.exec_ (same technique as the Phase 1
        # ad-hoc smoke) so _show_context_menu's builder runs but never blocks.
        from PyQt5.QtCore import QPoint
        from PyQt5.QtWidgets import QMenu

        captured = {}
        def fake_exec(self, *args):
            captured["items"] = [a.text() for a in self.actions() if a.text()]
            return None
        monkeypatch.setattr(QMenu, "exec_", fake_exec)

        pet_window._show_context_menu(QPoint(120, 120))

        items = captured.get("items", [])
        assert len(items) >= 3, f"context menu should have >=3 items, got {items}"
        assert all("Tanya" not in item and "Chat" not in item for item in items)
        assert all("Jadwal" not in item and "Calendar" not in item for item in items)

    def test_window_can_be_closed(self, pet_window):
        # close() on an unshown frameless tool window must not raise.
        pet_window.close()
        # re-open guard not needed; fixture teardown closes again safely.
