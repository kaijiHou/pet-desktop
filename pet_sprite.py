"""
Clippy sprite renderer — uses official Clippy sprites from Microsoft Office.
Each animation has proper frame durations for smooth playback.
"""

import math
from pathlib import Path
from PIL import Image, ImageDraw


SPRITE_SHEET = Path(__file__).parent / "assets" / "clippy_sheet.png"
SPRITE_W, SPRITE_H = 124, 93


# Animation data: (x, y, duration_ms)
ANIMATIONS = {
    "idle": [
        (0, 0, 100), (2108, 744, 100), (2232, 744, 100), (2356, 744, 100),
        (2480, 744, 300), (2604, 744, 100), (2728, 744, 100), (2852, 744, 300),
        (2976, 744, 100), (3100, 744, 100), (3224, 744, 300), (3348, 744, 100),
        (0, 837, 100), (124, 837, 100), (248, 837, 300), (372, 837, 100),
        (496, 837, 100), (620, 837, 300), (744, 837, 100), (868, 837, 100),
        (992, 837, 300), (1116, 837, 100), (1240, 837, 100), (1364, 837, 300),
        (1488, 837, 100), (1612, 837, 100), (1736, 837, 300), (1860, 837, 100),
        (1984, 837, 100), (2108, 837, 300), (2232, 837, 100), (2356, 837, 100),
        (2480, 837, 300), (2604, 837, 100), (2728, 837, 100), (2852, 837, 300),
        (2976, 837, 100), (3100, 837, 100), (0, 0, 100), (1116, 186, 100),
        (1240, 186, 100), (1364, 186, 900), (1240, 186, 100), (1116, 186, 100),
        (0, 0, 100),
    ],
    "talking": [
        (0, 0, 100), (1116, 186, 100), (1240, 186, 100), (1364, 186, 900),
        (1240, 186, 100), (1116, 186, 100), (0, 0, 100),
    ],
    "alert": [
        (0, 0, 100), (2356, 1116, 100), (2480, 1116, 100), (2604, 1116, 100),
        (2728, 1116, 100), (2852, 1116, 100), (2976, 1116, 100), (3100, 1116, 100),
        (3224, 1116, 100), (3348, 1116, 100), (0, 1209, 100),
        (124, 1209, 500), (248, 1209, 100), (372, 1209, 100), (496, 1209, 100),
        (620, 1209, 100), (744, 1209, 100), (868, 1209, 100), (992, 1209, 100),
        (1116, 1209, 100), (0, 0, 100),
    ],
    "sleep": [
        (0, 0, 100), (2480, 2046, 100), (2604, 2046, 100), (2728, 2046, 100),
        (2852, 2046, 100), (2976, 2046, 100), (3100, 2046, 100), (3224, 2046, 100),
        (3348, 2046, 400), (0, 2139, 100), (124, 2139, 100), (248, 2139, 100),
        (372, 2139, 100), (496, 2139, 100), (620, 2139, 100), (744, 2139, 100),
        (868, 2139, 100), (992, 2139, 100), (1116, 2139, 100), (1240, 2139, 100),
        (1364, 2139, 100), (1488, 2139, 100), (1612, 2139, 100), (1736, 2139, 100),
        (1860, 2139, 100), (1984, 2139, 100), (2108, 2139, 100), (2232, 2139, 100),
        (2356, 2139, 200), (2480, 2139, 200), (2604, 2139, 200), (2728, 2139, 200),
        (2852, 2139, 200), (2976, 2139, 200), (3100, 2139, 200), (3224, 2139, 200),
        (3348, 2139, 200), (0, 2232, 200), (124, 2232, 200), (248, 2232, 200),
        (372, 2232, 100), (496, 2232, 100), (620, 2232, 100), (744, 2232, 1200),
        (868, 2232, 100), (992, 2232, 100), (1116, 2232, 100), (1240, 2232, 100),
        (1364, 2232, 100), (1488, 2232, 100), (1612, 2232, 400), (1736, 2232, 100),
        (1860, 2232, 100), (1984, 2232, 100), (2108, 2232, 100), (2232, 2232, 100),
        (2356, 2232, 100), (2480, 2232, 100), (2604, 2232, 600), (2728, 2232, 300),
        (2852, 2232, 300), (2976, 2232, 300), (3100, 2232, 100), (3224, 2232, 100),
        (3348, 2232, 100), (0, 2325, 100), (124, 2325, 100), (248, 2325, 100),
        (372, 2325, 100), (496, 2325, 100), (620, 2325, 100), (744, 2325, 200),
        (868, 2325, 200), (992, 2325, 200), (1116, 2325, 200), (1240, 2325, 200),
        (1364, 2325, 200), (1488, 2325, 200), (1612, 2325, 100), (1736, 2325, 100),
        (1860, 2325, 100), (1984, 2325, 100), (2108, 2325, 100), (2232, 2325, 100),
        (2356, 2325, 100), (2480, 2325, 300), (2604, 2325, 100), (2728, 2325, 100),
        (2852, 2325, 100), (2976, 2325, 100), (3100, 2325, 100), (0, 0, 100),
    ],
}


