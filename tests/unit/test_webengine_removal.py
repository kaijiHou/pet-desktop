"""Phase 16 boundary: native renderer fully replaces WebEngine."""

from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.unit
class TestWebEngineRemoval:
    def test_webengine_window_and_html_renderer_are_deleted(self):
        assert not (ROOT / "pet_window_web.py").exists()
        assert not (ROOT / "assets" / "clippy.html").exists()

    def test_main_uses_native_window(self):
        source = (ROOT / "main.py").read_text(encoding="utf-8")
        assert "from pet_window import main" in source
        assert "pet_window_web" not in source

    def test_runtime_requirements_have_no_webengine(self):
        requirements = (ROOT / "requirements.txt").read_text(encoding="utf-8").lower()
        assert "webengine" not in requirements

    def test_native_catalog_is_tracked_and_html_free(self):
        assert (ROOT / "assets" / "animations.json").exists()
        source = (ROOT / "pet_sprite.py").read_text(encoding="utf-8")
        assert "animations.json" in source
        assert "clippy.html" not in source

    def test_no_production_imports_qt_webengine(self):
        for path in ROOT.glob("*.py"):
            source = path.read_text(encoding="utf-8")
            assert "QtWebEngine" not in source, path.name
