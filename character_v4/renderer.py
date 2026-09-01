"""Dynamic Pack Renderer — unified renderer for Codex-compatible dynamic pets.

Implements the CharacterRenderer interface for PetWindow integration.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

from PyQt5.QtCore import QObject, pyqtSignal
from PyQt5.QtGui import QPainter, QPixmap

from .atlas import SpritesheetAtlas
from .animation import AnimationPlayer
from .manifest import CodexPetManifest
from .state_machine import PetStateMachine

LOGGER = logging.getLogger("pet.character_v4.renderer")


class DynamicPackRenderer(QObject):
    """Renders a Codex-compatible dynamic pet pack."""
    frame_changed = pyqtSignal()

    def __init__(self, pack_root: Path, scale: float = 3.0, parent=None):
        super().__init__(parent)
        self.pack_root = pack_root
        self._scale = scale
        self._manifest: Optional[CodexPetManifest] = None
        self._atlas: Optional[SpritesheetAtlas] = None
        self._player: Optional[AnimationPlayer] = None
        self._state_machine: Optional[PetStateMachine] = None
        self._loaded = False
        self._global_bbox: Optional[tuple[int, int, int, int]] = None  # union alpha bbox

    def load(self) -> bool:
        """Load manifest + atlas + initialize player."""
        if self._loaded:
            return True
        try:
            self._manifest = CodexPetManifest.load(self.pack_root)
            result = self._manifest.validate(self.pack_root)
            if not result.ok:
                LOGGER.error("Manifest validation failed: %s", result.errors)
                return False
            self._atlas = SpritesheetAtlas(self._manifest, self.pack_root)
            if not self._atlas.load():
                return False
            self._player = AnimationPlayer(self._atlas, self)
            self._player.frame_changed.connect(self.frame_changed.emit)
            self._state_machine = PetStateMachine(self._atlas, self._player)
            self._compute_global_bbox()
            self._loaded = True
            return True
        except Exception:
            LOGGER.exception("Failed to load dynamic pack")
            return False

    def _compute_global_bbox(self):
        """Pre-compute union alpha bbox across all frames for stable anchoring."""
        if self._atlas is None or self._atlas._pil_image is None:
            return
        try:
            img = self._atlas._pil_image
            from .manifest import CODEX_CELL_W, CODEX_CELL_H
            rows = self._atlas._frames
            min_x, min_y = CODEX_CELL_W, CODEX_CELL_H
            max_x, max_y = 0, 0
            found = False
            for anim_name, frame_list in rows.items():
                if not frame_list:
                    continue
                # Use first frame of each animation
                qpix = frame_list[0]
                if qpix.isNull():
                    continue
                # Get alpha channel from PIL
                w, h = qpix.width(), qpix.height()
                # Sample a subset of frames for performance
                for fi in [0, len(frame_list)//2]:
                    if fi >= len(frame_list):
                        continue
                    qpix = frame_list[fi]
                    # Convert QPixmap to QImage to read alpha
                    qimg = qpix.toImage()
                    for y in range(0, h, 4):
                        for x in range(0, w, 4):
                            if qimg.pixelColor(x, y).alpha() > 10:
                                min_x = min(min_x, x)
                                min_y = min(min_y, y)
                                max_x = max(max_x, x)
                                max_y = max(max_y, y)
                                found = True
            if found:
                self._global_bbox = (min_x, min_y, max_x - min_x + 1, max_y - min_y + 1)
            else:
                cw, ch = self._atlas.cell_size
                self._global_bbox = (0, 0, cw, ch)
            LOGGER.debug("Global alpha bbox: %s", self._global_bbox)
        except Exception:
            cw, ch = self._atlas.cell_size if self._atlas else (192, 208)
            self._global_bbox = (0, 0, cw, ch)

    def set_scale(self, scale: float):
        self._scale = max(0.5, min(6.0, scale))

    def size(self) -> tuple[int, int]:
        """Return (w, h) at current scale."""
        if self._atlas is None:
            return (192, 208)
        cw, ch = self._atlas.cell_size
        return (round(cw * self._scale), round(ch * self._scale))

    def visible_bbox(self) -> tuple[int, int, int, int]:
        """Return union alpha bbox in source pixels (stable across frames)."""
        if self._global_bbox:
            x, y, w, h = self._global_bbox
            return (round(x * self._scale), round(y * self._scale),
                    round(w * self._scale), round(h * self._scale))
        cw, ch = self._atlas.cell_size if self._atlas else (192, 208)
        return (0, 0, round(cw * self._scale), round(ch * self._scale))

    def paint(self, painter: QPainter, x: int, y: int, w: int, h: int):
        """Paint the current frame at the given rectangle."""
        if self._player is None:
            return
        frame = self._player.current_frame
        if frame is None:
            return
        painter.drawPixmap(x, y, w, h, frame)

    def play_semantic(self, semantic: str):
        """Trigger an animation by business semantic."""
        if self._state_machine is None:
            return
        self._state_machine.transition(semantic)

    def idle(self):
        """Return to idle state."""
        if self._state_machine:
            self._state_machine.force_idle()

    def stop(self):
        """Stop all animations."""
        if self._player:
            self._player.stop()

    @property
    def display_name(self) -> str:
        if self._manifest:
            return self._manifest.display_name
        return "Dynamic Pet"

    @property
    def mode(self) -> str:
        return "dynamic_pack"

    @property
    def is_loaded(self) -> bool:
        return self._loaded
