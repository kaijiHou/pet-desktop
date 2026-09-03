"""Default Dynamic Pet Generator — creates an original animated ghost character.

Generates a valid Codex V1 atlas:
  8 columns × 9 rows = 1536×1872
  Cell size: 192×208

Rows:
  0 idle (6 frames) — breathing + blink
  1 running_r (8 frames) — move right with bounce
  2 running_l (8 frames) — move left with bounce
  3 waving (4 frames) — arm wave
  4 jumping (5 frames) — vertical bounce + squash
  5 failed (8 frames) — shake + X eyes
  6 waiting (6 frames) — drowsy bob
  7 running (6 frames) — generic run cycle
  8 review (6 frames) — look down + tilt

All frames are deterministic (no wall-clock input).
"""
from __future__ import annotations

import json
import logging
import math
from pathlib import Path

from PIL import Image, ImageDraw

LOGGER = logging.getLogger("pet.character_v4.default_pet")

# Codex V1 constants
COLS = 8
ROWS_V1 = 9
CELL_W = 192
CELL_H = 208
ATLAS_W = COLS * CELL_W   # 1536
ATLAS_H = ROWS_V1 * CELL_H  # 1872

# Ghost visual constants
BODY_COLOR = (180, 210, 255, 220)
EYE_COLOR = (30, 30, 70, 255)
MOUTH_COLOR = (30, 30, 70, 180)
HIGHLIGHT = (255, 255, 255, 255)
ARM_COLOR = (160, 195, 240, 200)
CX = CELL_W // 2   # center x in cell
CY = CELL_H // 2 + 12  # center y (ghost sits low)
SUPERSAMPLE = 4


class _ScaledDraw:
    """Scale ImageDraw primitives for a small 4x supersampled atlas."""
    def __init__(self, draw, scale): self._draw, self._scale = draw, scale
    def _box(self, box): return [round(v * self._scale) for v in box]
    def _kw(self, kw):
        kw = dict(kw)
        if "width" in kw: kw["width"] = max(1, round(kw["width"] * self._scale))
        return kw
    def ellipse(self, box, **kw): return self._draw.ellipse(self._box(box), **self._kw(kw))
    def line(self, xy, **kw):
        points = list(xy)
        if points and isinstance(points[0], (int, float)):
            points = list(zip(points[::2], points[1::2]))
        return self._draw.line([(round(p[0] * self._scale), round(p[1] * self._scale)) for p in points], **self._kw(kw))
    def arc(self, box, *args, **kw): return self._draw.arc(self._box(box), *args, **self._kw(kw))


def _ghost(draw, ox, oy, body_y=0, eye="open", arm_deg=0, squash=1.0, x_off=0):
    """Draw a ghost at cell origin (ox, oy) with animation params."""
    cx = ox + CX + x_off
    cy = oy + CY + int(body_y)
    bw, bh = int(48 * squash), int(54 / squash)

    # Body
    draw.ellipse([cx - bw, cy - bh, cx + bw, cy + bh], fill=BODY_COLOR)
    # Wavy bottom (3 bumps, deterministic by cx position)
    for i in range(3):
        bx = cx - bw + (2 * bw * (i + 1)) // 4
        wave = int(4 * math.sin(ox * 0.1 + i * 2.1))
        draw.ellipse([bx - 12, cy + bh - 8 + wave, bx + 12, cy + bh + 16 + wave],
                     fill=BODY_COLOR)

    # Eyes
    ey = cy - int(bh * 0.3)
    if eye == "open":
        draw.ellipse([cx - 16, ey - 7, cx - 4, ey + 7], fill=EYE_COLOR)
        draw.ellipse([cx + 4, ey - 7, cx + 16, ey + 7], fill=EYE_COLOR)
        draw.ellipse([cx - 12, ey - 3, cx - 8, ey + 1], fill=HIGHLIGHT)
        draw.ellipse([cx + 8, ey - 3, cx + 12, ey + 1], fill=HIGHLIGHT)
    elif eye == "blink":
        draw.line([cx - 16, ey, cx - 4, ey], fill=EYE_COLOR, width=2)
        draw.line([cx + 4, ey, cx + 16, ey], fill=EYE_COLOR, width=2)
    elif eye == "x":
        s = 6
        draw.line([cx - 16 - s, ey - s, cx - 4 + s, ey + s], fill=EYE_COLOR, width=2)
        draw.line([cx - 16 + s, ey - s, cx - 4 - s, ey + s], fill=EYE_COLOR, width=2)
        draw.line([cx + 4 - s, ey - s, cx + 16 + s, ey + s], fill=EYE_COLOR, width=2)
        draw.line([cx + 4 + s, ey - s, cx + 16 - s, ey + s], fill=EYE_COLOR, width=2)
    elif eye == "dizzy":
        # spiral eyes
        for ex in [cx - 10, cx + 10]:
            draw.arc([ex - 5, ey - 5, ex + 5, ey + 5], 0, 270, fill=EYE_COLOR, width=2)

    # Mouth
    my = cy + int(bh * 0.45)
    if eye == "x":
        draw.line([cx - 5, my, cx + 5, my + 3], fill=MOUTH_COLOR, width=2)
        draw.line([cx + 5, my, cx - 5, my + 3], fill=MOUTH_COLOR, width=2)
    elif eye == "dizzy":
        draw.arc([cx - 6, my - 2, cx + 6, my + 8], 0, 180, fill=MOUTH_COLOR, width=2)
    else:
        draw.arc([cx - 7, my - 3, cx + 7, my + 7], 0, 180, fill=MOUTH_COLOR, width=2)

    # Arm
    if arm_deg != 0:
        ax = cx + bw - 4
        ay = cy - 4
        arm_len = 22
        ex = ax + int(arm_len * math.cos(math.radians(arm_deg)))
        ey_a = ay - int(arm_len * math.sin(math.radians(arm_deg)))
        draw.line([ax, ay, ex, ey_a], fill=ARM_COLOR, width=5)
        draw.ellipse([ex - 5, ey_a - 5, ex + 5, ey_a + 5], fill=ARM_COLOR)


