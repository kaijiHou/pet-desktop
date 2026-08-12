"""Dialogs for creating and managing local reminders."""

from datetime import datetime, timedelta

from PyQt5.QtCore import QDate, Qt, QTime
from PyQt5.QtWidgets import (
    QDateEdit,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QTimeEdit,
    QVBoxLayout,
)


class AddReminderDialog(QDialog):
    """Collect reminder content plus a local date and time."""

    def __init__(self, parent=None, now_provider=None):
        super().__init__(parent)
        self._now = now_provider or datetime.now
        self.setWindowTitle("Add Reminder")
        self.setMinimumWidth(360)

        default_due = self._now() + timedelta(minutes=5)
        layout = QFormLayout(self)
        self.content_edit = QLineEdit()
        self.content_edit.setPlaceholderText("What should Clippy remind you about?")
        layout.addRow("Reminder:", self.content_edit)

        self.date_edit = QDateEdit(QDate(default_due.year, default_due.month, default_due.day))
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDisplayFormat("yyyy-MM-dd")
        layout.addRow("Date:", self.date_edit)

        self.time_edit = QTimeEdit(QTime(default_due.hour, default_due.minute))
        self.time_edit.setDisplayFormat("HH:mm")
        layout.addRow("Time:", self.time_edit)

        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    def values(self) -> tuple[str, datetime]:
        date = self.date_edit.date()
        time = self.time_edit.time()
        due_at = datetime(date.year(), date.month(), date.day(), time.hour(), time.minute())
        return self.content_edit.text().strip(), due_at

    def accept(self):
        content, _ = self.values()
        if not content:
            QMessageBox.warning(self, "Missing reminder", "Please enter what you want to remember.")
            self.content_edit.setFocus()
            return
        super().accept()


class ReminderListDialog(QDialog):
    """Show pending reminders and allow deleting the selected item."""

    def __init__(self, service, parent=None):
        super().__init__(parent)
        self.service = service
        self.setWindowTitle("My Reminders")
        self.setMinimumSize(440, 300)

        layout = QVBoxLayout(self)
        self.empty_label = QLabel("No pending reminders.")
        self.empty_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.empty_label)
        self.reminder_list = QListWidget()
        layout.addWidget(self.reminder_list)

        row = QHBoxLayout()
        self.delete_button = QPushButton("Delete")
        self.delete_button.clicked.connect(self.delete_selected)
        close_button = QPushButton("Close")
        close_button.clicked.connect(self.accept)
        row.addWidget(self.delete_button)
        row.addStretch()
        row.addWidget(close_button)
        layout.addLayout(row)
        self.refresh()

    def refresh(self):
        self.reminder_list.clear()
        for reminder in self.service.list_reminders():
            text = f"{reminder.due_at:%Y-%m-%d %H:%M}  —  {reminder.content}"
            item = QListWidgetItem(text)
            item.setData(Qt.UserRole, reminder.id)
            self.reminder_list.addItem(item)
        has_items = self.reminder_list.count() > 0
        if has_items:
            self.reminder_list.setCurrentRow(0)
        self.reminder_list.setVisible(has_items)
        self.empty_label.setVisible(not has_items)
        self.delete_button.setEnabled(has_items)

    def delete_selected(self):
        item = self.reminder_list.currentItem()
        if item and self.service.remove_reminder(item.data(Qt.UserRole)):
            self.refresh()
