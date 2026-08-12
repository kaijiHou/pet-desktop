"""Root conftest — test isolation & D-drive temp discipline (Phase 2).

Hard constraints honored here:
  * ALL test temp data lives under D:\\pet-desktop\\.tmp\\tests\\ (never C:).
    TEMP/TMP are redirected at conftest import time so pytest's own tmp
    machinery (tmp_path / basetemp) also stays on the project drive.
  * Every test gets an isolated temp dir, cleaned up afterwards.
  * Tests never touch the user's real files (Desktop/Downloads/Documents),
    and never read/write the real ~/desktop-pet/ config state.
  * sys.path gets the project root so business modules import cleanly.
"""

import os
import shutil
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Test temp root — fixed on D: per project policy.
TEST_TEMP_ROOT = PROJECT_ROOT / ".tmp" / "tests"

# Redirect process temp env BEFORE pytest/tempfile resolve their temp dirs, so
# nothing test-related ever lands on C:. (Requirement: test temp on D:.)
TEST_TEMP_ROOT.mkdir(parents=True, exist_ok=True)
os.environ["TEMP"] = str(TEST_TEMP_ROOT)
os.environ["TMP"] = str(TEST_TEMP_ROOT)

# NOTE: QT_QPA_PLATFORM=offscreen is deliberately NOT set. Phase 2 probing
# showed QWebEngineView.page() segfaults under offscreen (Chromium needs a
# real OpenGL context). GUI tests run on the real platform but construct
# windows WITHOUT show() and hide the tray icon, so nothing appears on screen.


@pytest.fixture
def test_temp_root(request):
    """Per-test isolated temp directory under D:\\pet-desktop\\.tmp\\tests\\.

    Created fresh for each test, removed (with subtree) afterwards.
    """
    safe = (
        request.node.nodeid.replace("/", "_").replace("::", "__")
        .replace("<", "_").replace(">", "_").replace(" ", "_")
    )
    d = TEST_TEMP_ROOT / safe
    if d.exists():
        shutil.rmtree(d)
    d.mkdir(parents=True)
    yield d
    shutil.rmtree(d, ignore_errors=True)


@pytest.fixture
def isolated_config(test_temp_root, monkeypatch):
    """A Config instance whose storage is redirected into a test temp dir.

    The upstream Config module binds CONFIG_DIR/CONFIG_FILE at import time,
    so we patch the module attributes (behavior-preserving test isolation —
    no production code change). The real ~/desktop-pet/config.json is never
    read or written by tests using this fixture.
    """
    import config as config_mod

    cfg_dir = test_temp_root / "desktop-pet"
    cfg_dir.mkdir()
    cfg_file = cfg_dir / "config.json"

    monkeypatch.setattr(config_mod, "CONFIG_DIR", cfg_dir)
    monkeypatch.setattr(config_mod, "CONFIG_FILE", cfg_file)

    return config_mod.Config()


@pytest.fixture(scope="session")
def qapp():
    """Session-wide QApplication under offscreen platform (GUI tests).

    Created once; Qt requires exactly one QApplication instance.
    """
    from PyQt5.QtWidgets import QApplication

    app = QApplication.instance()
    if app is None:
        app = QApplication([sys.argv[0]])
    yield app
