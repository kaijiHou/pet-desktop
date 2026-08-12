"""Phase 5 boundary tests for removal of the interval water reminder."""

from pathlib import Path

import pytest

import config as config_mod


PROJECT_ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.unit
class TestWaterReminderRemoval:
    def test_default_config_has_no_water_keys(self):
        assert all(not key.startswith("water_") for key in config_mod.DEFAULT_CONFIG)

    def test_legacy_water_keys_are_cleaned_from_disk(self, tmp_path, monkeypatch):
        config_dir = tmp_path / "desktop-pet"
        config_dir.mkdir()
        config_file = config_dir / "config.json"
        config_file.write_text(
            '{"water_enabled":true,"water_interval_min":30,"pet_name":"Clippy"}',
            encoding="utf-8",
        )
        monkeypatch.setattr(config_mod, "CONFIG_DIR", config_dir)
        monkeypatch.setattr(config_mod, "CONFIG_FILE", config_file)

        config = config_mod.Config()

        assert config.get("water_enabled") is None
        assert config.get("water_interval_min") is None
        assert "water_" not in config_file.read_text(encoding="utf-8")

    def test_active_reminder_and_ui_sources_have_no_water_behavior(self):
        for filename in ("reminder_service.py", "reminder_ui.py", "pet_window.py", "sounds.py"):
            source = (PROJECT_ROOT / filename).read_text(encoding="utf-8").lower()
            assert "water_" not in source, f"legacy water behavior remains in {filename}"
