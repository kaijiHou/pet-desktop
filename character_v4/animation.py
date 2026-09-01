"""Animation Player — manages frame playback for a single animation.

Emits frame_changed signal on every frame advance so PetWindow can repaint.
"""
from __future__ import annotations

import logging
from typing import Optional

from PyQt5.QtCore import QObject, QTimer, pyqtSignal
from PyQt5.QtGui import QPixmap

from .atlas import SpritesheetAtlas

LOGGER = logging.getLogger("pet.character_v4.animation")


class AnimationPlayer(QObject):
    """Plays a single animation sequence from an atlas.

    Emits frame_changed() on every frame advance for repaint.
    """
    frame_changed = pyqtSignal()

    def __init__(self, atlas: SpritesheetAtlas, parent=None):
        super().__init__(parent)
        self.atlas = atlas
        self._current_anim: Optional[str] = None
        self._frame_idx = 0
        self._loop = True
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._advance_frame)
        self._on_complete = None

    def play(self, animation: str, loop: bool = True, on_complete=None):
        """Start playing an animation."""
        if self.atlas.frame_count(animation) == 0:
            LOGGER.warning("Animation '%s' has no frames, falling back to idle", animation)
            animation = "idle"
        self._current_anim = animation
        self._frame_idx = 0
        self._loop = loop
        self._on_complete = on_complete
        ms = self.atlas.frame_ms(animation)
        self._timer.start(ms)
        self.frame_changed.emit()

    def stop(self):
        self._timer.stop()
        self._current_anim = None
        self._frame_idx = 0

    def _advance_frame(self):
        if self._current_anim is None:
            return
        count = self.atlas.frame_count(self._current_anim)
        if count == 0:
            self.stop()
            return
        self._frame_idx += 1
        if self._frame_idx >= count:
            if self._loop:
                self._frame_idx = 0
            else:
                self._frame_idx = count - 1
                self._timer.stop()
                cb = self._on_complete
                self._on_complete = None
                self.frame_changed.emit()
                if cb:
                    cb()
                return
        self.frame_changed.emit()

    @property
    def current_frame(self) -> Optional[QPixmap]:
        if self._current_anim is None:
            return None
        return self.atlas.get_frame(self._current_anim, self._frame_idx)

    @property
    def current_animation(self) -> Optional[str]:
        return self._current_anim

    @property
    def is_playing(self) -> bool:
        return self._timer.isActive()
