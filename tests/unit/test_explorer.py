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

    def test_falls_back_to_last_active_explorer_when_foreground_is_pet(self, test_temp_root):
        """D1 fix: after focusing Explorer C, opening the pet/pocket panel
        (foreground != explorer) must still target C."""
        folder = test_temp_root / "Explorer"; folder.mkdir()
        service = ExplorerService(runner=lambda *a, **k: SimpleNamespace(returncode=0, stdout=str(folder), stderr=""))
        # Pre-record that we were just working in this Explorer folder.
        service.set_last_active(folder)
        # Foreground is now the pet itself (not explorer); no Explorer window
        # resolves for it, and the raw directory query returns nothing.
        service._foreground_hwnd = lambda: 999
        service._foreground_is_explorer = lambda hwnd: False
        service._directory_for_hwnd = lambda hwnd: None
        # current_directory falls back to the cached last-active Explorer folder.
        assert service.current_directory() == folder.resolve()
