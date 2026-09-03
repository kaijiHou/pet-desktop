"""Pet Animation State Machine — maps business semantics to animations.

States:
    IDLE, HOVER, DRAG_LEFT, DRAG_RIGHT, CLICK, DOUBLE_CLICK,
    RECEIVE_FILE, CREATE_FILE, DELETE_FILE, RENAME_FILE,
    REMINDER, WAGE_PROGRESS, OVERTIME, CLOCK_OUT,
    SLEEP, ERROR

Priority: ERROR/REMINDER > file events > DRAG > WAGE > HOVER > IDLE
"""
from __future__ import annotations

import logging
import random
import time
from dataclasses import dataclass, field
from typing import Optional

from PyQt5.QtCore import QTimer

from .atlas import SpritesheetAtlas
from .animation import AnimationPlayer

LOGGER = logging.getLogger("pet.character_v4.state_machine")

# ── State definitions ──────────────────────────────────────────────────────
@dataclass
class StateDef:
    name: str
    animation: str          # atlas animation name
    priority: int           # higher = more important
    interruptible: bool = True
    loop: bool = False
    duration_ms: int = 0    # 0 = until animation completes
    next_state: str = "IDLE"
    fallback: str = "idle"  # atlas fallback if animation missing


# Default state definitions
DEFAULT_STATES = {
    "IDLE":          StateDef("IDLE", "idle", 0, loop=True, fallback="idle"),
    "HOVER":         StateDef("HOVER", "waving", 10, loop=False, next_state="IDLE", fallback="idle"),
    "CLICK":         StateDef("CLICK", "waving", 20, loop=False, next_state="IDLE", fallback="idle"),
    "DOUBLE_CLICK":  StateDef("DOUBLE_CLICK", "jumping", 25, loop=False, next_state="IDLE", fallback="idle"),
    "DRAG_LEFT":     StateDef("DRAG_LEFT", "running_l", 15, loop=True, fallback="idle"),
    "DRAG_RIGHT":    StateDef("DRAG_RIGHT", "running_r", 15, loop=True, fallback="idle"),
    "RECEIVE_FILE":  StateDef("RECEIVE_FILE", "waving", 30, loop=False, next_state="IDLE", fallback="idle"),
    "GIVE_FILE":     StateDef("GIVE_FILE", "waving", 30, loop=False, next_state="IDLE", fallback="idle"),
    "CREATE_FILE":   StateDef("CREATE_FILE", "jumping", 30, loop=False, next_state="IDLE", fallback="idle"),
    "COPY_FILE":     StateDef("COPY_FILE", "jumping", 30, loop=False, next_state="IDLE", fallback="idle"),
    "MOVE_FILE":     StateDef("MOVE_FILE", "waving", 30, loop=False, next_state="IDLE", fallback="idle"),
    "DELETE_FILE":   StateDef("DELETE_FILE", "failed", 35, loop=False, next_state="IDLE", fallback="idle"),
    "RENAME_FILE":   StateDef("RENAME_FILE", "review", 30, loop=False, next_state="IDLE", fallback="idle"),
    "REMINDER":      StateDef("REMINDER", "waving", 40, loop=False, next_state="IDLE", fallback="idle"),
    "WAGE_PROGRESS": StateDef("WAGE_PROGRESS", "review", 20, loop=False, next_state="IDLE", fallback="idle"),
    "OVERTIME":      StateDef("OVERTIME", "waiting", 15, loop=True, fallback="idle"),
    "CLOCK_OUT":     StateDef("CLOCK_OUT", "waving", 25, loop=False, next_state="IDLE", fallback="idle"),
    "MEAL_ALLOWANCE": StateDef("MEAL_ALLOWANCE", "waving", 25, loop=False, next_state="IDLE", fallback="idle"),
    "ERROR":         StateDef("ERROR", "failed", 50, loop=False, next_state="IDLE", fallback="idle"),
    "SLEEP":         StateDef("SLEEP", "waiting", 5, loop=True, fallback="idle"),
    "LOOK_UP":       StateDef("LOOK_UP", "look_up", 8, loop=False, next_state="IDLE", fallback="idle"),
    "LOOK_DOWN":     StateDef("LOOK_DOWN", "look_down", 8, loop=False, next_state="IDLE", fallback="idle"),
    "WAKE":          StateDef("WAKE", "waving", 25, loop=False, next_state="IDLE", fallback="idle"),
}


