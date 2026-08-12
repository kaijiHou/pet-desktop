#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Phase 1 baseline tool — synthetic asset generator + animations.json mechanical export.

Background (see docs/KNOWN_ISSUES.md KI-01/KI-10):
  * The upstream repo does NOT ship `clippy_sheet.png` or `animations.json`
    (both are .gitignored; README says bring-your-own assets).
  * The ORIGINAL runtime loads assets from `~/desktop-pet/assets/`
    (config.CONFIG_DIR / "assets"), NOT from the repo directory.

This script therefore:
  1. Mechanically extracts the ANIMS table embedded in assets/clippy.html
     and writes it verbatim to assets/animations.json (repo dir, gitignored).
     No redesign, no coordinate/duration changes, no renames.
  2. Generates a SYNTHETIC placeholder sprite sheet (distinct colored cell per
     124x93 frame slot with shape + coordinate label) so frame switching,
     coordinates and durations are visible to the eye. It is NOT the real
     Clippy artwork.
  3. Copies clippy.html + the synthetic sheet into ~/desktop-pet/assets/
     which is where the unmodified original program expects them.

NOT business code. Run:  .venv/Scripts/python.exe scripts/gen_synthetic_assets.py
"""

import json
import re
import shutil
import sys
from pathlib import Path

from PIL import Image, ImageDraw

REPO = Path(__file__).resolve().parent.parent
HTML_SRC = REPO / "assets" / "clippy.html"
ANIMS_OUT = REPO / "assets" / "animations.json"
SHEET_OUT = REPO / "assets" / "clippy_sheet.png"

# Original runtime asset dir (unmodified business code reads from here)
RUNTIME_ASSETS = Path.home() / "desktop-pet" / "assets"

FRAME_W, FRAME_H = 124, 93

PALETTE = [
    (230, 70, 70), (70, 160, 230), (90, 190, 90), (240, 170, 60),
    (170, 100, 220), (60, 200, 200), (240, 120, 180), (150, 190, 60),
    (255, 140, 100), (110, 130, 240), (200, 200, 80), (120, 220, 160),
]


def extract_anims() -> dict:
    """Mechanically extract the ANIMS object from clippy.html (verbatim data)."""
    html = HTML_SRC.read_text(encoding="utf-8")
    m = re.search(r"let\s+ANIMS\s*=\s*(\{.*?\})\s*;", html, re.DOTALL)
    if not m:
        sys.exit("FATAL: could not locate ANIMS object in clippy.html")
    return json.loads(m.group(1))


def verify_against_source(anims: dict) -> None:
    """Spot-check exported data against the JS source text."""
    html = HTML_SRC.read_text(encoding="utf-8")
    assert len(anims) == 43, f"expected 43 animations, got {len(anims)}"
    # spot checks (literal substrings from the JS source)
    assert '"Congratulate": [[0, 0, 100]' in html
    assert anims["Congratulate"][0] == [0, 0, 100]
    assert anims["Congratulate"][-1] == [0, 0, 100]
    assert anims["SendMail"][-1] == [0, 0, 100]
    assert anims["Thinking"][0] == [0, 0, 100]
    assert anims["LookRight"][1] == [620, 651, 100]
    # every frame must be [x, y, duration]
    for name, frames in anims.items():
        assert frames, f"animation {name} has no frames"
        for f in frames:
            assert len(f) == 3 and all(isinstance(v, int) for v in f), (name, f)
    print(f"[verify] 43 animations, spot checks OK")


def build_sheet(anims: dict) -> Image.Image:
    max_x = max(f[0] for frames in anims.values() for f in frames)
    max_y = max(f[1] for frames in anims.values() for f in frames)
    w, h = max_x + FRAME_W, max_y + FRAME_H
    print(f"[sheet] frame grid extent: max_x={max_x} max_y={max_y} -> {w}x{h}")

    img = Image.new("RGBA", (w, h), (40, 40, 48, 255))
    d = ImageDraw.Draw(img)

    # grid lines
    for x in range(0, w + 1, FRAME_W):
        d.line([(x, 0), (x, h)], fill=(70, 70, 80, 255), width=1)
    for y in range(0, h + 1, FRAME_H):
        d.line([(0, y), (w, y)], fill=(70, 70, 80, 255), width=1)

    cells = sorted({(f[0], f[1]) for frames in anims.values() for f in frames})
    print(f"[sheet] unique frame cells referenced by ANIMS: {len(cells)}")

    for (x, y) in cells:
        ci, ri = x // FRAME_W, y // FRAME_H
        color = PALETTE[(ci * 7 + ri * 13) % len(PALETTE)]
        shape = (ci + ri) % 3
        pad = 14
        x0, y0, x1, y1 = x + pad, y + pad, x + FRAME_W - pad, y + FRAME_H - pad
        if shape == 0:
            d.rectangle([x0, y0, x1, y1], fill=color + (255,), outline=(20, 20, 20, 255), width=3)
        elif shape == 1:
            d.ellipse([x0, y0, x1, y1], fill=color + (255,), outline=(20, 20, 20, 255), width=3)
        else:
            d.polygon([(x + FRAME_W // 2, y0), (x1, y1), (x0, y1)],
                      fill=color + (255,), outline=(20, 20, 20, 255))
        # frame slot coordinate label — makes every cell identifiable
        d.text((x + 4, y + 2), f"{x},{y}", fill=(255, 255, 255, 255))
        # inner marker differing per shape so adjacent same-color cells still differ
        d.text((x + 4, y + FRAME_H - 14), f"r{ri}c{ci}", fill=(255, 255, 255, 255))
    return img


def main():
    anims = extract_anims()
    print(f"[extract] {len(anims)} animations parsed from clippy.html")
    verify_against_source(anims)

    ANIMS_OUT.write_text(json.dumps(anims, indent=1), encoding="utf-8")
    total_frames = sum(len(v) for v in anims.values())
    print(f"[export] {ANIMS_OUT}  ({len(anims)} animations, {total_frames} frames)")
    print("         NOTE: runtime-derived asset exported verbatim from clippy.html;")
    print("         it is NOT new animation design and is gitignored upstream.")

    img = build_sheet(anims)
    img.save(SHEET_OUT)
    print(f"[sheet] synthetic sheet written: {SHEET_OUT} ({SHEET_OUT.stat().st_size} bytes)")

    # Deploy to the ORIGINAL runtime asset location (~/desktop-pet/assets/)
    RUNTIME_ASSETS.mkdir(parents=True, exist_ok=True)
    shutil.copy2(HTML_SRC, RUNTIME_ASSETS / "clippy.html")
    shutil.copy2(SHEET_OUT, RUNTIME_ASSETS / "clippy_sheet.png")
    print(f"[deploy] runtime assets -> {RUNTIME_ASSETS}")
    for f in sorted(RUNTIME_ASSETS.iterdir()):
        print(f"         {f.name}  {f.stat().st_size} bytes")


if __name__ == "__main__":
    main()
