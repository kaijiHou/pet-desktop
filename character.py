"""Character system V2: single-image mode, sprite-sheet mode, built-in default.

Modes
-----
- "single":  one transparent PNG. Animations are Qt transform presets
             (bob / shake / bounce / tilt) applied at paint time — no
             sprite sheet required. This is the default for new users.
- "sheet":   legacy Clippy-style sprite sheet + animations.json (unchanged).
- fallback:  when no user image exists, a built-in neutral round buddy
             is drawn programmatically (no ADD ART, no copyrighted art).
"""

from pathlib import Path
from PIL import Image, ImageDraw

from paths import PROJECT_ROOT, DATA_DIR

USER_ASSETS_DIR = PROJECT_ROOT / "assets"
DEFAULT_CHARACTER_NAME = "default_buddy.png"

# Single-image animation semantics (§7). Each is (key, frames, ms-per-step).
# Frames are transform recipes evaluated by the renderer, NOT sprite frames.
SINGLE_ANIMATIONS = {
    "IDLE":         [("bob", 0.0), ("bob", 1.5)],          # gentle breathing
    "RECEIVE_FILE": [("squash", 0.88), ("bounce", 1.10), ("normal", 1.0)],
    "GIVE_FILE":    [("tilt", 6), ("normal", 1.0)],
    "DELETE_FILE":  [("shake", 0), ("shake", 0), ("shake", 0), ("normal", 1.0)],  # 3 shakes
    "CREATE_FILE":  [("bounce", 1.08), ("bounce", 1.06), ("normal", 1.0)],        # double bounce
    "RENAME_FILE":  [("tilt", -8), ("tilt", 8), ("tilt", -4), ("normal", 1.0)],   # extra tilt
    "COPY_FILE":    [("pop", 1.10), ("pop", 1.10), ("pop", 1.08), ("normal", 1.0)],  # triple pop
    "MOVE_FILE":    [("slide", 15), ("slide", -15), ("slide", 8), ("normal", 1.0)],  # triple slide
    "REMINDER":     [("bounce", 1.14), ("bounce", 1.14), ("bounce", 1.10), ("normal", 1.0)],
    "SUCCESS":      [("bounce", 1.08), ("normal", 1.0)],
    "ERROR":        [("shake", 0), ("shake", 0), ("shake", 0), ("normal", 1.0)],
    "WAGE_PROGRESS": [("pop", 1.04), ("normal", 1.0)],
    "OVERTIME_START": [("bounce", 1.06), ("tilt", -4), ("normal", 1.0)],
    "CLOCK_OUT":    [("tilt", 5), ("pop", 1.06), ("normal", 1.0)],
    "MEAL_ALLOWANCE": [("pop", 1.08), ("normal", 1.0)],
    "SLEEP":        [("bob", -1.5), ("bob", -1.5)],
    "WAKE":         [("bounce", 1.10), ("normal", 1.0)],
}
STEP_MS = 160  # one transform step duration; timers stop after last step


