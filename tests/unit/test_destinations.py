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
