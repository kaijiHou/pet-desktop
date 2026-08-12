"""GUI construction smoke tests (Phase 2).

Runs on the REAL platform (offscreen segfaults QWebEngineView.page()).
Windows/dialogs are constructed but never shown; no network is touched:
  * ChatDialog construction only wires widgets — AIEngine.chat() is never
    called, so no OpenAI request is made.
  * Calendar is disabled in the fixture, so no Google OAuth occurs.
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
        assert w.ai_engine is not None
        assert w.calendar is not None
        assert w.reminder is not None

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

    def test_chat_dialog_constructs_without_network(self, pet_window):
        # ai_engine is passed but .chat() is never invoked -> no API call.
        d = pet_window_web.ChatDialog(pet_window.ai_engine, pet_window.config, "", pet_window)
        assert d is not None
        assert d.input_field is not None
        assert d.send_btn is not None
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
        assert len(items) >= 5, f"context menu should have >=5 items, got {items}"

    def test_window_can_be_closed(self, pet_window):
        # close() on an unshown frameless tool window must not raise.
        pet_window.close()
        # re-open guard not needed; fixture teardown closes again safely.
