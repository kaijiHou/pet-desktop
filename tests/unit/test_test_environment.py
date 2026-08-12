"""Test-environment self-checks (Phase 2).

Guard rails so a later phase cannot silently let test temp data drift back
onto C: or leak artifacts into git.
"""

import os
import subprocess
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.unit
class TestTestEnvironment:
    def test_test_temp_root_is_on_d_drive(self):
        from tests.conftest import TEST_TEMP_ROOT

        assert TEST_TEMP_ROOT.drive.upper() == "D:", str(TEST_TEMP_ROOT)
        assert str(TEST_TEMP_ROOT).startswith(str(PROJECT_ROOT))

    def test_process_temp_env_points_into_project_tmp(self):
        assert os.environ.get("TEMP", "").startswith(str(PROJECT_ROOT / ".tmp"))
        assert os.environ.get("TMP", "").startswith(str(PROJECT_ROOT / ".tmp"))

    def test_test_artifacts_are_ignored_by_git(self):
        # Anything written under .tmp/ or logs/ must never be committable.
        r = subprocess.run(
            ["git", "check-ignore", ".tmp/tests/example.txt", "logs/app.log"],
            cwd=PROJECT_ROOT, capture_output=True, text=True,
        )
        assert r.returncode == 0, f"check-ignore failed: {r.stdout} {r.stderr}"

    def test_test_files_themselves_are_not_ignored_by_git(self):
        # Regression for the upstream global `test_*.py` ignore rule:
        # tests/ must be trackable (rooted /test_*.py fix in .gitignore).
        r = subprocess.run(
            ["git", "check-ignore", "tests/unit/test_paths.py"],
            cwd=PROJECT_ROOT, capture_output=True, text=True,
        )
        assert r.returncode != 0, "tests/ is being git-ignored again"
