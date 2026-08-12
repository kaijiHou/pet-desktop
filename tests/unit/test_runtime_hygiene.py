"""Phase 17 acceptance boundaries for portable runtime storage and launchers."""

from pathlib import Path

import config
import paths
import pytest


ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.unit
def test_runtime_config_uses_project_local_data_directory():
    assert config.CONFIG_DIR == paths.PROJECT_ROOT / "data"
    assert config.CONFIG_FILE == config.CONFIG_DIR / "config.json"


@pytest.mark.unit
def test_obsolete_author_specific_launchers_are_absent():
    for name in ("launch_mochi.bat", "Mochi.vbs", "add_to_startup.bat"):
        assert not (ROOT / name).exists()


@pytest.mark.unit
def test_active_runtime_sources_have_no_author_or_home_storage_paths():
    active_sources = list(ROOT.glob("*.py"))
    combined = "\n".join(path.read_text(encoding="utf-8") for path in active_sources)
    assert "C:\\Users\\clara" not in combined
    assert "Path.home()" not in combined
