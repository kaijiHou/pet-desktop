"""Custom skin editor: pick a name, an accent and a backdrop colour."""

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import (QColorDialog, QHBoxLayout, QLabel, QLineEdit,
                             QPushButton, QVBoxLayout, QWidget)

from ui.modern.buttons import PrimaryButton, SecondaryButton
from ui.modern.dialog import ModernDialog
from ui.modern.inputs import ModernLineEdit
import ui_skin


class SkinEditorDialog(ModernDialog):
    """➕ 自定义皮肤 — 名称 + 强调色 + 背景色，其余颜色自动调配。"""

    def __init__(self, parent=None):
        super().__init__("自定义皮肤", "选一个强调色和底色，其余自动搭配", parent, min_width=380)
        self.saved_id = None

        lay = self.body
        lay.addWidget(QLabel("皮肤名称"))
        self.name_edit = ModernLineEdit()
        self.name_edit.setPlaceholderText("比如：蜜桃乌龙")
        lay.addWidget(self.name_edit)

        accent_row = QHBoxLayout()
        accent_row.addWidget(QLabel("强调色"))
        self.accent_hex = "#F27BA7"
        self.accent_btn = QPushButton(self.accent_hex.upper())
        self.accent_btn.clicked.connect(lambda: self._pick("accent"))
        accent_row.addWidget(self.accent_btn)
        accent_row.addStretch()
        lay.addLayout(accent_row)

        bg_row = QHBoxLayout()
        bg_row.addWidget(QLabel("底色"))
        self.bg_hex = "#FFF6FA"
        self.bg_btn = QPushButton(self.bg_hex.upper())
        self.bg_btn.clicked.connect(lambda: self._pick("bg"))
        bg_row.addWidget(self.bg_btn)
        bg_row.addStretch()
        lay.addLayout(bg_row)

        self.preview = QWidget()
        self.preview.setFixedHeight(64)
        self._paint_preview()
        lay.addWidget(self.preview)

        cancel = SecondaryButton("取消")
        cancel.clicked.connect(self.reject)
        save = PrimaryButton("保存并使用")
        save.clicked.connect(self._save)
        self.add_footer(cancel)
        self.add_footer(save)

    def _pick(self, which):
        current = getattr(self, f"{which}_hex")
        color = QColorDialog.getColor(QColor(current), self, "选择颜色")
        if not color.isValid():
            return
        setattr(self, f"{which}_hex", color.name())
        getattr(self, f"{which}_btn").setText(color.name().upper())
        self._paint_preview()

    def _paint_preview(self):
        colors = ui_skin.build_custom_colors(self.accent_hex, self.bg_hex)
        self.preview.setStyleSheet(
            f"background: {colors['menu_bg']}; border: 1px solid {colors['menu_border']};"
            f" border-radius: 10px;")
        self.preview_layout = colors

    def _save(self):
        name = self.name_edit.text().strip() or "我的皮肤"
        colors = ui_skin.build_custom_colors(self.accent_hex, self.bg_hex)
        self.saved_id = ui_skin.save_custom_skin(name, colors)
        self.accept()
