"""Pocket list window and safe reference actions."""

import subprocess

from PyQt5.QtCore import QMimeData, QUrl, Qt
from PyQt5.QtGui import QDesktopServices, QDrag
from PyQt5.QtWidgets import (
    QApplication,
    QDialog,
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMenu,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)

from file_ops import FileOperationService
from destinations import DestinationService


class PocketListWidget(QListWidget):
    """List that exports selected existing paths as standard file URLs."""

    def __init__(self, service, parent=None):
        super().__init__(parent)
        self.service = service
        self.setDragEnabled(True)

    def mime_data_for_selected(self):
        urls = []
        for list_item in self.selectedItems():
            pocket_item = self.service.get(list_item.data(Qt.UserRole))
            if pocket_item and pocket_item.exists:
                urls.append(QUrl.fromLocalFile(str(pocket_item.path)))
        if not urls:
            return None
        mime = QMimeData()
        mime.setUrls(urls)
        return mime

    def startDrag(self, supported_actions):
        mime = self.mime_data_for_selected()
        if mime is None:
            return
        drag = QDrag(self)
        drag.setMimeData(mime)
        drag.exec_(Qt.CopyAction)


class PocketDialog(QDialog):
    """Browse and manage Pocket references without deleting target files."""

    def __init__(self, service, parent=None, file_operations=None, destinations=None):
        super().__init__(parent)
        self.service = service
        self.file_operations = file_operations or FileOperationService()
        self.destinations = destinations or DestinationService()
        self.setWindowTitle("Pocket")
        self.setMinimumSize(520, 340)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Files and folders stay in their original locations."))
        self.empty_label = QLabel("Pocket is empty. Drag files or folders onto Clippy.")
        self.empty_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.empty_label)

        self.item_list = PocketListWidget(service)
        self.item_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.item_list.customContextMenuRequested.connect(self._show_context_menu)
        self.item_list.itemDoubleClicked.connect(lambda _: self.open_selected())
        layout.addWidget(self.item_list)

        row = QHBoxLayout()
        self.open_button = QPushButton("Open")
        self.reveal_button = QPushButton("Show in Explorer")
        self.copy_button = QPushButton("Copy Path")
        self.copy_to_button = QPushButton("Copy To…")
        self.move_to_button = QPushButton("Move To…")
        self.remove_button = QPushButton("Remove from Pocket")
        self.cleanup_button = QPushButton("Clean Missing")
        for button, handler in (
            (self.open_button, self.open_selected),
            (self.reveal_button, self.reveal_selected),
            (self.copy_button, self.copy_selected),
            (self.copy_to_button, self.copy_selected_to),
            (self.move_to_button, self.move_selected_to),
            (self.remove_button, self.remove_selected),
            (self.cleanup_button, self.cleanup_missing),
        ):
            button.clicked.connect(handler)
            row.addWidget(button)
        layout.addLayout(row)

        favorite_row = QHBoxLayout()
        favorite_row.addWidget(QLabel("Favorite destination:"))
        self.favorite_combo = QComboBox()
        favorite_row.addWidget(self.favorite_combo, 1)
        self.add_favorite_button = QPushButton("Add Favorite…")
        self.remove_favorite_button = QPushButton("Remove Favorite")
        self.copy_favorite_button = QPushButton("Copy to Favorite")
        self.move_favorite_button = QPushButton("Move to Favorite")
        self.add_favorite_button.clicked.connect(self.add_favorite)
        self.remove_favorite_button.clicked.connect(self.remove_favorite)
        self.copy_favorite_button.clicked.connect(lambda: self.perform_favorite("copy"))
        self.move_favorite_button.clicked.connect(lambda: self.perform_favorite("move"))
        for button in (self.add_favorite_button, self.remove_favorite_button,
                       self.copy_favorite_button, self.move_favorite_button):
            favorite_row.addWidget(button)
        layout.addLayout(favorite_row)

        recent_row = QHBoxLayout()
        recent_row.addWidget(QLabel("Recent destination:"))
        self.recent_combo = QComboBox()
        recent_row.addWidget(self.recent_combo, 1)
        self.copy_recent_button = QPushButton("Copy to Recent")
        self.move_recent_button = QPushButton("Move to Recent")
        self.clear_recents_button = QPushButton("Clear Recents")
        self.copy_recent_button.clicked.connect(lambda: self.perform_recent("copy"))
        self.move_recent_button.clicked.connect(lambda: self.perform_recent("move"))
        self.clear_recents_button.clicked.connect(self.clear_recents)
        for button in (self.copy_recent_button, self.move_recent_button, self.clear_recents_button):
            recent_row.addWidget(button)
        layout.addLayout(recent_row)

        close_button = QPushButton("Close")
        close_button.clicked.connect(self.accept)
        layout.addWidget(close_button, alignment=Qt.AlignRight)
        self.refresh()
        self.refresh_favorites()
        self.refresh_recents()

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
        for button in (
            self.open_button, self.reveal_button, self.copy_button,
            self.copy_to_button, self.move_to_button, self.remove_button,
        ):
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

    def copy_selected_to(self):
        destination = QFileDialog.getExistingDirectory(self, "Copy To")
        if destination:
            self.perform_selected("copy", destination)

    def move_selected_to(self):
        destination = QFileDialog.getExistingDirectory(self, "Move To")
        if destination:
            self.perform_selected("move", destination)

    def perform_selected(self, action, destination, notify=True):
        item = self.selected_item()
        if not item:
            return None
        operation = self.file_operations.copy if action == "copy" else self.file_operations.move
        report = operation([item.path], destination)
        if action == "move" and report.succeeded:
            result = next(result for result in report.items if result.status == "succeeded")
            self.service.replace_path(item.id, result.destination)
            self.refresh()
        if report.succeeded:
            self.destinations.record_recent(destination)
            self.refresh_recents()
        if notify:
            QMessageBox.information(
                self,
                f"{action.title()} complete",
                f"Succeeded: {report.succeeded}\nSkipped: {report.skipped}\nFailed: {report.failed}",
            )
        return report

    def refresh_favorites(self):
        self.favorite_combo.clear()
        for favorite in self.destinations.list_favorites():
            suffix = " [missing]" if not favorite.exists else ""
            self.favorite_combo.addItem(f"{favorite.name}{suffix}", favorite.id)
        has_favorites = self.favorite_combo.count() > 0
        self.remove_favorite_button.setEnabled(has_favorites)
        self.copy_favorite_button.setEnabled(has_favorites)
        self.move_favorite_button.setEnabled(has_favorites)

    def add_favorite(self):
        path = QFileDialog.getExistingDirectory(self, "Add Favorite Destination")
        if path:
            self.destinations.add_favorite(path)
            self.refresh_favorites()

    def remove_favorite(self):
        favorite_id = self.favorite_combo.currentData()
        if favorite_id:
            self.destinations.remove_favorite(favorite_id)
            self.refresh_favorites()

    def perform_favorite(self, action, notify=True):
        favorite = self.destinations.get_favorite(self.favorite_combo.currentData())
        if not favorite or not favorite.exists:
            return None
        return self.perform_selected(action, favorite.path, notify=notify)

    def refresh_recents(self):
        self.recent_combo.clear()
        for recent in self.destinations.list_recents():
            suffix = " [missing]" if not recent.exists else ""
            self.recent_combo.addItem(f"{recent.name}{suffix}", recent.id)
        has_recents = self.recent_combo.count() > 0
        self.copy_recent_button.setEnabled(has_recents)
        self.move_recent_button.setEnabled(has_recents)
        self.clear_recents_button.setEnabled(has_recents)

    def perform_recent(self, action, notify=True):
        recent = self.destinations.get_recent(self.recent_combo.currentData())
        if not recent or not recent.exists:
            return None
        return self.perform_selected(action, recent.path, notify=notify)

    def clear_recents(self):
        self.destinations.clear_recents()
        self.refresh_recents()

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
            menu.addAction("Copy To…"): self.copy_selected_to,
            menu.addAction("Move To…"): self.move_selected_to,
            menu.addAction("Remove from Pocket"): self.remove_selected,
        }
        selected = menu.exec_(self.item_list.mapToGlobal(position))
        if selected in actions:
            actions[selected]()
