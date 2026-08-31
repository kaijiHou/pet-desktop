"""Default Dynamic Pet Generator — creates an original animated pet with Pillow.

Generates a simple "小幽灵" (little ghost) character with:
- Idle: breathing animation (2 frames)
- Waving: arm movement (3 frames)
- Jumping: vertical bounce (3 frames)
- Failed: shake animation (3 frames)
- Waiting: subtle idle (2 frames)

All frames are procedurally generated — no external assets needed.
"""
from __future__ import annotations

import json
import logging
import math
from pathlib import Path

from PIL import Image, ImageDraw

LOGGER = logging.getLogger("pet.character_v4.default_pet")

# Atlas layout: 8 columns × 6 rows (V1 subset)
COLS = 8
ROWS = 6
CELL_W = 192
CELL_H = 208
ATLAS_W = COLS * CELL_W  # 1536
ATLAS_H = ROWS * CELL_H  # 1248

# Ghost parameters
GHOST_BODY_COLOR = (200, 220, 255, 200)  # light blue, semi-transparent
GHOST_EYE_COLOR = (40, 40, 80, 255)
GHOST_MOUTH_COLOR = (40, 40, 80, 200)
GHOST_CENTER_X = CELL_W // 2
GHOST_CENTER_Y = CELL_H // 2 + 10


def _draw_ghost(draw: ImageDraw.ImageDraw, cx: int, cy: int,
                body_offset: float = 0, eye_state: str = "open",
                arm_angle: float = 0, bounce: float = 0):
    """Draw a simple ghost character at (cx, cy) with animation parameters."""
    cy_adj = int(cy + bounce)

    # Body (rounded rectangle + wavy bottom)
    bw, bh = 50, 55
    body_top = cy_adj - bh // 2 + int(body_offset)
    body_bottom = cy_adj + bh // 2 + int(body_offset)

    # Main body ellipse
    draw.ellipse(
        [cx - bw, body_top, cx + bw, body_bottom],
        fill=GHOST_BODY_COLOR,
    )

    # Wavy bottom (3 bumps)
    for i in range(3):
        bx = cx - bw + (2 * bw * (i + 1)) // 4
        wave_y = int(5 * math.sin(time_module.time() * 3 + i))
        draw.ellipse(
            [bx - 15, body_bottom - 10 + wave_y, bx + 15, body_bottom + 20 + wave_y],
            fill=GHOST_BODY_COLOR,
        )

    # Eyes
    ey = cy_adj - 10 + int(body_offset)
    if eye_state == "open":
        draw.ellipse([cx - 18, ey - 8, cx - 6, ey + 8], fill=GHOST_EYE_COLOR)
        draw.ellipse([cx + 6, ey - 8, cx + 18, ey + 8], fill=GHOST_EYE_COLOR)
        # Highlights
        draw.ellipse([cx - 14, ey - 4, cx - 10, ey], fill=(255, 255, 255, 255))
        draw.ellipse([cx + 10, ey - 4, cx + 14, ey], fill=(255, 255, 255, 255))
    elif eye_state == "blink":
        draw.line([cx - 18, ey, cx - 6, ey], fill=GHOST_EYE_COLOR, width=2)
        draw.line([cx + 6, ey, cx + 18, ey], fill=GHOST_EYE_COLOR, width=2)

    # Mouth
    my = cy_adj + 12 + int(body_offset)
    draw.arc([cx - 8, my - 4, cx + 8, my + 8], 0, 180, fill=GHOST_MOUTH_COLOR, width=2)

    # Arm (waving)
    if arm_angle != 0:
        ax = cx + bw - 5
        ay = cy_adj - 5 + int(body_offset)
        arm_len = 25
        ex = ax + int(arm_len * math.cos(math.radians(arm_angle)))
        ey_arm = ay - int(arm_len * math.sin(math.radians(arm_angle)))
        draw.line([ax, ay, ex, ey_arm], fill=GHOST_BODY_COLOR, width=6)
        draw.ellipse([ex - 6, ey_arm - 6, ex + 6, ey_arm + 6], fill=GHOST_BODY_COLOR)


import time as time_module


def generate_default_pet(output_dir: Path) -> Path:
    """Generate the default dynamic pet pack.

    Returns the path to the installed pack directory.
    """
    pack_dir = output_dir / "default_dynamic_ghost"
    pack_dir.mkdir(parents=True, exist_ok=True)

    atlas = Image.new("RGBA", (ATLAS_W, ATLAS_H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(atlas)

    # Row 0: idle (6 frames) — breathing
    for i in range(6):
        offset = 2 * math.sin(i * math.pi / 3)
        blink = "blink" if i == 3 else "open"
        _draw_ghost(draw, GHOST_CENTER_X + i * CELL_W, GHOST_CENTER_Y,
                    body_offset=offset, eye_state=blink)

    # Row 1: running_right (8 frames) — move right
    for i in range(8):
        x_off = 10 * math.sin(i * math.pi / 4)
        bounce = -5 * abs(math.sin(i * math.pi / 4))
        _draw_ghost(draw, GHOST_CENTER_X + i * CELL_W + int(x_off), GHOST_CENTER_Y,
                    bounce=bounce)

    # Row 2: running_left (8 frames) — mirror of running_right
    for i in range(8):
        x_off = -10 * math.sin(i * math.pi / 4)
        bounce = -5 * abs(math.sin(i * math.pi / 4))
        _draw_ghost(draw, GHOST_CENTER_X + i * CELL_W + int(x_off), GHOST_CENTER_Y,
                    bounce=bounce)

    # Row 3: waving (4 frames)
    for i in range(4):
        arm = -30 + 60 * i / 3
        _draw_ghost(draw, GHOST_CENTER_X + i * CELL_W, GHOST_CENTER_Y,
                    arm_angle=arm)

    # Row 4: jumping (5 frames)
    for i in range(5):
        if i < 3:
            bounce = -20 * (i / 2)
        else:
            bounce = -20 * (1 - (i - 2) / 2)
        _draw_ghost(draw, GHOST_CENTER_X + i * CELL_W, GHOST_CENTER_Y,
                    bounce=bounce)

    # Row 5: failed (8 frames) — shake
    for i in range(8):
        x_off = 8 if i % 2 == 0 else -8
        _draw_ghost(draw, GHOST_CENTER_X + i * CELL_W + x_off, GHOST_CENTER_Y)

    # Save atlas
    atlas_path = pack_dir / "spritesheet.webp"
    atlas.save(str(atlas_path), "WEBP", quality=90)

    # Create pet.json
    manifest = {
        "id": "default_dynamic_ghost",
        "displayName": "小幽灵",
        "description": "原创动态角色 — 半透明小幽灵，支持呼吸/挥手/跳跃/失败动画",
        "spritesheetPath": "spritesheet.webp",
        "spriteVersionNumber": 1,
    }
    with open(pack_dir / "pet.json", "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)

    LOGGER.info("Default dynamic pet generated: %s", pack_dir)
    return pack_dir
