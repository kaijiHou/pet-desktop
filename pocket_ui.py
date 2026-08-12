"""Pocket list window and safe reference actions."""

import subprocess

from PyQt5.QtCore import QUrl, Qt
from PyQt5.QtGui import QDesktopServices
from PyQt5.QtWidgets import (
    QApplication,
    QDialog,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMenu,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)


class PocketDialog(QDialog):
    """Browse and manage Pocket references without deleting target files."""

    def __init__(self, service, parent=None):
        super().__init__(parent)
        self.service = service
        self.setWindowTitle("Pocket")
        self.setMinimumSize(520, 340)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Files and folders stay in their original locations."))
        self.empty_label = QLabel("Pocket is empty. Drag files or folders onto Clippy.")
        self.empty_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.empty_label)

        self.item_list = QListWidget()
        self.item_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.item_list.customContextMenuRequested.connect(self._show_context_menu)
        self.item_list.itemDoubleClicked.connect(lambda _: self.open_selected())
        layout.addWidget(self.item_list)

        row = QHBoxLayout()
        self.open_button = QPushButton("Open")
        self.reveal_button = QPushButton("Show in Explorer")
        self.copy_button = QPushButton("Copy Path")
        self.remove_button = QPushButton("Remove from Pocket")
        self.cleanup_button = QPushButton("Clean Missing")
        for button, handler in (
            (self.open_button, self.open_selected),
            (self.reveal_button, self.reveal_selected),
            (self.copy_button, self.copy_selected),
            (self.remove_button, self.remove_selected),
            (self.cleanup_button, self.cleanup_missing),
        ):
            button.clicked.connect(handler)
            row.addWidget(button)
        layout.addLayout(row)

        close_button = QPushButton("Close")
        close_button.clicked.connect(self.accept)
        layout.addWidget(close_button, alignment=Qt.AlignRight)
        self.refresh()

    def refresh(self):
        self.item_list.clear()
        for pocket_item in self.service.list_items():
            marker = "📁" if pocket_item.item_type == "directory" else "📄"
            suffix = "  [missing]" if not pocket_item.exists else ""
            item = QListWidgetItem(f"{marker} {pocket_item.name}{suffix}\n{pocket_item.path}")
            item.setData(Qt.UserRole, pocket_item.id)
            if not pocket_item.exists:
                item.setForeground(Qt.gray)
            self.item_list.addItem(item)
        has_items = self.item_list.count() > 0
        if has_items:
            self.item_list.setCurrentRow(0)
        self.item_list.setVisible(has_items)
        self.empty_label.setVisible(not has_items)
        for button in (self.open_button, self.reveal_button, self.copy_button, self.remove_button):
            button.setEnabled(has_items)

    def selected_item(self):
        current = self.item_list.currentItem()
        return self.service.get(current.data(Qt.UserRole)) if current else None

    def open_selected(self):
        item = self.selected_item()
        if item and item.exists:
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(item.path)))

    def reveal_selected(self):
        item = self.selected_item()
        if not item or not item.exists:
            return
        subprocess.Popen(
            ["explorer.exe", "/select,", str(item.path)],
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )

    def copy_selected(self):
        item = self.selected_item()
        if item:
            QApplication.clipboard().setText(str(item.path))

    def remove_selected(self, confirm=True):
        item = self.selected_item()
        if not item:
            return
        if confirm:
            answer = QMessageBox.question(
                self,
                "Remove from Pocket",
                "Remove this reference from Pocket? The original file will not be deleted.",
            )
            if answer != QMessageBox.Yes:
                return
        self.service.remove(item.id)
        self.refresh()

    def cleanup_missing(self):
        removed = self.service.cleanup_missing()
        self.refresh()
        return removed

    def _show_context_menu(self, position):
        if not self.selected_item():
            return
        menu = QMenu(self)
        actions = {
            menu.addAction("Open"): self.open_selected,
            menu.addAction("Show in Explorer"): self.reveal_selected,
            menu.addAction("Copy Path"): self.copy_selected,
            menu.addAction("Remove from Pocket"): self.remove_selected,
        }
        selected = menu.exec_(self.item_list.mapToGlobal(position))
        if selected in actions:
            actions[selected]()
