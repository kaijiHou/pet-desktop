"""Spritesheet Atlas — loads Codex atlas and provides cached QPixmap frames.

Performance: loads atlas once, extracts frames as QPixmap for fast QPainter
drawing. No per-frame PIL crop in paintEvent.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

from PyQt5.QtGui import QImage, QPixmap
from PIL import Image

from .manifest import CODEX_CELL_W, CODEX_CELL_H, CODEX_V1_ROWS, CODEX_V2_ROWS, CodexPetManifest

LOGGER = logging.getLogger("pet.character_v4.atlas")


class SpritesheetAtlas:
    """Load a Codex spritesheet and provide frame access via QPixmap."""

    def __init__(self, manifest: CodexPetManifest, pack_root: Path):
        self.manifest = manifest
        self.pack_root = pack_root
        self._pil_image: Optional[Image.Image] = None
        self._qimage: Optional[QImage] = None
        self._frames: dict[str, list[QPixmap]] = {}  # anim_name -> [QPixmap, ...]
        self._frame_ms: dict[str, int] = {}  # anim_name -> ms per frame
        self._loaded = False

    def load(self) -> bool:
        """Load the atlas image and prepare frame cache."""
        if self._loaded:
            return True
        sheet_path = self.pack_root / self.manifest.spritesheet_path
        if not sheet_path.exists():
            LOGGER.error("Spritesheet not found: %s", sheet_path)
            return False
        try:
            self._pil_image = Image.open(sheet_path).convert("RGBA")
            # Convert to QImage for fast QPixmap extraction
            data = self._pil_image.tobytes("raw", "RGBA")
            w, h = self._pil_image.size
            self._qimage = QImage(data, w, h, w * 4, QImage.Format_RGBA8888)
            self._extract_all_frames()
            self._loaded = True
            LOGGER.info("Atlas loaded: %s (%d×%d)", sheet_path.name, w, h)
            return True
        except Exception:
            LOGGER.exception("Failed to load atlas")
            return False

    def _extract_all_frames(self):
        """Pre-extract all animation frames as QPixmap."""
        if self._qimage is None:
            return
        rows = CODEX_V2_ROWS if self.manifest.sprite_version == 2 else CODEX_V1_ROWS
        for anim_name, (row_idx, frame_count) in rows.items():
            frames = []
            for col in range(frame_count):
                x = col * CODEX_CELL_W
                y = row_idx * CODEX_CELL_H
                cell = self._qimage.copy(x, y, CODEX_CELL_W, CODEX_CELL_H)
                frames.append(QPixmap.fromImage(cell))
            self._frames[anim_name] = frames
            self._frame_ms[anim_name] = 200 if anim_name == "idle" else 150
        LOGGER.info("Extracted frames: %s", {k: len(v) for k, v in self._frames.items()})

    def get_frame(self, animation: str, frame_idx: int) -> Optional[QPixmap]:
        """Get a specific frame. Returns None if animation/frame not found."""
        frames = self._frames.get(animation)
        if not frames:
            return None
        idx = frame_idx % len(frames)
        return frames[idx]

    def frame_count(self, animation: str) -> int:
        return len(self._frames.get(animation, []))

    def frame_ms(self, animation: str) -> int:
        return self._frame_ms.get(animation, 150)

    @property
    def cell_size(self) -> tuple[int, int]:
        return CODEX_CELL_W, CODEX_CELL_H

    @property
    def has_animation(self) -> bool:
        return len(self._frames) > 0
