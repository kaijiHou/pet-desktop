"""Phase 13 tests for foreground Explorer directory discovery."""

from pathlib import Path
from types import SimpleNamespace

import pytest

from explorer import ExplorerService


@pytest.mark.unit
class TestExplorerService:
    def test_returns_existing_directory_from_foreground_shell_window(self, test_temp_root):
        folder = test_temp_root / "Explorer"; folder.mkdir()
        calls = []
        def runner(command, **kwargs):
            calls.append(command)
            return SimpleNamespace(returncode=0, stdout=str(folder), stderr="")
        service = ExplorerService(runner=runner, foreground_hwnd_provider=lambda: 12345)
        assert service.current_directory() == folder.resolve()
        assert "12345" in calls[0][-1]

    def test_no_foreground_window_returns_none_without_shell_query(self):
        called = []
        service = ExplorerService(runner=lambda *a, **k: called.append(True),
                                  foreground_hwnd_provider=lambda: 0)
        assert service.current_directory() is None
        assert called == []

    def test_non_explorer_or_shell_error_returns_none(self):
        result = SimpleNamespace(returncode=0, stdout="", stderr="")
        service = ExplorerService(runner=lambda *a, **k: result,
                                  foreground_hwnd_provider=lambda: 1)
        assert service.current_directory() is None

    def test_nonexistent_output_is_not_reported_as_directory(self, test_temp_root):
        result = SimpleNamespace(returncode=0, stdout=str(test_temp_root / "missing"), stderr="")
        service = ExplorerService(runner=lambda *a, **k: result,
                                  foreground_hwnd_provider=lambda: 1)
        assert service.current_directory() is None
