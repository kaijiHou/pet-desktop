"""V5.0 fallback hardening regressions (task §20/§21/§22)."""

import logging

import pytest


@pytest.fixture()
def dynamic_pet(pet_window_dynamic):
    return pet_window_dynamic


def _warn_count(caplog):
    return sum(1 for r in caplog.records
               if r.levelno >= logging.WARNING and "failed or missing" in r.getMessage())


def test_missing_id_warns_once_then_persists(dynamic_pet, caplog):
    """§20: first startup with a stale id warns once and persists the
    effective id; a second 'restart' must not warn again."""
    pet = dynamic_pet
    pet.config.set("selected_character_id", "missing_pet")
    caplog.clear()
    pet._load_dynamic_renderer()
    first = _warn_count(caplog)
    assert pet.config.get("selected_character_id") == "default_dynamic_ghost"
    # simulate a second process start: reload from the persisted config
    caplog.clear()
    pet._load_dynamic_renderer()
    second = _warn_count(caplog)
    assert first == 1, f"expected exactly one fallback warning, got {first}"
    assert second == 0, f"restart must not re-warn, got {second}"


def test_valid_custom_character_not_overridden(dynamic_pet, test_temp_root, monkeypatch):
    """§21: an installed custom pack must survive startup untouched."""
    import json
    import shutil
    from pathlib import Path
    from paths import DATA_DIR

    packs = DATA_DIR / "characters" / "my-cat"
    packs.mkdir(parents=True, exist_ok=True)
    builtin = Path(dynamic_pet.dynamic_renderer.pack_root)
    for name in ("pet.json", "spritesheet.webp"):
        shutil.copy2(builtin / name, packs / name)
    manifest = json.loads((packs / "pet.json").read_text(encoding="utf-8-sig"))
    manifest["id"] = "my-cat"
    (packs / "pet.json").write_text(json.dumps(manifest, ensure_ascii=False), encoding="utf-8")

    dynamic_pet.config.set("selected_character_id", "my-cat")
    dynamic_pet._load_dynamic_renderer()
    assert dynamic_pet.dynamic_renderer.is_loaded
    assert dynamic_pet.config.get("selected_character_id") == "my-cat", \
        "valid custom character must not be overridden by the builtin ghost"


def test_corrupted_pack_falls_back_then_emergency_single(dynamic_pet, caplog, monkeypatch):
    """§22: corrupted requested pack → builtin ghost; if the ghost itself
    can't load → emergency single mode, never a white screen."""
    pet = dynamic_pet
    previous = pet.dynamic_renderer   # working renderer from fixture startup
    pet.config.set("selected_character_id", "broken_pack")
    monkeypatch.setattr("character_v4.renderer.DynamicPackRenderer.load", lambda self: False)
    caplog.clear()
    pet._load_dynamic_renderer()
    messages = [r.getMessage() for r in caplog.records if r.levelno >= logging.WARNING]
    assert any("fallback default_dynamic_ghost" in m for m in messages), messages
    assert any("emergency fallback to single mode" in m for m in messages), messages
    # Emergency never tears down a working renderer (no white screen) —
    # it just refuses to install a broken one.
    assert pet.dynamic_renderer is previous
    assert pet.config.get("selected_character_id") == "broken_pack", \
        "emergency must not persist a fallback id when the builtin itself failed"
