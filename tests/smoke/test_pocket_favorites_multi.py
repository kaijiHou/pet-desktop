"""Multi-selection safety and reference mapping for favorite destinations."""

import pytest
from PyQt5.QtCore import Qt

from destinations import DestinationService
from pocket_service import PocketService
from pocket_window import PocketWindow


def _select(window, ids):
    selected = set(ids)
    for index in range(window.item_list.count()):
        item = window.item_list.item(index)
        item.setSelected(item.data(Qt.UserRole) in selected)
    window._on_selection_changed()


@pytest.mark.smoke
@pytest.mark.gui
def test_copy_selected_files_to_favorite_is_batch_and_records_recent_once(qapp, test_temp_root):
    source = test_temp_root / "source"; source.mkdir()
    target = test_temp_root / "Project"; target.mkdir()
    files = {name: source / f"{name}.txt" for name in ("a", "b", "c")}
    for name, path in files.items():
        path.write_text(name, encoding="utf-8")

    pocket = PocketService(test_temp_root / "pocket.json")
    ids = {name: pocket.add(path).id for name, path in files.items()}
    destinations = DestinationService(test_temp_root / "destinations.json")
    favorite = destinations.add_favorite(target)
    window = PocketWindow(pocket, destinations=destinations)
    _select(window, (ids["a"], ids["b"]))

    report = window._operate_on_selected_target("copy", window.favorite_combo, favorite=True)

    assert report.succeeded == 2 and report.failed == report.skipped == 0
    assert all(files[name].exists() for name in ("a", "b", "c"))
    assert (target / "a.txt").read_text(encoding="utf-8") == "a"
    assert (target / "b.txt").read_text(encoding="utf-8") == "b"
    assert not (target / "c.txt").exists()
    assert len(destinations.list_recents()) == 1
    assert destinations.list_recents()[0].path == favorite.path
    window.close()


@pytest.mark.smoke
@pytest.mark.gui
def test_move_selected_files_updates_each_pocket_reference(qapp, test_temp_root):
    source = test_temp_root / "source"; source.mkdir()
    target = test_temp_root / "Project"; target.mkdir()
    files = {name: source / f"{name}.txt" for name in ("d", "e")}
    for name, path in files.items():
        path.write_text(name, encoding="utf-8")

    pocket = PocketService(test_temp_root / "pocket.json")
    ids = {name: pocket.add(path).id for name, path in files.items()}
    destinations = DestinationService(test_temp_root / "destinations.json")
    favorite = destinations.add_favorite(target)
    window = PocketWindow(pocket, destinations=destinations)
    _select(window, ids.values())

    report = window._operate_on_selected_target("move", window.favorite_combo, favorite=True)

    assert report.succeeded == 2 and report.failed == report.skipped == 0
    for name, original in files.items():
        target_path = (target / original.name).resolve()
        assert not original.exists() and target_path.is_file()
        assert pocket.get(ids[name]).path == target_path
    assert len(destinations.list_recents()) == 1
    assert destinations.list_recents()[0].path == favorite.path
    window.close()


@pytest.mark.smoke
@pytest.mark.gui
def test_mixed_move_updates_only_succeeded_reference_and_keeps_missing_item(qapp, test_temp_root):
    source = test_temp_root / "source"; source.mkdir()
    target = test_temp_root / "Project"; target.mkdir()
    good = source / "good.txt"; good.write_text("ok", encoding="utf-8")
    missing = source / "missing.txt"; missing.write_text("gone", encoding="utf-8")

    pocket = PocketService(test_temp_root / "pocket.json")
    good_id = pocket.add(good).id
    missing_id = pocket.add(missing).id
    missing.unlink()
    destinations = DestinationService(test_temp_root / "destinations.json")
    favorite = destinations.add_favorite(target)
    window = PocketWindow(pocket, destinations=destinations)
    _select(window, (good_id, missing_id))

    report = window._operate_on_selected_target("move", window.favorite_combo, favorite=True)

    assert report.succeeded == 1 and report.failed == 1
    assert pocket.get(good_id).path == (target / good.name).resolve()
    assert pocket.get(missing_id).path == missing.resolve()
    assert not missing.exists() and (target / good.name).is_file()
    assert len(destinations.list_recents()) == 1
    assert destinations.list_recents()[0].path == favorite.path
    row = next(window.item_list.item(i) for i in range(window.item_list.count())
               if window.item_list.item(i).data(Qt.UserRole) == missing_id)
    assert "路径失效" in row.text()
    window.close()
