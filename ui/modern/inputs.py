from PyQt5.QtCore import QTime
from PyQt5.QtWidgets import QComboBox, QLineEdit, QTimeEdit, QDoubleSpinBox, QAbstractSpinBox


class ModernLineEdit(QLineEdit):
    pass


class ModernComboBox(QComboBox):
    pass


class ModernTimeField(QTimeEdit):
    def __init__(self, value=None, parent=None):
        super().__init__(parent)
        self.setDisplayFormat("HH:mm")
        self.setTime(value if isinstance(value, QTime) else QTime(9, 0))
        self.setButtonSymbols(QAbstractSpinBox.NoButtons)
        self.setMinimumHeight(38)


class ModernMoneyField(QDoubleSpinBox):
    def __init__(self, value=0.0, parent=None):
        super().__init__(parent)
        self.setRange(0, 99999999); self.setDecimals(2); self.setValue(float(value))
        self.setSuffix(" 元/月"); self.setButtonSymbols(QAbstractSpinBox.NoButtons); self.setMinimumHeight(38)


class ModernSelect(ModernComboBox):
    def __init__(self, parent=None):
        super().__init__(parent); self.setMinimumHeight(38)
