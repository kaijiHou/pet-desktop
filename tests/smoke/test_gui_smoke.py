"""GUI construction smoke tests (Phase 2).

Runs on the REAL platform (offscreen segfaults QWebEngineView.page()).
Windows/dialogs are constructed but never shown.
"""

from datetime import datetime, timedelta

import pytest

import pet_window_web
from reminder_ui import AddReminderDialog, ReminderListDialog
from pocket_ui import PocketDialog
from destinations import DestinationService


class FakeDropEvent:
    def __init__(self, urls):
        self._urls = urls
        self.accepted = False
        self.ignored = False

    def mimeData(self):
        return self

    def hasUrls(self):
        return bool(self._urls)

    def urls(self):
        return self._urls

    def acceptProposedAction(self):
        self.accepted = True

    def ignore(self):
        self.ignored = True


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
        assert w.pocket is not None
        assert w.acceptDrops()

    def test_drag_enter_accepts_local_files_only(self, pet_window, test_temp_root):
        from PyQt5.QtCore import QUrl

        source = test_temp_root / "drop.txt"
        source.touch()
        local = FakeDropEvent([QUrl.fromLocalFile(str(source))])
        remote = FakeDropEvent([QUrl("https://example.com/file.txt")])

        pet_window.dragEnterEvent(local)
        pet_window.dragEnterEvent(remote)

        assert local.accepted is True
        assert remote.ignored is True

    def test_drop_adds_file_and_directory_references_without_copying(self, pet_window, test_temp_root):
        from PyQt5.QtCore import QUrl

        source = test_temp_root / "drop.txt"
        folder = test_temp_root / "folder"
        source.write_text("untouched", encoding="utf-8")
        folder.mkdir()
        event = FakeDropEvent([
            QUrl.fromLocalFile(str(source)),
            QUrl.fromLocalFile(str(folder)),
        ])

        pet_window.dropEvent(event)

        assert event.accepted is True
        assert {item.path for item in pet_window.pocket.list_items()} == {
            source.resolve(), folder.resolve()
        }
        assert source.read_text(encoding="utf-8") == "untouched"
        assert "Pocket" in pet_window._bubble_text
        for item in list(pet_window.pocket.list_items()):
            pet_window.pocket.remove(item.id)

    def test_pocket_dialog_lists_copies_and_removes_reference(
        self, pet_window, test_temp_root, monkeypatch
    ):
        from PyQt5.QtWidgets import QApplication

        class FakeClipboard:
            text_value = ""

            def setText(self, value):
                self.text_value = value

        clipboard = FakeClipboard()
        monkeypatch.setattr(QApplication, "clipboard", staticmethod(lambda: clipboard))
        source = test_temp_root / "pocket-ui.txt"
        source.touch()
        pet_window.pocket.add(source)
        dialog = PocketDialog(pet_window.pocket, pet_window)

        assert dialog.item_list.count() == 1
        assert "pocket-ui.txt" in dialog.item_list.item(0).text()
        dialog.copy_selected()
        assert clipboard.text_value == str(source.resolve())
        dialog.remove_selected(confirm=False)
        assert pet_window.pocket.list_items() == []
        assert source.exists()
        dialog.close()

    def test_pocket_dialog_marks_and_cleans_missing_reference(self, pet_window, test_temp_root):
        source = test_temp_root / "missing-ui.txt"
        source.touch()
        pet_window.pocket.add(source)
        source.unlink()
        dialog = PocketDialog(pet_window.pocket, pet_window)

        assert "[missing]" in dialog.item_list.item(0).text()
        removed = dialog.cleanup_missing()
        assert len(removed) == 1
        assert dialog.item_list.count() == 0
        dialog.close()

    def test_pocket_drag_exports_standard_local_file_urls(self, pet_window, test_temp_root):
        source = test_temp_root / "drag-out.txt"
        source.touch()
        pet_window.pocket.add(source)
        dialog = PocketDialog(pet_window.pocket, pet_window)

        mime = dialog.item_list.mime_data_for_selected()

        assert mime is not None and mime.hasUrls()
        assert mime.urls()[0].isLocalFile()
        from pathlib import Path
        assert Path(mime.urls()[0].toLocalFile()) == source.resolve()
        assert source.exists()
        dialog.remove_selected(confirm=False)
        dialog.close()

    def test_missing_pocket_item_cannot_start_drag(self, pet_window, test_temp_root):
        source = test_temp_root / "no-drag.txt"
        source.touch()
        pet_window.pocket.add(source)
        source.unlink()
        dialog = PocketDialog(pet_window.pocket, pet_window)
        assert dialog.item_list.mime_data_for_selected() is None
        dialog.cleanup_missing()
        dialog.close()

    def test_pocket_copy_and_move_to_keep_reference_consistent(self, pet_window, test_temp_root):
        source = test_temp_root / "operate.txt"
        copy_dest = test_temp_root / "copies"
        move_dest = test_temp_root / "moves"
        source.write_text("payload"); copy_dest.mkdir(); move_dest.mkdir()
        original = pet_window.pocket.add(source)
        dialog = PocketDialog(pet_window.pocket, pet_window)

        copied = dialog.perform_selected("copy", copy_dest, notify=False)
        assert copied.succeeded == 1
        assert source.exists() and (copy_dest / source.name).exists()
        assert pet_window.pocket.get(original.id).path == source.resolve()

        moved = dialog.perform_selected("move", move_dest, notify=False)
        assert moved.succeeded == 1
        assert not source.exists()
        assert pet_window.pocket.get(original.id).path == (move_dest / source.name).resolve()
        dialog.remove_selected(confirm=False)
        dialog.close()

    def test_favorite_destination_copy_and_remove_only_reference(self, pet_window, test_temp_root):
        source = test_temp_root / "favorite-source.txt"
        favorite_folder = test_temp_root / "favorite"
        source.write_text("favorite"); favorite_folder.mkdir()
        pet_window.pocket.add(source)
        destinations = DestinationService(test_temp_root / "destinations.json")
        favorite = destinations.add_favorite(favorite_folder)
        dialog = PocketDialog(pet_window.pocket, pet_window, destinations=destinations)

        assert dialog.favorite_combo.count() == 1
        report = dialog.perform_favorite("copy", notify=False)
        assert report.succeeded == 1
        assert (favorite_folder / source.name).exists()
        dialog.remove_favorite()
        assert destinations.list_favorites() == []
        assert favorite_folder.exists()
        dialog.remove_selected(confirm=False)
        dialog.close()

    def test_successful_operation_records_recent_and_clear_keeps_target(self, pet_window, test_temp_root):
        source = test_temp_root / "recent-source.txt"
        target = test_temp_root / "recent-target"
        source.touch(); target.mkdir()
        pet_window.pocket.add(source)
        destinations = DestinationService(test_temp_root / "recent-destinations.json")
        dialog = PocketDialog(pet_window.pocket, pet_window, destinations=destinations)

        report = dialog.perform_selected("copy", target, notify=False)
        assert report.succeeded == 1
        assert destinations.list_recents()[0].path == target.resolve()
        assert dialog.recent_combo.count() == 1
        dialog.clear_recents()
        assert destinations.list_recents() == []
        assert target.exists()
        dialog.remove_selected(confirm=False)
        dialog.close()

    def test_settings_dialog_constructs(self, pet_window):
        d = pet_window_web.SettingsDialog(pet_window.config, pet_window)
        assert d is not None
        assert d.minimumWidth() >= 360
        d.close()

    def test_settings_dialog_has_no_legacy_reminder_controls(self, pet_window):
        d = pet_window_web.SettingsDialog(pet_window.config, pet_window)
        assert not hasattr(d, "water_interval")
        assert not hasattr(d, "water_enabled")
        d.close()

    def test_local_reminder_dialogs_construct(self, pet_window):
        add_dialog = AddReminderDialog(pet_window)
        assert add_dialog.content_edit is not None
        assert add_dialog.date_edit.date().isValid()
        add_dialog.close()

        list_dialog = ReminderListDialog(pet_window.reminder, pet_window)
        assert list_dialog.reminder_list.count() == 0
        list_dialog.close()

    def test_reminder_list_shows_and_deletes_pending_item(self, pet_window):
        reminder = pet_window.reminder.add_reminder(
            "GUI smoke", datetime.now() + timedelta(hours=1)
        )
        dialog = ReminderListDialog(pet_window.reminder, pet_window)
        assert dialog.reminder_list.count() == 1
        assert "GUI smoke" in dialog.reminder_list.item(0).text()
        dialog.delete_selected()
        assert pet_window.reminder.list_reminders() == []
        dialog.close()

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
        assert any("Add Reminder" in item for item in items)
        assert any("My Reminders" in item for item in items)
        assert any("Pocket" in item for item in items)

    def test_window_can_be_closed(self, pet_window):
        # close() on an unshown frameless tool window must not raise.
        pet_window.close()
        # re-open guard not needed; fixture teardown closes again safely.
