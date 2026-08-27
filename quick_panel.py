"""Today's assistant panel: wage snapshot first, pocket and reminders below."""

from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame
import theme


class QuickPanel(QWidget):
    ITEM_PREVIEW = 3

    def __init__(self, pet_window, parent=None):
        super().__init__(parent)
        self.pet = pet_window
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
        layout = QVBoxLayout(card); layout.setContentsMargins(14, 12, 14, 12); layout.setSpacing(7)
        top = QHBoxLayout(); title = QLabel("今日助手"); title.setObjectName("title")
        close = QPushButton("✕"); close.setObjectName("flat"); close.setFixedSize(24, 24); close.clicked.connect(self.hide); self.panel_close_btn = close
        top.addWidget(title); top.addStretch(); top.addWidget(close); layout.addLayout(top)

        self.wage_status = QLabel("工资统计未配置"); self.wage_status.setObjectName("title")
        self.wage_amount = QLabel("设置工资与工作时间"); self.wage_amount.setStyleSheet(f"font-size: 16pt; font-weight: 700; color: {theme.ACCENT};")
        self.wage_detail = QLabel(""); self.wage_detail.setWordWrap(True)
        self.wage_setup_btn = QPushButton("设置工资与工作时间"); self.wage_setup_btn.setObjectName("primary"); self.wage_setup_btn.clicked.connect(self._open_wage_settings)
        layout.addWidget(self.wage_status); layout.addWidget(self.wage_amount); layout.addWidget(self.wage_detail); layout.addWidget(self.wage_setup_btn)
        wage_buttons = QHBoxLayout(); self.clock_out_btn = QPushButton("下班打卡"); self.clock_out_btn.setObjectName("primary"); self.clock_out_btn.clicked.connect(self._clock_out); self.calendar_btn = QPushButton("工时日历"); self.calendar_btn.clicked.connect(self._open_calendar)
        wage_buttons.addWidget(self.clock_out_btn); wage_buttons.addWidget(self.calendar_btn); layout.addLayout(wage_buttons)

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
            lbl = QLabel(f"  {item.name if item.exists else item.name + ' [missing]'}"); lbl.setStyleSheet(f"font-size: 8pt; color: {theme.TEXT}; padding: 1px 0;"); self.pocket_items_layout.addWidget(lbl)
        if len(items) > self.ITEM_PREVIEW:
            lbl = QLabel(f"  还有 {len(items) - self.ITEM_PREVIEW} 项..."); lbl.setStyleSheet(f"font-size: 8pt; color: {theme.TEXT_MUTED};"); self.pocket_items_layout.addWidget(lbl)
        reminders = self.pet.reminder.list_reminders(); self._clear(self.remind_items_layout)
        if reminders:
            first = reminders[0]; self.next_reminder_label.setText(f"{first.due_at:%m-%d %H:%M}  {first.content}"); self.no_remind_label.hide()
            for rem in reminders[1:3]:
                lbl = QLabel(f"  {rem.due_at:%m-%d %H:%M}  {rem.content}"); lbl.setWordWrap(True); lbl.setStyleSheet(f"font-size: 8pt; color: {theme.TEXT}; padding: 1px 0;"); self.remind_items_layout.addWidget(lbl)
        else:
            self.next_reminder_label.setText("暂无提醒"); self.no_remind_label.show()

    refresh = _refresh
    def _open_pocket(self): self.pet._open_pocket(); self.hide()
    def _open_add_reminder(self): self.pet._open_add_reminder(); self._refresh()
    def _open_reminders(self): self.pet._open_reminders(); self._refresh()
    def _open_calendar(self): self.pet._open_calendar(); self._refresh()
    def _open_wage_settings(self): self.pet._open_wage_settings(); self._refresh()
    def _clock_out(self): self.pet._clock_out(); self._refresh()
    def showNear(self, pet_window): self.move_near(pet_window.geometry(), live=False, screen=pet_window.screen())

    def move_near(self, anchor_rect, live=False, screen=None):
        from PyQt5.QtWidgets import QApplication
        scr = screen or QApplication.screenAt(anchor_rect.center()) or QApplication.primaryScreen(); avail = scr.availableGeometry(); self.adjustSize(); pw = self.width(); ph = max(self.sizeHint().height() + 16, self.height()); x, y = anchor_rect.right() + 8, anchor_rect.top()
        if x + pw - 1 > avail.right(): x = anchor_rect.left() - pw - 8
        if y + ph - 1 > avail.bottom(): y = avail.bottom() - ph + 1
        x = max(avail.left(), min(x, avail.right() - pw + 1)); y = max(avail.top(), min(y, avail.bottom() - ph + 1)); self.setGeometry(x, y, pw, ph)
        if not live: self.show(); self.raise_(); self.activateWindow()
    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape: self.hide()
    def focusOutEvent(self, event): QTimer.singleShot(150, self._check_focus_close)
    def _check_focus_close(self):
        if not self.isActiveWindow() and not self.pet.geometry().intersects(self.geometry()): self.hide()
