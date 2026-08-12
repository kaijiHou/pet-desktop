"""Phase 10 tests for explicit copy/move operations."""

from pathlib import Path

import pytest

from file_ops import FileOperationService


@pytest.fixture
def service():
    return FileOperationService()


@pytest.mark.unit
class TestCopyOperations:
    def test_copy_file_preserves_source_and_content(self, service, test_temp_root):
        source = test_temp_root / "source.txt"
        destination = test_temp_root / "dest"
        source.write_text("hello", encoding="utf-8")
        destination.mkdir()
        report = service.copy([source], destination)
        assert report.succeeded == 1 and report.failed == 0
        assert source.exists()
        assert (destination / "source.txt").read_text(encoding="utf-8") == "hello"

    def test_copy_directory_recursively(self, service, test_temp_root):
        source = test_temp_root / "folder"
        destination = test_temp_root / "dest"
        source.mkdir(); destination.mkdir()
        (source / "nested.txt").write_text("nested", encoding="utf-8")
        report = service.copy([source], destination)
        assert report.succeeded == 1
        assert (destination / "folder" / "nested.txt").read_text() == "nested"

    def test_default_conflict_renames_without_overwriting(self, service, test_temp_root):
        source = test_temp_root / "same.txt"
        destination = test_temp_root / "dest"
        source.write_text("new"); destination.mkdir()
        (destination / "same.txt").write_text("old")
        report = service.copy([source], destination)
        assert (destination / "same.txt").read_text() == "old"
        assert (destination / "same (1).txt").read_text() == "new"
        assert report.items[0].destination.name == "same (1).txt"

    def test_skip_conflict_reports_skipped(self, service, test_temp_root):
        source = test_temp_root / "same.txt"
        destination = test_temp_root / "dest"
        source.touch(); destination.mkdir(); (destination / "same.txt").touch()
        report = service.copy([source], destination, conflict="skip")
        assert report.skipped == 1 and report.succeeded == 0


@pytest.mark.unit
class TestMoveAndErrors:
    def test_move_relocates_file(self, service, test_temp_root):
        source = test_temp_root / "move.txt"
        destination = test_temp_root / "dest"
        source.write_text("move"); destination.mkdir()
        report = service.move([source], destination)
        assert report.succeeded == 1
        assert not source.exists()
        assert (destination / "move.txt").exists()

    def test_missing_source_is_reported_without_raising(self, service, test_temp_root):
        destination = test_temp_root / "dest"; destination.mkdir()
        report = service.copy([test_temp_root / "missing"], destination)
        assert report.failed == 1
        assert "not found" in report.items[0].error.lower()

    def test_invalid_destination_is_reported(self, service, test_temp_root):
        source = test_temp_root / "source.txt"; source.touch()
        report = service.copy([source], test_temp_root / "missing-dest")
        assert report.failed == 1

    def test_batch_continues_after_individual_failure(self, service, test_temp_root):
        good = test_temp_root / "good.txt"; good.write_text("ok")
        destination = test_temp_root / "dest"; destination.mkdir()
        report = service.copy([test_temp_root / "missing", good], destination)
        assert report.failed == 1 and report.succeeded == 1
        assert (destination / "good.txt").exists()

    def test_unknown_conflict_policy_is_rejected(self, service, test_temp_root):
        with pytest.raises(ValueError, match="conflict"):
            service.copy([], test_temp_root, conflict="overwrite")

    def test_directory_cannot_be_copied_into_its_own_descendant(self, service, test_temp_root):
        source = test_temp_root / "source"
        destination = source / "nested"
        source.mkdir(); destination.mkdir()
        report = service.copy([source], destination)
        assert report.failed == 1
        assert "inside" in report.items[0].error
