"""Tests for character_v4 — Codex manifest, atlas, state machine, importer."""
import json
import tempfile
import zipfile
from pathlib import Path

import pytest
from PIL import Image, ImageDraw


# ── Manifest tests ──────────────────────────────────────────────────────────

@pytest.mark.unit
def test_codex_v1_constants():
    """Codex V1 SDK contract: 1536×1872, 8×9 cells, 192×208."""
    from character_v4.manifest import (
        CODEX_V1_SIZE, CODEX_CELL_W, CODEX_CELL_H, CODEX_V1_ROWS
    )
    assert CODEX_V1_SIZE == (1536, 1872)
    assert CODEX_CELL_W == 192
    assert CODEX_CELL_H == 208
    assert len(CODEX_V1_ROWS) == 9  # 9 animation rows


@pytest.mark.unit
def test_codex_v2_constants():
    """Codex V2 SDK contract: 1536×2288, 8×11 cells."""
    from character_v4.manifest import CODEX_V2_SIZE, CODEX_V2_ROWS
    assert CODEX_V2_SIZE == (1536, 2288)
    assert len(CODEX_V2_ROWS) == 11  # V1 + look_up + look_down


@pytest.mark.unit
def test_manifest_from_dict():
    from character_v4.manifest import CodexPetManifest
    m = CodexPetManifest.from_dict({
        "id": "test-pet",
        "displayName": "Test Pet",
        "spritesheetPath": "sheet.webp",
        "spriteVersionNumber": 2,
    })
    assert m.id == "test-pet"
    assert m.display_name == "Test Pet"
    assert m.sprite_version == 2


@pytest.mark.unit
def test_manifest_to_dict():
    from character_v4.manifest import CodexPetManifest
    m = CodexPetManifest(id="x", display_name="X")
    d = m.to_dict()
    assert d["id"] == "x"
    assert d["displayName"] == "X"


@pytest.mark.unit
def test_manifest_load_and_validate(tmp_path):
    from character_v4.manifest import CodexPetManifest
    # Create a valid V1 pack
    pack = tmp_path / "test_pack"
    pack.mkdir()
    atlas = Image.new("RGBA", (1536, 1872), (0, 0, 0, 0))
    atlas.save(str(pack / "spritesheet.webp"), "WEBP")
    with open(pack / "pet.json", "w") as f:
        json.dump({"id": "test", "displayName": "Test", "spriteVersionNumber": 1}, f)
    m = CodexPetManifest.load(pack)
    assert m.id == "test"
    result = m.validate(pack)
    assert result.ok, f"Errors: {result.errors}"


@pytest.mark.unit
def test_manifest_rejects_wrong_size(tmp_path):
    from character_v4.manifest import CodexPetManifest
    pack = tmp_path / "bad_pack"
    pack.mkdir()
    atlas = Image.new("RGBA", (100, 100), (0, 0, 0, 0))
    atlas.save(str(pack / "spritesheet.webp"), "WEBP")
    with open(pack / "pet.json", "w") as f:
        json.dump({"id": "bad", "spriteVersionNumber": 1}, f)
    m = CodexPetManifest.load(pack)
    result = m.validate(pack)
    assert not result.ok
    assert any("size" in e.lower() or "dimension" in e.lower() for e in result.errors)


@pytest.mark.unit
def test_manifest_missing_spritesheet():
    from character_v4.manifest import CodexPetManifest
    m = CodexPetManifest(id="x", display_name="X")
    result = m.validate(Path("/nonexistent"))
    assert not result.ok


# ── Atlas tests ─────────────────────────────────────────────────────────────

@pytest.mark.unit
def test_atlas_loads_v1(tmp_path, qapp):
    from character_v4.manifest import CodexPetManifest
    from character_v4.atlas import SpritesheetAtlas
    pack = tmp_path / "atlas_test"
    pack.mkdir()
    atlas = Image.new("RGBA", (1536, 1872), (0, 0, 0, 0))
    # Draw something in idle frame (row 0, col 0)
    d = ImageDraw.Draw(atlas)
    d.rectangle([10, 10, 180, 190], fill=(255, 0, 0, 255))
    atlas.save(str(pack / "spritesheet.webp"), "WEBP")
    with open(pack / "pet.json", "w") as f:
        json.dump({"id": "test", "spriteVersionNumber": 1}, f)
    m = CodexPetManifest.load(pack)
    a = SpritesheetAtlas(m, pack)
    assert a.load()
    assert a.frame_count("idle") == 6
    assert a.frame_count("running_r") == 8
    frame = a.get_frame("idle", 0)
    assert frame is not None


# ── State machine tests ─────────────────────────────────────────────────────

@pytest.mark.unit
def test_state_machine_starts_idle():
    from character_v4.state_machine import PetStateMachine, DEFAULT_STATES
    from character_v4.atlas import SpritesheetAtlas
    from character_v4.animation import AnimationPlayer
    from character_v4.manifest import CodexPetManifest
    from PIL import Image, ImageDraw
    import json
    pack = Path(tempfile.mkdtemp()) / "sm_test"
    pack.mkdir()
    atlas_img = Image.new("RGBA", (1536, 1872), (0, 0, 0, 0))
    atlas_img.save(str(pack / "spritesheet.webp"), "WEBP")
    with open(pack / "pet.json", "w") as f:
        json.dump({"id": "test", "spriteVersionNumber": 1}, f)
    m = CodexPetManifest.load(pack)
    a = SpritesheetAtlas(m, pack)
    a.load()
    p = AnimationPlayer(a)
    sm = PetStateMachine(a, p)
    assert sm.current_state == "IDLE"
    assert sm.is_idle


