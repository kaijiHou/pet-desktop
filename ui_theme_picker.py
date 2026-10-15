"""V5.8 主题中心 — category tabs + preview cards + live skin switching.

Reuses the single ui_skin architecture (no second theme manager): every card
renders a mini mockup from that skin's resolved palette, clicking a card calls
ui_skin.set_skin() which persists and re-skins the whole app. Zero
paintEvent — translucent frameless surfaces stay QLabel/QSS only (IME red line).
"""

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (QFrame, QGridLayout, QHBoxLayout, QLabel,
                             QPushButton, QVBoxLayout, QWidget)

import ui_skin
from ui.modern.dialog import ModernDialog

CATEGORY_LABELS = (("cute", "🌸 可爱"), ("cool", "⚡ 炫酷"))


def _fill_pixmap(path, width: int, height: int):
    """Cover-scale a theme illustration into a fixed box (center-crop)."""
    from PyQt5.QtGui import QPixmap
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
        QFrame#themeCard {{ background: {p['bg']}; border: {width}px solid {border}; border-radius: 14px; }}
        QLabel#tcName {{ color: {p['text']}; font-weight: 700; font-size: 10pt; background: transparent; border: none; }}
        QLabel#tcBadge {{ background: {p['section_bg']}; color: {p['amount']}; border: 1px solid {p['section_border']}; border-radius: 8px; padding: 1px 7px; font-size: 8pt; font-weight: 700; }}
        QFrame#tcHero {{ background: qlineargradient(x1:0 y1:0, x2:1 y2:1, stop:0 {p['hero_top']}, stop:1 {p['hero_bottom']}); border: 1px solid {p['section_border']}; border-radius: 9px; }}
        QLabel#tcAmount {{ color: {p['amount']}; font-size: 11pt; font-weight: 700; background: transparent; border: none; }}
        QLabel#tcChip {{ background: {p['chip']}; border: 1px solid {p['tint_border']}; border-radius: 7px; padding: 2px 6px; font-size: 8pt; color: {p['text']}; }}
        QPushButton#tcPrimary {{ background: {p['action_bg']}; color: {p['action_text']}; border: none; border-radius: 8px; padding: 3px 8px; font-size: 8pt; font-weight: 600; }}
        QPushButton#tcSecondary {{ background: {p['chip']}; color: {p['text']}; border: 1px solid {p['secondary_border']}; border-radius: 8px; padding: 3px 8px; font-size: 8pt; }}
    """


class ThemeCard(QFrame):
    """Mini mockup of one skin; clicking applies it (real switch, persisted)."""

    def __init__(self, skin_id, name, colors, active, on_pick, parent=None):
        super().__init__(parent)
        self.skin_id = skin_id
        self._on_pick = on_pick
        self.setObjectName("themeCard")
        p = ui_skin.resolve_palette(colors)
        self.setStyleSheet(_card_qss(p, active))
        self.setCursor(Qt.PointingHandCursor)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(10, 8, 10, 9)
        lay.setSpacing(5)
        head = QHBoxLayout(); head.setSpacing(4)
        name_lbl = QLabel(f"{p['deco']} {name}"); name_lbl.setObjectName("tcName")
        head.addWidget(name_lbl); head.addStretch()
        if active:
            badge = QLabel("✓"); badge.setObjectName("tcBadge")
            head.addWidget(badge)
        lay.addLayout(head)
        hero = QFrame(); hero.setObjectName("tcHero")
        hero_grid = QGridLayout(hero); hero_grid.setContentsMargins(0, 0, 0, 0); hero_grid.setSpacing(0)
        hero_lay = QVBoxLayout(); hero_lay.setContentsMargins(8, 4, 8, 5); hero_lay.setSpacing(0)
        hero_art = ui_skin.theme_asset("hero_scene", skin_id)
        if hero_art is not None:
            art = QLabel(); art.setFixedSize(112, 44)
            art.setPixmap(_fill_pixmap(hero_art, 112, 44))
            art.setStyleSheet("background: transparent; border: none;")
            hero_grid.addWidget(art, 0, 0)
            hero_grid.addLayout(hero_lay, 0, 0)
        else:
            hero_grid.addLayout(hero_lay, 0, 0)
        status = QLabel("工作中"); status.setStyleSheet(f"color:{p['text_soft']};font-size:7pt;background:transparent;border:none;")
        amount = QLabel("¥757.34"); amount.setObjectName("tcAmount")
        hero_lay.addWidget(status); hero_lay.addWidget(amount)
        lay.addWidget(hero)
        pills = QHBoxLayout(); pills.setSpacing(4)
        primary = QPushButton("下班打卡"); primary.setObjectName("tcPrimary")
        secondary = QPushButton("日历"); secondary.setObjectName("tcSecondary")
        pills.addWidget(primary); pills.addWidget(secondary)
        lay.addLayout(pills)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._on_pick(self.skin_id)
        super().mousePressEvent(event)


class ThemePickerDialog(ModernDialog):
    """🎨 主题中心 — 可爱/炫酷(/自定义) 页签 + 预览卡网格 + 当前选中态。"""

    def __init__(self, parent=None):
        super().__init__("主题中心", "17 套主题 · 点卡片立即切换，重启后记住", parent, min_width=620)
        customs = ui_skin._load_custom_skins()
        self._categories = list(CATEGORY_LABELS)
        if customs:
            self._categories.append(("custom", "🧵 自定义"))
        self.tab_buttons = {}
        tab_row = QHBoxLayout(); tab_row.setSpacing(6)
        for key, label in self._categories:
            btn = QPushButton(label); btn.setCheckable(True); btn.setObjectName("categoryTab"); btn.setCursor(Qt.PointingHandCursor)
            btn.clicked.connect(lambda _checked=False, k=key: self._show_category(k))
            self.tab_buttons[key] = btn
            tab_row.addWidget(btn)
        tab_row.addStretch()
        self.add_body(_layout_widget(tab_row))
        self.setStyleSheet(self.styleSheet() + """
            QPushButton#categoryTab { border-radius: 13px; padding: 5px 16px; font-weight: 600; }
            QPushButton#categoryTab:checked { background: {PRIMARY}; color: {ACTION_TEXT}; }
        """.replace("{PRIMARY}", ui_skin.palette()["action_bg"]).replace("{ACTION_TEXT}", ui_skin.palette()["action_text"]))
        self.grid_host = QWidget(); self.grid_host.setStyleSheet("background: transparent;")
        self.grid = QGridLayout(self.grid_host); self.grid.setContentsMargins(0, 2, 0, 0)
        self.grid.setHorizontalSpacing(8); self.grid.setVerticalSpacing(8)
        self.add_body(self.grid_host)
        self.add_footer(self._footer_note())
        self._show_category(ui_skin.category_of(ui_skin.active_id()))

    def _footer_note(self):
        from ui.modern.buttons import SecondaryButton
        note = QLabel("皮肤文件保存在 data/ui_skins.json"); note.setObjectName("muted")
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
            self._show_category("custom" if "custom" in self.tab_buttons else self._cat)

    def _show_category(self, key):
        self._current_cat = key
        for k, btn in self.tab_buttons.items():
            btn.setChecked(k == key)
        while self.grid.count():
            item = self.grid.takeAt(0)
            if item.widget():
                item.widget().hide(); item.widget().deleteLater()
        active = ui_skin.active_id()
        if key == "custom":
            entries = list(ui_skin._load_custom_skins().items())
        else:
            entries = list(ui_skin.skins_by_category(key).items())
        for index, (skin_id, (name, colors)) in enumerate(entries):
            card = ThemeCard(skin_id, name, colors, skin_id == active, self._pick)
            card.setFixedSize(132, 128)
            self.grid.addWidget(card, index // 4, index % 4)

    def _pick(self, skin_id):
        if ui_skin.set_skin(skin_id):
            # restyle every card against the new active marker + app QSS
            self._show_category(self._current_cat)


def _layout_widget(layout):
    widget = QWidget(); widget.setLayout(layout); return widget
