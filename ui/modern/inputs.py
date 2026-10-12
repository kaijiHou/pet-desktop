from PyQt5.QtCore import QTime
from PyQt5.QtWidgets import QComboBox, QLineEdit, QTimeEdit, QDoubleSpinBox, QAbstractSpinBox


class ModernLineEdit(QLineEdit):
    pass


class ModernComboBox(QComboBox):
    """QComboBox whose popup view is styled from the CURRENT tokens.

    The dropdown list is a popup whose parent chain carries the dialog
    stylesheet, but Windows dark-app-mode theming can still paint it raw
    black — nailing the palette onto the view itself is the reliable fix.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setView(__import__("PyQt5.QtWidgets", fromlist=["QListView"]).QListView(self))

    def showPopup(self):
        from ui.modern import tokens
        view = self.view()
        view.setStyleSheet(
            f"QAbstractItemView {{ background: {tokens.CARD}; color: {tokens.TEXT};"
            f" border: 1px solid {tokens.BORDER}; border-radius: 10px;"
            f" selection-background-color: {tokens.PRIMARY}; selection-color: white;"
            f" outline: none; padding: 4px; }}"
            f"QAbstractItemView::item {{ min-height: 30px; border-radius: 6px; padding: 2px 8px; }}"
            f"QAbstractItemView::item:hover {{ background: {tokens.PRIMARY}; color: white; }}"
            f"QAbstractItemView::item:selected {{ background: {tokens.PRIMARY}; color: white; }}"
        )
        super().showPopup()


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
