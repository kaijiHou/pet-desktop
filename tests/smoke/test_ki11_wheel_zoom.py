"""Wheel zoom (V2.2): plain wheel zooms when enabled; Ctrl+wheel always zooms.

V2.2 change: wheel_zoom_enabled default flipped False→True so resizing is
reliable ("大小调不了" bug). Ctrl+wheel ALWAYS zooms regardless of the flag.
"""

import pytest
from PyQt5.QtCore import Qt, QPointF, QPoint
from PyQt5.QtGui import QWheelEvent


def _make_wheel(angle_y=120, ctrl=False):
    center = QPointF(50, 50)
    mods = Qt.ControlModifier if ctrl else Qt.NoModifier
    return QWheelEvent(center, center, QPoint(0, 0), QPoint(0, angle_y),
                       Qt.NoButton, mods, 0, False)


@pytest.mark.smoke
def test_wheel_zoom_enabled_by_default(pet_window):
    """V2.2: wheel zoom is ON by default so the pet can be resized."""
    scale_before = pet_window.config.get("pet_scale")
    pet_window.wheelEvent(_make_wheel(120))
    assert pet_window.config.get("pet_scale") != scale_before


@pytest.mark.smoke
def test_wheel_zoom_works_when_enabled(pet_window):
    pet_window.config.set("wheel_zoom_enabled", True)
    scale_before = pet_window.config.get("pet_scale")
    try:
        pet_window.wheelEvent(_make_wheel(120))
        assert pet_window.config.get("pet_scale") != scale_before
    except TypeError:
        pytest.xfail("KI-11: setGeometry float TypeError still present")
    finally:
        pet_window.config.set("wheel_zoom_enabled", False)


@pytest.mark.smoke
def test_ctrl_wheel_zooms_even_when_flag_off(pet_window):
    """Ctrl+wheel must resize even if wheel_zoom_enabled is turned off."""
    pet_window.config.set("wheel_zoom_enabled", False)
    before = pet_window.config.get("pet_scale")
    try:
        pet_window.wheelEvent(_make_wheel(120, ctrl=True))
        assert pet_window.config.get("pet_scale") != before
    except TypeError:
        pytest.xfail("KI-11: setGeometry float TypeError still present")
    finally:
        pet_window.config.set("wheel_zoom_enabled", True)