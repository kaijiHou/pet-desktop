"""Dialogs for creating and managing local reminders (V2: Chinese, quick times)."""
from datetime import datetime, timedelta
from PyQt5.QtCore import QDate, Qt, QTime
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import (
    QDateEdit, QDialog, QDialogButtonBox, QFormLayout, QHBoxLayout,
    QLabel, QLineEdit, QListWidget, QListWidgetItem, QMessageBox,
    QPushButton, QTimeEdit, QVBoxLayout,
)
import theme


class AddReminderDialog(QDialog):
    """V2: Chinese labels, quick-time buttons."""

    def __init__(self, parent=None, now_provider=None):
        super().__init__(parent)
        self._now = now_provider or datetime.now
        self.setWindowTitle("新建提醒")
        self.setMinimumWidth(380)

        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        # Title
        lbl = QLabel("提醒我")
        lbl.setObjectName("title")
        layout.addWidget(lbl)

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
        date_col.addWidget(self.date_edit)
        dt_layout.addLayout(date_col)

        time_col = QVBoxLayout()
        time_col.addWidget(QLabel("时间"))
        self.time_edit = QTimeEdit(QTime(default_due.hour, default_due.minute))
        self.time_edit.setDisplayFormat("HH:mm")
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

        # Buttons
        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.button(QDialogButtonBox.Save).setText("保存提醒")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

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


class ReminderListDialog(QDialog):
    """V2: Chinese labels, grouped by date, edit + snooze."""

    def __init__(self, service, parent=None):
        super().__init__(parent)
        self.service = service
        self.setWindowTitle("我的提醒")
        self.setMinimumSize(460, 320)

        layout = QVBoxLayout(self)

        self.empty_label = QLabel("暂无提醒")
        self.empty_label.setAlignment(Qt.AlignCenter)
        self.empty_label.setStyleSheet(f"color: {theme.TEXT_MUTED};")
        layout.addWidget(self.empty_label)

        self.reminder_list = QListWidget()
        self.reminder_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.reminder_list.customContextMenuRequested.connect(self._show_menu)
        layout.addWidget(self.reminder_list)

        row = QHBoxLayout()
        self.add_button = QPushButton("新建提醒")
        self.add_button.setObjectName("primary")
        self.add_button.clicked.connect(self._add_reminder)
        self.delete_button = QPushButton("删除")
        self.delete_button.setObjectName("danger")
        self.delete_button.clicked.connect(self.delete_selected)
        close_button = QPushButton("关闭")
        close_button.clicked.connect(self.accept)
        row.addWidget(self.add_button)
        row.addWidget(self.delete_button)
        row.addStretch()
        row.addWidget(close_button)
        layout.addLayout(row)
        self.refresh()

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
            self.reminder_list.addItem(header)
            for rem in items:
                text = f"  {rem.due_at:%H:%M}  {rem.content}"
                item = QListWidgetItem(text)
                item.setData(Qt.UserRole, rem.id)
                self.reminder_list.addItem(item)

        has_items = len(reminders) > 0
        self.reminder_list.setVisible(has_items)
        self.empty_label.setVisible(not has_items)
        self.delete_button.setEnabled(has_items)

    def delete_selected(self):
        item = self.reminder_list.currentItem()
        if item and self.service.remove_reminder(item.data(Qt.UserRole)):
            self.refresh()

    def _add_reminder(self):
        from pet_window import AddReminderDialog
        d = AddReminderDialog(self)
        if d.exec_():
            content, due_at = d.values()
            self.service.add_reminder(content, due_at)
            self.refresh()

    def _show_menu(self, pos):
        item = self.reminder_list.itemAt(pos)
        if not item or not item.data(Qt.UserRole):
            return
        menu = QMenu(self)
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
        if d.exec_():
            content, due_at = d.values()
            self.service.remove_reminder(rid)
            self.service.add_reminder(content, due_at)
            self.refresh()

    def _delete(self, item):
        if self.service.remove_reminder(item.data(Qt.UserRole)):
            self.refresh()