def draw_default_buddy(size=192) -> Image.Image:
    """Built-in neutral character: a friendly round buddy. No copyright issues."""
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    s = size / 192.0
    cx, cy = size // 2, int(size * 0.52)
    r = int(64 * s)
    # body: soft blue-grey circle
    d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=(91, 122, 222, 255))
    d.ellipse((cx - r, cy - r, cx + r, cy + r), outline=(58, 82, 170, 255), width=max(2, int(3 * s)))
    # face plate
    fr = int(46 * s)
    d.ellipse((cx - fr, cy - int(30 * s), cx + fr, cy + int(52 * s)), fill=(233, 238, 250, 255))
    # eyes
    er = int(7 * s)
    ex_off = int(20 * s)
    ey = cy - int(2 * s)
    d.ellipse((cx - ex_off - er, ey - er, cx - ex_off + er, ey + er), fill=(35, 40, 60, 255))
    d.ellipse((cx + ex_off - er, ey - er, cx + ex_off + er, ey + er), fill=(35, 40, 60, 255))
    # smile
    d.arc((cx - int(18 * s), cy + int(6 * s), cx + int(18 * s), cy + int(30 * s)),
          start=15, end=165, fill=(35, 40, 60, 255), width=max(2, int(4 * s)))
    # blush
    br = int(6 * s)
    for sx in (-1, 1):
        bx = cx + sx * int(32 * s)
        by = cy + int(12 * s)
        d.ellipse((bx - br, by - br // 2, bx + br, by + br // 2), fill=(255, 170, 170, 160))
    return img


class CharacterController:
    """Resolves current character mode and produces frames for the renderer.

    single mode: get_frame returns (PIL.Image, transform_name, param)
                 where transform is applied by the Qt painter.
    sheet mode:  get_frame returns (PIL.Image, None, None) — raw sprite frame.
    """

    def __init__(self, config, scale=3.0):
        self.config = config
        self._scale = float(scale)
        self._single_image = None      # PIL.Image or None
        self._single_base_size = 0
        self._mode = "sheet"
        self._visible_alpha_bbox = None
        self._preview_image = None
        self._reload()

    # ── loading ──
    def _character_path(self) -> Path:
        name = self.config.get("character_image", "")
        if name:
            path = Path(name)
            if path.is_absolute():
                return path
            data_path = DATA_DIR / path
            if data_path.exists():
                return data_path
            image_path = DATA_DIR / "character_images" / path.name
            if image_path.exists():
                return image_path
            return USER_ASSETS_DIR / path.name
        return USER_ASSETS_DIR / DEFAULT_CHARACTER_NAME

    def _reload(self):
        mode = self.config.get("character_mode", "single")
        image = None
        if mode == "sheet":
            # Legacy sprite sheet mode: use pet_sprite loader.
            self._mode = "sheet"
            self._loaded_builtin = False
            self._single_image = None
            self._single_base_size = 0
            self._visible_alpha_bbox = None
            return
        # single mode
        path = self._character_path()
        if self.config.get("character_image", "") and path.exists():
            try:
                image = Image.open(path).convert("RGBA")
            except OSError:
                image = None
        if image is None:
            image = draw_default_buddy()
            self._loaded_builtin = True
        else:
            self._loaded_builtin = False
        self._mode = "single"
        self._single_image = image
        self._single_base_size = max(image.size)
        # Cache the true drawable bounds once.  Transparent padding is common
        # in user-supplied sprites and must not influence panel/bubble anchors.
        self._visible_alpha_bbox = image.getchannel("A").getbbox()
        if self._visible_alpha_bbox is None:
            self._visible_alpha_bbox = (0, 0, image.width, image.height)

    def reload(self):
        self._reload()

    def preview_image(self, image):
        """Temporarily use a PIL image for live preview (no Config write)."""
        if image.mode != "RGBA":
            image = image.convert("RGBA")
        self._preview_image = image
        self._mode = "single"
        self._single_image = image
        self._single_base_size = max(image.size)
        self._visible_alpha_bbox = image.getchannel("A").getbbox()
        if self._visible_alpha_bbox is None:
            self._visible_alpha_bbox = (0, 0, image.width, image.height)

    def clear_preview(self):
        """Discard preview and reload from Config."""
        self._preview_image = None
        self._reload()

    # ── properties ──
    @property
    def mode(self) -> str:
        return self._mode

    @property
    def using_builtin_default(self) -> bool:
        """True when no user image is configured OR it failed to load."""
        return self._loaded_builtin

    def set_scale(self, scale):
        self._scale = max(1.0, min(6.0, float(scale)))

    @property
    def scale(self):
        return self._scale

    @property
    def visible_alpha_bbox(self):
        """Visible RGBA bounds in source-image pixels (cached)."""
        return self._visible_alpha_bbox

    def base_size(self):
        """(w, h) the character occupies at current scale.

        Uses longest-side normalization: the output's longest dimension
        equals BASE_CHARACTER_SIZE * scale, regardless of aspect ratio.
        This prevents portrait images (e.g. 512x1024) from becoming huge.
        """
        if self._mode == "single":
            src_w, src_h = self._single_image.size
            target_long = 192 * self._scale  # 192 = default buddy size
            long_side = max(src_w, src_h)
            ratio = target_long / long_side
            return round(src_w * ratio), round(src_h * ratio)
        from pet_sprite import SPRITE_W, SPRITE_H
        return int(SPRITE_W * self._scale), int(SPRITE_H * self._scale)

    # ── frames ──
    def get_single_frame(self, transform=None, param=None):
        """Return the single-mode image (renderer applies transform)."""
        return self._single_image

    def get_frame(self, animation, frame):
        """Sheet-mode compatibility: raw sprite frame (unused in single mode)."""
        from pet_sprite import PetSpriteLoader
        if not hasattr(self, "_sheet_loader"):
            self._sheet_loader = PetSpriteLoader(scale=self._scale)
        return self._sheet_loader.get_frame(animation, frame)

    # ── animation semantics ──
    def animation_steps(self, semantic):
        """Steps [(transform, param)] for a semantic name; IDLE fallback."""
        return SINGLE_ANIMATIONS.get(semantic, SINGLE_ANIMATIONS["IDLE"])

    def semantic_duration_ms(self, semantic):
        return len(self.animation_steps(semantic)) * STEP_MS


def import_character_image(src: Path, assets_dir: Path = None) -> Path:
    """Validate + copy a user-chosen image into portable assets. Returns stored name."""
    src = Path(src)
    if not src.exists():
        raise FileNotFoundError(src)
    if src.suffix.lower() not in {".png", ".webp", ".jpg", ".jpeg"}:
        raise ValueError("仅支持 PNG / WebP / JPG / JPEG 图片")
    try:
        img = Image.open(src)
        img.verify()
        img = Image.open(src).convert("RGBA")
    except OSError as exc:
        raise ValueError(f"图片无法读取: {exc}") from exc
    if img.width < 16 or img.height < 16:
        raise ValueError("图片太小（至少 16×16）")
    if img.width > 4096 or img.height > 4096:
        raise ValueError("图片太大（超过 4096×4096）")

    assets_dir = Path(assets_dir) if assets_dir else USER_ASSETS_DIR
    assets_dir.mkdir(parents=True, exist_ok=True)
    # keep original file name when sane; de-collide with prefix
    # Always save as PNG for uniform RGBA handling
    name = src.stem + ".png"
    target = assets_dir / name
    i = 1
    while target.exists() and src.resolve() != target.resolve():
        target = assets_dir / f"{Path(name).stem}_{i}{Path(name).suffix}"
        i += 1
    # re-save through Pillow: normalizes format, strips weird metadata
    img.save(target)
    return target.name
