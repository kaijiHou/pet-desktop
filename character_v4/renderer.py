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
        """Union alpha bbox in CELL-RELATIVE coordinates.

        The character sits inside its own 192×208 cell, but walk frames
        drift horizontally across the strip — a sheet-wide absolute union
        spans ~8 cells and once threw every anchor/bubble to the middle of
        the screen. Union the per-cell bboxes on CELL-RELATIVE coords
        instead: stable across frames and never larger than one cell.
        (The original per-pixel QImage.pixelColor loop was correct but cost
        ~4.5M sip calls per load; per-cell numpy keeps it under 100ms.)
        """
        if self._atlas is None or self._atlas._pil_image is None:
            return
        try:
            import numpy as np
            from .manifest import CODEX_CELL_W as CW, CODEX_CELL_H as CH
            img = self._atlas._pil_image
            cols, rows = img.width // CW, img.height // CH
            min_x, min_y, max_x, max_y = CW, CH, -1, -1
            for r in range(rows):
                band = np.asarray(img.crop((0, r * CH, img.width, (r + 1) * CH)))
                for c in range(cols):
                    cell_alpha = band[:, c * CW:(c + 1) * CW, 3]
                    ys, xs = np.nonzero(cell_alpha > 10)
                    if not len(xs):
                        continue
                    min_x, max_x = min(min_x, int(xs.min())), max(max_x, int(xs.max()))
                    min_y, max_y = min(min_y, int(ys.min())), max(max_y, int(ys.max()))
            if max_x >= 0:
                self._global_bbox = (min_x, min_y, max_x - min_x + 1, max_y - min_y + 1)
            else:
                self._global_bbox = (0, 0, CW, CH)
        except Exception:
            LOGGER.exception("global bbox computation failed; using full cell")
            cw, ch = self._atlas.cell_size
            self._global_bbox = (0, 0, cw, ch)
            LOGGER.debug("Global alpha bbox: %s", self._global_bbox)
        except Exception:
            cw, ch = self._atlas.cell_size if self._atlas else (192, 208)
            self._global_bbox = (0, 0, cw, ch)

    def set_scale(self, scale: float):
        self._scale = max(0.5, min(6.0, scale))

    def set_speed(self, factor: float):
        """Playback multiplier (>1 = faster); delegates to the player."""
        self._speed = max(0.25, min(4.0, float(factor or 1.0)))
        if self._player is not None:
            self._player.set_speed(self._speed)

    @property
    def speed(self) -> float:
        return getattr(self, "_speed", 1.0)

    def size(self) -> tuple[int, int]:
        """Return (w, h) at current scale."""
        if self._atlas is None:
            return (192, 208)
        cw, ch = self._atlas.cell_size
        return (round(cw * self._scale), round(ch * self._scale))

    def visible_bbox(self) -> tuple[int, int, int, int]:
        """Return union alpha bbox in UNSCALED source pixels.

        Consumers (PetWindow.visible_pet_rect) apply the current scale
        themselves — returning scaled values here double-scaled the anchor
        into a screen-filling rectangle, which threw every bubble/panel to
        the middle of the screen.
        """
        if self._global_bbox:
            x, y, w, h = self._global_bbox
            return (x, y, w, h)
        cw, ch = self._atlas.cell_size if self._atlas else (192, 208)
        return (0, 0, cw, ch)

    def paint(self, painter: QPainter, x: int, y: int, w: int, h: int):
        """Paint the current frame at the given rectangle."""
        if self._player is None:
            return
        frame = self._player.current_frame
        if frame is None:
            return
        painter.drawPixmap(x, y, w, h, frame)

    def current_frame(self) -> Optional[QPixmap]:
        """Return the current frame without exposing the animation player."""
        return self._player.current_frame if self._player is not None else None

    def current_pixmap(self) -> Optional[QPixmap]:
        return self.current_frame()

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
        if self._state_machine:
            self._state_machine.stop()

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
