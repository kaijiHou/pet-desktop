"""Phase 9 boundary: Pocket drag-out uses file URLs only."""

from pathlib import Path

import pytest


@pytest.mark.unit
def test_drag_out_uses_qmime_file_urls_without_modifying_sources():
    source = (Path(__file__).resolve().parents[2] / "pocket_ui.py").read_text(encoding="utf-8")
    assert "QMimeData" in source
    assert "QUrl.fromLocalFile" in source
    assert "QDrag" in source
    assert "Qt.CopyAction" in source
    assert "shutil.copy" not in source
    assert "shutil.move" not in source
