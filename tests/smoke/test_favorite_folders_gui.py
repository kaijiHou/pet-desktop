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
def test_manager_row_keeps_reorder_inside_more_menu(qapp, favorite_service, test_temp_root):
    from PyQt5.QtWidgets import QPushButton
    from favorite_folders_ui import FavoriteFoldersDialog

    for name in ("Alpha", "Beta"):
        (test_temp_root / name).mkdir()
        favorite_service.add_favorite(test_temp_root / name)
    dialog = FavoriteFoldersDialog(favorite_service)
    buttons = [button.text() for button in dialog.rows_by_id[
        favorite_service.list_favorites()[0].id
    ].findChildren(QPushButton)]
    assert buttons == ["打开", "⋯"]
    dialog.close()


@pytest.mark.smoke
@pytest.mark.gui
def test_missing_favorite_focus_shows_repair_guidance(qapp, favorite_service, test_temp_root):
    from favorite_folders_ui import FavoriteFoldersDialog

    folder = test_temp_root / "missing"; folder.mkdir()
    favorite = favorite_service.add_favorite(folder)
    folder.rmdir()
    dialog = FavoriteFoldersDialog(favorite_service, focus_id=favorite.id)
    assert not dialog.banner.isHidden()
    assert "修改路径" in dialog.banner.label.text()
    assert dialog.selected_favorite_id == favorite.id
    assert favorite.id in dialog.rows_by_id
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
def test_quick_panel_elides_long_name_and_routes_missing_click_to_repair(
    qapp, favorite_service, test_temp_root,
):
    from quick_panel import QuickPanel

    folder = test_temp_root / "2026年无人机跨视角地理定位全部实验资料"; folder.mkdir()
    favorite = favorite_service.add_favorite(folder)
    notices = []
    pet = SimpleNamespace(
        wage=SimpleNamespace(configured=False),
        pocket=SimpleNamespace(list_items=lambda: []),
        reminder=SimpleNamespace(list_reminders=lambda: []),
        _manage_favorite_folders=lambda *args, **kwargs: notices.append((args, kwargs)),
    )
    panel = QuickPanel(pet, destinations=favorite_service)
    button = panel.favorite_grid.itemAt(0).widget()
    assert button.text() != favorite.name
    assert favorite.name in button.toolTip()
    assert str(folder) in button.toolTip()

    folder.rmdir()
    panel.refresh()
    button = panel.favorite_grid.itemAt(0).widget()
    assert "路径失效" in button.toolTip()
    assert panel._open_favorite(favorite.id) is False
    assert notices[-1][0][0] == favorite.id
    assert "已经失效" in notices[-1][1]["focus_message"]
    panel.close()


@pytest.mark.smoke
@pytest.mark.gui
def test_current_explorer_pin_requires_confirmation_and_adds_named_path(
    qapp, monkeypatch, favorite_service, test_temp_root,
):
    from PyQt5.QtWidgets import QDialog
    import favorite_folders_ui
    import quick_panel
    from quick_panel import QuickPanel
    from ui.modern.dialog import ModernDialog

    folder = test_temp_root / "当前项目"; folder.mkdir()
    pet = SimpleNamespace(
        wage=SimpleNamespace(configured=False), pocket=SimpleNamespace(list_items=lambda: []),
        reminder=SimpleNamespace(list_reminders=lambda: []),
        explorer_service=SimpleNamespace(current_directory=lambda: folder, last_directory_status="ok"),
    )
    # Accept the explicit confirmation; keep the manager modal out of the test.
    monkeypatch.setattr(ModernDialog, "exec_", lambda _self: QDialog.Accepted)
    monkeypatch.setattr(favorite_folders_ui.FavoriteFoldersDialog, "exec_",
                        lambda _self: QDialog.Rejected)
    panel = QuickPanel(pet, destinations=favorite_service)
    assert panel._pin_current_folder() is True
    favorite = favorite_service.list_favorites()[0]
    assert favorite.path == folder.resolve()
    assert favorite.name == "当前项目"
    panel.close()