class PetStateMachine:
    """Manages animation state transitions for a pet character."""

    def __init__(self, atlas: SpritesheetAtlas, player: AnimationPlayer):
        self.atlas = atlas
        self.player = player
        self._states = dict(DEFAULT_STATES)  # copy
        self._current_state = "IDLE"
        self._state_start = time.time()
        self._idle_timer = QTimer()
        self._idle_timer.timeout.connect(self._maybe_random_idle_action)
        self._idle_timer.start(15000)  # 15s base interval
        self._last_idle_action = 0
        # Start idle
        self._enter_state("IDLE")

    def _enter_state(self, state_name: str):
        """Enter a new state and play its animation."""
        st = self._states.get(state_name)
        if st is None:
            LOGGER.warning("Unknown state: %s, falling back to IDLE", state_name)
            st = self._states["IDLE"]
        self._current_state = state_name
        self._state_start = time.time()
        anim = st.animation
        # Check if animation exists in atlas, use fallback
        if self.atlas.frame_count(anim) == 0:
            anim = st.fallback
        self.player.play(anim, loop=st.loop, on_complete=self._on_animation_complete)
        LOGGER.debug("State → %s (anim=%s, loop=%s)", state_name, anim, st.loop)

    def _on_animation_complete(self):
        """Called when a non-looping animation finishes."""
        st = self._states.get(self._current_state)
        if st and not st.loop:
            next_s = st.next_state
            self._enter_state(next_s)

    def transition(self, event: str) -> bool:
        """Try to transition to a new state based on a business event.

        Returns True if transition occurred.
        """
        target = self._resolve_event(event)
        if target is None:
            return False
        new_st = self._states.get(target)
        cur_st = self._states.get(self._current_state)
        if new_st is None:
            return False
        # Can only interrupt if current state is interruptible
        if cur_st and not cur_st.interruptible:
            return False
        # Allow same-priority directional switching (drag L↔R, look U↔D)
        same_dir_pair = {
            ("DRAG_LEFT", "DRAG_RIGHT"), ("DRAG_RIGHT", "DRAG_LEFT"),
            ("LOOK_UP", "LOOK_DOWN"), ("LOOK_DOWN", "LOOK_UP"),
        }
        is_same_dir = (self._current_state, target) in same_dir_pair
        if cur_st and not is_same_dir and new_st.priority <= cur_st.priority:
            return False
        self._enter_state(target)
        return True

    def _resolve_event(self, event: str) -> Optional[str]:
        """Map a business event to a state name."""
        mapping = {
            "idle": "IDLE",
            "hover": "HOVER",
            "click": "CLICK",
            "double_click": "DOUBLE_CLICK",
            "drag_left": "DRAG_LEFT",
            "drag_right": "DRAG_RIGHT",
            "receive_file": "RECEIVE_FILE",
            "give_file": "GIVE_FILE",
            "create_file": "CREATE_FILE",
            "delete_file": "DELETE_FILE",
            "rename_file": "RENAME_FILE",
            "copy_file": "COPY_FILE",
            "move_file": "MOVE_FILE",
            "reminder": "REMINDER",
            "wage_progress": "WAGE_PROGRESS",
            "overtime": "OVERTIME",
            "clock_out": "CLOCK_OUT",
            "meal_allowance": "MEAL_ALLOWANCE",
            "success": "CLICK",
            "error": "ERROR",
            "sleep": "SLEEP",
            "look_up": "LOOK_UP",
            "look_down": "LOOK_DOWN",
            "wake": "WAKE",
        }
        key = str(event or "").lower()
        target = mapping.get(key)
        if target is None:
            LOGGER.warning("Ignoring unknown semantic event: %s", event)
        return target

    def _maybe_random_idle_action(self):
        """Random idle action every 15-45s."""
        if self._current_state != "IDLE":
            return
        now = time.time()
        if now - self._last_idle_action < 15:
            return
        if random.random() < 0.3:  # 30% chance
            action = random.choice(["waving", "jumping", "look_up", "look_down"])
            self._enter_state("CLICK" if action == "waving" else "DOUBLE_CLICK" if action == "jumping" else "LOOK_UP" if action == "look_up" else "LOOK_DOWN")
            self._last_idle_action = now

    @property
    def current_state(self) -> str:
        return self._current_state

    @property
    def is_idle(self) -> bool:
        return self._current_state == "IDLE"

    def force_idle(self):
        """Force return to idle state."""
        self._enter_state("IDLE")

    def stop(self):
        """Stop random idle actions and playback during teardown."""
        self._idle_timer.stop()
        self.player.stop()
