"""Unit tests for the Phase 6 reference-only Pocket data layer."""

from datetime import datetime
import json

import pytest

from pocket_service import PocketService


@pytest.fixture
def pocket(test_temp_root):
    storage = test_temp_root / "pocket.json"
    now = lambda: datetime(2026, 8, 12, 12, 30, 0)
    return PocketService(storage_path=storage, now_provider=now), storage


@pytest.mark.unit
class TestPocketCrud:
    def test_starts_empty_without_creating_storage(self, pocket):
        service, storage = pocket
        assert service.list_items() == []
        assert not storage.exists()

    def test_add_file_stores_reference_metadata_only(self, pocket, test_temp_root):
        service, storage = pocket
        source = test_temp_root / "report.txt"
        source.write_text("original", encoding="utf-8")

        item = service.add(source)

        assert item.path == source.resolve()
        assert item.name == "report.txt"
        assert item.item_type == "file"
        assert item.added_at == datetime(2026, 8, 12, 12, 30)
        assert source.read_text(encoding="utf-8") == "original"
        assert set(test_temp_root.iterdir()) == {source, storage}

    def test_add_directory(self, pocket, test_temp_root):
        service, _ = pocket
        folder = test_temp_root / "Project"
        folder.mkdir()
        assert service.add(folder).item_type == "directory"

    def test_add_missing_path_is_rejected(self, pocket, test_temp_root):
        service, _ = pocket
        with pytest.raises(FileNotFoundError):
            service.add(test_temp_root / "missing.txt")

    def test_duplicate_path_returns_existing_item(self, pocket, test_temp_root):
        service, _ = pocket
        source = test_temp_root / "same.txt"
        source.touch()
        first = service.add(source)
        second = service.add(source)
        assert second.id == first.id
        assert len(service.list_items()) == 1

    def test_remove_existing_and_missing_item(self, pocket, test_temp_root):
        service, storage = pocket
        source = test_temp_root / "remove.txt"
        source.touch()
        item = service.add(source)
        assert service.remove(item.id) is True
        assert service.remove("missing") is False
        assert json.loads(storage.read_text(encoding="utf-8")) == []

    def test_replace_path_preserves_identity_after_external_move(self, pocket, test_temp_root):
        service, _ = pocket
        source = test_temp_root / "old.txt"; source.touch()
        item = service.add(source)
        target = test_temp_root / "new.txt"
        source.rename(target)
        replaced = service.replace_path(item.id, target)
        assert replaced.id == item.id
        assert replaced.path == target.resolve()


@pytest.mark.unit
class TestPocketPersistence:
    def test_items_survive_restart(self, pocket, test_temp_root):
        service, storage = pocket
        source = test_temp_root / "persistent.txt"
        source.touch()
        created = service.add(source)

        restarted = PocketService(storage_path=storage)
        assert restarted.list_items()[0].id == created.id
        assert restarted.list_items()[0].path == source.resolve()

    def test_corrupt_storage_falls_back_to_empty(self, pocket):
        _, storage = pocket
        storage.write_text("broken", encoding="utf-8")
        assert PocketService(storage_path=storage).list_items() == []

    def test_invalid_entries_are_skipped(self, pocket, test_temp_root):
        _, storage = pocket
        source = test_temp_root / "valid.txt"
        source.touch()
        storage.write_text(json.dumps([
            {"id": "ok", "path": str(source), "name": "valid.txt",
             "item_type": "file", "added_at": "2026-08-12T12:30:00"},
            {"id": "bad", "path": str(source), "item_type": "unknown"},
        ]), encoding="utf-8")
        assert [item.id for item in PocketService(storage_path=storage).list_items()] == ["ok"]


@pytest.mark.unit
class TestPocketValidity:
    def test_item_reports_whether_target_still_exists(self, pocket, test_temp_root):
        service, _ = pocket
        source = test_temp_root / "temporary.txt"
        source.touch()
        item = service.add(source)
        assert item.exists is True
        source.unlink()
        assert item.exists is False

    def test_list_can_include_or_hide_missing_targets(self, pocket, test_temp_root):
        service, _ = pocket
        source = test_temp_root / "gone.txt"
        source.touch()
        service.add(source)
        source.unlink()
        assert len(service.list_items(include_missing=True)) == 1
        assert service.list_items(include_missing=False) == []

    def test_cleanup_missing_removes_only_invalid_references(self, pocket, test_temp_root):
        service, storage = pocket
        keep = test_temp_root / "keep.txt"
        gone = test_temp_root / "gone.txt"
        keep.touch()
        gone.touch()
        service.add(keep)
        missing = service.add(gone)
        gone.unlink()

        removed = service.cleanup_missing()

        assert [item.id for item in removed] == [missing.id]
        assert [item.path for item in service.list_items()] == [keep.resolve()]
        assert len(json.loads(storage.read_text(encoding="utf-8"))) == 1