@pytest.mark.smoke
@pytest.mark.gui
@pytest.mark.parametrize(
    ("status", "expected"),
    [("no_explorer", "没有检测到"), ("not_filesystem", "不是普通文件夹")],
)
def test_current_explorer_pin_reports_unavailable_location(
    qapp, favorite_service, status, expected,
):
    from quick_panel import QuickPanel

    notices = []
    pet = SimpleNamespace(
        wage=SimpleNamespace(configured=False), pocket=SimpleNamespace(list_items=lambda: []),
        reminder=SimpleNamespace(list_reminders=lambda: []),
        explorer_service=SimpleNamespace(current_directory=lambda: None, last_directory_status=status),
        _manage_favorite_folders=lambda *args, **kwargs: notices.append(kwargs),
    )
    panel = QuickPanel(pet, destinations=favorite_service)
    assert panel._pin_current_folder() is False
    assert expected in notices[-1]["focus_message"]
    panel.close()


@pytest.mark.smoke
@pytest.mark.gui
def test_quick_panel_and_manager_probe_exists_once_per_refresh(
    qapp, monkeypatch, favorite_service, test_temp_root,
):
    from destinations import FavoriteDestination
    from favorite_folders_ui import FavoriteFoldersDialog
    from quick_panel import QuickPanel

    folder = test_temp_root / "probe"; folder.mkdir()
    favorite = favorite_service.add_favorite(folder)
    calls = {}
    original = FavoriteDestination.exists.fget

    def counted(item):
        calls[item.id] = calls.get(item.id, 0) + 1
        return original(item)

    monkeypatch.setattr(FavoriteDestination, "exists", property(counted))
    pet = SimpleNamespace(
        wage=SimpleNamespace(configured=False), pocket=SimpleNamespace(list_items=lambda: []),
        reminder=SimpleNamespace(list_reminders=lambda: []),
    )
    panel = QuickPanel(pet, destinations=favorite_service)
    calls.clear()
    panel._refresh_favorites()
    assert calls == {favorite.id: 1}
    calls.clear()
    dialog = FavoriteFoldersDialog(favorite_service)
    assert calls == {favorite.id: 1}
    dialog.close(); panel.close()


@pytest.mark.smoke
@pytest.mark.gui
def test_d_drive_root_favorite_opens_root_url_contract(qapp, monkeypatch, favorite_service):
    import quick_panel
    from quick_panel import QuickPanel

    root = Path("D:/")
    if not root.is_dir():
        pytest.skip("D: root is unavailable")
    favorite = favorite_service.add_favorite(root)
    pet = SimpleNamespace(
        wage=SimpleNamespace(configured=False), pocket=SimpleNamespace(list_items=lambda: []),
        reminder=SimpleNamespace(list_reminders=lambda: []),
    )
    opened = []
    monkeypatch.setattr(quick_panel, "QDesktopServices",
                        SimpleNamespace(openUrl=lambda url: opened.append(url.toLocalFile()) or True))
    panel = QuickPanel(pet, destinations=favorite_service)
    assert favorite.name == "D盘"
    assert panel._open_favorite(favorite.id)
    assert len(opened) == 1 and Path(opened[0]) == root
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
    pocket = PocketWindow(pet_window.pocket, destinations=pet_window.destination_service,
                          explorer_service=pet_window.explorer_service)
    assert pet_window.destination_service is panel.destinations is pocket.destinations
    assert pet_window.explorer_service is pocket.explorer

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


