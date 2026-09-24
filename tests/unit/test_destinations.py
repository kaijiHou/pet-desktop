"""Phase 11 favorite destination tests."""

import json
import os
from datetime import datetime
from pathlib import Path

import pytest

from destinations import DestinationService, display_default_name


@pytest.fixture
def destinations(test_temp_root):
    return DestinationService(test_temp_root / "destinations.json")


@pytest.mark.unit
class TestFavoriteDestinations:
    def test_starts_empty_without_storage(self, destinations):
        assert destinations.list_favorites() == []

    def test_add_favorite(self, destinations, test_temp_root):
        folder = test_temp_root / "Work"; folder.mkdir()
        favorite = destinations.add_favorite(folder)
        assert favorite.path == folder.resolve()
        assert favorite.name == "Work"
        restarted = DestinationService(destinations.storage_path)
        assert restarted.list_favorites()[0].id == favorite.id

    def test_rejects_file_or_missing_path(self, destinations, test_temp_root):
        file = test_temp_root / "file.txt"; file.touch()
        with pytest.raises(NotADirectoryError): destinations.add_favorite(file)
        with pytest.raises(NotADirectoryError): destinations.add_favorite(test_temp_root / "missing")

    def test_duplicate_path_returns_existing(self, destinations, test_temp_root):
        folder = test_temp_root / "Same"; folder.mkdir()
        first = destinations.add_favorite(folder)
        assert destinations.add_favorite(folder).id == first.id
        assert len(destinations.list_favorites()) == 1

    def test_remove_favorite(self, destinations, test_temp_root):
        folder = test_temp_root / "Keep"; folder.mkdir()
        favorite = destinations.add_favorite(folder)
        assert destinations.remove_favorite(favorite.id) is True
        assert folder.exists()

    def test_missing_folder_is_retained(self, destinations, test_temp_root):
        folder = test_temp_root / "Gone"; folder.mkdir()
        favorite = destinations.add_favorite(folder)
        folder.rmdir()
        assert destinations.list_favorites()[0].exists is False

    def test_corrupt_storage_falls_back_to_empty(self, destinations):
        original = b"broken"
        destinations.storage_path.write_bytes(original)
        assert DestinationService(destinations.storage_path).list_favorites() == []
        assert destinations.storage_path.read_bytes() == original
        backups = list(destinations.storage_path.parent.glob("destinations.json.corrupt-*.bak"))
        assert len(backups) == 1 and backups[0].read_bytes() == original

    def test_rename_favorite(self, destinations, test_temp_root):
        folder = test_temp_root / "Work"; folder.mkdir()
        favorite = destinations.add_favorite(folder)
        renamed = destinations.rename_favorite(favorite.id, "  项目资料  ")
        assert renamed.name == "项目资料"
        assert renamed.id == favorite.id and renamed.path == favorite.path
        assert destinations.rename_favorite(favorite.id, "项目资料").name == "项目资料"

    def test_rename_rejects_blank_or_overlong_name(self, destinations, test_temp_root):
        folder = test_temp_root / "Work"; folder.mkdir()
        favorite = destinations.add_favorite(folder)
        with pytest.raises(ValueError): destinations.rename_favorite(favorite.id, "  ")
        with pytest.raises(ValueError): destinations.rename_favorite(favorite.id, "名" * 41)
        assert destinations.rename_favorite("unknown", "有效") is None

    def test_update_favorite_path(self, destinations, test_temp_root):
        old = test_temp_root / "MissingSoon"; old.mkdir()
        new = test_temp_root / "Replacement"; new.mkdir()
        favorite = destinations.add_favorite(old)
        renamed = destinations.rename_favorite(favorite.id, "项目")
        updated = destinations.update_favorite_path(favorite.id, new)
        assert (updated.id, updated.name, updated.order) == (renamed.id, "项目", 0)
        assert updated.path == new.resolve()

    def test_update_path_requires_directory(self, destinations, test_temp_root):
        folder = test_temp_root / "Existing"; folder.mkdir()
        favorite = destinations.add_favorite(folder)
        with pytest.raises(NotADirectoryError):
            destinations.update_favorite_path(favorite.id, test_temp_root / "not-a-folder")
        assert destinations.update_favorite_path("unknown", folder) is None

    def test_update_path_rejects_duplicate_target(self, destinations, test_temp_root):
        first_path = test_temp_root / "First"; first_path.mkdir()
        second_path = test_temp_root / "Second"; second_path.mkdir()
        first = destinations.add_favorite(first_path)
        second = destinations.add_favorite(second_path)
        with pytest.raises(ValueError, match="已经添加"):
            destinations.update_favorite_path(first.id, second_path)

    def test_reorder_favorites(self, destinations, test_temp_root):
        folders = [test_temp_root / name for name in ("A", "B", "C")]
        for folder in folders: folder.mkdir()
        favorites = [destinations.add_favorite(folder) for folder in folders]
        result = destinations.reorder_favorites([favorites[2].id, favorites[0].id, favorites[1].id])
        assert [(item.name, item.order) for item in result] == [("C", 0), ("A", 1), ("B", 2)]
        restarted = DestinationService(destinations.storage_path)
        assert [item.id for item in restarted.list_favorites()] == [favorites[2].id, favorites[0].id, favorites[1].id]

    def test_reorder_rejects_unknown_ids(self, destinations, test_temp_root):
        folder = test_temp_root / "Only"; folder.mkdir()
        favorite = destinations.add_favorite(folder)
        with pytest.raises(ValueError): destinations.reorder_favorites(["unknown"])
        with pytest.raises(ValueError): destinations.reorder_favorites([])

    def test_reorder_rejects_duplicates(self, destinations, test_temp_root):
        folder = test_temp_root / "Only"; folder.mkdir()
        favorite = destinations.add_favorite(folder)
        with pytest.raises(ValueError): destinations.reorder_favorites([favorite.id, favorite.id])

    def test_v1_migration(self, destinations, test_temp_root):
        folders = [test_temp_root / name for name in ("Legacy A", "Legacy B")]
        for folder in folders: folder.mkdir()
        created = datetime(2024, 1, 2, 3, 4, 5).isoformat(timespec="seconds")
        legacy = {"favorites": [
            {"id": "a", "path": str(folders[0]), "name": "甲", "added_at": created},
            {"id": "b", "path": str(folders[1]), "name": "乙", "added_at": created},
        ], "recents": []}
        destinations.storage_path.write_text(json.dumps(legacy), encoding="utf-8")
        loaded = DestinationService(destinations.storage_path)
        assert [(item.id, item.order) for item in loaded.list_favorites()] == [("a", 0), ("b", 1)]
        loaded.rename_favorite("a", "新名称")
        saved = json.loads(destinations.storage_path.read_text(encoding="utf-8"))
        assert saved["version"] == 2
        assert [item["order"] for item in saved["favorites"]] == [0, 1]

    def test_favorite_limit_is_enforced(self, destinations, test_temp_root):
        for index in range(20):
            folder = test_temp_root / f"Favorite {index}"; folder.mkdir()
            destinations.add_favorite(folder)
        overflow = test_temp_root / "Overflow"; overflow.mkdir()
        with pytest.raises(ValueError, match="最多"):
            destinations.add_favorite(overflow)

    def test_root_drive_default_name(self):
        assert display_default_name(Path("D:/")) == "D盘"

    def test_v1_over_limit_records_are_preserved_and_reorderable(self, destinations, test_temp_root):
        folder = test_temp_root / "new"; folder.mkdir()
        raw = {"favorites": [
            {"id": str(index), "path": str(test_temp_root / f"old-{index}"),
             "name": f"旧目录 {index}", "added_at": "2026-01-01T00:00:00"}
            for index in range(25)
        ], "recents": []}
        destinations.storage_path.write_text(json.dumps(raw), encoding="utf-8")
        loaded = DestinationService(destinations.storage_path)
        assert len(loaded.list_favorites()) == 25
        with pytest.raises(ValueError, match="最多"):
            loaded.add_favorite(folder)
        reordered = loaded.reorder_favorites([item.id for item in reversed(loaded.list_favorites())])
        assert len(reordered) == 25 and reordered[0].id == "24"

    @pytest.mark.skipif(os.name != "nt", reason="Windows paths are case-insensitive")
    def test_windows_case_variant_path_is_not_added_twice(self, destinations, test_temp_root):
        folder = test_temp_root / "Project"; folder.mkdir()
        first = destinations.add_favorite(folder)
        second = destinations.add_favorite(Path(str(folder).swapcase()))
        assert second.id == first.id
        assert len(destinations.list_favorites()) == 1

    def test_corrupt_file_backup_is_idempotent(self, test_temp_root):
        path = test_temp_root / "destinations.json"
        original = b"{ this is not json\xff"
        path.write_bytes(original)
        for _ in range(3):
            assert DestinationService(path).list_favorites() == []
        backups = list(test_temp_root.glob("destinations.json.corrupt-*.bak"))
        assert len(backups) == 1
        assert backups[0].read_bytes() == original
        assert path.read_bytes() == original


