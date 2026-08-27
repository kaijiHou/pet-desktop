"""V2 PocketWindow GUI tests.

Covers the REAL V2 pocket UI (pocket_window.PocketWindow), which the
production PetWindow._open_pocket now uses. This closes the reviewer gap
where smoke tests exercised the obsolete pocket_ui.PocketDialog instead.
"""
import pytest
from PyQt5.QtCore import QUrl


def _mk(pet_window, **kw):
    from pocket_window import PocketWindow
    return PocketWindow(pet_window.pocket, **kw)


@pytest.mark.smoke
@pytest.mark.gui
class TestPocketWindowGui:
    def test_lists_items_with_missing_marker(self, pet_window, test_temp_root):
        source = test_temp_root / "pocket-ui.txt"; source.touch()
        pet_window.pocket.add(source)
        pw = _mk(pet_window)
        assert pw.item_list.count() == 1
        assert "pocket-ui.txt" in pw.item_list.item(0).text()
        assert pw.item_list.item(0).data(0x0100)  # Qt.UserRole id present
        pw.close()
        for i in list(pet_window.pocket.list_items()): pet_window.pocket.remove(i.id)

    def test_remove_selected_keeps_original_file(self, pet_window, test_temp_root):
        source = test_temp_root / "rem.txt"; source.touch()
        pet_window.pocket.add(source)
        pw = _mk(pet_window)
        pw.item_list.item(0).setSelected(True)
        pw._remove_selected()
        assert pet_window.pocket.list_items() == []
        assert source.exists()
        pw.close()

    def test_drag_out_exports_local_file_urls(self, pet_window, test_temp_root):
        source = test_temp_root / "dragout.txt"; source.touch()
        pet_window.pocket.add(source)
        pw = _mk(pet_window)
        mime = pw.item_list.mime_data_for_selected()
        assert mime is not None and mime.hasUrls()
        assert mime.urls()[0].isLocalFile()
        from pathlib import Path
        assert Path(mime.urls()[0].toLocalFile()) == source.resolve()
        pw.close()
        for i in list(pet_window.pocket.list_items()): pet_window.pocket.remove(i.id)

    def test_missing_item_cannot_start_drag(self, pet_window, test_temp_root):
        source = test_temp_root / "nodrag.txt"; source.touch()
        pet_window.pocket.add(source); source.unlink()
        pw = _mk(pet_window)
        assert pw.item_list.mime_data_for_selected() is None
        pw.close()
        for i in list(pet_window.pocket.list_items()): pet_window.pocket.remove(i.id)

    def test_copy_and_move_update_ref(self, pet_window, test_temp_root):
        source = test_temp_root / "op.txt"; source.write_text("payload")
        copy_dest = test_temp_root / "copies"; move_dest = test_temp_root / "moves"
        copy_dest.mkdir(); move_dest.mkdir()
        orig = pet_window.pocket.add(source)
        pw = _mk(pet_window)
        pw.item_list.item(0).setSelected(True)
        rep = pw._run_operation("copy", copy_dest)
        assert rep and rep.succeeded == 1
        assert source.exists() and (copy_dest / source.name).exists()
        assert pet_window.pocket.get(orig.id).path == source.resolve()
        # move updates ref to new location
        rep2 = pw._run_operation("move", move_dest)
        assert rep2 and rep2.succeeded == 1
        assert not source.exists()
        assert pet_window.pocket.get(orig.id).path == (move_dest / source.name).resolve()
        pw.close()
        for i in list(pet_window.pocket.list_items()): pet_window.pocket.remove(i.id)

    def test_favorite_copy_keeps_reference(self, pet_window, test_temp_root):
        from destinations import DestinationService
        source = test_temp_root / "fav-src.txt"; source.write_text("f")
        fav_folder = test_temp_root / "fav"; fav_folder.mkdir()
        dests = DestinationService(test_temp_root / "d.json")
        dests.add_favorite(fav_folder)
        pet_window.pocket.add(source)
        pw = _mk(pet_window, destinations=dests)
        pw.item_list.item(0).setSelected(True)
        report = pw._run_operation("copy", fav_folder)
        assert report and report.succeeded == 1
        assert (fav_folder / source.name).exists()
        pw.close()
        for i in list(pet_window.pocket.list_items()): pet_window.pocket.remove(i.id)

    def test_records_recent_on_success(self, pet_window, test_temp_root):
        from destinations import DestinationService
        source = test_temp_root / "rec-src.txt"; source.touch()
        target = test_temp_root / "rec-target"; target.mkdir()
        dests = DestinationService(test_temp_root / "recent.json")
        pet_window.pocket.add(source)
        pw = _mk(pet_window, destinations=dests)
        pw.item_list.item(0).setSelected(True)
        report = pw._run_operation("copy", target)
        assert report and report.succeeded == 1
        assert dests.list_recents()[0].path == target.resolve()
        pw.close()
        for i in list(pet_window.pocket.list_items()): pet_window.pocket.remove(i.id)

    def test_explorer_action_uses_snapshot(self, pet_window, test_temp_root):
        source = test_temp_root / "exp-src.txt"; source.write_text("e")
        target = test_temp_root / "exp-target"; target.mkdir()
        pet_window.pocket.add(source)
        class FakeExplorer:
            def current_directory(self): return target
        pw = _mk(pet_window, explorer_service=FakeExplorer())
        pw._snapshot_explorer()  # capture snapshot from FakeExplorer
        pw.item_list.item(0).setSelected(True)
        report = pw._run_operation("copy", pw._explorer_snapshot)
        assert report and report.succeeded == 1
        assert (target / source.name).read_text() == "e"
        pw.close()
        for i in list(pet_window.pocket.list_items()): pet_window.pocket.remove(i.id)

    def test_empty_state_shows_hint(self, pet_window):
        pw = _mk(pet_window)
        assert pw.item_list.count() == 0
        # empty_label should be shown (not hidden) in empty state
        assert not pw.empty_label.isHidden()
        pw.close()