@pytest.mark.smoke
@pytest.mark.gui
def test_favorite_manager_live_refreshes_open_quick_panel_and_pocket(
    qapp, monkeypatch, pet_window, favorite_service, test_temp_root,
):
    from PyQt5.QtWidgets import QDialog
    import favorite_folders_ui
    from favorite_folders_ui import FavoriteFoldersDialog
    from pocket_window import PocketWindow
    from quick_panel import QuickPanel

    paths = {}
    for name in ("项目", "工作", "资料"):
        paths[name] = test_temp_root / name
        paths[name].mkdir()
    project = favorite_service.add_favorite(paths["项目"])
    work = favorite_service.add_favorite(paths["工作"])

    old_service = pet_window.destination_service
    old_panel, old_pocket = pet_window._quick_panel, pet_window._pocket_window
    pet_window.destination_service = favorite_service
    panel = QuickPanel(pet_window, destinations=favorite_service)
    pocket = PocketWindow(pet_window.pocket, destinations=favorite_service)
    pet_window._quick_panel, pet_window._pocket_window = panel, pocket
    real_exec = FavoriteFoldersDialog.exec_

    def edit_from_open_manager(dialog):
        assert dialog._rename_favorite(project.id, "公司项目")
        assert "公司项目" in panel.favorite_grid.itemAt(0).widget().toolTip()
        assert pocket.favorite_combo.itemText(pocket.favorite_combo.findData(project.id)) == "公司项目"

        assert dialog._move_favorite(work.id, -1)
        assert "工作" in panel.favorite_grid.itemAt(0).widget().toolTip()

        dialog._confirm_remove = lambda _favorite: True
        assert dialog._remove_favorite(project.id)
        assert all(panel.favorite_grid.itemAt(i).widget().toolTip().splitlines()[0] != "公司项目"
                   for i in range(panel.favorite_grid.count()))
        assert pocket.favorite_combo.currentData() != project.id

        assert dialog._add_path(paths["资料"])
        assert any("资料" in panel.favorite_grid.itemAt(i).widget().toolTip()
                   for i in range(panel.favorite_grid.count()))
        assert pocket.favorite_combo.findText("资料") >= 0
        return QDialog.Rejected

    monkeypatch.setattr(favorite_folders_ui.FavoriteFoldersDialog, "exec_", edit_from_open_manager)
    try:
        pet_window._manage_favorite_folders()
    finally:
        pet_window.destination_service = old_service
        pet_window._quick_panel, pet_window._pocket_window = old_panel, old_pocket
        monkeypatch.setattr(favorite_folders_ui.FavoriteFoldersDialog, "exec_", real_exec)
        panel.close(); pocket.close()


@pytest.mark.smoke
@pytest.mark.gui
def test_pet_favorite_submenu_is_shared_capped_and_opens_path(qapp, monkeypatch, pet_window,
                                                               favorite_service, test_temp_root):
    from PyQt5.QtWidgets import QMenu
    import pet_window as pet_module

    paths = []
    for index in range(10):
        folder = test_temp_root / f"目录{index}"; folder.mkdir()
        paths.append(folder)
        favorite_service.add_favorite(folder)
    missing = favorite_service.list_favorites()[2]
    paths[2].rmdir()

    old_service = pet_window.destination_service
    pet_window.destination_service = favorite_service
    opened, managed = [], []

    class DesktopServices:
        @staticmethod
        def openUrl(url):
            opened.append(url.toLocalFile())
            return True

    monkeypatch.setattr(pet_module, "QDesktopServices", DesktopServices)
    monkeypatch.setattr(pet_window, "_manage_favorite_folders", lambda: managed.append(True))
    menu = QMenu()
    try:
        submenu = pet_window._add_favorite_context_menu(menu)
        actions = submenu.actions()
        favorite_actions = [action for action in actions if action.text().startswith("目录")]
        assert len(favorite_actions) == 8
        assert favorite_actions[2].text() == "目录2（路径失效）"
        assert not favorite_actions[2].isEnabled()
        assert all("目录8" not in action.text() and "目录9" not in action.text()
                   for action in favorite_actions)
        assert actions[-1].text() == "管理常用文件夹"
        favorite_actions[0].trigger()
        assert Path(opened[0]) == paths[0].resolve()
        actions[-1].trigger()
        assert managed == [True]
    finally:
        pet_window.destination_service = old_service
        menu.deleteLater()