def generate_default_pet(output_dir: Path) -> Path:
    """Generate the default dynamic pet pack. Returns pack directory path."""
    pack_dir = output_dir / "default_dynamic_ghost"
    pack_dir.mkdir(parents=True, exist_ok=True)

    atlas = Image.new("RGBA", (ATLAS_W * SUPERSAMPLE, ATLAS_H * SUPERSAMPLE), (0, 0, 0, 0))
    draw = _ScaledDraw(ImageDraw.Draw(atlas), SUPERSAMPLE)

    # Row 0: idle (6 frames) — breathing + periodic blink
    for i in range(6):
        body_y = 3 * math.sin(i * math.pi / 3)
        eye = "blink" if i == 3 else "open"
        _ghost(draw, i * CELL_W, 0, body_y=body_y, eye=eye)

    # Row 1: running_r (8 frames) — move right with bounce
    for i in range(8):
        bounce = -6 * abs(math.sin(i * math.pi / 4))
        x_off = 8 * math.sin(i * math.pi / 4)
        _ghost(draw, i * CELL_W, 1 * CELL_H, body_y=bounce, x_off=int(x_off))

    # Row 2: running_l (8 frames) — mirror of running_r
    for i in range(8):
        bounce = -6 * abs(math.sin(i * math.pi / 4))
        x_off = -8 * math.sin(i * math.pi / 4)
        _ghost(draw, i * CELL_W, 2 * CELL_H, body_y=bounce, x_off=int(x_off))

    # Row 3: waving (4 frames) — arm wave
    for i in range(4):
        arm = -20 + 40 * i / 3
        _ghost(draw, i * CELL_W, 3 * CELL_H, arm_deg=arm)

    # Row 4: jumping (5 frames) — vertical bounce + squash
    for i in range(5):
        if i < 3:
            bounce = -25 * (i / 2)
            squash = 0.9 + 0.1 * (i / 2)
        else:
            bounce = -25 * (1 - (i - 2) / 2)
            squash = 1.0 - 0.1 * ((i - 2) / 2)
        _ghost(draw, i * CELL_W, 4 * CELL_H, body_y=bounce, squash=squash)

    # Row 5: failed (8 frames) — shake + X eyes
    for i in range(8):
        x_off = 8 if i % 2 == 0 else -8
        _ghost(draw, i * CELL_W, 5 * CELL_H, eye="x", x_off=x_off)

    # Row 6: waiting (6 frames) — drowsy bob + dizzy eyes
    for i in range(6):
        body_y = 2 * math.sin(i * math.pi / 3)
        eye = "dizzy" if i % 3 == 0 else "blink"
        _ghost(draw, i * CELL_W, 6 * CELL_H, body_y=body_y, eye=eye)

    # Row 7: running (6 frames) — generic run cycle
    for i in range(6):
        bounce = -5 * abs(math.sin(i * math.pi / 3))
        _ghost(draw, i * CELL_W, 7 * CELL_H, body_y=bounce)

    # Row 8: review (6 frames) — look down + tilt
    for i in range(6):
        tilt_y = 3 * math.sin(i * math.pi / 3)
        _ghost(draw, i * CELL_W, 8 * CELL_H, body_y=tilt_y, eye="blink")

    # Downsample once after all primitives are drawn for smooth, compact edges.
    atlas = atlas.resize((ATLAS_W, ATLAS_H), Image.Resampling.LANCZOS)

    # Save atlas
    atlas_path = pack_dir / "spritesheet.webp"
    atlas.save(str(atlas_path), "WEBP", quality=90)

    # Create valid V1 manifest
    manifest = {
        "id": "default_dynamic_ghost",
        "displayName": "小幽灵",
        "description": "原创动态角色 — 半透明小幽灵，支持呼吸/挥手/跳跃/失败/等待动画",
        "spritesheetPath": "spritesheet.webp",
        "spriteVersionNumber": 1,
    }
    with open(pack_dir / "pet.json", "w", encoding="utf-8") as f:
        # ASCII escapes keep the manifest readable on legacy Windows locale
        # readers while preserving the same Unicode values when decoded.
        json.dump(manifest, f, ensure_ascii=True, indent=2)

    LOGGER.info("Default dynamic pet generated: %s (%dx%d V1)", pack_dir, ATLAS_W, ATLAS_H)
    return pack_dir
