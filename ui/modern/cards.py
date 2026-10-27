from PyQt5.QtCore import Qt, QSize, QRectF
from PyQt5.QtGui import QPainter, QColor, QPen
from PyQt5.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout, QCheckBox


class Card(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("modernCard")


class StatCard(Card):
    def __init__(self, title: str, value: str = "—", hint: str = "", parent=None):
        super().__init__(parent)
        self.setMinimumHeight(76)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 11, 14, 11)
        self.title = QLabel(title); self.title.setObjectName("muted")
        self.value = QLabel(value); self.value.setStyleSheet("font-size: 19px; font-weight: 700;")
        self.hint = QLabel(hint); self.hint.setObjectName("muted")
        layout.addWidget(self.title); layout.addWidget(self.value)
        if hint: layout.addWidget(self.hint)

    def set_value(self, value: str, hint: str = None):
        self.value.setText(value)
        if hint is not None:
            self.hint.setText(hint)


class SectionTitle(QLabel):
    def __init__(self, text="", parent=None):
        super().__init__(text, parent)
        self.setStyleSheet("font-size: 14px; font-weight: 700; margin-top: 4px;")


class SettingsRow(QFrame):
    """Compact label/control row used inside settings cards."""
    def __init__(self, label, hint="", control=None, parent=None):
        super().__init__(parent)
        self.setObjectName("settingsRow")
        layout = QHBoxLayout(self); layout.setContentsMargins(4, 6, 4, 6); layout.setSpacing(12)
        text = QVBoxLayout(); text.setSpacing(1)
        title = QLabel(label); title.setStyleSheet("font-weight:600;")
        text.addWidget(title)
        if hint:
            sub = QLabel(hint); sub.setObjectName("muted"); sub.setWordWrap(True); text.addWidget(sub)
        layout.addLayout(text, 1)
        if control is not None: layout.addWidget(control)


class SettingsSwitch(QCheckBox):
    """Native checkbox behavior with a larger theme-colored switch surface."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(48, 32)
        self.setCursor(Qt.PointingHandCursor)
        self.setFocusPolicy(Qt.StrongFocus)

    def sizeHint(self):
        return QSize(48, 32)

    def hitButton(self, pos):
        return self.rect().contains(pos)

    def paintEvent(self, event):
        from . import tokens
        painter = QPainter(self); painter.setRenderHint(QPainter.Antialiasing)
        track = QRectF(3, 4, 42, 24)
        painter.setPen(QPen(QColor(tokens.PRIMARY if self.isChecked() else tokens.SURFACE_BORDER), 1.3))
        painter.setBrush(QColor(tokens.PRIMARY if self.isChecked() else tokens.SURFACE))
        painter.drawRoundedRect(track, 12, 12)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(tokens.ACTION_TEXT if self.isChecked() else tokens.MUTED))
        painter.drawEllipse(QRectF(25 if self.isChecked() else 7, 8, 16, 16))
        if self.hasFocus():
            painter.setBrush(Qt.NoBrush); painter.setPen(QPen(QColor(tokens.FOCUS_RING), 1, Qt.DashLine))
            painter.drawRoundedRect(QRectF(1, 2, 46, 28), 14, 14)


class ToggleRow(SettingsRow):
    def __init__(self, label, checked=False, hint="", parent=None):
        self.toggle = SettingsSwitch(); self.toggle.setChecked(checked)
        self.toggle.setAccessibleName(label)
        super().__init__(label, hint, self.toggle, parent)
