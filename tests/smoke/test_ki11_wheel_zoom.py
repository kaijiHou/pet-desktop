"""KI-11 regression/characterization test (Phase 2).

Upstream bug (docs/KNOWN_ISSUES.md KI-11):
  pet_window_web.PetWindow.wheelEvent computes
      w, h = 124 * self._scale_val + 20, 93 * self._scale_val + 20
  and passes the FLOAT results to self.web.setGeometry(...). PyQt5 rejects
  float arguments -> TypeError on the first wheel event (scale becomes 3.5).

Phase 2 does NOT fix this (out of scope). This test pins the expected
correct behavior and is marked xfail(strict=True):
  * Reproduces deterministically today  -> XFAIL (suite stays clean).
  * If the bug is ever fixed, the test XPASSes and strict=True FAILS the
    suite, forcing us to remove the xfail marker and update the docs.
Reproduction method mirrors scripts/smoke_baseline.py (the only recorded
FAIL in the Phase 1 baseline, stably re-verified).
"""

import pytest

from PyQt5.QtCore import Qt, QPoint, QPointF
from PyQt5.QtGui import QWheelEvent


@pytest.mark.smoke
@pytest.mark.gui
@pytest.mark.baseline
@pytest.mark.xfail(
    strict=True,
    reason="KI-11: wheelEvent passes float 124*scale to QWebEngineView.setGeometry -> TypeError (upstream bug, deliberately NOT fixed in Phase 2)",
)
def test_wheel_zoom_scales_without_error(pet_window, qapp):
    scale_before = pet_window._scale_val

    wheel = QWheelEvent(
        QPointF(20, 20),
        QPointF(pet_window.pos() + QPoint(20, 20)),
        QPoint(0, 0), QPoint(0, 120), 120, Qt.Vertical,
        Qt.NoButton, Qt.NoModifier,
    )

    pet_window.wheelEvent(wheel)  # raises TypeError today (KI-11)

    assert pet_window._scale_val == scale_before + 0.5
    assert pet_window.width() == int(124 * pet_window._scale_val + 20)
