"""Native Pillow sprite renderer backed by the tracked animation catalog."""

import json
from collections import OrderedDict
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw


ASSETS_DIR = Path(__file__).parent / "assets"
SPRITE_SHEET = ASSETS_DIR / "clippy_sheet.png"
ANIMATIONS_FILE = ASSETS_DIR / "animations.json"
SPRITE_W, SPRITE_H = 124, 93


def load_animations(path=ANIMATIONS_FILE):
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


ANIMATIONS = load_animations()


def _remove_magic_pink(image):
    """Make the legacy sprite-sheet key color transparent using Pillow ops."""
    rgba = image.convert("RGBA")
    red, green, blue, alpha = rgba.split()
    high_red = red.point(lambda value: 255 if value > 250 else 0)
    low_green = green.point(lambda value: 255 if value < 10 else 0)
    high_blue = blue.point(lambda value: 255 if value > 250 else 0)
    key_mask = ImageChops.multiply(ImageChops.multiply(high_red, low_green), high_blue)
    rgba.putalpha(ImageChops.subtract(alpha, key_mask))
    return rgba


class ClippySprites:
    """Load a user-provided sprite sheet and cache scaled frames."""

    def __init__(self, sheet_path=None, animations=None):
        path = Path(sheet_path or SPRITE_SHEET)
        self.animations = animations or ANIMATIONS
        self.using_placeholder = not path.exists()
        self.sheet = (_placeholder_sheet() if self.using_placeholder
                      else _remove_magic_pink(Image.open(path)))
        self._cache = OrderedDict()

    def get_frame(self, animation, frame_index, scale=3.0):
        frames = self.animations.get(animation) or self.animations["RestPose"]
        index = frame_index % len(frames)
        width, height = int(SPRITE_W * scale), int(SPRITE_H * scale)
        key = (animation, index, width, height)
        if key not in self._cache:
            x, y, _ = frames[index]
            frame = self.sheet.crop((x, y, x + SPRITE_W, y + SPRITE_H))
            if (width, height) != (SPRITE_W, SPRITE_H):
                frame = frame.resize((width, height), Image.Resampling.LANCZOS)
            self._cache[key] = frame
            self._cache.move_to_end(key)
            while len(self._cache) > 96:
                self._cache.popitem(last=False)
        return self._cache[key]

    def get_duration(self, animation, frame_index):
        frames = self.animations.get(animation) or self.animations["RestPose"]
        return frames[frame_index % len(frames)][2]

    def get_frame_count(self, animation):
        return len(self.animations.get(animation) or self.animations["RestPose"])


class PetSpriteLoader:
    def __init__(self, assets_dir=ASSETS_DIR, scale=3.0):
        self.assets_dir = Path(assets_dir)
        self.scale = float(scale)
        self._sprites = ClippySprites(self.assets_dir / "clippy_sheet.png")

    def get_frame(self, animation, frame):
        return self._sprites.get_frame(animation, frame, self.scale)

    def get_duration(self, animation, frame):
        return self._sprites.get_duration(animation, frame)

    def get_frame_count(self, animation):
        return self._sprites.get_frame_count(animation)

    def set_scale(self, scale):
        self.scale = float(scale)


def generate_sprite(animation="RestPose", frame=0, scale=3.0):
    return ClippySprites().get_frame(animation, frame, scale)


def _placeholder_sheet():
    """Original neutral placeholder used when no user artwork is installed."""
    max_x = max(frame[0] for frames in ANIMATIONS.values() for frame in frames)
    max_y = max(frame[1] for frames in ANIMATIONS.values() for frame in frames)
    sheet = Image.new("RGBA", (max_x + SPRITE_W, max_y + SPRITE_H), (0, 0, 0, 0))
    frame = Image.new("RGBA", (SPRITE_W, SPRITE_H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(frame)
    draw.rounded_rectangle((38, 8, 83, 84), radius=20, outline=(105, 105, 115, 255), width=7)
    draw.rounded_rectangle((49, 18, 72, 71), radius=11, outline=(215, 215, 225, 255), width=5)
    draw.text((29, 74), "ADD ART", fill=(95, 95, 105, 255))
    for frames in ANIMATIONS.values():
        for x, y, _ in frames:
            sheet.alpha_composite(frame, (x, y))
    return sheet