class ClippySprites:
    """Loads and caches Clippy frames with smooth scaling."""

    def __init__(self, sheet_path=None):
        raw = Image.open(sheet_path or SPRITE_SHEET)
        # Convert palette to RGBA and make magic pink (255,0,255) transparent
        raw = raw.convert("RGBA")
        pixels = raw.load()
        w, h = raw.size
        for y in range(h):
            for x in range(w):
                r, g, b, a = pixels[x, y]
                if r > 250 and g < 10 and b > 250:  # magic pink
                    pixels[x, y] = (0, 0, 0, 0)
        self.sheet = raw
        self._cache = {}

    def get_frame(self, state, frame_idx, scale=3):
        frames = ANIMATIONS.get(state, ANIMATIONS["idle"])
        if not frames:
            return Image.new("RGBA", (SPRITE_W*scale, SPRITE_H*scale), (0,0,0,0))
        idx = frame_idx % len(frames)
        key = (state, idx, scale)
        if key in self._cache:
            return self._cache[key]
        x, y, _ = frames[idx]
        frame = self.sheet.crop((x, y, x + SPRITE_W, y + SPRITE_H))
        if scale != 1:
            frame = frame.resize((SPRITE_W * scale, SPRITE_H * scale), Image.LANCZOS)
        self._cache[key] = frame
        return frame

    def get_duration(self, state, frame_idx):
        frames = ANIMATIONS.get(state, ANIMATIONS["idle"])
        if not frames:
            return 100
        idx = frame_idx % len(frames)
        return frames[idx][2]

    def get_frame_count(self, state):
        return len(ANIMATIONS.get(state, ANIMATIONS["idle"]))


_clippy = None
def get_clippy():
    global _clippy
    if _clippy is None:
        _clippy = ClippySprites()
    return _clippy


def generate_sprite(state="idle", frame=0, scale=3):
    return get_clippy().get_frame(state, frame, scale)


def generate_all_sprites(output_dir, scale=3):
    c = get_clippy()
    for state in ANIMATIONS:
        d = output_dir / state
        d.mkdir(parents=True, exist_ok=True)
        for i in range(len(ANIMATIONS[state])):
            c.get_frame(state, i, scale).save(d / f"frame_{i:03d}.png")
    print(f"Generated Clippy sprites in {output_dir}")


class PetSpriteLoader:
    def __init__(self, assets_dir, scale=3):
        self.assets_dir = Path(assets_dir)
        self.scale = scale
        self._cache = {}
        self._c = get_clippy()

    def get_frame(self, state, frame):
        frames = ANIMATIONS.get(state, ANIMATIONS["idle"])
        if not frames:
            return Image.new("RGBA", (124*self.scale, 93*self.scale), (0,0,0,0))
        idx = frame % len(frames)
        p = self.assets_dir / "sprites" / state / f"frame_{idx:03d}.png"
        if p.exists():
            k = (state, idx)
            if k not in self._cache:
                self._cache[k] = Image.open(p).convert("RGBA")
            return self._cache[k]
        return self._c.get_frame(state, frame, self.scale)

    def get_duration(self, state, frame):
        return self._c.get_duration(state, frame)

    def get_frame_count(self, state):
        return self._c.get_frame_count(state)


if __name__ == "__main__":
    import sys
    from pathlib import Path
    s = int(sys.argv[1]) if len(sys.argv) > 1 else 3
    generate_all_sprites(Path(__file__).parent / "assets" / "sprites", s)
    for state in ["idle", "talking", "alert", "sleep"]:
        get_clippy().get_frame(state, 0, 4).save(f"C:/Users/clara/Desktop/{state}.png")
    print("Done!")
