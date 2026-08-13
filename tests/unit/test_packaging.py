"""Phase 18 packaging contract tests."""

from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.unit
def test_spec_bundles_animation_catalog_and_excludes_webengine():
    source = (ROOT / "pet-desktop.spec").read_text(encoding="utf-8")
    assert "assets" in source and "animations.json" in source
    assert "PyQt5.QtWebEngineWidgets" in source
    assert 'name="DesktopPet"' in source


@pytest.mark.unit
def test_release_build_is_project_local_and_clean():
    source = (ROOT / "scripts" / "build_release.ps1").read_text(encoding="utf-8")
    assert 'Join-Path $projectRoot "build"' in source
    assert 'Join-Path $projectRoot "dist"' in source
    assert 'Join-Path $projectRoot "release"' in source
    assert "GetFullPath" in source
    assert "--clean" in source
    assert 'Join-Path $packageDir "assets"' in source
    assert "PYINSTALLER_CONFIG_DIR" in source
    assert '$env:TEMP = $tempDir' in source


@pytest.mark.unit
def test_dev_requirements_pin_pyinstaller():
    requirements = (ROOT / "requirements-dev.txt").read_text(encoding="utf-8")
    assert "pyinstaller==6.15.0" in requirements.lower()


@pytest.mark.unit
def test_release_verifier_checks_black_box_runtime_boundaries():
    source = (ROOT / "scripts" / "verify_release.ps1").read_text(encoding="utf-8")
    for boundary in ("running", "responding", "animation_catalog", "user_assets_dir",
                     "log_created", "webengine_files"):
        assert boundary in source


@pytest.mark.unit
def test_manual_drag_fixture_verifies_copy_semantics():
    source = (ROOT / "scripts" / "manual_drag_acceptance.py").read_text(encoding="utf-8")
    assert '"target_copy_exists"' in source
    assert '"source_still_exists"' in source
    assert '"status": "PASS"' in source
