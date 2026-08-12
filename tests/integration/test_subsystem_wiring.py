"""Integration tests: real subsystems wired together (Phase 2).

Only external network boundaries are faked (Google Calendar). Everything else
is real: real Config persistence, real ReminderService logic, real
HTML-source animation metadata.
"""

import importlib.util
import json
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
ANIMS_JSON = PROJECT_ROOT / "assets" / "animations.json"
GENERATOR = PROJECT_ROOT / "scripts" / "gen_synthetic_assets.py"


@pytest.mark.integration
class TestReminderConfigPersistence:
    def test_set_water_interval_survives_config_reload(self, isolated_config):
        from reminder_service import ReminderService
        import config as config_mod

        svc = ReminderService(isolated_config)
        svc.set_water_interval(77)

        fresh_cfg = config_mod.Config()
        assert fresh_cfg.get("water_interval_min") == 77

        # A reminder rebuilt on the fresh config fires at the new interval.
        fired = []
        svc2 = ReminderService(fresh_cfg)
        svc2.on_water_reminder = fired.append
        svc2.tick(77 * 60)
        assert len(fired) == 1

    def test_enable_water_flag_persists_across_reload(self, isolated_config):
        from reminder_service import ReminderService
        import config as config_mod

        svc = ReminderService(isolated_config)
        svc.enable_water(False)

        fresh_cfg = config_mod.Config()
        assert fresh_cfg.get("water_enabled") is False

        fired = []
        svc2 = ReminderService(fresh_cfg)
        svc2.on_water_reminder = fired.append
        svc2.tick(30 * 60)
        assert fired == []  # still disabled after reload


@pytest.mark.integration
class TestAnimationMetadataConsistency:
    def test_exported_json_matches_html_source_extraction(self):
        """animations.json must equal a fresh mechanical extraction of the
        ANIMS table embedded in assets/clippy.html (single source of truth).
        """
        if not ANIMS_JSON.exists():
            pytest.skip("animations.json not generated (gitignored derivative)")

        spec = importlib.util.spec_from_file_location("gen_synthetic_assets", GENERATOR)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)

        extracted = mod.extract_anims()
        exported = json.loads(ANIMS_JSON.read_text(encoding="utf-8"))

        assert extracted == exported, (
            "assets/animations.json drifted from the ANIMS table in "
            "assets/clippy.html — regenerate with scripts/gen_synthetic_assets.py"
        )
