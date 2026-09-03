from PyQt5.QtCore import QTime
from PyQt5.QtWidgets import QComboBox, QLineEdit, QTimeEdit


class ModernLineEdit(QLineEdit):
    pass


class ModernComboBox(QComboBox):
    pass


class ModernTimeField(QTimeEdit):
    def __init__(self, value=None, parent=None):
        super().__init__(parent)
        self.setDisplayFormat("HH:mm")
        self.setTime(value if isinstance(value, QTime) else QTime(9, 0))
