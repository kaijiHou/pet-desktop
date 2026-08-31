"""Animation Player — manages frame playback for a single animation."""
from __future__ import annotations

import logging
from typing import Optional

from PyQt5.QtCore import QTimer
from PyQt5.QtGui import QPixmap

from .atlas import SpritesheetAtlas

LOGGER = logging.getLogger("pet.character_v4.animation")


class AnimationPlayer:
    """Plays a single animation sequence from an atlas.

    Handles frame timing, looping, and completion callbacks.
    """
    def __init__(self, atlas: SpritesheetAtlas, timer_parent=None):
        self.atlas = atlas
        self._current_anim: Optional[str] = None
        self._frame_idx = 0
        self._timer = QTimer(timer_parent)
        self._timer.timeout.connect(self._advance_frame)
        self._on_complete = None  # callback when non-looping anim finishes

    def play(self, animation: str, loop: bool = True, on_complete=None):
        """Start playing an animation."""
        if self.atlas.frame_count(animation) == 0:
            LOGGER.warning("Animation '%s' has no frames, falling back to idle", animation)
            animation = "idle"
        self._current_anim = animation
        self._frame_idx = 0
        self._on_complete = on_complete
        ms = self.atlas.frame_ms(animation)
        if loop:
            self._timer.start(ms)
        else:
            # Play once: start timer, stop after last frame
            self._timer.start(ms)

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
            if self._on_complete:
                self._on_complete()
            else:
                # Loop by default
                self._frame_idx = 0

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
