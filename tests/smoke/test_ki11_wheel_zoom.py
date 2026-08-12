"""KI-11 fixed regression: native wheel scaling accepts fractional sizes."""

import pytest

from PyQt5.QtCore import Qt, QPoint, QPointF
from PyQt5.QtGui import QWheelEvent


@pytest.mark.smoke
@pytest.mark.gui
def test_wheel_zoom_scales_without_error(pet_window, qapp):
    scale_before = float(pet_window.config.get("pet_scale"))
    wheel = QWheelEvent(
        QPointF(20, 20), QPointF(pet_window.pos() + QPoint(20, 20)),
        QPoint(), QPoint(0, 120), 120, Qt.Vertical,
        Qt.NoButton, Qt.NoModifier,
    )
    pet_window.wheelEvent(wheel)
    assert pet_window.config.get("pet_scale") == round(scale_before + 0.1, 1)
    assert pet_window.width() == int(124 * pet_window.config.get("pet_scale") + 20)
