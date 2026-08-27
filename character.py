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

from paths import PROJECT_ROOT

USER_ASSETS_DIR = PROJECT_ROOT / "assets"
DEFAULT_CHARACTER_NAME = "default_buddy.png"

# Single-image animation semantics (§7). Each is (key, frames, ms-per-step).
# Frames are transform recipes evaluated by the renderer, NOT sprite frames.
SINGLE_ANIMATIONS = {
    "IDLE":         [("bob", 0.0), ("bob", 1.5)],          # gentle breathing
    "RECEIVE_FILE": [("squash", 0.88), ("bounce", 1.10), ("normal", 1.0)],
    "GIVE_FILE":    [("tilt", 6), ("normal", 1.0)],
    "DELETE_FILE":  [("shake", 0), ("shake", 0), ("normal", 1.0)],
    "CREATE_FILE":  [("bounce", 1.06), ("normal", 1.0)],
    "RENAME_FILE":  [("tilt", -6), ("tilt", 6), ("normal", 1.0)],
    "COPY_FILE":    [("pop", 1.08), ("pop", 1.08), ("normal", 1.0)],
    "MOVE_FILE":    [("slide", 10), ("slide", -10), ("normal", 1.0)],
    "REMINDER":     [("bounce", 1.12), ("bounce", 1.12), ("normal", 1.0)],
    "SUCCESS":      [("bounce", 1.08), ("normal", 1.0)],
    "ERROR":        [("shake", 0), ("shake", 0), ("shake", 0), ("normal", 1.0)],
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
        self._reload()

    # ── loading ──
    def _character_path(self) -> Path:
        name = self.config.get("character_image", "")
        if name:
            return USER_ASSETS_DIR / name
        return USER_ASSETS_DIR / DEFAULT_CHARACTER_NAME

    def _reload(self):
        path = self._character_path()
        image = None
        if self.config.get("character_image", "") and path.exists():
            try:
                image = Image.open(path).convert("RGBA")
            except OSError:
                image = None
        if image is None:
            # built-in default buddy, shipped from programmatic drawing
            image = draw_default_buddy()
            self._mode = "single"
            self._loaded_builtin = True
        else:
            self._mode = "single"
            self._loaded_builtin = False
        self._single_image = image
        self._single_base_size = max(image.size)

    def reload(self):
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

    def base_size(self):
        """(w, h) the character occupies at current scale."""
        if self._mode == "single":
            ratio = self._single_image.height / self._single_image.width
            w = int(self._single_base_size * self._scale)
            return w, int(w * ratio)
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
    if src.suffix.lower() not in {".png", ".webp"}:
        raise ValueError("仅支持 PNG / WebP 图片")
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
    name = src.name
    if not name.lower().endswith((".png", ".webp")):
        name += ".png"
    target = assets_dir / name
    i = 1
    while target.exists() and src.resolve() != target.resolve():
        target = assets_dir / f"{Path(name).stem}_{i}{Path(name).suffix}"
        i += 1
    # re-save through Pillow: normalizes format, strips weird metadata
    img.save(target)
    return target.name
