from PyQt5.QtCore import Qt
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
        layout = QHBoxLayout(self); layout.setContentsMargins(0, 5, 0, 5); layout.setSpacing(12)
        text = QVBoxLayout(); text.setSpacing(1)
        title = QLabel(label); title.setStyleSheet("font-weight:600;")
        text.addWidget(title)
        if hint:
            sub = QLabel(hint); sub.setObjectName("muted"); sub.setWordWrap(True); text.addWidget(sub)
        layout.addLayout(text, 1)
        if control is not None: layout.addWidget(control)


class ToggleRow(SettingsRow):
    def __init__(self, label, checked=False, hint="", parent=None):
        self.toggle = QCheckBox(); self.toggle.setChecked(checked)
        super().__init__(label, hint, self.toggle, parent)
