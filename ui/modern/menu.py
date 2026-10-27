"""Native Qt menus with a rounded window shape and theme-owned colors."""

from PyQt5.QtCore import Qt, QRectF
from PyQt5.QtGui import QPainterPath, QRegion
from PyQt5.QtWidgets import QMenu

import ui_skin


class RoundedMenu(QMenu):
    RADIUS = 12

    def __init__(self, *args):
        super().__init__(*args)
        self.setWindowFlags(self.windowFlags() | Qt.FramelessWindowHint | Qt.NoDropShadowWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self._apply_skin()

    def _apply_skin(self):
        p = ui_skin.palette()
        self.setStyleSheet(f"""
            QMenu {{ background: {p['menu_bg']}; color: {p['text']};
                     border: 1px solid {p['menu_border']}; border-radius: 12px;
                     padding: 5px; min-width: 160px; font-size: 10pt; }}
            QMenu::item {{ padding: 2px 10px; margin: 0; border: 1px solid transparent; border-radius: 7px; font-size: 10pt; }}
            QMenu::item:selected {{ background: {p['menu_highlight']}; color: {p['text']}; border-color: {p['menu_border']}; }}
            QMenu::item:disabled {{ color: {p['muted']}; }}
            QMenu::separator {{ height: 1px; background: {p['menu_border']}; margin: 3px 8px; }}
        """)

    def addMenu(self, *args):
        if len(args) == 1 and isinstance(args[0], str):
            submenu = RoundedMenu(args[0], self)
            super().addMenu(submenu)
            return submenu
        return super().addMenu(*args)

    def _update_mask(self):
        path = QPainterPath()
        path.addRoundedRect(QRectF(self.rect()), self.RADIUS, self.RADIUS)
        self.setMask(QRegion(path.toFillPolygon().toPolygon()))

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._update_mask()

    def showEvent(self, event):
        self._apply_skin()
        super().showEvent(event)
        self._update_mask()