@pytest.mark.unit
class TestRecentDestinations:
    def test_record_recent_is_newest_first_and_persistent(self, destinations, test_temp_root):
        first = test_temp_root / "First"; second = test_temp_root / "Second"
        first.mkdir(); second.mkdir()
        destinations.record_recent(first)
        destinations.record_recent(second)
        assert [item.path for item in destinations.list_recents()] == [second.resolve(), first.resolve()]
        assert len(DestinationService(destinations.storage_path).list_recents()) == 2

    def test_reusing_recent_moves_it_to_front_without_duplicate(self, destinations, test_temp_root):
        first = test_temp_root / "First"; second = test_temp_root / "Second"
        first.mkdir(); second.mkdir()
        destinations.record_recent(first); destinations.record_recent(second); destinations.record_recent(first)
        assert [item.path for item in destinations.list_recents()] == [first.resolve(), second.resolve()]

    def test_recents_still_limited_to_10(self, destinations, test_temp_root):
        for index in range(12):
            folder = test_temp_root / str(index); folder.mkdir()
            destinations.record_recent(folder)
        assert len(destinations.list_recents()) == 10
        assert destinations.list_recents()[0].name == "11"

    def test_clear_recents_does_not_clear_favorites(self, destinations, test_temp_root):
        folder = test_temp_root / "Shared"; folder.mkdir()
        destinations.add_favorite(folder); destinations.record_recent(folder)
        destinations.clear_recents()
        assert destinations.list_recents() == []
        assert len(destinations.list_favorites()) == 1
