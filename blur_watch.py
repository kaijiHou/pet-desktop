"""Click-outside detection for focus-less panels.

The pet's side panels (QuickPanel / PocketWindow / TodayWageWindow) use
WA_ShowWithoutActivating — they must not steal focus from the user's active
application, so Qt never receives the clicks that land on the desktop or
other applications, and activation-based auto-close cannot work for them.

ClickOutsideWatch polls the left-button state instead: on the press→release
edge it evaluates where the click happened. If BOTH press and release were
outside every keep-out rectangle AND no Qt widget sits under the cursor
(i.e. the click landed on the desktop or a foreign application), the
registered callback fires (typically owner.hide()). Clicks on our own
windows (pet, other panels, dialogs) never trigger it — a Qt widget is
under the cursor there.
"""
import ctypes

from PyQt5.QtCore import QObject, QTimer
from PyQt5.QtGui import QCursor
from PyQt5.QtWidgets import QApplication

VK_LBUTTON = 0x01


class ClickOutsideWatch(QObject):
    def __init__(self, owner, keep_out_rects, on_outside, interval_ms=200):
        """owner: watched widget; keep_out_rects: callable -> list[QRect]
        (global coords); on_outside: no-arg callback."""
        super().__init__(owner)
        self.owner = owner
        self._keep_out_rects = keep_out_rects
        self._on_outside = on_outside
        self._timer = QTimer(self)
        self._timer.setInterval(interval_ms)
        self._timer.timeout.connect(self._poll)
        self._press_pos = None

    def start(self):
        self._press_pos = None
        self._timer.start()

    def stop(self):
        self._timer.stop()
        self._press_pos = None

    def _poll(self):
        if not self.owner.isVisible():
            self.stop()
            return
        try:
            pressed = bool(ctypes.windll.user32.GetAsyncKeyState(VK_LBUTTON) & 0x8000)
        except (AttributeError, OSError):
            self.stop()   # non-Windows host: feature unavailable
            return
        pos = QCursor.pos()
        outside = self._is_outside(pos)
        if pressed:
            if self._press_pos is None and outside:
                self._press_pos = pos      # track only presses that start outside
            return
        if self._press_pos is not None:    # release edge
            started_outside = self._is_outside(self._press_pos)
            self._press_pos = None
            if started_outside and outside and self._foreign_surface(pos):
                self.stop()
                self._on_outside()

    def _is_outside(self, pos):
        return not any(rect.contains(pos) for rect in self._keep_out_rects())

    @staticmethod
    def _foreign_surface(pos):
        """True when no widget of ours sits under the cursor (desktop/other app)."""
        return QApplication.widgetAt(pos) is None
