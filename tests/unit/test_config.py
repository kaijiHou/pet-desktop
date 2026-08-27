"""Characterization tests for config.Config (Phase 2).

V2 update (ux-redesign-v2): default pet_name changed "Clippy" → "小助手"
and V2 behavior keys added (character_mode / wheel_zoom_enabled /
show_welcome / ...). The old characterization pinned the baseline default
name; the V2 task mandates unified Chinese product language, so the
expected default intentionally changed. All other semantics (persistence,
merge, corrupt-file fallback) are unchanged.

Storage is isolated via the `isolated_config` fixture (monkeypatched module
paths); the real ~/desktop-pet/config.json is never touched.
"""

import json

import pytest

import config as config_mod


# ── Defaults present on a fresh Config ─────────────────────────────────────

EXPECTED_DEFAULTS = {
    "pet_scale": 3.0,
    "pet_x": -1,
    "pet_y": -1,
    "pet_name": "小助手",
    # V2 behavior keys
    "character_mode": "single",
    "character_image": "",
    "wheel_zoom_enabled": False,
    "show_pet_name": False,
    "show_welcome": True,
}


@pytest.mark.unit
class TestConfigDefaults:
    def test_init_exposes_all_documented_defaults(self, isolated_config):
        cfg = isolated_config
        for key, expected in EXPECTED_DEFAULTS.items():
            assert cfg.get(key) == expected, f"default for {key} changed"

    def test_get_missing_key_returns_supplied_default(self, isolated_config):
        assert isolated_config.get("does_not_exist", "fallback") == "fallback"

    def test_get_missing_key_returns_none_when_no_default(self, isolated_config):
        assert isolated_config.get("does_not_exist") is None

    def test_pet_name_property_reflects_default(self, isolated_config):
        assert isolated_config.pet_name == "小助手"


# ── Persistence round-trip ─────────────────────────────────────────────────

@pytest.mark.unit
class TestConfigPersistence:
    def test_set_persists_and_is_reread_by_new_instance(self, isolated_config, tmp_path, monkeypatch):
        cfg = isolated_config
        cfg.set("pet_name", "Persistent")

        # A brand-new Config reading the same isolated file sees the value.
        fresh = config_mod.Config()
        assert fresh.get("pet_name") == "Persistent"

    def test_save_writes_valid_json_to_config_file(self, isolated_config, monkeypatch):
        cfg = isolated_config
        cfg.set("pet_name", "MochiTest")

        written = json.loads(config_mod.CONFIG_FILE.read_text())
        assert written["pet_name"] == "MochiTest"

    def test_load_merges_file_over_defaults_without_dropping_defaults(self, tmp_path, monkeypatch):
        # Arrange: a config file carrying only ONE key.
        cfg_dir = tmp_path / "desktop-pet"
        cfg_dir.mkdir()
        (cfg_dir / "config.json").write_text(json.dumps({"pet_scale": 5.0}))
        monkeypatch.setattr(config_mod, "CONFIG_DIR", cfg_dir)
        monkeypatch.setattr(config_mod, "CONFIG_FILE", cfg_dir / "config.json")

        # Act
        cfg = config_mod.Config()

        # Assert: override applied, other defaults intact.
        assert cfg.get("pet_scale") == 5.0
        assert cfg.get("pet_name") == EXPECTED_DEFAULTS["pet_name"]


# ── Missing / corrupt config file behavior ─────────────────────────────────

@pytest.mark.unit
class TestConfigResilience:
    def test_missing_config_file_uses_defaults(self, tmp_path, monkeypatch):
        cfg_dir = tmp_path / "desktop-pet"
        cfg_dir.mkdir()
        monkeypatch.setattr(config_mod, "CONFIG_DIR", cfg_dir)
        monkeypatch.setattr(config_mod, "CONFIG_FILE", cfg_dir / "config.json")

        cfg = config_mod.Config()
        assert cfg.get("pet_scale") == EXPECTED_DEFAULTS["pet_scale"]

    def test_corrupt_config_file_silently_falls_back_to_defaults(self, tmp_path, monkeypatch):
        # Arrange: malformed JSON. Upstream catches JSONDecodeError/OSError and
        # silently keeps defaults (config.py _load). Characterized, not "fixed".
        cfg_dir = tmp_path / "desktop-pet"
        cfg_dir.mkdir()
        (cfg_dir / "config.json").write_text("{not valid json!!!")
        monkeypatch.setattr(config_mod, "CONFIG_DIR", cfg_dir)
        monkeypatch.setattr(config_mod, "CONFIG_FILE", cfg_dir / "config.json")

        cfg = config_mod.Config()
        assert cfg.get("pet_scale") == EXPECTED_DEFAULTS["pet_scale"]

    def test_set_after_corrupt_load_recovers_persistence(self, tmp_path, monkeypatch):
        cfg_dir = tmp_path / "desktop-pet"
        cfg_dir.mkdir()
        (cfg_dir / "config.json").write_text("garbage")
        monkeypatch.setattr(config_mod, "CONFIG_DIR", cfg_dir)
        monkeypatch.setattr(config_mod, "CONFIG_FILE", cfg_dir / "config.json")

        cfg = config_mod.Config()
        cfg.set("pet_x", 42)

        fresh = config_mod.Config()
        assert fresh.get("pet_x") == 42
