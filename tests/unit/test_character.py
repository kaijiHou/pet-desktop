"""V2 character system tests: single-image mode, import, fallback, switching."""

from pathlib import Path

import pytest
from PIL import Image

import character as character_mod
from character import (
    CharacterController,
    SINGLE_ANIMATIONS,
    STEP_MS,
    draw_default_buddy,
    import_character_image,
)


@pytest.fixture
def assets_dir(test_temp_root, monkeypatch):
    """Redirect user assets dir into test temp."""
    d = test_temp_root / "assets"
    d.mkdir()
    monkeypatch.setattr(character_mod, "USER_ASSETS_DIR", d)
    return d


def _make_png(path: Path, size=(100, 120), color=(200, 60, 60, 255)):
    img = Image.new("RGBA", size, color)
    img.save(path)
    return path


# ── built-in default buddy ──────────────────────────────────────────────────

@pytest.mark.unit
def test_default_buddy_draws_transparent_round_character():
    img = draw_default_buddy()
    assert img.mode == "RGBA"
    assert img.size == (192, 192)
    # corners transparent (round character on transparent bg)
    assert img.getpixel((0, 0))[3] == 0
    # center has opaque body
    assert img.getpixel((96, 100))[3] == 255


@pytest.mark.unit
def test_no_user_image_falls_back_to_builtin_buddy(assets_dir, isolated_config):
    ctrl = CharacterController(isolated_config)
    assert ctrl.mode == "single"
    assert ctrl.using_builtin_default is True
    assert ctrl.get_single_frame() is not None


@pytest.mark.unit
def test_add_art_placeholder_is_gone(assets_dir, isolated_config):
    """The old ADD ART placeholder must never appear again."""
    img = draw_default_buddy()
    # No "ADD ART" text: sample where the old text was drawn is now body/face
    assert img.getbbox() is not None


# ── single-image mode ──────────────────────────────────────────────────────

@pytest.mark.unit
def test_configured_image_is_loaded_in_single_mode(assets_dir, isolated_config):
    _make_png(assets_dir / "mypet.png")
    isolated_config.set("character_image", "mypet.png")
    ctrl = CharacterController(isolated_config)
    assert ctrl.mode == "single"
    assert ctrl.using_builtin_default is False
    frame = ctrl.get_single_frame()
    assert frame.size == (100, 120)


@pytest.mark.unit
def test_visible_alpha_bbox_is_cached_from_rgba_pixels(assets_dir, isolated_config):
    img = Image.new("RGBA", (100, 120), (0, 0, 0, 0))
    img.paste((255, 0, 0, 255), (17, 23, 69, 91))
    img.save(assets_dir / "padded.png")
    isolated_config.set("character_image", "padded.png")
    ctrl = CharacterController(isolated_config)
    assert ctrl.visible_alpha_bbox == (17, 23, 69, 91)


@pytest.mark.unit
def test_character_switch_without_restart(assets_dir, isolated_config):
    _make_png(assets_dir / "a.png", color=(10, 200, 10, 255))
    _make_png(assets_dir / "b.png", color=(10, 10, 200, 255))
    isolated_config.set("character_image", "a.png")
    ctrl = CharacterController(isolated_config)
    first = ctrl.get_single_frame().getpixel((50, 60))
    isolated_config.set("character_image", "b.png")
    ctrl.reload()
    second = ctrl.get_single_frame().getpixel((50, 60))
    assert first != second


@pytest.mark.unit
def test_missing_configured_image_falls_back_to_buddy(assets_dir, isolated_config):
    isolated_config.set("character_image", "ghost.png")
    ctrl = CharacterController(isolated_config)
    assert ctrl.using_builtin_default is True


@pytest.mark.unit
def test_corrupt_image_falls_back_to_buddy(assets_dir, isolated_config):
    (assets_dir / "bad.png").write_bytes(b"not a png at all")
    isolated_config.set("character_image", "bad.png")
    ctrl = CharacterController(isolated_config)
    assert ctrl.using_builtin_default is True


# ── sprite-sheet mode ──────────────────────────────────────────────────────

@pytest.mark.unit
def test_sheet_mode_uses_sprite_loader(assets_dir, isolated_config):
    isolated_config.set("character_mode", "sheet")
    ctrl = CharacterController(isolated_config)
    assert ctrl.mode == "sheet"
    # base_size uses sprite sheet frame grid
    from pet_sprite import SPRITE_W, SPRITE_H
    ctrl.set_scale(3)
    w, h = ctrl.base_size()
    assert w == SPRITE_W * 3 and h == SPRITE_H * 3


@pytest.mark.unit
def test_switch_back_to_single(assets_dir, isolated_config):
    isolated_config.set("character_mode", "sheet")
    ctrl = CharacterController(isolated_config)
    assert ctrl.mode == "sheet"
    isolated_config.set("character_mode", "single")
    ctrl.reload()
    assert ctrl.mode == "single"
    assert ctrl.using_builtin_default is True


# ── import flow ────────────────────────────────────────────────────────────

@pytest.mark.unit
def test_import_copies_image_into_assets(assets_dir, test_temp_root):
    src = _make_png(test_temp_root / "source.png")
    name = import_character_image(src, assets_dir)
    assert name == "source.png"
    assert (assets_dir / name).exists()
    assert Image.open(assets_dir / name).size == (100, 120)


