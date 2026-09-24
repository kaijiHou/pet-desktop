"""Behavioral contracts for favorite-folder UI surfaces (no screen automation)."""

from types import SimpleNamespace
from pathlib import Path

import pytest

from destinations import DestinationService


@pytest.fixture
def favorite_service(test_temp_root):
    return DestinationService(test_temp_root / "destinations.json")


@pytest.mark.smoke
@pytest.mark.gui
def test_manager_add_duplicate_rename_and_reorder(qapp, favorite_service, test_temp_root):
    from favorite_folders_ui import FavoriteFoldersDialog

    folders = [test_temp_root / name for name in ("Alpha", "Beta")]
    for folder in folders:
        folder.mkdir()
    dialog = FavoriteFoldersDialog(favorite_service)
    assert not dialog.empty_label.isHidden()
    assert dialog.empty_label.text().startswith("还没有常用文件夹")

    first = dialog._add_path(folders[0])
    assert first.name == "Alpha"
    assert dialog._add_path(folders[0]).id == first.id
    assert dialog.banner.label.text() == "已经是常用文件夹"
    second = dialog._add_path(folders[1])
    assert [item.name for item in favorite_service.list_favorites()] == ["Alpha", "Beta"]

    dialog._rename_favorite(first.id, "  项目  ")
    assert favorite_service.get_favorite(first.id).name == "项目"
    assert dialog._move_favorite(second.id, -1)
    assert [(item.name, item.order) for item in favorite_service.list_favorites()] == [
        ("Beta", 0), ("项目", 1),
    ]
    dialog.close()


@pytest.mark.smoke
@pytest.mark.gui
def test_manager_path_repair_missing_state_and_remove_never_deletes_folder(
    qapp, favorite_service, test_temp_root,
):
    from PyQt5.QtWidgets import QLabel, QPushButton
    from favorite_folders_ui import FavoriteFoldersDialog

    old = test_temp_root / "Old"; old.mkdir()
    replacement = test_temp_root / "Replacement"; replacement.mkdir()
    favorite = favorite_service.add_favorite(old)
    dialog = FavoriteFoldersDialog(favorite_service)
    old.rmdir()
    dialog.refresh()
    row = dialog.rows_by_id[favorite.id]
    open_button = next(button for button in row.findChildren(QPushButton) if button.text() == "打开")
    assert not open_button.isEnabled()
    assert "路径失效" in [label.text() for label in row.findChildren(QLabel)]
    old.mkdir()
    dialog.refresh()
    restored_row = dialog.rows_by_id[favorite.id]
    restored_open = next(button for button in restored_row.findChildren(QPushButton) if button.text() == "打开")
    assert restored_open.isEnabled()
    old.rmdir()

    updated = dialog._update_path(favorite.id, replacement)
    assert updated.id == favorite.id and updated.name == favorite.name
    assert updated.exists
    dialog._confirm_remove = lambda _favorite: True
    assert dialog._remove_favorite(favorite.id)
    assert replacement.is_dir()
    assert favorite_service.list_favorites() == []
    dialog.close()


@pytest.mark.smoke
@pytest.mark.gui
def test_quick_panel_shows_only_first_six_and_open_does_not_record_recent(
    qapp, monkeypatch, favorite_service, test_temp_root,
):
    import quick_panel
    from quick_panel import QuickPanel

    pet = SimpleNamespace(
        wage=SimpleNamespace(configured=False),
        pocket=SimpleNamespace(list_items=lambda: []),
        reminder=SimpleNamespace(list_reminders=lambda: []),
    )
    opened = []

    class DesktopServices:
        @staticmethod
        def openUrl(url):
            opened.append(url.toLocalFile())
            return True

    monkeypatch.setattr(quick_panel, "QDesktopServices", DesktopServices)
    empty_panel = QuickPanel(pet, destinations=favorite_service)
    assert not empty_panel.favorite_empty.isHidden()
    assert not empty_panel.favorite_add_btn.isHidden()
    empty_panel.close()
    favorites = []
    for index in range(8):
        folder = test_temp_root / f"Folder {index}"; folder.mkdir()
        favorites.append(favorite_service.add_favorite(folder))
    panel = QuickPanel(pet, destinations=favorite_service)
    panel.refresh()
    assert panel.favorite_grid.count() == 6
    assert panel.favorite_count == 8
    assert panel.favorite_view_all_btn.text() == "查看全部（8）"
    assert panel.sizeHint().height() <= 520
    assert panel._open_favorite(favorites[0].id)
    assert len(opened) == 1 and Path(opened[0]) == favorites[0].path
    assert favorite_service.list_recents() == []
    panel.close()


@pytest.mark.smoke
@pytest.mark.gui
def test_pocket_favorite_controls_use_shared_service_and_refresh(qapp, favorite_service, test_temp_root):
    from pocket_service import PocketService
    from pocket_window import PocketWindow

    source = test_temp_root / "source.txt"; source.write_text("payload", encoding="utf-8")
    move_source = test_temp_root / "move-source.txt"; move_source.write_text("move me", encoding="utf-8")
    target = test_temp_root / "Target"; target.mkdir()
    favorite = favorite_service.add_favorite(target)
    pocket = PocketService(test_temp_root / "pocket.json")
    pocket.add(source)
    move_item = pocket.add(move_source)
    window = PocketWindow(pocket, destinations=favorite_service)
    assert window.favorite_combo.currentData() == favorite.id
    window.item_list.item(0).setSelected(True)
    window._on_selection_changed()
    assert window.copy_favorite_btn.isEnabled()
    report = window._operate_on_selected_target("copy", window.favorite_combo, favorite=True)
    assert report.succeeded == 1
    assert (target / source.name).read_text(encoding="utf-8") == "payload"
    assert favorite_service.list_recents()[0].path == target.resolve()

    window.item_list.clearSelection()
    window.item_list.item(1).setSelected(True)
    report = window._operate_on_selected_target("move", window.favorite_combo, favorite=True)
    assert report.succeeded == 1
    assert not move_source.exists()
    assert (target / move_source.name).read_text(encoding="utf-8") == "move me"
    assert pocket.get(move_item.id).path == (target / move_source.name).resolve()

    favorite_service.remove_favorite(favorite.id)
    window.refresh_destinations()
    assert window.favorite_combo.currentData() is None
    assert not window.copy_favorite_btn.isEnabled()
    window.close()


@pytest.mark.smoke
@pytest.mark.gui
def test_pet_window_injects_one_destination_service_into_all_surfaces(qapp, monkeypatch, pet_window):
    from PyQt5.QtWidgets import QDialog
    import favorite_folders_ui
    from pocket_window import PocketWindow
    from quick_panel import QuickPanel

    panel = QuickPanel(pet_window)
    pocket = PocketWindow(pet_window.pocket, destinations=pet_window.destination_service)
    assert pet_window.destination_service is panel.destinations is pocket.destinations

    captured = {}
    real_init = favorite_folders_ui.FavoriteFoldersDialog.__init__

    def capture_init(dialog, destinations=None, parent=None, **kwargs):
        captured["destinations"] = destinations
        real_init(dialog, destinations, parent, **kwargs)

    monkeypatch.setattr(favorite_folders_ui.FavoriteFoldersDialog, "__init__", capture_init)
    monkeypatch.setattr(favorite_folders_ui.FavoriteFoldersDialog, "exec_", lambda _dialog: QDialog.Rejected)
    pet_window._manage_favorite_folders()
    assert captured["destinations"] is pet_window.destination_service
    panel.close()
    pocket.close()
