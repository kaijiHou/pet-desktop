from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout


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
