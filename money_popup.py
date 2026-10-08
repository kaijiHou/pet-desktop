"""Floating ¥-amount popup above the pet's head (income notification).

Deliberately a pure QLabel with a QSS chip — no Python paintEvent. A
custom Python paintEvent on a transient translucent top-level is the
re-entrancy crash carrier on real Windows IME hosts (see
bubble_window.py docstring); C++-painted QLabel never crashes there.
"""

from PyQt5.QtCore import Qt, QTimer, QRect
from PyQt5.QtWidgets import QLabel, QApplication


class MoneyPopup(QLabel):
    """Rounded amount chip that drifts up and fades above the pet."""

    STEPS = 60            # 60 × 40ms ≈ 2.4s total life
    HOLD_STEPS = 38       # fully opaque hold before fading
    DRIFT_PX = 34

    def __init__(self):
        super().__init__(None)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Tool | Qt.WindowStaysOnTopHint
                            | Qt.WindowTransparentForInput)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WA_InputMethodEnabled, False)
        self.setAttribute(Qt.WA_QuitOnClose, False)
        self.setFocusPolicy(Qt.NoFocus)
        self.setStyleSheet("""
            background: rgba(43, 44, 48, 232);
            color: #FFD76A;
            font-size: 17pt;
            font-weight: 800;
            padding: 8px 18px;
            border: 1px solid rgba(255, 215, 106, 120);
            border-radius: 14px;
        """)
        self.hide()
        self._step = 0
        self._base_pos = None
        self._timer = QTimer(self)
        self._timer.setInterval(40)
        self._timer.timeout.connect(self._tick)

    def pop(self, text: str, anchor_rect: QRect, screen=None):
        """Show *text* centered above *anchor_rect* (global coords)."""
        self.setText(text)
        self.adjustSize()
        screen = screen or QApplication.screenAt(anchor_rect.center()) or QApplication.primaryScreen()
        avail = screen.availableGeometry()
        x = anchor_rect.center().x() - self.width() // 2
        y = anchor_rect.top() - self.height() - 6
        x = max(avail.left(), min(x, avail.right() - self.width() + 1))
        y = max(avail.top() + 2, y)
        self._base_pos = (x, y)
        self.move(x, y)
        self.setWindowOpacity(1.0)
        self.show()
        self.raise_()
        self._step = 0
        self._timer.start()

    def _tick(self):
        self._step += 1
        if self._step >= self.STEPS:
            self._timer.stop()
            self.hide()
            return
        if self._step > self.HOLD_STEPS:
            fade = 1.0 - (self._step - self.HOLD_STEPS) / (self.STEPS - self.HOLD_STEPS)
            self.setWindowOpacity(max(0.0, fade))
            drift = int(self.DRIFT_PX * (self._step - self.HOLD_STEPS)
                        / (self.STEPS - self.HOLD_STEPS))
            if self._base_pos:
                self.move(self._base_pos[0], self._base_pos[1] - drift)
