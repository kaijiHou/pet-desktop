"""Tests for the unified paths module (Phase 2 infrastructure)."""

import pytest

import paths


@pytest.mark.unit
class TestProjectPaths:
    def test_project_root_is_the_repo_directory(self):
        assert paths.PROJECT_ROOT.name == "pet-desktop"
        assert (paths.PROJECT_ROOT / "main.py").exists()

    def test_log_dir_is_project_local(self):
        assert paths.LOG_DIR == paths.PROJECT_ROOT / "logs"

    def test_temp_dir_is_project_local(self):
        assert paths.TEMP_DIR == paths.PROJECT_ROOT / ".tmp"

    def test_data_dir_is_project_local(self):
        assert paths.DATA_DIR == paths.PROJECT_ROOT / "data"

    def test_no_path_is_hardcoded_to_c_drive(self):
        # The paths module must stay workspace-independent (D: policy).
        for p in (paths.PROJECT_ROOT, paths.DATA_DIR, paths.LOG_DIR, paths.TEMP_DIR):
            assert not str(p).upper().startswith("C:"), str(p)
