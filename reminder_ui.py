"""Dialogs for creating and managing local reminders (V2: Chinese, quick times)."""
from datetime import datetime, timedelta
from PyQt5.QtCore import QDate, QSize, Qt, QTime
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import (
    QDateEdit, QDialog, QHBoxLayout,
    QLabel, QLineEdit, QListWidget, QListWidgetItem, QMessageBox,
    QPushButton, QTimeEdit, QVBoxLayout, QSpinBox, QWidget,
)
import theme
from ui.modern import ModernDialog, ModernComboBox, PrimaryButton, SecondaryButton, RoundedMenu


def _layout_widget(layout):
    widget = QWidget(); widget.setLayout(layout); return widget


class AddReminderDialog(ModernDialog):
    """V2: Chinese labels, quick-time buttons."""

    def __init__(self, parent=None, now_provider=None):
        super().__init__("新建提醒", "一次提醒、每天或按间隔重复", parent, min_width=460, resizable=True)
        self._now = now_provider or datetime.now
        self.setWindowTitle("新建提醒")

        self.resize(500, 430)
        layout = self.body
        layout.setSpacing(10)

        # Content
        self.content_edit = QLineEdit()
        self.content_edit.setPlaceholderText("输入提醒内容...")
        layout.addWidget(self.content_edit)

        # Date + Time
        default_due = self._now() + timedelta(minutes=5)
        dt_layout = QHBoxLayout()
        dt_layout.setSpacing(8)

        date_col = QVBoxLayout()
        date_col.addWidget(QLabel("日期"))
        self.date_edit = QDateEdit(QDate(default_due.year, default_due.month, default_due.day))
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDisplayFormat("yyyy-MM-dd")
        self.date_edit.setMinimumHeight(38)
        date_col.addWidget(self.date_edit)
        dt_layout.addLayout(date_col)

        time_col = QVBoxLayout()
        time_col.addWidget(QLabel("时间"))
        self.time_edit = QTimeEdit(QTime(default_due.hour, default_due.minute))
        self.time_edit.setDisplayFormat("HH:mm")
        self.time_edit.setMinimumHeight(38)
        time_col.addWidget(self.time_edit)
        dt_layout.addLayout(time_col)

        layout.addLayout(dt_layout)

        # Quick times
        qt_layout = QHBoxLayout()
        qt_layout.setSpacing(6)
        for text, delta in [("10分钟后", timedelta(minutes=10)),
                             ("1小时后", timedelta(hours=1)),
                             ("今天晚上", self._tonight()),
                             ("明天", self._tomorrow())]:
            btn = QPushButton(text)
            btn.setObjectName("flat")
            btn.clicked.connect(lambda checked, d=delta: self._apply_quick(d))
            qt_layout.addWidget(btn)
        qt_layout.addStretch()
        layout.addLayout(qt_layout)

        repeat_row = QHBoxLayout()
        repeat_row.addWidget(QLabel("重复"))
        self.repeat_combo = ModernComboBox()
        for label, value in (("仅一次", ""), ("每天", "daily"), ("每隔一段时间", "interval"), ("每月", "monthly")):
            self.repeat_combo.addItem(label, value)
        repeat_row.addWidget(self.repeat_combo, 1); layout.addLayout(repeat_row)
        self.interval_host = QWidget()
        self.interval_host.setObjectName("reminderInterval")
        self.interval_host.setStyleSheet("QWidget#reminderInterval { background: transparent; }")
        interval_row = QHBoxLayout(self.interval_host); interval_row.setContentsMargins(0, 0, 0, 0)
        interval_row.addWidget(QLabel("每隔"))
        self.interval_spin = QSpinBox(); self.interval_spin.setRange(1, 999); self.interval_spin.setValue(30)
        self.interval_spin.setMinimumHeight(38); interval_row.addWidget(self.interval_spin)
        self.interval_unit = ModernComboBox(); self.interval_unit.addItem("分钟", 1); self.interval_unit.addItem("小时", 60)
        interval_row.addWidget(self.interval_unit); interval_row.addWidget(QLabel("提醒一次"))
        layout.addWidget(self.interval_host)
        self.repeat_hint = QLabel(); self.repeat_hint.setObjectName("muted"); self.repeat_hint.setWordWrap(True)
        layout.addWidget(self.repeat_hint)
        self.repeat_combo.currentIndexChanged.connect(self._update_repeat)
        self._update_repeat()

        # Buttons
        cancel = SecondaryButton("取消"); cancel.clicked.connect(self.reject); self.add_footer(cancel)
        save = PrimaryButton("保存提醒"); save.clicked.connect(self.accept); self.add_footer(save)

    def _update_repeat(self):
        repeat = self.repeat_combo.currentData()
        self.interval_host.setVisible(repeat == "interval")
        self.repeat_hint.setText({"": "在所选日期和时间提醒一次。", "daily": "从所选日期开始，每天在这个时间提醒。",
                                  "interval": "从所选日期和时间开始，按上述间隔重复提醒。",
                                  "monthly": "每月顺延一次；遇到短月份，取当月最后一天。"}[repeat])

    def recurrence_values(self):
        repeat = self.repeat_combo.currentData()
        minutes = self.interval_spin.value() * self.interval_unit.currentData() if repeat == "interval" else 0
        return {"recurrence": repeat, "interval_minutes": minutes}

    def set_recurrence(self, repeat, minutes=0):
        self.repeat_combo.setCurrentIndex(max(0, self.repeat_combo.findData(repeat)))
        if repeat == "interval":
            unit = 60 if minutes and minutes % 60 == 0 else 1
            self.interval_unit.setCurrentIndex(self.interval_unit.findData(unit))
            self.interval_spin.setValue(max(1, minutes // unit))

    def _tonight(self):
        n = self._now()
        target = n.replace(hour=20, minute=0, second=0, microsecond=0)
        if target <= n:
            target += timedelta(days=1)
        return target - n

    def _tomorrow(self):
        n = self._now()
        target = n.replace(hour=9, minute=0, second=0, microsecond=0) + timedelta(days=1)
        return target - n

    def _apply_quick(self, delta):
        target = self._now() + delta
        self.date_edit.setDate(QDate(target.year, target.month, target.day))
        self.time_edit.setTime(QTime(target.hour, target.minute))

    def values(self):
        date = self.date_edit.date()
        time = self.time_edit.time()
        due_at = datetime(date.year(), date.month(), date.day(), time.hour(), time.minute())
        return self.content_edit.text().strip(), due_at

    def accept(self):
        content, _ = self.values()
        if not content:
            QMessageBox.warning(self, "提醒内容不能为空", "请输入你想提醒的内容。")
            self.content_edit.setFocus()
            return
        super().accept()


class ReminderListDialog(ModernDialog):
    """V2: Chinese labels, grouped by date, edit + snooze.

    V5.18: migrated onto ModernDialog (theme card + blur auto-close), and
    编辑 is now a visible button / double-click — it used to hide in the
    right-click menu only (user could not modify existing reminders).
    """

    def __init__(self, service, parent=None):
        super().__init__("我的提醒", "双击条目可编辑；右键还有稍后提醒", parent,
                         min_width=470, min_height=380, resizable=True)
        self.service = service
        self.setWindowTitle("我的提醒")

        self.empty_label = QLabel("暂无提醒 · 点下方新建")
        self.empty_label.setAlignment(Qt.AlignCenter)
        self.empty_label.setObjectName("muted")
        self.add_body(self.empty_label)

        self.reminder_list = QListWidget()
        self.reminder_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.reminder_list.customContextMenuRequested.connect(self._show_menu)
        self.reminder_list.itemDoubleClicked.connect(
            lambda item: self._edit(item) if item.data(Qt.UserRole) else None)
        self.reminder_list.itemSelectionChanged.connect(self._on_selection)
        self.add_body(self.reminder_list)

        row = QHBoxLayout()
        self.add_button = PrimaryButton("新建提醒")
        self.add_button.clicked.connect(self._add_reminder)
        self.edit_button = SecondaryButton("编辑")
        self.edit_button.setEnabled(False)
        self.edit_button.clicked.connect(self.edit_selected)
        self.delete_button = SecondaryButton("删除")
        self.delete_button.setObjectName("danger")
        self.delete_button.setEnabled(False)
        self.delete_button.clicked.connect(self.delete_selected)
        close_button = SecondaryButton("关闭")
        close_button.clicked.connect(self.accept)
        row.addWidget(self.add_button)
        row.addWidget(self.edit_button)
        row.addWidget(self.delete_button)
        row.addStretch()
        row.addWidget(close_button)
        self.add_body(_layout_widget(row))
        self.refresh()

    def _on_selection(self):
        item = self.reminder_list.currentItem()
        editable = item is not None and item.data(Qt.UserRole)
        self.edit_button.setEnabled(bool(editable))
        self.delete_button.setEnabled(bool(editable))

    def edit_selected(self):
        item = self.reminder_list.currentItem()
        if item and item.data(Qt.UserRole):
            self._edit(item)

    def _layout_row(self):
        raise NotImplementedError

    def refresh(self):
        self.reminder_list.clear()
        reminders = self.service.list_reminders()
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        tomorrow = today + timedelta(days=1)

        def _group(d):
            if d < today: return "已过期"
            if d < tomorrow: return "今天"
            if d < tomorrow + timedelta(days=1): return "明天"
            return "未来"

        groups = {}
        for rem in reminders:
            g = _group(rem.due_at)
            groups.setdefault(g, []).append(rem)

        order = ["已过期", "今天", "明天", "未来"]
        for grp_name in order:
            items = groups.get(grp_name, [])
            if not items:
                continue
            header = QListWidgetItem(f"  {grp_name}")
            header.setFlags(Qt.NoItemFlags)
            header.setForeground(QColor(theme.TEXT_MUTED))
            header.setSizeHint(QSize(0, 30))
            self.reminder_list.addItem(header)
            for rem in items:
                rule = {"daily": "每天", "monthly": "每月", "interval": f"每隔 {rem.interval_minutes} 分钟"}.get(rem.recurrence, "")
                text = f"  {rem.due_at:%m-%d %H:%M}  {rem.content}" + (f" · {rule}" if rule else "")
                item = QListWidgetItem(text)
                item.setData(Qt.UserRole, rem.id)
                item.setSizeHint(QSize(0, 36))
                self.reminder_list.addItem(item)

        has_items = len(reminders) > 0
        self.reminder_list.setVisible(has_items)
        self.empty_label.setVisible(not has_items)
        self._on_selection()

    def delete_selected(self):
        item = self.reminder_list.currentItem()
        if item and self.service.remove_reminder(item.data(Qt.UserRole)):
            self.refresh()

    def _add_reminder(self):
        from pet_window import AddReminderDialog
        d = AddReminderDialog(self)
        if d.exec_():
            content, due_at = d.values()
            self.service.add_reminder(content, due_at, **d.recurrence_values())
            self.refresh()

    def _show_menu(self, pos):
        item = self.reminder_list.itemAt(pos)
        if not item or not item.data(Qt.UserRole):
            return
        menu = RoundedMenu(self)
        menu.addAction("编辑").triggered.connect(lambda: self._edit(item))
        menu.addAction("稍后提醒 (10分钟)").triggered.connect(lambda: self._snooze(item, 10))
        menu.addAction("删除").triggered.connect(lambda: self._delete(item))
        menu.exec_(self.reminder_list.mapToGlobal(pos))

    def _snooze(self, item, minutes):
        rid = item.data(Qt.UserRole)
        try:
            self.service.snooze_reminder(rid, minutes)
            self.refresh()
        except (KeyError, ValueError):
            pass

    def _edit(self, item):
        rid = item.data(Qt.UserRole)
        reminders = self.service.list_reminders()
        rem = next((r for r in reminders if r.id == rid), None)
        if not rem:
            return
        d = AddReminderDialog(self)
        d.content_edit.setText(rem.content)
        d.date_edit.setDate(QDate(rem.due_at.year, rem.due_at.month, rem.due_at.day))
        d.time_edit.setTime(QTime(rem.due_at.hour, rem.due_at.minute))
        d.set_recurrence(rem.recurrence, rem.interval_minutes)
        if d.exec_():
            content, due_at = d.values()
            self.service.add_reminder(content, due_at, **d.recurrence_values())
            self.service.remove_reminder(rid)
            self.refresh()

    def _delete(self, item):
        if self.service.remove_reminder(item.data(Qt.UserRole)):
            self.refresh()