@pytest.mark.unit
def test_state_machine_delete_interrupts_idle():
    from character_v4.state_machine import PetStateMachine
    from character_v4.atlas import SpritesheetAtlas
    from character_v4.animation import AnimationPlayer
    from character_v4.manifest import CodexPetManifest
    from PIL import Image, ImageDraw
    import json
    pack = Path(tempfile.mkdtemp()) / "sm_test2"
    pack.mkdir()
    atlas_img = Image.new("RGBA", (1536, 1872), (0, 0, 0, 0))
    atlas_img.save(str(pack / "spritesheet.webp"), "WEBP")
    with open(pack / "pet.json", "w") as f:
        json.dump({"id": "test", "spriteVersionNumber": 1}, f)
    m = CodexPetManifest.load(pack)
    a = SpritesheetAtlas(m, pack)
    a.load()
    p = AnimationPlayer(a)
    sm = PetStateMachine(a, p)
    assert sm.current_state == "IDLE"
    sm.transition("delete_file")
    assert sm.current_state == "DELETE_FILE"


@pytest.mark.unit
def test_state_machine_priority():
    """ERROR should override DELETE."""
    from character_v4.state_machine import PetStateMachine
    from character_v4.atlas import SpritesheetAtlas
    from character_v4.animation import AnimationPlayer
    from character_v4.manifest import CodexPetManifest
    from PIL import Image, ImageDraw
    import json
    pack = Path(tempfile.mkdtemp()) / "sm_test3"
    pack.mkdir()
    atlas_img = Image.new("RGBA", (1536, 1872), (0, 0, 0, 0))
    atlas_img.save(str(pack / "spritesheet.webp"), "WEBP")
    with open(pack / "pet.json", "w") as f:
        json.dump({"id": "test", "spriteVersionNumber": 1}, f)
    m = CodexPetManifest.load(pack)
    a = SpritesheetAtlas(m, pack)
    a.load()
    p = AnimationPlayer(a)
    sm = PetStateMachine(a, p)
    sm.transition("delete_file")
    assert sm.current_state == "DELETE_FILE"
    sm.transition("error")
    assert sm.current_state == "ERROR"


# ── Importer tests ──────────────────────────────────────────────────────────

@pytest.mark.unit
def test_import_folder(tmp_path):
    from character_v4.importer import import_codex_pack
    # Create source pack
    src = tmp_path / "src_pack"
    src.mkdir()
    atlas = Image.new("RGBA", (1536, 1872), (0, 0, 0, 0))
    atlas.save(str(src / "spritesheet.webp"), "WEBP")
    with open(src / "pet.json", "w") as f:
        json.dump({"id": "import_test", "displayName": "Import Test", "spriteVersionNumber": 1}, f)
    dest = tmp_path / "installed"
    dest.mkdir()
    path, result = import_codex_pack(src, dest)
    assert path is not None
    assert result.ok
    assert (path / "pet.json").exists()


@pytest.mark.unit
def test_import_zip(tmp_path):
    from character_v4.importer import import_codex_pack
    # Create source pack
    src = tmp_path / "zip_pack"
    src.mkdir()
    atlas = Image.new("RGBA", (1536, 1872), (0, 0, 0, 0))
    atlas.save(str(src / "spritesheet.webp"), "WEBP")
    with open(src / "pet.json", "w") as f:
        json.dump({"id": "zip_test", "displayName": "ZIP Test", "spriteVersionNumber": 1}, f)
    # Create ZIP
    zip_path = tmp_path / "pack.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.write(src / "pet.json", "pet.json")
        zf.write(src / "spritesheet.webp", "spritesheet.webp")
    dest = tmp_path / "zip_installed"
    dest.mkdir()
    path, result = import_codex_pack(zip_path, dest)
    assert path is not None
    assert result.ok


@pytest.mark.unit
def test_import_rejects_oversized_zip(tmp_path):
    from character_v4.importer import import_codex_pack
    zip_path = tmp_path / "huge.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("pet.json", json.dumps({"id": "x"}))
    dest = tmp_path / "dest"
    dest.mkdir()
    path, result = import_codex_pack(zip_path, dest)
    assert path is None
    assert not result.ok


@pytest.mark.unit
def test_import_rejects_zip_slip(tmp_path):
    from character_v4.importer import import_codex_pack
    zip_path = tmp_path / "slip.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("../../etc/passwd", "bad")
    dest = tmp_path / "dest"
    dest.mkdir()
    path, result = import_codex_pack(zip_path, dest)
    assert path is None
    assert not result.ok


# ── Default pet tests ───────────────────────────────────────────────────────

@pytest.mark.unit
def test_default_pet_generation(tmp_path):
    from character_v4.default_pet import generate_default_pet
    pack_dir = generate_default_pet(tmp_path)
    assert (pack_dir / "pet.json").exists()
    assert (pack_dir / "spritesheet.webp").exists()
    # Verify atlas dimensions
    img = Image.open(pack_dir / "spritesheet.webp")
    assert img.size == (1536, 1872)  # 8×9 V1 cells
    # Verify manifest
    with open(pack_dir / "pet.json") as f:
        m = json.load(f)
    assert m["id"] == "default_dynamic_ghost"
    assert m["spriteVersionNumber"] == 1
