"""V4.9 contract regressions from the pre-acceptance audit.

Covers the gaps found without computer control:
  * stale selected_character_id falls back to the builtin ghost and the
    effective id is persisted (V4.9 task item 55)
  * QuickPanel calendar button uses the unified 工作日历 naming (item 36)
  * gallery/preview switching ×20 leaves no growing animation timers (items 17/58)
"""

import sys

import pytest


def test_stale_character_id_falls_back_to_builtin_ghost(pet_window_dynamic, monkeypatch):
    pet = pet_window_dynamic
    # Point config at a pack that does not exist, then reload the renderer.
    pet.config.set("selected_character_id", "missing_pet")
    pet._load_dynamic_renderer()
    assert pet.dynamic_renderer is not None and pet.dynamic_renderer.is_loaded
    assert pet.config.get("selected_character_id") == "default_dynamic_ghost", \
        "effective id must be persisted so the fallback warning doesn't repeat"


def test_quick_panel_uses_work_calendar_naming(pet_window):
    from quick_panel import QuickPanel
    panel = QuickPanel(pet_window)
    try:
        assert panel.calendar_btn.text() == "工作日历"
    finally:
        panel.close()


def test_gallery_switch_20x_no_timer_leak(pet_window_dynamic):
    """Items 17/58: switching preview characters many times must not leave
    a growing set of animation timers behind (each switch tears down the
    previous renderer: stop + disconnect + deleteLater)."""
    pet = pet_window_dynamic

    def active_animation_timers():
        timers = []
        for w in QApplication_allWidgets():
            for t in w.findChildren(type(pet.dynamic_renderer._player._timer)):
                if t.isActive():
                    timers.append(t)
        return len(timers)

    def QApplication_allWidgets():
        from PyQt5.QtWidgets import QApplication
        return QApplication.allWidgets()

    baseline = active_animation_timers()
    assert baseline >= 1, "desktop dynamic pet should own one active animation timer"
    for i in range(20):
        pet._load_dynamic_renderer()
    # give deleteLater events a chance to run
    from PyQt5.QtWidgets import QApplication
    QApplication.processEvents()
    after = active_animation_timers()
    assert after <= baseline + 1, \
        f"animation timers grew from {baseline} to {after} after 20 reloads — renderer leak"
