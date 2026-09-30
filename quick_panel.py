"""Today's assistant panel: wage snapshot first, pocket and reminders below."""

from PyQt5.QtCore import Qt, QTimer, QEvent, QUrl, QFileInfo
from PyQt5.QtGui import QDesktopServices, QFontMetrics
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


def _panel_qss(p: dict) -> str:
    """Assistant-panel stylesheet derived from the active skin palette."""
    return f"""
        QFrame#card {{ background: {p['card']}; border: 1px solid {p['border']}; border-radius: 14px; }}
        QLabel#panelHeading {{ color: {p['text']}; font-size: 11pt; font-weight: 700; }}
        QLabel#panelCaption {{ color: {p['muted']}; font-size: 8pt; }}
        QLabel#panelSectionTitle {{ color: {p['text']}; font-size: 10pt; font-weight: 650; }}
        QLabel#panelStatus {{ color: {p['text_soft']}; font-size: 8pt; font-weight: 600; }}
        QLabel#panelAmount {{ color: {p['amount']}; font-size: 17pt; font-weight: 700; }}
        QLabel#panelDetail {{ color: {p['text_soft']}; font-size: 8pt; }}
        QFrame#wageCard {{ background: {p['section_bg']}; border: 1px solid {p['section_border']}; border-radius: 11px; }}
        QPushButton#panelPrimary {{ background: {p['action_bg']}; color: #FFFFFF; border: 1px solid {p['action_bg']}; border-radius: 8px; padding: 7px 10px; font-weight: 600; }}
        QPushButton#panelPrimary:hover:enabled {{ background: {p['action_hover']}; border-color: {p['action_hover']}; }}
        QPushButton#panelPrimary:pressed:enabled {{ background: {p['accent_pressed']}; border-color: {p['accent_pressed']}; padding-top: 8px; padding-bottom: 6px; }}
        QPushButton#panelPrimary:focus {{ border: 2px solid {p['focus_ring']}; }}
        QPushButton#panelPrimary:disabled {{ background: {p['tint_light']}; color: {p['text_soft']}; border-color: {p['tint_border']}; }}
        QPushButton#panelSecondary {{ background: {p['card']}; color: {p['text']}; border: 1px solid {p['secondary_border']}; border-radius: 8px; padding: 6px 9px; }}
        QPushButton#panelSecondary:hover:enabled {{ background: {p['tint_light']}; border-color: {p['focus_ring']}; }}
        QPushButton#panelSecondary:pressed:enabled {{ background: {p['menu_highlight']}; border-color: {p['accent_hover']}; }}
        QPushButton#panelSecondary:disabled {{ background: {p['tint_light']}; color: {p['text_soft']}; border-color: {p['border']}; }}
        QPushButton#panelQuiet {{ background: transparent; color: {p['text_soft']}; border: 1px solid transparent; border-radius: 8px; padding: 5px 9px; }}
        QPushButton#panelQuiet:hover {{ background: {p['tint_light']}; color: {p['amount']}; border-color: {p['border']}; }}
        QPushButton#panelQuiet:pressed {{ background: {p['menu_highlight']}; border-color: {p['focus_ring']}; }}
        QPushButton#panelManager {{ background: {p['card']}; color: {p['text_soft']}; border: 1px solid {p['secondary_border']}; border-radius: 8px; padding: 4px 9px; font-size: 8pt; }}
        QPushButton#panelManager:hover {{ background: {p['tint_light']}; color: {p['amount']}; border-color: {p['focus_ring']}; }}
        QPushButton#panelManager:pressed {{ background: {p['menu_highlight']}; border-color: {p['accent_hover']}; }}
        QPushButton#panelIconButton {{ background: {p['tint_light']}; color: {p['amount']}; border: 1px solid {p['tint_border']}; border-radius: 8px; font-size: 12pt; font-weight: 600; }}
        QPushButton#panelIconButton:hover {{ background: {p['menu_highlight']}; border-color: {p['focus_ring']}; color: {p['amount']}; }}
        QPushButton#panelIconButton:pressed {{ background: {p['section_border']}; border-color: {p['accent_hover']}; }}
        QPushButton#panelIconButton:focus {{ border: 2px solid {p['focus_ring']}; }}
        QToolButton#panelIconButton {{ background: {p['tint_light']}; color: {p['amount']}; border: 1px solid {p['tint_border']}; border-radius: 8px; font-size: 12pt; font-weight: 600; }}
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
        self.setFixedWidth(320); self.setMaximumHeight(520)
        self._build_ui(); self._refresh()
        ui_skin.skinChanged.connect(self._apply_skin)

    def _section_line(self, layout):
        sep = QFrame(); sep.setFrameShape(QFrame.NoFrame); sep.setFixedHeight(1)
        self._section_lines.append(sep)
        if self._section_lines and hasattr(self, "_card"):
            sep.setStyleSheet(f"background: {ui_skin.palette()['tint_border']};")
        layout.addWidget(sep)

    def _apply_skin(self):
        """Re-paint every locally-styled surface from the active skin."""
        p = ui_skin.palette()
        self._card.setStyleSheet(_panel_qss(p))
        if getattr(self, "_mark", None) is not None:
            self._mark.setStyleSheet(
                f"background:{p['menu_highlight']}; color:{p['amount']}; "
                f"border:1px solid {p['tint_border']}; border-radius:9px; "
                "font-size:10pt; font-weight:700;")
        for sep in getattr(self, "_section_lines", []):
            sep.setStyleSheet(f"background: {p['tint_border']};")
        if getattr(self, "pocket_count", None) is not None:
            self.pocket_count.setStyleSheet(f"color: {p['amount']}; font-weight: 700;")
        if hasattr(self, "favorite_grid"):
            self._refresh_favorites()

    def _build_ui(self):
        self._section_lines = []
        root = QVBoxLayout(self); root.setContentsMargins(0, 0, 0, 0)
        card = QFrame(); card.setObjectName("card"); self._card = card
        self._apply_skin()
        layout = QVBoxLayout(card); layout.setContentsMargins(13, 11, 13, 11); layout.setSpacing(7)

        top = QHBoxLayout(); top.setSpacing(9)
        mark = QLabel("🎀"); mark.setAlignment(Qt.AlignCenter); mark.setFixedSize(30, 30)
        self._mark = mark
        heading = QVBoxLayout(); heading.setSpacing(0)
        title = QLabel("小迪助手"); title.setObjectName("panelHeading")
        subtitle = QLabel("工作 · 文件 · 提醒"); subtitle.setObjectName("panelCaption")
        heading.addWidget(title); heading.addWidget(subtitle)
        close = QPushButton("×"); close.setObjectName("panelIconButton"); close.setFixedSize(26, 26); close.setToolTip("收起面板"); close.clicked.connect(self.hide); self.panel_close_btn = close
        top.addWidget(mark); top.addLayout(heading); top.addStretch(); top.addWidget(close); layout.addLayout(top)

        wage_card = QFrame(); wage_card.setObjectName("wageCard")
        wage_layout = QVBoxLayout(wage_card); wage_layout.setContentsMargins(10, 8, 10, 9); wage_layout.setSpacing(2)
        self.wage_status = QLabel("工资统计未配置"); self.wage_status.setObjectName("panelStatus")
        self.wage_amount = QLabel("未配置"); self.wage_amount.setObjectName("panelAmount")
        self.wage_detail = QLabel(""); self.wage_detail.setObjectName("panelDetail"); self.wage_detail.setWordWrap(True)
        self.wage_setup_btn = QPushButton("设置工资与工作时间"); self.wage_setup_btn.setObjectName("panelPrimary"); self.wage_setup_btn.clicked.connect(self._open_wage_settings)
        wage_layout.addWidget(self.wage_status); wage_layout.addWidget(self.wage_amount); wage_layout.addWidget(self.wage_detail); wage_layout.addSpacing(4); wage_layout.addWidget(self.wage_setup_btn)
        layout.addWidget(wage_card)

        wage_buttons = QHBoxLayout(); wage_buttons.setSpacing(6)
        self.clock_out_btn = QPushButton("下班打卡"); self.clock_out_btn.setObjectName("panelSecondary"); self.clock_out_btn.clicked.connect(self._clock_out)
        self.calendar_btn = QPushButton("工作日历"); self.calendar_btn.setObjectName("panelSecondary"); self.calendar_btn.clicked.connect(self._open_calendar)
        wage_buttons.addWidget(self.clock_out_btn); wage_buttons.addWidget(self.calendar_btn); layout.addLayout(wage_buttons)

        self._section_line(layout)
        favorite_header = QHBoxLayout()
        self.favorite_title = QLabel("⭐ 常用文件夹"); self.favorite_title.setObjectName("panelSectionTitle")
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

        self._section_line(layout)
        hdr = QHBoxLayout(); self.pocket_title = QLabel("🎒 文件口袋"); self.pocket_title.setObjectName("panelSectionTitle"); self.pocket_count = QLabel("0"); self.pocket_count.setStyleSheet(""); hdr.addWidget(self.pocket_title); hdr.addStretch(); hdr.addWidget(self.pocket_count); layout.addLayout(hdr)
        self.pocket_items_layout = QVBoxLayout(); self.pocket_items_layout.setSpacing(2); layout.addLayout(self.pocket_items_layout)
        self.empty_label = QLabel("暂无内容 · 拖文件到角色即可暂存"); self.empty_label.setWordWrap(True); self.empty_label.setObjectName("panelCaption"); layout.addWidget(self.empty_label)
        self.open_pocket_btn = QPushButton("🎒 打开文件口袋"); self.open_pocket_btn.setObjectName("panelPrimary"); self.open_pocket_btn.clicked.connect(self._open_pocket); layout.addWidget(self.open_pocket_btn)

        self._section_line(layout)
        remind_hdr = QHBoxLayout(); self.remind_title = QLabel("⏰ 下个提醒"); self.remind_title.setObjectName("panelSectionTitle"); self.remind_btn = QPushButton("＋"); self.remind_btn.setObjectName("panelIconButton"); self.remind_btn.setFixedSize(28, 28); self.remind_btn.clicked.connect(self._open_add_reminder); remind_hdr.addWidget(self.remind_title); remind_hdr.addStretch(); remind_hdr.addWidget(self.remind_btn); layout.addLayout(remind_hdr)
        self.next_reminder_label = QLabel("暂无提醒"); self.next_reminder_label.setWordWrap(True); layout.addWidget(self.next_reminder_label)
        self.remind_items_layout = QVBoxLayout(); self.remind_items_layout.setSpacing(2); layout.addLayout(self.remind_items_layout)
        self.no_remind_label = QLabel("暂无提醒"); self.no_remind_label.setObjectName("panelCaption"); self.no_remind_label.hide(); layout.addWidget(self.no_remind_label)
        self.open_reminders_btn = QPushButton("🔔 我的提醒"); self.open_reminders_btn.setObjectName("panelQuiet"); self.open_reminders_btn.clicked.connect(self._open_reminders); layout.addWidget(self.open_reminders_btn)
        self.scroll_area = QScrollArea(self); self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.NoFrame); self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll_area.setWidget(card); root.addWidget(self.scroll_area)

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
        self.clock_out_btn.setEnabled(snap.overtime_minutes > 0 and rec is None)
        self.wage_status.setText(f"{rec.actual_clock_out:%H:%M} 下班" if rec and rec.actual_clock_out else {"workday": "工作中", "adjusted_workday": "调休上班", "rest": "休息日", "leave": "请假"}.get(snap.status, snap.status))
        if wage.settings.privacy_mode:
            self.wage_amount.setText(f"今日进度 {snap.progress}%"); self.wage_detail.setText("金额已隐藏 · " + (f"已加班 {snap.overtime_minutes // 60}h{snap.overtime_minutes % 60:02d}m" if snap.overtime_minutes else "正常工作时间进行中"))
        else:
            self.wage_amount.setText(f"今日已赚 ¥{snap.total_earned:.2f}"); self.wage_detail.setText(f"正常工资 ¥{snap.base_earned:.2f}  ·  加班 {snap.overtime_minutes // 60}h{snap.overtime_minutes % 60:02d}m  ·  加班费 ¥{snap.overtime_pay:.2f}  ·  餐补 ¥{snap.confirmed_meal_allowance:.2f}")

    def _refresh(self):
        self._refresh_wage(); items = self.pet.pocket.list_items(); self.pocket_count.setText(str(len(items))); self.empty_label.setVisible(not items); self._clear(self.pocket_items_layout)
        for item in items[: self.ITEM_PREVIEW]:
            lbl = QLabel(f"  {item.name if item.exists else item.name + '（路径失效）'}"); lbl.setStyleSheet(f"font-size: 8pt; color: {theme.TEXT}; padding: 1px 0;"); self.pocket_items_layout.addWidget(lbl)
        if len(items) > self.ITEM_PREVIEW:
            lbl = QLabel(f"  还有 {len(items) - self.ITEM_PREVIEW} 项..."); lbl.setStyleSheet(f"font-size: 8pt; color: {theme.TEXT_MUTED};"); self.pocket_items_layout.addWidget(lbl)
        reminders = self.pet.reminder.list_reminders(); self._clear(self.remind_items_layout)
        if reminders:
            first = reminders[0]; self.next_reminder_label.setText(f"{first.due_at:%m-%d %H:%M}  {first.content}"); self.no_remind_label.hide()
            for rem in reminders[1:3]:
                lbl = QLabel(f"  {rem.due_at:%m-%d %H:%M}  {rem.content}"); lbl.setWordWrap(True); lbl.setStyleSheet(f"font-size: 8pt; color: {theme.TEXT}; padding: 1px 0;"); self.remind_items_layout.addWidget(lbl)
        else:
            self.next_reminder_label.setText("暂无提醒"); self.no_remind_label.show()
        self._refresh_favorites()

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
            button.setIcon(provider.icon(QFileInfo(str(favorite.path))) if exists
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
                f"QToolButton {{ text-align:left; color:{p['text'] if exists else p['muted']}; background:{p['bg']}; padding:3px 5px; border:1px solid {p['border']}; border-radius:7px; }}"
                f"QToolButton:hover:enabled {{ background:{p['tint_light']}; border-color:{p['tint_border']}; }}"
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
    def _clock_out(self): self.pet._clock_out(); self._refresh()
    def showNear(self, pet_window):
        rect = (pet_window.visible_pet_global_rect()
                if hasattr(pet_window, "visible_pet_global_rect") else pet_window.geometry())
        self.move_near(rect, live=False, screen=pet_window.screen())

    def move_near(self, anchor_rect, live=False, screen=None):
        self.adjustSize()
        ph = min(max(self.sizeHint().height() + 16, self.height()), self.maximumHeight())
        self.resize(self.width(), ph)
        import anchor
        anchor.place_panel(self, anchor_rect, screen=screen)
        if not live:
            self.show(); self.raise_(); self.activateWindow()
            QApplication.instance().installEventFilter(self)

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
