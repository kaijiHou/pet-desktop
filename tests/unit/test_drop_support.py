"""Phase 7 boundaries for drag-to-Pocket support."""

from pathlib import Path

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.unit
def test_both_window_tracks_accept_local_url_drops_without_file_operations():
    for filename in ("pet_window.py",):
        source = (PROJECT_ROOT / filename).read_text(encoding="utf-8")
        assert "setAcceptDrops(True)" in source
        assert "def dragEnterEvent" in source
        assert "def dropEvent" in source
        assert "PocketService" in source
        assert "shutil.copy" not in source
        assert "shutil.move" not in source
