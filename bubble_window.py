"""Small non-activating bubble window anchored to the visible pet pixels.

Render model (V3.1): a pure QLabel showing a pre-rendered pixmap — the
class has NO Python paintEvent.

Why: on real Windows hosts, running a Python-level paintEvent on a
transient translucent frameless Qt.Tool top-level can be re-entered by
IME/CTF messages (Sogou/msctf/textinputframework seen in crash dumps)
and hard-fails inside Qt5Core (0xC0000409) while the sip→Python paint
frame is on the stack, killing the whole pet process the first time a
bubble shows. Across A/B batches on the affected machine, every variant
with a custom Python paintEvent crashed during bad IME states while the
pure QLabel (C++-painted) variant never crashed. So the bubble body is
painted once into a QImage raster (safe — QPainter-on-image never
crashed) and the window only blits it through QLabel's native painting.

The window is also input-transparent: it must never swallow wheel/mouse
events aimed at the pet (V3.1 scale Case 1) and never needs an IME
context of its own.
"""

from PyQt5.QtCore import Qt, QRect, QRectF
from PyQt5.QtGui import QPainter, QPainterPath, QPen, QFont, QFontMetrics, QColor, QImage
from PyQt5.QtWidgets import QLabel, QApplication

import theme


class BubbleWindow(QLabel):
    GAP = 7
    TAIL = 8

    def __init__(self, parent=None):
        super().__init__(None)
        self._text = ""
        self._tail = "down"
        self._anchor = QRect()
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Tool | Qt.WindowStaysOnTopHint
                            | Qt.WindowTransparentForInput)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WA_InputMethodEnabled, False)
        self.setAttribute(Qt.WA_QuitOnClose, False)
        self.setFocusPolicy(Qt.NoFocus)
        self.hide()

    # ── content ──
    def set_text(self, text: str):
        self._text = str(text)
        font = QFont("Microsoft YaHei UI", 8)
        fm = QFontMetrics(font)
        max_text_w = 300
        rect = fm.boundingRect(QRect(0, 0, max_text_w, 200),
                               Qt.TextWordWrap | Qt.AlignLeft | Qt.AlignTop, self._text)
        width = min(max_text_w + 20, max(100, rect.width() + 20))
        height = min(170, max(42, rect.height() + 28 + self.TAIL))
        self.setPixmap(self._render(width, height, self._tail))
        self.setFixedSize(width, height)

    def _render(self, w: int, h: int, tail: str):
        """Paint the whole bubble into an offscreen raster (IME-safe)."""
        img = QImage(w, h, QImage.Format_ARGB32_Premultiplied)
        img.fill(Qt.transparent)
        p = QPainter(img)
        p.setRenderHint(QPainter.Antialiasing)
        margin = 1
        rect = QRect(margin, margin, w - 2, h - 2)
        tail_len = self.TAIL
        body = QRect(rect)
        if tail == "down":
            body.setBottom(body.bottom() - tail_len)
        elif tail == "up":
            body.setTop(body.top() + tail_len)
        elif tail == "left":
            body.setLeft(body.left() + tail_len)
        else:
            body.setRight(body.right() - tail_len)
        path = QPainterPath()
        path.addRoundedRect(QRectF(body), 10, 10)
        cx = body.center().x() if tail in {"up", "down"} else body.center().y()
        if tail == "down":
            path.moveTo(cx - tail_len, body.bottom()); path.lineTo(cx, rect.bottom()); path.lineTo(cx + tail_len, body.bottom())
        elif tail == "up":
            path.moveTo(cx - tail_len, body.top()); path.lineTo(cx, rect.top()); path.lineTo(cx + tail_len, body.top())
        elif tail == "left":
            path.moveTo(body.right(), cx - tail_len); path.lineTo(rect.right(), cx); path.lineTo(body.right(), cx + tail_len)
        else:
            path.moveTo(body.left(), cx - tail_len); path.lineTo(rect.left(), cx); path.lineTo(body.left(), cx + tail_len)
        path.closeSubpath()
        p.fillPath(path, QColor(255, 255, 255, 242))
        p.setPen(QPen(QColor(theme.BORDER), 1.2)); p.drawPath(path)
        p.setPen(QColor(theme.TEXT)); p.setFont(QFont("Microsoft YaHei UI", 8))
        p.drawText(body.adjusted(9, 7, -9, -6), Qt.TextWordWrap | Qt.AlignLeft | Qt.AlignTop, self._text)
        p.end()
        from PyQt5.QtGui import QPixmap
        return QPixmap.fromImage(img)

    # ── placement ──
    def place_near(self, anchor: QRect, screen=None):
        """Place next to *anchor* while staying in availableGeometry."""
        self._anchor = QRect(anchor)
        screen = screen or QApplication.screenAt(anchor.center()) or QApplication.primaryScreen()
        avail = screen.availableGeometry()
        w, h = self.width(), self.height()
        candidates = [
            (anchor.left() + (anchor.width() - w) // 2, anchor.top() - h - self.GAP, "down"),
            (anchor.left() + (anchor.width() - w) // 2, anchor.bottom() + self.GAP, "up"),
            (anchor.right() + self.GAP, anchor.top() + (anchor.height() - h) // 2, "left"),
            (anchor.left() - w - self.GAP, anchor.top() + (anchor.height() - h) // 2, "right"),
        ]
        chosen = None
        for x, y, tail in candidates:
            if (x >= avail.left() and y >= avail.top()
                    and x + w - 1 <= avail.right() and y + h - 1 <= avail.bottom()):
                chosen = (x, y, tail)
                break
        if chosen is None:
            x = max(avail.left(), min(candidates[0][0], avail.right() - w + 1))
            y = max(avail.top(), min(candidates[0][1], avail.bottom() - h + 1))
            chosen = (x, y, candidates[0][2])
        x, y, new_tail = chosen
        if new_tail != self._tail:
            self._tail = new_tail
            self.setPixmap(self._render(w, h, new_tail))
        self.setGeometry(x, y, w, h)
        return self.geometry()
