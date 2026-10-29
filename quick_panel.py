"""Today's assistant panel: wage snapshot first, pocket and reminders below."""

from pathlib import Path

from PyQt5.QtCore import Qt, QTimer, QEvent, QUrl, QFileInfo, QSize
from PyQt5.QtGui import QDesktopServices, QFontMetrics, QPixmap, QIcon
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QPushButton, QFrame,
    QApplication, QToolButton, QFileIconProvider, QMenu, QFileDialog, QLineEdit,
    QSizePolicy, QScrollArea,
)
from destinations import DestinationService, display_default_name
from ui.modern.dialog import ModernDialog
from ui.modern.message import InlineBanner
import theme
import ui_skin
from blur_watch import ClickOutsideWatch


def _fill_pixmap(path, width: int, height: int) -> QPixmap:
    """Scale an image to COVER the box, center-cropped (hero/banner layers)."""
    src = QPixmap(str(path))
    if src.isNull() or width <= 0 or height <= 0:
        return QPixmap()
    scaled = src.scaled(width, height, Qt.KeepAspectRatioByExpanding,
                        Qt.SmoothTransformation)
    x = max(0, (scaled.width() - width) // 2)
    y = max(0, (scaled.height() - height) // 2)
    return scaled.copy(x, y, width, height)


def _fit_pixmap(path, size: int) -> QPixmap:
    src = QPixmap(str(path))
    if src.isNull():
        return QPixmap()
    return src.scaled(size, size, Qt.KeepAspectRatio, Qt.SmoothTransformation)


def _skin_icon(name: str) -> QIcon:
    """Theme-sheet icon (e.g. 'icons/clock'); empty QIcon when skin has none."""
    path = ui_skin.theme_asset(f"icons/{name}")
    if path is None:
        return QIcon()
    pm = _fit_pixmap(path, 48)
    return QIcon() if pm.isNull() else QIcon(pm)


def _panel_qss(p: dict) -> str:
    """Assistant-panel stylesheet derived from the active skin palette.

    V5.8: wage card is a gradient hero card with a status chip and a theme
    decoration; buttons are pills; sections are separated by whitespace and
    chip rows instead of hairlines (per the reference pack)."""
    return f"""
        QFrame#card {{ background: {p['card']}; border: 1px solid {p['border']}; border-radius: 20px; }}
        QLabel#panelHeading {{ color: {p['text']}; font-size: 11pt; font-weight: 700; }}
        QLabel#panelCaption {{ color: {p['muted']}; font-size: 8pt; }}
        QLabel#panelSectionTitle {{ color: {p['text']}; font-size: 10pt; font-weight: 650; }}
        QLabel#panelMark {{ background: {p['chip']}; border: 1px solid {p['tint_border']}; border-radius: 15px; font-size: 13pt; }}
        QLabel#panelStatus {{ background: {p['section_bg']}; color: {p['text_soft']}; border: none; border-radius: 9px; padding: 2px 9px; font-size: 8pt; font-weight: 600; }}
        QLabel#panelAmount {{ color: {p['amount']}; font-size: 19pt; font-weight: 700; }}
        QLabel#panelDetail {{ color: {p['text_soft']}; font-size: 8pt; }}
        QLabel#panelDecor {{ background: transparent; border: none; font-size: 25pt; }}
        QLabel#panelAvatar {{ background: transparent; border: none; }}
        QLabel#wageArtBg, QLabel#pocketArtBg {{ background: transparent; border: none; }}
        QLabel#wageArtScrim {{ background: qlineargradient(x1:0 y1:0, x2:1 y2:0, stop:0 {p['scrim_left']}, stop:0.55 {p['scrim_mid']}, stop:1 {p['scrim_right']}); border: none; }}
        QLabel#sectionIcon, QLabel#roseDecor {{ background: transparent; border: none; }}
        QFrame#pocketBanner {{ background: {p['card']}; border: 1px solid {p['section_border']}; border-radius: 14px; }}
        QPushButton#pocketBannerBtn {{ background: transparent; color: {p['text']}; border: 1px solid transparent; border-radius: 13px; padding: 6px 10px; font-weight: 700; }}
        QPushButton#pocketBannerBtn:hover {{ background: rgba(255,255,255,36); border-color: {p['tint_border']}; }}
        QPushButton#pocketBannerBtn:pressed {{ background: rgba(255,255,255,60); }}
        QLabel#panelRow {{ background: {p['chip']}; border: 1px solid {p['tint_border']}; border-radius: 9px; padding: 4px 8px; font-size: 8pt; color: {p['text']}; }}
        QFrame#wageCard {{ background: qlineargradient(x1:0 y1:0, x2:1 y2:1, stop:0 {p['hero_top']}, stop:1 {p['hero_bottom']}); border: 1px solid {p['section_border']}; border-radius: 16px; }}
        QPushButton#panelSetup {{ background: {p['action_bg']}; color: {p['action_text']}; border: 1px solid {p['action_bg']}; border-radius: 9px; padding: 8px 10px; font-weight: 600; }}
        QPushButton#panelSetup:hover:enabled {{ background: {p['action_hover']}; border-color: {p['action_hover']}; }}
        QPushButton#panelPrimary {{ background: qlineargradient(x1:0 y1:0, x2:0 y2:1, stop:0 {p['action_bg']}, stop:1 {p['accent_pressed']}); color: {p['action_text']}; border: 1px solid {p['action_bg']}; border-radius: 15px; padding: 7px 10px; font-weight: 600; }}
        QPushButton#panelPrimary:hover:enabled {{ background: {p['action_hover']}; border-color: {p['action_hover']}; }}
        QPushButton#panelPrimary:pressed:enabled {{ background: {p['accent_pressed']}; border-color: {p['accent_pressed']}; padding-top: 8px; padding-bottom: 6px; }}
        QPushButton#panelPrimary:focus {{ border: 2px solid {p['focus_ring']}; }}
        QPushButton#panelPrimary:disabled {{ background: {p['tint_light']}; color: {p['text_soft']}; border-color: {p['tint_border']}; }}
        QPushButton#panelSecondary {{ background: {p['chip']}; color: {p['text']}; border: 1px solid {p['secondary_border']}; border-radius: 15px; padding: 6px 9px; font-weight: 600; }}
        QPushButton#panelSecondary:hover:enabled {{ background: {p['tint_light']}; border-color: {p['focus_ring']}; }}
        QPushButton#panelSecondary:pressed:enabled {{ background: {p['menu_highlight']}; border-color: {p['accent_hover']}; }}
        QPushButton#panelSecondary:disabled {{ background: {p['tint_light']}; color: {p['text_soft']}; border-color: {p['border']}; }}
        QPushButton#panelQuiet {{ background: transparent; color: {p['text_soft']}; border: 1px solid transparent; border-radius: 12px; padding: 5px 9px; }}
        QPushButton#panelQuiet:hover {{ background: {p['tint_light']}; color: {p['amount']}; border-color: {p['border']}; }}
        QPushButton#panelQuiet:pressed {{ background: {p['menu_highlight']}; border-color: {p['focus_ring']}; }}
        QPushButton#panelManager {{ background: {p['tint_light']}; color: {p['amount']}; border: 1px solid {p['tint_border']}; border-radius: 12px; padding: 4px 12px; font-size: 9pt; font-weight: 600; }}
        QPushButton#panelManager:hover {{ background: {p['accent']}; color: {p['action_text']}; border-color: {p['accent']}; }}
        QPushButton#panelManager:pressed {{ background: {p['accent_pressed']}; border-color: {p['accent_pressed']}; }}
        QPushButton#panelIconButton {{ background: {p['tint_light']}; color: {p['amount']}; border: 1px solid {p['tint_border']}; border-radius: 12px; font-size: 12pt; font-weight: 600; }}
        QPushButton#panelIconButton:hover {{ background: {p['menu_highlight']}; border-color: {p['focus_ring']}; color: {p['amount']}; }}
        QPushButton#panelIconButton:pressed {{ background: {p['section_border']}; border-color: {p['accent_hover']}; }}
        QPushButton#panelIconButton:focus {{ border: 2px solid {p['focus_ring']}; }}
        QToolButton#panelIconButton {{ background: {p['tint_light']}; color: {p['amount']}; border: 1px solid {p['tint_border']}; border-radius: 12px; font-size: 12pt; font-weight: 600; }}
        QToolButton#panelIconButton:hover {{ background: {p['menu_highlight']}; border-color: {p['focus_ring']}; color: {p['amount']}; }}
        QToolButton#panelIconButton:pressed {{ background: {p['section_border']}; border-color: {p['accent_hover']}; }}
    """


class QuickPanel(QWidget):
    ITEM_PREVIEW = 3

    def __init__(self, pet_window, parent=None, destinations=None):
        super().__init__(parent)
        self.pet = pet_window
        self.destinations = destinations or getattr(pet_window, "destination_service", None) or DestinationService()
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.setFixedWidth(320); self.setMaximumHeight(600)
        self._build_ui(); self._refresh()
        # 工资区 5 分钟自刷新：仅面板可见期间运行（showNear 启动 / hideEvent 停止）
        from PyQt5.QtCore import QTimer
        self.refresh_timer = QTimer(self)
        self.refresh_timer.setInterval(5 * 60 * 1000)
        self.refresh_timer.timeout.connect(self._refresh_wage)
        ui_skin.skinChanged.connect(self._apply_skin)
        self._outside_watch = ClickOutsideWatch(self, self._keep_out_rects, self.hide)

    def _keep_out_rects(self):
        rects = [self.geometry()]
        pet = self.pet
        if pet is not None and pet.isVisible():
            rects.append(pet.visible_pet_global_rect()
                         if hasattr(pet, "visible_pet_global_rect") else pet.geometry())
        return rects

    def _apply_skin(self):
        """Re-paint every locally-styled surface from the active skin."""
        p = ui_skin.palette()
        self._card.setStyleSheet(_panel_qss(p))
        self.setStyleSheet(f"QuickPanel {{ background: transparent; }}")
        if hasattr(self, "_favorite_icon"):
            self._apply_art()
        if getattr(self, "pocket_count", None) is not None:
            self.pocket_count.setStyleSheet(f"color: {p['amount']}; font-weight: 700;")
        if hasattr(self, "favorite_grid"):
            self._refresh_favorites()

    def _section_host(self, icon_name, text, fallback_emoji):
        """Section header = sheet icon (fallback emoji) + title + rose accent."""
        host = QWidget(); host.setStyleSheet("background: transparent;")
        row = QHBoxLayout(host); row.setContentsMargins(0, 0, 0, 0); row.setSpacing(6)
        icon_lbl = QLabel(); icon_lbl.setAlignment(Qt.AlignCenter); icon_lbl.setFixedSize(18, 18)
        title = QLabel(text); title.setObjectName("panelSectionTitle")
        rose = QLabel(); rose.setFixedSize(14, 14)
        row.addWidget(icon_lbl); row.addWidget(title); row.addWidget(rose)
        return host, icon_lbl, title, rose

    @staticmethod
    def _set_section_icon(lbl, name, fallback_emoji):
        path = ui_skin.theme_asset(f"icons/{name}")
        if path is not None:
            lbl.setPixmap(_fit_pixmap(path, 20)); lbl.setText("")
        else:
            lbl.setPixmap(QPixmap()); lbl.setText(fallback_emoji)

    def _apply_art(self):
        """Wire per-skin illustration assets; emoji fallback when absent."""
        avatar = ui_skin.theme_asset("avatar")
        if avatar is not None:
            self._mark.setObjectName("panelAvatar")
            self._mark.setText("")
            self._mark.setPixmap(_fill_pixmap(avatar, 32, 32))
        else:
            self._mark.setObjectName("panelMark")
            self._mark.setPixmap(QPixmap())
            self._mark.setText(ui_skin.palette()["deco"])
        self._mark.style().unpolish(self._mark); self._mark.style().polish(self._mark)

        hero = ui_skin.theme_asset("hero_scene")
        if hero is not None:
            self._wage_bg.setPixmap(QPixmap(str(hero)))
            self._wage_bg.show(); self._wage_scrim.show(); self.wage_decor.hide()
        else:
            self._wage_bg.setPixmap(QPixmap()); self._wage_bg.hide()
            self._wage_scrim.hide()
            self.wage_decor.setText(ui_skin.palette()["deco"]); self.wage_decor.show()

        if self._pocket_bg is not None:
            banner = ui_skin.theme_asset("pocket_banner")
            if banner is not None:
                self._pocket_bg.setPixmap(QPixmap(str(banner)))

        self._set_section_icon(self._favorite_icon, "folder", "⭐")
        self._set_section_icon(self._pocket_icon, "pocket", "🎒")
        self._set_section_icon(self._remind_icon, "bell", "⏰")
        rose = ui_skin.theme_asset("icons/rose")
        rose_pm = _fit_pixmap(rose, 16) if rose is not None else QPixmap()
        for lbl in (self._favorite_rose, self._pocket_rose, self._remind_rose):
            lbl.setPixmap(rose_pm)

        self.clock_out_btn.setIconSize(QSize(18, 18)); self.clock_out_btn.setIcon(_skin_icon("clock"))
        self.calendar_btn.setIconSize(QSize(18, 18)); self.calendar_btn.setIcon(_skin_icon("calendar"))
        self.open_reminders_btn.setIconSize(QSize(18, 18)); self.open_reminders_btn.setIcon(_skin_icon("bell"))
        self.panel_close_btn.setIconSize(QSize(16, 16))
        self.panel_close_btn.setIcon(_skin_icon("close"))
        self.panel_close_btn.setText("" if not self.panel_close_btn.icon().isNull() else "×")
        self.remind_btn.setIconSize(QSize(18, 18))
        self.remind_btn.setIcon(_skin_icon("plus"))
        self.remind_btn.setText("" if not self.remind_btn.icon().isNull() else "+")
        self.favorite_pin_btn.setIconSize(QSize(18, 18))
        self.favorite_pin_btn.setIcon(_skin_icon("plus"))
        self.favorite_pin_btn.setText("" if not self.favorite_pin_btn.icon().isNull() else "＋")
        self.open_pocket_btn.setIconSize(QSize(20, 20))
        self.open_pocket_btn.setIcon(_skin_icon("pocket"))
        if not self.open_pocket_btn.icon().isNull():
            self.open_pocket_btn.setText("打开文件口袋")

    def showEvent(self, event):
        # Art layers crop from the laid-out card size — recompute once real.
        QTimer.singleShot(0, self._apply_art)
        super().showEvent(event)

    def _build_ui(self):
        root = QVBoxLayout(self); root.setContentsMargins(0, 0, 0, 0)
        card = QFrame(); card.setObjectName("card"); self._card = card
        self._apply_skin()
        layout = QVBoxLayout(card); layout.setContentsMargins(13, 10, 13, 11); layout.setSpacing(6)

        top = QHBoxLayout(); top.setSpacing(9)
        mark = QLabel(); mark.setAlignment(Qt.AlignCenter); mark.setFixedSize(32, 32)
        self._mark = mark
        heading = QVBoxLayout(); heading.setSpacing(0)
        title = QLabel("小迪助手"); title.setObjectName("panelHeading")
        subtitle = QLabel("工作 · 文件 · 提醒"); subtitle.setObjectName("panelCaption")
        heading.addWidget(title); heading.addWidget(subtitle)
        close = QPushButton(); close.setObjectName("panelIconButton"); close.setFixedSize(26, 26); close.setToolTip("收起面板"); close.clicked.connect(self.hide); self.panel_close_btn = close
        top.addWidget(mark); top.addLayout(heading); top.addStretch(); top.addWidget(close); layout.addLayout(top)

        # Hero wage card: theme art (V5.10) as stacked background + scrim, real
        # controls on top — data is never baked into the image.
        wage_card = QFrame(); wage_card.setObjectName("wageCard")
        wage_stack = QGridLayout(wage_card); wage_stack.setContentsMargins(0, 0, 0, 0); wage_stack.setSpacing(0)
        ignored = QSizePolicy.Ignored
        self._wage_bg = QLabel(); self._wage_bg.setObjectName("wageArtBg")
        self._wage_bg.setScaledContents(True)
        self._wage_bg.setSizePolicy(ignored, ignored)
        wage_stack.addWidget(self._wage_bg, 0, 0)
        self._wage_scrim = QLabel(); self._wage_scrim.setObjectName("wageArtScrim")
        self._wage_scrim.setSizePolicy(ignored, ignored)
        wage_stack.addWidget(self._wage_scrim, 0, 0)
        wage_body = QHBoxLayout(); wage_body.setSpacing(4); wage_body.setContentsMargins(11, 9, 8, 9)
        wage_text = QVBoxLayout(); wage_text.setSpacing(2)
        self.wage_status = QLabel("工资统计未配置"); self.wage_status.setObjectName("panelStatus")
        self.wage_status.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.wage_amount = QLabel("未配置"); self.wage_amount.setObjectName("panelAmount")
        self.wage_detail = QLabel(""); self.wage_detail.setObjectName("panelDetail"); self.wage_detail.setWordWrap(True)
        self.wage_setup_btn = QPushButton("设置工资与工作时间"); self.wage_setup_btn.setObjectName("panelSetup"); self.wage_setup_btn.clicked.connect(self._open_wage_settings)
        wage_text.addWidget(self.wage_status); wage_text.addWidget(self.wage_amount); wage_text.addWidget(self.wage_detail); wage_text.addSpacing(4); wage_text.addWidget(self.wage_setup_btn)
        self.wage_decor = QLabel(ui_skin.palette().get("deco", "🎀")); self.wage_decor.setObjectName("panelDecor")
        self.wage_decor.setAlignment(Qt.AlignTop | Qt.AlignRight); self.wage_decor.setFixedWidth(52)
        wage_body.addLayout(wage_text, 1); wage_body.addWidget(self.wage_decor)
        wage_content = QWidget(); wage_content.setLayout(wage_body); wage_content.setStyleSheet("background: transparent;")
        wage_stack.addWidget(wage_content, 0, 0)
        self._wage_scrim.raise_(); wage_content.raise_()
        layout.addWidget(wage_card)

        wage_buttons = QHBoxLayout(); wage_buttons.setSpacing(6)
        self.clock_out_btn = QPushButton("下班打卡"); self.clock_out_btn.setObjectName("panelSecondary"); self.clock_out_btn.clicked.connect(self._clock_out)
        self.calendar_btn = QPushButton("工作日历"); self.calendar_btn.setObjectName("panelSecondary"); self.calendar_btn.clicked.connect(self._open_calendar)
        wage_buttons.addWidget(self.clock_out_btn); wage_buttons.addWidget(self.calendar_btn); layout.addLayout(wage_buttons)
        layout.addSpacing(4)
        favorite_header = QHBoxLayout()
        self._favorite_host, self._favorite_icon, self.favorite_title, self._favorite_rose = self._section_host("folder", "常用文件夹", "⭐")
        self.favorite_manage_btn = QPushButton("管理")
        self.favorite_manage_btn.setObjectName("panelManager")
        self.favorite_manage_btn.setCursor(Qt.PointingHandCursor)
        self.favorite_manage_btn.clicked.connect(lambda: self._manage_favorites())
        self.favorite_pin_btn = QToolButton()
        self.favorite_pin_btn.setText("＋")
        self.favorite_pin_btn.setObjectName("panelIconButton")
        self.favorite_pin_btn.setFixedSize(28, 28)
        self.favorite_pin_btn.setToolTip("固定当前文件夹或选择其他文件夹")
        self.favorite_pin_menu = QMenu(self.favorite_pin_btn)
        self.favorite_pin_menu.addAction("固定当前文件夹", self._pin_current_folder)
        self.favorite_pin_menu.addAction("选择其他文件夹", self._choose_other_folder)
        self.favorite_pin_btn.setMenu(self.favorite_pin_menu)
        self.favorite_pin_btn.setPopupMode(QToolButton.InstantPopup)
        # 菜单箭头写在按钮自身样式上（面板级子控件选择器对 InstantPopup 不生效）
        self.favorite_pin_btn.setStyleSheet(
            "QToolButton::menu-indicator { image: none; width: 0; subcontrol-position: right center; }"
            "QToolButton { padding: 0; }")
        favorite_header.addWidget(self.favorite_title); favorite_header.addStretch(); favorite_header.addWidget(self.favorite_manage_btn); favorite_header.addWidget(self.favorite_pin_btn)
        self.favorite_banner = InlineBanner()
        self.favorite_banner.hide()
        layout.addWidget(self.favorite_banner)
        layout.addLayout(favorite_header)
        self.favorite_empty = QLabel("还没有常用文件夹")
        self.favorite_empty.setObjectName("panelCaption")
        layout.addWidget(self.favorite_empty)
        self.favorite_add_btn = QPushButton("+ 添加文件夹")
        self.favorite_add_btn.setObjectName("panelQuiet")
        self.favorite_add_btn.clicked.connect(lambda: self._manage_favorites())
        layout.addWidget(self.favorite_add_btn)
        self.favorite_grid = QGridLayout(); self.favorite_grid.setContentsMargins(0, 0, 0, 0); self.favorite_grid.setHorizontalSpacing(6); self.favorite_grid.setVerticalSpacing(6)
        layout.addLayout(self.favorite_grid)
        self.favorite_view_all_btn = QPushButton("查看全部（0）")
        self.favorite_view_all_btn.setObjectName("flat")
        self.favorite_view_all_btn.clicked.connect(lambda: self._manage_favorites())
        layout.addWidget(self.favorite_view_all_btn)

        layout.addSpacing(4)
        hdr = QHBoxLayout(); self._pocket_host, self._pocket_icon, self.pocket_title, self._pocket_rose = self._section_host("pocket", "文件口袋", "🎒"); self.pocket_count = QLabel("0"); self.pocket_count.setStyleSheet(""); hdr.addWidget(self.pocket_title); hdr.addStretch(); hdr.addWidget(self.pocket_count); layout.addLayout(hdr)
        self.pocket_items_layout = QVBoxLayout(); self.pocket_items_layout.setSpacing(3); layout.addLayout(self.pocket_items_layout)
        self.empty_label = QLabel("暂无内容 · 拖文件到角色即可暂存"); self.empty_label.setWordWrap(True); self.empty_label.setObjectName("panelCaption"); layout.addWidget(self.empty_label)
        # 文件口袋横幅（V5.10）：主题横幅插画为底层，真实按钮铺满可点击。
        pocket_art = ui_skin.theme_asset("pocket_banner")
        if pocket_art is not None:
            banner = QFrame(); banner.setObjectName("pocketBanner")
            banner_grid = QGridLayout(banner); banner_grid.setContentsMargins(0, 0, 0, 0); banner_grid.setSpacing(0)
            self._pocket_bg = QLabel(); self._pocket_bg.setObjectName("pocketArtBg")
            self._pocket_bg.setScaledContents(True)
            self._pocket_bg.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Ignored)
            banner_grid.addWidget(self._pocket_bg, 0, 0)
            self.open_pocket_btn = QPushButton("打开文件口袋"); self.open_pocket_btn.setObjectName("pocketBannerBtn"); self.open_pocket_btn.setCursor(Qt.PointingHandCursor); self.open_pocket_btn.clicked.connect(self._open_pocket)
            banner_grid.addWidget(self.open_pocket_btn, 0, 0)
            self.open_pocket_btn.raise_()
            self._pocket_banner = banner
            layout.addWidget(banner)
        else:
            self._pocket_bg = None
            self._pocket_banner = None
            self.open_pocket_btn = QPushButton("🎒 打开文件口袋"); self.open_pocket_btn.setObjectName("panelPrimary"); self.open_pocket_btn.clicked.connect(self._open_pocket); layout.addWidget(self.open_pocket_btn)

        layout.addSpacing(4)
        remind_hdr = QHBoxLayout(); self._remind_host, self._remind_icon, self.remind_title, self._remind_rose = self._section_host("bell", "下个提醒", "⏰"); self.remind_btn = QToolButton(); self.remind_btn.setObjectName("panelIconButton"); self.remind_btn.setFixedSize(30, 30); self.remind_btn.clicked.connect(self._open_add_reminder); remind_hdr.addWidget(self.remind_title); remind_hdr.addStretch(); remind_hdr.addWidget(self.remind_btn); layout.addLayout(remind_hdr)
        self.next_reminder_label = QLabel("暂无提醒"); self.next_reminder_label.setWordWrap(True); layout.addWidget(self.next_reminder_label)
        self.remind_items_layout = QVBoxLayout(); self.remind_items_layout.setSpacing(2); layout.addLayout(self.remind_items_layout)
        self.no_remind_label = QLabel("暂无提醒"); self.no_remind_label.setObjectName("panelCaption"); self.no_remind_label.hide(); layout.addWidget(self.no_remind_label)
        self.open_reminders_btn = QPushButton("我的提醒"); self.open_reminders_btn.setObjectName("panelQuiet"); self.open_reminders_btn.clicked.connect(self._open_reminders); layout.addWidget(self.open_reminders_btn)
        # 无外层滚动容器：QScrollArea 的方形视口会在圆角卡片四角露出"尖尖"，
        # 而内容量在 600px 上限内（收藏区自带滚动），直接铺卡片即可。
        self._apply_art()
        root.addWidget(card)

    @staticmethod
    def _clear(layout):
        while layout.count():
            child = layout.takeAt(0)
            if child.widget(): child.widget().deleteLater()

    def _refresh_wage(self):
        wage = getattr(self.pet, "wage", None)
        if wage is None or not wage.configured:
            self.wage_status.setText("工资统计未配置"); self.wage_amount.setText("未配置"); self.wage_detail.setText("首次使用请在设置中填写工资和上班时间"); self.wage_setup_btn.show(); self.clock_out_btn.setEnabled(False); return
        self.wage_setup_btn.hide(); snap = wage.current_breakdown(); rec = wage.record_for()
        self.clock_out_btn.setEnabled(True)   # 随时可打，重复点击以最新为准
        self.wage_status.setText(f"{rec.actual_clock_out:%H:%M} 下班" if rec and rec.actual_clock_out else {"workday": "工作中", "adjusted_workday": "调休上班", "rest": "休息日", "leave": "请假"}.get(snap.status, snap.status))
        if wage.settings.privacy_mode:
            self.wage_amount.setText(f"今日进度 {snap.progress}%"); self.wage_detail.setText("金额已隐藏 · " + (f"已加班 {snap.overtime_minutes // 60}h{snap.overtime_minutes % 60:02d}m" if snap.overtime_minutes else "正常工作时间进行中"))
        else:
            self.wage_amount.setText(f"今日已赚 ¥{snap.total_earned:.2f}"); self.wage_detail.setText(f"正常工资 ¥{snap.base_earned:.2f}  ·  加班 {snap.overtime_minutes // 60}h{snap.overtime_minutes % 60:02d}m  ·  加班费 ¥{snap.overtime_pay:.2f}  ·  餐补 ¥{snap.confirmed_meal_allowance:.2f}")

    def _refresh(self):
        self._refresh_wage(); items = self.pet.pocket.list_items(); self.pocket_count.setText(str(len(items))); self.empty_label.setVisible(not items); self._clear(self.pocket_items_layout)
        for item in items[: self.ITEM_PREVIEW]:
            lbl = QLabel(item.name if item.exists else item.name + "（路径失效）"); lbl.setObjectName("panelRow"); lbl.setWordWrap(True); self.pocket_items_layout.addWidget(lbl)
        if len(items) > self.ITEM_PREVIEW:
            lbl = QLabel(f"还有 {len(items) - self.ITEM_PREVIEW} 项…"); lbl.setObjectName("panelRow"); self.pocket_items_layout.addWidget(lbl)
        reminders = self.pet.reminder.list_reminders(); self._clear(self.remind_items_layout)
        if reminders:
            first = reminders[0]; self.next_reminder_label.setText(f"{first.due_at:%m-%d %H:%M}  {first.content}"); self._set_row_style(self.next_reminder_label, True); self.no_remind_label.hide()
            for rem in reminders[1:3]:
                lbl = QLabel(f"{rem.due_at:%m-%d %H:%M}  {rem.content}"); lbl.setWordWrap(True); lbl.setObjectName("panelRow"); self.remind_items_layout.addWidget(lbl)
        else:
            self.next_reminder_label.setText("暂无提醒"); self._set_row_style(self.next_reminder_label, False); self.no_remind_label.show()
        self._refresh_favorites()

    @staticmethod
    def _set_row_style(label, as_row):
        """First reminder renders as a chip row when present, caption when empty."""
        label.setObjectName("panelRow" if as_row else "panelCaption")
        label.style().unpolish(label); label.style().polish(label)

    refresh = _refresh

    def _refresh_favorites(self):
        self._clear(self.favorite_grid)
        p = ui_skin.palette()
        favorites = self.destinations.list_favorites()
        self.favorite_empty.setVisible(not favorites)
        self.favorite_add_btn.setVisible(not favorites)
        self.favorite_view_all_btn.setVisible(len(favorites) > 6)
        self.favorite_view_all_btn.setText(f"查看全部（{len(favorites)}）")
        provider = QFileIconProvider()
        for index, favorite in enumerate(favorites[:6]):
            exists = favorite.exists
            button = QToolButton()
            button.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
            rose_folder = _skin_icon("folder")
            button.setIcon(rose_folder if not rose_folder.isNull()
                           else provider.icon(QFileInfo(str(favorite.path))) if exists
                           else provider.icon(QFileIconProvider.Folder))
            button.setFixedWidth(max(104, (self.width() - 36) // 2))
            button.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
            label = f"{favorite.name}  ›" if exists else f"{favorite.name}  ⚠"
            text_width = max(24, button.width() - button.iconSize().width() - 26)
            button.setText(QFontMetrics(button.font()).elidedText(label, Qt.ElideRight, text_width))
            button.setToolTip(f"{favorite.name}\n{favorite.path}" + ("\n路径失效" if not exists else ""))
            button.setEnabled(True)  # keep the context menu available for repairing a missing path
            button.setFixedHeight(31)
            button.setStyleSheet(
                f"QToolButton {{ text-align:left; color:{p['text'] if exists else p['muted']}; background:{p['chip']}; padding:3px 6px; border:1px solid {p['tint_border']}; border-radius:10px; }}"
                f"QToolButton:hover:enabled {{ background:{p['tint_light']}; border-color:{p['focus_ring']}; }}"
                f"QToolButton:pressed:enabled {{ background:{p['menu_highlight']}; border-color:{p['section_border']}; }}"
                f"QToolButton:focus {{ border:1px solid {p['focus_ring']}; }}"
            )
            button.setCursor(Qt.PointingHandCursor)
            button.setContextMenuPolicy(Qt.CustomContextMenu)
            button.customContextMenuRequested.connect(
                lambda pos, fid=favorite.id, btn=button: self._show_favorite_menu(fid, btn, pos)
            )
            button.clicked.connect(lambda _=False, fid=favorite.id: self._open_favorite(fid))
            self.favorite_grid.addWidget(button, index // 2, index % 2)
        self.favorite_count = len(favorites)

    def _open_favorite(self, favorite_id):
        favorite = self.destinations.get_favorite(favorite_id)
        if not favorite:
            return False
        if not favorite.exists:
            self._manage_favorites(
                favorite_id, focus_message=f"“{favorite.name}”的路径已经失效。可通过“修改路径”重新关联。",
            )
            return False
        return QDesktopServices.openUrl(QUrl.fromLocalFile(str(favorite.path)))

    def _manage_favorites(self, focus_id=None, action=None, *, focus_message=None,
                          initial_path=None, initial_name=None):
        if hasattr(self.pet, "_manage_favorite_folders"):
            return self.pet._manage_favorite_folders(
                focus_id, action, focus_message=focus_message,
                initial_path=initial_path, initial_name=initial_name,
            )
        from favorite_folders_ui import FavoriteFoldersDialog
        dialog = FavoriteFoldersDialog(
            self.destinations, self, focus_id=focus_id, focus_action=action,
            focus_message=focus_message,
        )
        dialog.favorites_changed.connect(self._refresh_favorites)
        if initial_path:
            dialog._add_path(initial_path, initial_name)
        return dialog.exec_()

    def _choose_other_folder(self):
        path = QFileDialog.getExistingDirectory(self, "选择常用文件夹")
        if path:
            self._manage_favorites(initial_path=path)

    def _pin_current_folder(self):
        explorer = getattr(self.pet, "explorer_service", None)
        path = explorer.current_directory() if explorer is not None else None
        if path is None:
            status = getattr(explorer, "last_directory_status", "no_explorer")
            message = ("当前资源管理器位置不是普通文件夹。" if status == "not_filesystem"
                       else "没有检测到当前资源管理器文件夹。")
            self._manage_favorites(focus_message=message)
            return False

        favorite = next((item for item in self.destinations.list_favorites()
                         if str(item.path).casefold() == str(path).casefold()), None)
        if favorite:
            self._manage_favorites(favorite.id, focus_message="已经是常用文件夹。")
            return favorite

        dialog = ModernDialog("固定当前文件夹", "确认将这个位置加入常用文件夹。", self, min_width=440)
        path_label = QLabel(f"路径\n{path}")
        path_label.setWordWrap(True)
        path_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        name_label = QLabel("名称")
        name_input = QLineEdit(display_default_name(path))
        name_input.setMaxLength(40)
        dialog.add_body(path_label)
        dialog.add_body(name_label)
        dialog.add_body(name_input)
        cancel = QPushButton("取消")
        cancel.clicked.connect(dialog.reject)
        pin = QPushButton("固定")
        pin.setObjectName("primary")
        pin.clicked.connect(dialog.accept)
        dialog.add_footer(cancel)
        dialog.add_footer(pin)
        if dialog.exec_() != ModernDialog.Accepted:
            return False
        name = name_input.text().strip()
        if not name:
            self._manage_favorites(focus_message="名称不能为空，请输入 1 到 40 个字符。")
            return False
        self._manage_favorites(initial_path=path, initial_name=name)
        return True

    def _show_favorite_menu(self, favorite_id, button, pos):
        favorite = self.destinations.get_favorite(favorite_id)
        if not favorite:
            return
        menu = QMenu(self)
        exists = favorite.exists
        open_action = menu.addAction("打开")
        open_action.setEnabled(exists)
        copy_action = menu.addAction("复制路径")
        menu.addSeparator()
        rename_action = menu.addAction("重命名")
        update_action = menu.addAction("修改路径")
        remove_action = menu.addAction("移除")
        chosen = menu.exec_(button.mapToGlobal(pos))
        if chosen == open_action:
            self._open_favorite(favorite_id)
        elif chosen == copy_action:
            QApplication.clipboard().setText(str(favorite.path))
        elif chosen == rename_action:
            self._manage_favorites(favorite_id, "rename")
        elif chosen == update_action:
            self._manage_favorites(favorite_id, "update_path")
        elif chosen == remove_action:
            self._manage_favorites(favorite_id, "remove")
    def _open_pocket(self): self.pet._open_pocket(); self.hide()
    def _open_add_reminder(self): self.pet._open_add_reminder(); self._refresh()
    def _open_reminders(self): self.pet._open_reminders(); self._refresh()
    def _open_calendar(self): self.pet._open_calendar(); self._refresh()
    def _open_wage_settings(self): self.pet._open_wage_settings(); self._refresh()
    def _clock_out(self):
        from clockout_confirm import confirm_clockout
        if confirm_clockout(self.pet.wage, self.pet):
            self.pet._clock_out()
            self._refresh()
    def showNear(self, pet_window):
        rect = (pet_window.visible_pet_global_rect()
                if hasattr(pet_window, "visible_pet_global_rect") else pet_window.geometry())
        self.move_near(rect, live=False, screen=pet_window.screen())

    def move_near(self, anchor_rect, live=False, screen=None):
        # The scroll area swallows the window's own sizeHint, so size from
        # the CARD's content hint instead — the panel grows to fit its
        # content (≤ maxHeight) and only scrolls in extreme cases.
        self.adjustSize()
        content_h = self._card.sizeHint().height() + 26   # margins + scrollbar
        ph = min(max(content_h, 380), self.maximumHeight())
        self.resize(self.width(), ph)
        import anchor
        anchor.place_panel(self, anchor_rect, screen=screen)
        if not live:
            self.show(); self.raise_(); self.activateWindow()
            QApplication.instance().installEventFilter(self)
            self.refresh_timer.start()
            self._outside_watch.start()

    def eventFilter(self, obj, event):
        """Click-anywhere-outside closes the assistant panel.

        Clicks on the pet itself are skipped: PetWindow toggles the panel in
        its own mouse handler. Clicks on other applications' windows never
        reach Qt — those are covered by focusOutEvent below.
        """
        if event.type() == QEvent.MouseButtonPress and self.isVisible():
            gpos = event.globalPos()
            inside_panel = self.geometry().contains(gpos)
            pet = self.pet
            pet_rect = (pet.visible_pet_global_rect()
                        if hasattr(pet, "visible_pet_global_rect") else pet.geometry())
            inside_pet = pet.isVisible() and pet_rect.contains(gpos)
            if not inside_panel and not inside_pet:
                self.hide()
        return super().eventFilter(obj, event)

    def hideEvent(self, event):
        QApplication.instance().removeEventFilter(self)
        self.refresh_timer.stop()
        self._outside_watch.stop()
        super().hideEvent(event)
    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape: self.hide()
    def focusOutEvent(self, event):
        # Focus went to another application window (in-app clicks are handled
        # by eventFilter). Hide like any popup — no geometry heuristics.
        QTimer.singleShot(0, self._close_if_inactive)
    def _close_if_inactive(self):
        if self.isVisible() and not self.isActiveWindow():
            self.hide()
