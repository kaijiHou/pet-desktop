from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout


class InlineBanner(QFrame):
    """Non-blocking status/warning banner; safe for startup and tests."""
    def __init__(self, text="", level="info", parent=None):
        super().__init__(parent)
        self.setObjectName("inlineBanner")
        self.label = QLabel(text); self.label.setWordWrap(True)
        layout = QHBoxLayout(self); layout.setContentsMargins(10, 7, 10, 7); layout.addWidget(self.label)
        self.set_level(level)

    def set_level(self, level):
        colors = {"warning": ("#fff7ed", "#c2410c"), "success": ("#ecfdf5", "#047857"), "info": ("#eff6ff", "#1d4ed8")}
        bg, fg = colors.get(level, colors["info"])
        self.setStyleSheet(f"QFrame#inlineBanner{{background:{bg};border-radius:8px;}} QLabel{{color:{fg};}}")


class Toast(QLabel):
    """Tiny transient message, intentionally parented to its dialog."""
    def __init__(self, text="", parent=None, timeout=2800):
        super().__init__(text, parent)
        self.setStyleSheet("background:#111827;color:white;border-radius:8px;padding:8px 12px;")
        self.setWindowFlags(self.windowFlags() | 0x00080000)  # Qt.Tool
        self.adjustSize()
        if parent is not None:
            self.move(max(8, parent.width() - self.width() - 18), max(8, parent.height() - self.height() - 18))
        self.show()
        QTimer.singleShot(timeout, self.deleteLater)
