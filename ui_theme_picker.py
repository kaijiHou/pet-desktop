"""V5.10 主题中心 — preview-card grid + live skin switching.

Reuses the single ui_skin architecture (no second theme manager): every card
renders its theme's real palette (and illustration assets when the theme has
them), clicking a card calls ui_skin.set_skin() which persists and re-skins
the whole app. Zero paintEvent — QLabel/QSS only (IME red line).
"""

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPixmap
from PyQt5.QtWidgets import (QFrame, QGridLayout, QHBoxLayout, QLabel,
                             QPushButton, QVBoxLayout, QWidget)

import ui_skin
from ui.modern.dialog import ModernDialog


def _fill_pixmap(path, width: int, height: int):
    """Cover-scale a theme illustration into a fixed box (center-crop)."""
    src = QPixmap(str(path))
    if src.isNull() or width <= 0 or height <= 0:
        return QPixmap()
    scaled = src.scaled(width, height, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
    return scaled.copy((scaled.width() - width) // 2, (scaled.height() - height) // 2,
                       width, height)


def _card_qss(p: dict, selected: bool) -> str:
    border = p["accent"] if selected else p["border"]
    width = 2 if selected else 1
    return f"""
        QFrame#themeCard {{ background: {p['card']}; border: {width}px solid {border}; border-radius: 14px; }}
        QFrame#tcHero {{ border: none; border-radius: 9px; }}
        QLabel#tcHeroArt {{ border: none; }}
        QFrame#tcHeroWash {{ background: qlineargradient(x1:0 y1:0, x2:1 y2:1, stop:0 {p['hero_top']}, stop:1 {p['hero_bottom']}); border: 1px solid {p['section_border']}; border-radius: 9px; }}
        QLabel#tcName {{ color: {p['text']}; font-weight: 700; font-size: 10pt; background: transparent; border: none; }}
        QLabel#tcBadge {{ background: {p['accent']}; color: {p['action_text']}; border: none; border-radius: 8px; padding: 1px 8px; font-size: 8pt; font-weight: 700; }}
    """


class ThemeCard(QFrame):
    """One theme preview: hero art (or palette wash) + name row; click applies."""

    def __init__(self, skin_id, name, colors, active, on_pick, parent=None):
        super().__init__(parent)
        self.skin_id = skin_id
        self._on_pick = on_pick
        self.setObjectName("themeCard")
        p = ui_skin.resolve_palette(colors)
        self.setStyleSheet(_card_qss(p, active))
        self.setCursor(Qt.PointingHandCursor)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(10, 9, 10, 9)
        lay.setSpacing(7)

        hero = QFrame(); hero.setObjectName("tcHero"); hero.setFixedSize(148, 58)
        hero_grid = QGridLayout(hero); hero_grid.setContentsMargins(0, 0, 0, 0); hero_grid.setSpacing(0)
        hero_art = ui_skin.theme_asset("hero_scene", skin_id)
        if hero_art is not None:
            art = QLabel(); art.setObjectName("tcHeroArt")
            art.setPixmap(_fill_pixmap(hero_art, 148, 58))
            art.setScaledContents(True)
            art.setFixedSize(148, 58)
            art.setStyleSheet(f"border-radius: 9px; background: {p['bg']};")
            hero_grid.addWidget(art, 0, 0)
        else:
            wash = QFrame(); wash.setObjectName("tcHeroWash"); wash.setFixedSize(148, 58)
            hero_grid.addWidget(wash, 0, 0)
        lay.addWidget(hero, 0, Qt.AlignHCenter)

        head = QHBoxLayout(); head.setSpacing(5)
        name_lbl = QLabel(f"{p['deco']} {name}"); name_lbl.setObjectName("tcName")
        head.addWidget(name_lbl); head.addStretch()
        if active:
            badge = QLabel("✓ 当前"); badge.setObjectName("tcBadge")
            head.addWidget(badge)
        lay.addLayout(head)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._on_pick(self.skin_id)
        super().mousePressEvent(event)


class ThemePickerDialog(ModernDialog):
    """🎨 主题中心 — 预览卡网格（预设 + 自定义），点卡片立即切换并记住。"""

    def __init__(self, parent=None):
        super().__init__("主题中心", "点击卡片立即切换，重启后记住", parent, min_width=600)
        self.grid_host = QWidget(); self.grid_host.setStyleSheet("background: transparent;")
        self.grid = QGridLayout(self.grid_host); self.grid.setContentsMargins(0, 2, 0, 0)
        self.grid.setHorizontalSpacing(10); self.grid.setVerticalSpacing(10)
        self.add_body(self.grid_host)
        self.add_footer(self._footer_note())
        self._rebuild_grid()

    def _footer_note(self):
        from ui.modern.buttons import SecondaryButton
        note = QLabel("自定义皮肤保存在 data/ui_skins.json"); note.setObjectName("muted")
        custom_btn = SecondaryButton("➕ 自定义皮肤…")
        custom_btn.clicked.connect(self._open_custom_editor)
        wrap = QWidget(); wrap.setStyleSheet("background: transparent;")
        lay = QHBoxLayout(wrap); lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(note); lay.addStretch(); lay.addWidget(custom_btn)
        return wrap

    def _open_custom_editor(self):
        from ui_skin_dialog import SkinEditorDialog
        dlg = SkinEditorDialog(self)
        if dlg.exec_() == ModernDialog.Accepted and dlg.saved_id:
            ui_skin.set_skin(dlg.saved_id)
            self._rebuild_grid()

    def _rebuild_grid(self):
        active = ui_skin.active_id()
        while self.grid.count():
            item = self.grid.takeAt(0)
            if item.widget():
                item.widget().hide(); item.widget().deleteLater()
        entries = list(ui_skin.PRESETS.items()) + list(ui_skin._load_custom_skins().items())
        for index, (skin_id, (name, colors)) in enumerate(entries):
            card = ThemeCard(skin_id, name, colors, skin_id == active, self._pick)
            card.setFixedSize(168, 104)
            self.grid.addWidget(card, index // 3, index % 3)

    def _pick(self, skin_id):
        if ui_skin.set_skin(skin_id):
            self._rebuild_grid()
