"""Align the two supplied custom pet sheets to the Codex V1 frame grid."""

from pathlib import Path

import cv2
import numpy as np
from PIL import Image


ROOT = Path(__file__).resolve().parents[1] / "data" / "characters"
ROW_COUNTS = (6, 8, 8, 4, 5, 8, 6, 6, 6)
# Per-pack: (source, alpha_threshold, opening, source_counts, band_clamp, piece_filter)
#   band_clamp   — forbid pixels outside the row band (kills cross-row
#                  fragments, but also cuts feet that legitimately cross the
#                  band edge, e.g. the gray pack's running frames)
#   piece_filter — keep only the main connected piece + vicinity (kills stray
#                  same-row fragments, but also deletes legitimately detached
#                  shoes that MORPH_OPEN splits off the legs)
# gray uses the pure ownership cut: its shoes connect to the legs at
# threshold 128 and its runner's feet cross the band edge — either
# safeguard would amputate them.
PACKS = {
    # spritesheet.png in each installed pack is the ALIGNED output;
    # the untouched originals are kept as spritesheet_original.png.
    "brown_glasses_girl": (
        "spritesheet_original.png", 251, 3, ROW_COUNTS, True, True
    ),
    "brown_glasses_girl_green": (
        "spritesheet_new_source.png", 251, 3, (7, 8, 8, 5, 5, 8, 7, 7, 7), True, True
    ),
    "brown_glasses_girl_gray": (
        "spritesheet_original.png", 128, 1, ROW_COUNTS, False, False
    ),
}
CELL_W, CELL_H = 192, 208


def align(
    pack_name: str, source_name: str, alpha_threshold: int,
    opening: int, source_counts: tuple[int, ...],
    band_clamp: bool = True, piece_filter: bool = True,
) -> None:
    pack = ROOT / pack_name
    source = pack / source_name
    target = pack / "spritesheet_aligned.png"
    pixels = np.asarray(Image.open(source).convert("RGBA"))
    source_h, source_w = pixels.shape[:2]
    row_height = source_h / len(ROW_COUNTS)
    mask = (pixels[:, :, 3] > alpha_threshold).astype(np.uint8)
    if opening > 1:
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, np.ones((opening, opening), np.uint8))
    _, components, stats, centers = cv2.connectedComponentsWithStats(mask, 8)
    rows = [[] for _ in ROW_COUNTS]
    for component in range(1, len(stats)):
        if stats[component, cv2.CC_STAT_AREA] < 1500:
            continue
        row = max(0, min(8, round((centers[component, 1] - row_height / 2) / row_height)))
        rows[row].append(component)
    for row, (found, expected) in enumerate(zip(rows, source_counts)):
        if len(found) != expected:
            raise ValueError(f"{pack_name} row {row}: found {len(found)}, expected {expected}")
        found.sort(key=lambda component: centers[component, 0])

    # Assign shared antialiased edge pixels to the nearest detected character.
    main_components = [component for row in rows for component in row]
    seeds = np.isin(components, main_components).astype(np.uint8)
    _, nearest = cv2.distanceTransformWithLabels(
        1 - seeds, cv2.DIST_L2, 5, labelType=cv2.DIST_LABEL_CCOMP
    )

    sheet = Image.new("RGBA", (1536, 1872), (0, 0, 0, 0))
    for row, found in enumerate(rows):
        for col, component in enumerate(found[:ROW_COUNTS[row]]):
            x, y, width, height, _ = map(int, stats[component])
            x0, y0 = max(0, x - 30), max(0, y - 30)
            x1, y1 = min(source_w, x + width + 30), min(source_h, y + height + 30)
            # A frame may never steal pixels from another row: the ±30px
            # padding reaches into the neighbouring band, and small stray
            # pieces there (hair wisps, shoes) are owned by "nearest"
            # component — sometimes this one — showing up as floating
            # fragments above the pet. Only apply where safe: packs whose
            # frames never cross the band edge (see PACKS flags).
            if band_clamp:
                band_top = int(row * row_height)
                band_bottom = int(round((row + 1) * row_height))
                y0 = max(y0, band_top)
                y1 = min(y1, band_bottom)
            seed_y, seed_x = np.argwhere(components[y:y + height, x:x + width] == component)[0]
            owner = nearest[y + seed_y, x + seed_x]
            cut = pixels[y0:y1, x0:x1].copy()
            belongs = (nearest[y0:y1, x0:x1] == owner) & (cut[:, :, 3] > 8)
            cut[~belongs] = 0
            if piece_filter:
                # Keep only the main connected piece (plus a small dilated
                # vicinity) — stray same-row fragments that pass the
                # nearest-owner test (hair wisps of the neighbour frame) die
                # here. Off where legitimate detached pieces exist (shoes).
                solid = cv2.morphologyEx(
                    ((cut[:, :, 3] > 128) & belongs).astype(np.uint8),
                    cv2.MORPH_OPEN, np.ones((3, 3), np.uint8),
                )
                _, pieces = cv2.connectedComponents(solid, 8)
                own_seed = components[y0:y1, x0:x1] == component
                piece_ids, overlaps = np.unique(pieces[own_seed], return_counts=True)
                main_piece = int(piece_ids[piece_ids > 0][np.argmax(overlaps[piece_ids > 0])])
                keep = cv2.dilate((pieces == main_piece).astype(np.uint8), np.ones((5, 5), np.uint8))
                cut[keep == 0] = 0
            # The detection core excludes hair and shoes; keep their owned edge pixels.
            bounds = np.argwhere(belongs & (cut[:, :, 3] > 128))
            if not len(bounds):
                raise ValueError(f"Empty frame: {pack_name} row {row} column {col}")
            top_edge, left_edge = np.maximum(bounds.min(axis=0) - 3, 0)
            bottom_edge, right_edge = np.minimum(bounds.max(axis=0) + 4, cut.shape[:2])
            cut = cut[top_edge:bottom_edge, left_edge:right_edge]
            frame = Image.fromarray(cut, "RGBA")
            scale = min(178 / frame.width, 194 / frame.height)
            size = (round(frame.width * scale), round(frame.height * scale))
            frame = frame.resize(size, Image.Resampling.LANCZOS)
            left = col * CELL_W + (CELL_W - frame.width) // 2
            top = row * CELL_H + CELL_H - 7 - frame.height
            sheet.alpha_composite(frame, (left, top))
    sheet.save(target)
    print(f"{pack_name}: aligned {sum(ROW_COUNTS)} frames -> {target}")


if __name__ == "__main__":
    for name, settings in PACKS.items():
        align(name, *settings)
