"""Phase 3 regression tests: AI Chat/OpenAI are fully removed.

Reminders and the current WebEngine renderer intentionally remain. These tests
guard the AI-removal boundary after later phases remove other integrations.
"""

from pathlib import Path

import pytest

import config as config_mod


PROJECT_ROOT = Path(__file__).resolve().parents[2]
PRODUCTION_FILES = (
    PROJECT_ROOT / "pet_window.py",
    PROJECT_ROOT / "pet_window_web.py",
    PROJECT_ROOT / "sounds.py",
)


@pytest.mark.unit
class TestAiRemoval:
    def test_ai_engine_module_is_deleted(self):
        assert not (PROJECT_ROOT / "ai_engine.py").exists()

    def test_default_config_has_no_openai_or_personality_keys(self):
        forbidden = {
            "openai_api_key",
            "openai_model",
            "openai_base_url",
            "ai_personality",
        }
        assert forbidden.isdisjoint(config_mod.DEFAULT_CONFIG)

    def test_legacy_ai_keys_are_ignored_when_loading(self, tmp_path, monkeypatch):
        config_dir = tmp_path / "desktop-pet"
        config_dir.mkdir()
        config_file = config_dir / "config.json"
        config_file.write_text(
            '{"openai_api_key":"secret","openai_model":"old",'
            '"ai_personality":"old","ai_name":"Mochi","pet_scale":4.0}',
            encoding="utf-8",
        )
        monkeypatch.setattr(config_mod, "CONFIG_DIR", config_dir)
        monkeypatch.setattr(config_mod, "CONFIG_FILE", config_file)

        cfg = config_mod.Config()

        assert cfg.get("pet_scale") == 4.0
        assert cfg.get("openai_api_key") is None
        assert cfg.get("openai_model") is None
        assert cfg.get("ai_personality") is None
        assert cfg.pet_name == "Mochi"
        persisted = config_file.read_text(encoding="utf-8")
        assert "secret" not in persisted
        assert "openai_" not in persisted
        assert "ai_personality" not in persisted
        assert '"ai_name"' not in persisted
        assert '"pet_name": "Mochi"' in persisted

    def test_production_sources_have_no_ai_chat_or_openai_references(self):
        forbidden = ("AIEngine", "ChatDialog", "openai_", "OpenAI", "_open_chat", "play_chat")
        for path in PRODUCTION_FILES:
            source = path.read_text(encoding="utf-8")
            for token in forbidden:
                assert token not in source, f"{token!r} remains in {path.name}"
