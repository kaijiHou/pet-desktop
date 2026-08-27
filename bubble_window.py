"""Small non-activating bubble window anchored to the visible pet pixels."""

from PyQt5.QtCore import Qt, QRect, QPoint, QSize
from PyQt5.QtGui import QPainter, QPainterPath, QPen, QFont, QFontMetrics, QColor
from PyQt5.QtWidgets import QWidget, QApplication

import theme


class BubbleWindow(QWidget):
    GAP = 7
    TAIL = 8

    def __init__(self, parent=None):
        super().__init__(None)
        self._text = ""
        self._tail = "down"
        self._anchor = QRect()
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Tool | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.setAttribute(Qt.WA_QuitOnClose, False)
        self.setFocusPolicy(Qt.NoFocus)
        self.hide()

    def set_text(self, text: str):
        self._text = str(text)
        font = QFont("Microsoft YaHei UI", 8)
        fm = QFontMetrics(font)
        max_text_w = 300
        rect = fm.boundingRect(QRect(0, 0, max_text_w, 200),
                               Qt.TextWordWrap | Qt.AlignLeft | Qt.AlignTop, self._text)
        width = min(max_text_w + 20, max(100, rect.width() + 20))
        height = min(170, max(42, rect.height() + 28 + self.TAIL))
        self.setFixedSize(width, height)
        self.update()

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
        x, y, self._tail = chosen
        self.setGeometry(x, y, w, h)
        return self.geometry()

    def paintEvent(self, event):
        if not self._text:
            return
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        margin = 1
        rect = QRect(margin, margin, self.width() - 2, self.height() - 2)
        tail = self.TAIL
        body = QRect(rect)
        if self._tail == "down":
            body.setBottom(body.bottom() - tail)
        elif self._tail == "up":
            body.setTop(body.top() + tail)
        elif self._tail == "left":
            body.setLeft(body.left() + tail)
        else:
            body.setRight(body.right() - tail)
        path = QPainterPath()
        path.addRoundedRect(body, 10, 10)
        cx = body.center().x() if self._tail in {"up", "down"} else body.center().y()
        if self._tail == "down":
            path.moveTo(cx - tail, body.bottom()); path.lineTo(cx, rect.bottom()); path.lineTo(cx + tail, body.bottom())
        elif self._tail == "up":
            path.moveTo(cx - tail, body.top()); path.lineTo(cx, rect.top()); path.lineTo(cx + tail, body.top())
        elif self._tail == "left":
            path.moveTo(body.right(), cx - tail); path.lineTo(rect.right(), cx); path.lineTo(body.right(), cx + tail)
        else:
            path.moveTo(body.left(), cx - tail); path.lineTo(rect.left(), cx); path.lineTo(body.left(), cx + tail)
        path.closeSubpath()
        p.fillPath(path, QColor(255, 255, 255, 242))
        p.setPen(QPen(QColor(theme.BORDER), 1.2)); p.drawPath(path)
        p.setPen(QColor(theme.TEXT)); p.setFont(QFont("Microsoft YaHei UI", 8))
        p.drawText(body.adjusted(9, 7, -9, -6), Qt.TextWordWrap | Qt.AlignLeft | Qt.AlignTop, self._text)
        p.end()

