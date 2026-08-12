"""Phase 11 favorite destination tests."""

import json

import pytest

from destinations import DestinationService


@pytest.fixture
def destinations(test_temp_root):
    return DestinationService(test_temp_root / "destinations.json")


@pytest.mark.unit
class TestFavoriteDestinations:
    def test_starts_empty_without_storage(self, destinations):
        assert destinations.list_favorites() == []

    def test_adds_existing_directory_and_persists(self, destinations, test_temp_root):
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

    def test_duplicate_returns_existing(self, destinations, test_temp_root):
        folder = test_temp_root / "Same"; folder.mkdir()
        first = destinations.add_favorite(folder)
        assert destinations.add_favorite(folder).id == first.id
        assert len(destinations.list_favorites()) == 1

    def test_remove_only_deletes_reference(self, destinations, test_temp_root):
        folder = test_temp_root / "Keep"; folder.mkdir()
        favorite = destinations.add_favorite(folder)
        assert destinations.remove_favorite(favorite.id) is True
        assert folder.exists()

    def test_missing_favorite_remains_visible_as_invalid(self, destinations, test_temp_root):
        folder = test_temp_root / "Gone"; folder.mkdir()
        favorite = destinations.add_favorite(folder)
        folder.rmdir()
        assert destinations.list_favorites()[0].exists is False

    def test_corrupt_storage_falls_back_to_empty(self, destinations):
        destinations.storage_path.write_text("broken")
        assert DestinationService(destinations.storage_path).list_favorites() == []


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

    def test_recent_history_is_capped_at_ten(self, destinations, test_temp_root):
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