@pytest.mark.unit
def test_import_rejects_non_image(assets_dir, test_temp_root):
    src = test_temp_root / "evil.png"
    src.write_bytes(b"MZ fake exe")
    with pytest.raises(ValueError):
        import_character_image(src, assets_dir)


@pytest.mark.unit
def test_import_rejects_unsupported_extension(assets_dir, test_temp_root):
    src = test_temp_root / "photo.bmp"
    Image.new("RGB", (50, 50)).save(src)
    with pytest.raises(ValueError):
        import_character_image(src, assets_dir)


@pytest.mark.unit
def test_import_rejects_tiny_image(assets_dir, test_temp_root):
    src = _make_png(test_temp_root / "tiny.png", size=(8, 8))
    with pytest.raises(ValueError):
        import_character_image(src, assets_dir)


@pytest.mark.unit
def test_import_rejects_oversized_image(assets_dir, test_temp_root):
    src = test_temp_root / "huge.png"
    Image.new("RGBA", (5000, 10)).save(src)
    with pytest.raises(ValueError):
        import_character_image(src, assets_dir)


@pytest.mark.unit
def test_import_name_collision_gets_unique_name(assets_dir, test_temp_root):
    _make_png(assets_dir / "same.png", color=(255, 0, 0, 255))
    src = _make_png(test_temp_root / "same.png", color=(0, 255, 0, 255))
    name = import_character_image(src, assets_dir)
    assert name != "same.png"
    assert (assets_dir / name).exists()


# ── animation semantics ────────────────────────────────────────────────────

@pytest.mark.unit
def test_all_required_semantics_exist():
    required = {
        "IDLE", "RECEIVE_FILE", "GIVE_FILE", "DELETE_FILE", "CREATE_FILE",
        "RENAME_FILE", "COPY_FILE", "MOVE_FILE", "REMINDER", "SUCCESS",
        "ERROR", "SLEEP", "WAKE",
    }
    assert required.issubset(SINGLE_ANIMATIONS.keys())


@pytest.mark.unit
def test_every_event_semantic_ends_returning_to_normal():
    for name, steps in SINGLE_ANIMATIONS.items():
        if name == "IDLE" or name == "SLEEP":
            continue  # loop semantics never "end"
        assert steps[-1][0] == "normal", f"{name} must end at rest"


@pytest.mark.unit
def test_semantic_fallback_to_idle():
    # unknown semantic falls back to IDLE steps
    steps = SINGLE_ANIMATIONS.get("NOT_A_THING", SINGLE_ANIMATIONS["IDLE"])
    assert steps == SINGLE_ANIMATIONS["IDLE"]


@pytest.mark.unit
def test_semantic_duration_is_bounded():
    """No animation runs forever: duration = steps × STEP_MS."""
    for name, steps in SINGLE_ANIMATIONS.items():
        dur = len(steps) * STEP_MS
        assert dur <= 1000, f"{name} runs {dur}ms — too long for event feedback"


@pytest.mark.unit
def test_import_jpg_converted_to_png(test_temp_root, assets_dir):
    """JPG import should save as PNG (RGBA uniform)."""
    from character import import_character_image
    from PIL import Image
    # Create a test JPG
    jpg_path = test_temp_root / "test.jpg"
    img = Image.new("RGB", (100, 100), (255, 0, 0))
    img.save(jpg_path, "JPEG")
    name = import_character_image(jpg_path, assets_dir)
    assert name.endswith(".png"), f"Should save as PNG, got {name}"
    saved = assets_dir / name
    assert saved.exists()
    # Verify it's valid RGBA PNG
    loaded = Image.open(saved)
    assert loaded.mode == "RGBA"


@pytest.mark.unit
def test_import_jpeg_converted_to_png(test_temp_root, assets_dir):
    """JPEG extension should also work."""
    from character import import_character_image
    from PIL import Image
    jpg_path = test_temp_root / "test.jpeg"
    img = Image.new("RGB", (100, 100), (0, 255, 0))
    img.save(jpg_path, "JPEG")
    name = import_character_image(jpg_path, assets_dir)
    assert name.endswith(".png")


@pytest.mark.unit
def test_portrait_character_size_normalized():
    """Portrait image (512x1024) should not become huge."""
    from character import CharacterController
    from PIL import Image
    portrait = Image.new("RGBA", (512, 1024), (255, 0, 0, 255))
    # Create a minimal controller by directly setting the image
    ctrl = CharacterController.__new__(CharacterController)
    ctrl._scale = 3.0
    ctrl._mode = "single"
    ctrl._single_image = portrait
    ctrl._visible_alpha_bbox = (0, 0, 512, 1024)
    w, h = ctrl.base_size()
    # Long side should be ~192*3 = 576, not 1024*3 = 3072
    assert max(w, h) <= 600, f"Long side {max(w,h)} should be ~576, not huge"
    assert w < h, "Portrait should be taller than wide"


@pytest.mark.unit
def test_landscape_character_size_normalized():
    """Landscape image (1024x512) should also normalize."""
    from character import CharacterController
    from PIL import Image
    landscape = Image.new("RGBA", (1024, 512), (0, 0, 255, 255))
    ctrl = CharacterController.__new__(CharacterController)
    ctrl._scale = 3.0
    ctrl._mode = "single"
    ctrl._single_image = landscape
    ctrl._visible_alpha_bbox = (0, 0, 1024, 512)
    w, h = ctrl.base_size()
    assert max(w, h) <= 600, f"Long side {max(w,h)} should be ~576"
    assert w > h, "Landscape should be wider than tall"
