"""Phase 4 regression tests: Google Calendar/OAuth are fully removed."""

from pathlib import Path

import pytest

import config as config_mod


PROJECT_ROOT = Path(__file__).resolve().parents[2]
PRODUCTION_FILES = (
    PROJECT_ROOT / "pet_window.py",
    PROJECT_ROOT / "pet_window_web.py",
    PROJECT_ROOT / "reminder_service.py",
)


@pytest.mark.unit
class TestCalendarRemoval:
    def test_calendar_service_module_is_deleted(self):
        assert not (PROJECT_ROOT / "calendar_service.py").exists()

    def test_default_config_has_no_calendar_keys(self):
        assert all(not key.startswith("calendar_") for key in config_mod.DEFAULT_CONFIG)

    def test_config_module_has_no_oauth_paths(self):
        assert not hasattr(config_mod, "OAUTH_FILE")
        assert not hasattr(config_mod, "CREDENTIALS_FILE")

    def test_legacy_calendar_keys_are_removed_from_disk(self, tmp_path, monkeypatch):
        config_dir = tmp_path / "desktop-pet"
        config_dir.mkdir()
        config_file = config_dir / "config.json"
        config_file.write_text(
            '{"calendar_enabled":true,"calendar_check_interval_min":15,'
            '"calendar_reminder_minutes_before":10,"water_interval_min":44}',
            encoding="utf-8",
        )
        monkeypatch.setattr(config_mod, "CONFIG_DIR", config_dir)
        monkeypatch.setattr(config_mod, "CONFIG_FILE", config_file)

        cfg = config_mod.Config()

        assert cfg.get("water_interval_min") is None
        assert cfg.get("calendar_enabled") is None
        persisted = config_file.read_text(encoding="utf-8")
        assert "calendar_" not in persisted

    def test_production_sources_have_no_calendar_or_oauth_references(self):
        forbidden = (
            "CalendarService",
            "calendar_service",
            "calendar_",
            "_show_schedule",
            "_init_calendar",
            "on_meeting_reminder",
            "OAuth",
            "OAUTH_FILE",
            "CREDENTIALS_FILE",
        )
        for path in PRODUCTION_FILES:
            source = path.read_text(encoding="utf-8")
            for token in forbidden:
                assert token not in source, f"{token!r} remains in {path.name}"

    def test_current_requirements_have_no_google_calendar_dependencies(self):
        requirements = (PROJECT_ROOT / "requirements.txt").read_text(encoding="utf-8").lower()
        forbidden = ("google-api-python-client", "google-auth-oauthlib", "pytz")
        assert all(package not in requirements for package in forbidden)
