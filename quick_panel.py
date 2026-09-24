"""Today's assistant panel: wage snapshot first, pocket and reminders below."""

from PyQt5.QtCore import Qt, QTimer, QEvent, QUrl, QFileInfo
from PyQt5.QtGui import QDesktopServices, QFontMetrics
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QPushButton, QFrame,
    QApplication, QToolButton, QFileIconProvider, QMenu, QFileDialog, QLineEdit,
    QSizePolicy,
)
from destinations import DestinationService, display_default_name
from ui.modern.dialog import ModernDialog
from ui.modern.message import InlineBanner
import theme


class QuickPanel(QWidget):
    ITEM_PREVIEW = 3

    def __init__(self, pet_window, parent=None, destinations=None):
        super().__init__(parent)
        self.pet = pet_window
        self.destinations = destinations or getattr(pet_window, "destination_service", None) or DestinationService()
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.setFixedWidth(280); self.setMaximumHeight(520)
        self._build_ui(); self._refresh()

    def _section_line(self, layout):
        sep = QFrame(); sep.setFrameShape(QFrame.HLine); sep.setStyleSheet(f"background: {theme.BORDER}; max-height: 1px;"); layout.addWidget(sep)

    def _build_ui(self):
        root = QVBoxLayout(self); root.setContentsMargins(0, 0, 0, 0)
        card = QFrame(); card.setObjectName("card"); card.setStyleSheet(f"QFrame#card {{ background: {theme.BG_CARD}; border: 1px solid {theme.BORDER}; border-radius: {theme.RADIUS}px; }}")
        layout = QVBoxLayout(card); layout.setContentsMargins(14, 10, 14, 10); layout.setSpacing(4)
        top = QHBoxLayout(); title = QLabel("今日助手"); title.setObjectName("title")
        close = QPushButton("✕"); close.setObjectName("flat"); close.setFixedSize(24, 24); close.clicked.connect(self.hide); self.panel_close_btn = close
        top.addWidget(title); top.addStretch(); top.addWidget(close); layout.addLayout(top)

        self.wage_status = QLabel("工资统计未配置"); self.wage_status.setObjectName("title")
        self.wage_amount = QLabel("设置工资与工作时间"); self.wage_amount.setStyleSheet(f"font-size: 16pt; font-weight: 700; color: {theme.ACCENT};")
        self.wage_detail = QLabel(""); self.wage_detail.setWordWrap(True)
        self.wage_setup_btn = QPushButton("设置工资与工作时间"); self.wage_setup_btn.setObjectName("primary"); self.wage_setup_btn.clicked.connect(self._open_wage_settings)
        layout.addWidget(self.wage_status); layout.addWidget(self.wage_amount); layout.addWidget(self.wage_detail); layout.addWidget(self.wage_setup_btn)
        wage_buttons = QHBoxLayout(); self.clock_out_btn = QPushButton("下班打卡"); self.clock_out_btn.setObjectName("primary"); self.clock_out_btn.clicked.connect(self._clock_out); self.calendar_btn = QPushButton("工作日历"); self.calendar_btn.clicked.connect(self._open_calendar)
        wage_buttons.addWidget(self.clock_out_btn); wage_buttons.addWidget(self.calendar_btn); layout.addLayout(wage_buttons)

        self._section_line(layout)
        favorite_header = QHBoxLayout()
        self.favorite_title = QLabel("常用文件夹"); self.favorite_title.setObjectName("title")
        self.favorite_manage_btn = QPushButton("管理")
        self.favorite_manage_btn.setObjectName("flat")
        self.favorite_manage_btn.clicked.connect(lambda: self._manage_favorites())
        self.favorite_pin_btn = QToolButton()
        self.favorite_pin_btn.setText("＋")
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
        self.favorite_empty.setStyleSheet(f"color: {theme.TEXT_MUTED}; font-size: 8pt;")
        layout.addWidget(self.favorite_empty)
        self.favorite_add_btn = QPushButton("+ 添加文件夹")
        self.favorite_add_btn.setObjectName("flat")
        self.favorite_add_btn.clicked.connect(lambda: self._manage_favorites())
        layout.addWidget(self.favorite_add_btn)
        self.favorite_grid = QGridLayout(); self.favorite_grid.setContentsMargins(0, 0, 0, 0); self.favorite_grid.setHorizontalSpacing(6); self.favorite_grid.setVerticalSpacing(2)
        layout.addLayout(self.favorite_grid)
        self.favorite_view_all_btn = QPushButton("查看全部（0）")
        self.favorite_view_all_btn.setObjectName("flat")
        self.favorite_view_all_btn.clicked.connect(lambda: self._manage_favorites())
        layout.addWidget(self.favorite_view_all_btn)

        self._section_line(layout)
        hdr = QHBoxLayout(); self.pocket_title = QLabel("文件口袋"); self.pocket_title.setObjectName("title"); self.pocket_count = QLabel("0"); self.pocket_count.setStyleSheet(f"color: {theme.ACCENT}; font-weight: 600;"); hdr.addWidget(self.pocket_title); hdr.addStretch(); hdr.addWidget(self.pocket_count); layout.addLayout(hdr)
        self.pocket_items_layout = QVBoxLayout(); self.pocket_items_layout.setSpacing(2); layout.addLayout(self.pocket_items_layout)
        self.empty_label = QLabel("暂无内容 · 拖文件到角色即可暂存"); self.empty_label.setWordWrap(True); self.empty_label.setStyleSheet(f"color: {theme.TEXT_MUTED}; font-size: 8pt;"); layout.addWidget(self.empty_label)
        self.open_pocket_btn = QPushButton("打开文件口袋"); self.open_pocket_btn.setObjectName("primary"); self.open_pocket_btn.clicked.connect(self._open_pocket); layout.addWidget(self.open_pocket_btn)

        self._section_line(layout)
        remind_hdr = QHBoxLayout(); self.remind_title = QLabel("下个提醒"); self.remind_title.setObjectName("title"); self.remind_btn = QPushButton("+"); self.remind_btn.setObjectName("primary"); self.remind_btn.setFixedSize(28, 28); self.remind_btn.clicked.connect(self._open_add_reminder); remind_hdr.addWidget(self.remind_title); remind_hdr.addStretch(); remind_hdr.addWidget(self.remind_btn); layout.addLayout(remind_hdr)
        self.next_reminder_label = QLabel("暂无提醒"); self.next_reminder_label.setWordWrap(True); layout.addWidget(self.next_reminder_label)
        self.remind_items_layout = QVBoxLayout(); self.remind_items_layout.setSpacing(2); layout.addLayout(self.remind_items_layout)
        self.no_remind_label = QLabel("暂无提醒"); self.no_remind_label.setStyleSheet(f"color: {theme.TEXT_MUTED}; font-size: 8pt;"); self.no_remind_label.hide(); layout.addWidget(self.no_remind_label)
        self.open_reminders_btn = QPushButton("我的提醒"); self.open_reminders_btn.setObjectName("flat"); self.open_reminders_btn.clicked.connect(self._open_reminders); layout.addWidget(self.open_reminders_btn)
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
            button.setFixedWidth(max(96, (self.width() - 36) // 2))
            button.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
            label = f"{favorite.name}  ›" if exists else f"{favorite.name}  ⚠"
            text_width = max(24, button.width() - button.iconSize().width() - 26)
            button.setText(QFontMetrics(button.font()).elidedText(label, Qt.ElideRight, text_width))
            button.setToolTip(f"{favorite.name}\n{favorite.path}" + ("\n路径失效" if not exists else ""))
            button.setEnabled(True)  # keep the context menu available for repairing a missing path
            button.setFixedHeight(25)
            button.setStyleSheet(
                f"QToolButton {{ text-align:left; color:{theme.TEXT}; padding:3px 5px; border-radius:5px; }}"
                f"QToolButton:hover {{ background:{theme.BG}; }}"
                "QToolButton:disabled { color:#9ca3af; }"
            )
            if not exists:
                button.setStyleSheet(
                    f"QToolButton {{ text-align:left; color:#9ca3af; padding:3px 5px; border-radius:5px; }}"
                )
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
        ph = max(self.sizeHint().height() + 16, self.height())
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
