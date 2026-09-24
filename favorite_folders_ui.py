"""Modern manager for the existing favorite-folder records."""

from pathlib import Path

from PyQt5.QtCore import Qt, QUrl, QFileInfo, pyqtSignal
from PyQt5.QtGui import QDesktopServices, QFontMetrics
from PyQt5.QtWidgets import (
    QApplication, QFileDialog, QFileIconProvider, QFrame, QHBoxLayout,
    QLabel, QMenu, QPushButton, QVBoxLayout, QScrollArea, QWidget,
)

from destinations import DestinationService, MAX_FAVORITES
from ui.modern.cards import Card
from ui.modern.dialog import ModernConfirmDialog, ModernDialog, ModernTextInputDialog
from ui.modern.message import InlineBanner


class FavoriteFoldersDialog(ModernDialog):
    """Edit favorite references without modifying the folders themselves."""

    favorites_changed = pyqtSignal()

    def __init__(self, destinations=None, parent=None, *, focus_id=None, focus_action=None):
        super().__init__(
            "常用文件夹", "固定常用位置；移除只取消固定，不会删除实际文件夹。",
            parent=parent, min_width=600, min_height=380, resizable=True,
        )
        self.destinations = destinations or DestinationService()
        self.selected_favorite_id = focus_id
        self._pending_focus_action = focus_action
        self.resize(660, 520)

        toolbar = QHBoxLayout()
        self.add_button = QPushButton("添加文件夹")
        self.add_button.setObjectName("primary")
        self.add_button.clicked.connect(self._choose_folder)
        toolbar.addWidget(self.add_button)
        toolbar.addStretch()
        self.count_label = QLabel()
        self.count_label.setObjectName("muted")
        toolbar.addWidget(self.count_label)
        self.add_body_widget = QFrame()
        self.add_body_widget.setLayout(toolbar)
        self.add_body(self.add_body_widget)

        self.banner = InlineBanner()
        self.banner.hide()
        self.add_body(self.banner)
        self.empty_label = QLabel("还没有常用文件夹。添加后可在桌面助手和文件口袋中快速访问。")
        self.empty_label.setWordWrap(True)
        self.empty_label.setAlignment(Qt.AlignCenter)
        self.empty_label.setObjectName("muted")
        self.add_body(self.empty_label)

        self.list_scroll = QScrollArea()
        self.list_scroll.setWidgetResizable(True)
        self.list_scroll.setFrameShape(QFrame.NoFrame)
        self.list_frame = QWidget()
        self.list_layout = QVBoxLayout(self.list_frame)
        self.list_layout.setContentsMargins(0, 0, 0, 0)
        self.list_layout.setSpacing(8)
        self.list_scroll.setWidget(self.list_frame)
        self.add_body(self.list_scroll)

        close_button = QPushButton("完成")
        close_button.setObjectName("secondary")
        close_button.clicked.connect(self.accept)
        self.add_footer(close_button)

        self.rows_by_id = {}
        self.refresh()

    def refresh(self):
        self._clear_rows()
        favorites = self.destinations.list_favorites()
        self.count_label.setText(f"{len(favorites)} / {MAX_FAVORITES}")
        self.add_button.setEnabled(len(favorites) < MAX_FAVORITES)
        self.empty_label.setVisible(not favorites)
        self.list_scroll.setVisible(bool(favorites))
        provider = QFileIconProvider()
        for index, favorite in enumerate(favorites):
            card = Card()
            row = QHBoxLayout(card)
            row.setContentsMargins(12, 9, 10, 9)
            row.setSpacing(10)

            icon = QLabel()
            icon.setPixmap(provider.icon(QFileInfo(str(favorite.path))).pixmap(28, 28))
            row.addWidget(icon)

            details = QVBoxLayout()
            details.setSpacing(2)
            name = QLabel(favorite.name)
            name.setStyleSheet("font-weight: 600;")
            name.setToolTip(favorite.name)
            full_path = str(favorite.path)
            path = QLabel(QFontMetrics(self.font()).elidedText(full_path, Qt.ElideMiddle, 320))
            path.setObjectName("muted")
            path.setTextInteractionFlags(Qt.TextSelectableByMouse)
            path.setToolTip(full_path)
            path.setWordWrap(False)
            details.addWidget(name)
            details.addWidget(path)
            if not favorite.exists:
                missing = QLabel("路径失效")
                missing.setStyleSheet("color: #c2410c; font-size: 11px;")
                details.addWidget(missing)
            row.addLayout(details, 1)

            open_button = QPushButton("打开")
            open_button.setObjectName("secondary")
            open_button.setEnabled(favorite.exists)
            open_button.clicked.connect(lambda _=False, fid=favorite.id: self._open_favorite(fid))
            row.addWidget(open_button)

            up_button = QPushButton("↑")
            up_button.setObjectName("secondary")
            up_button.setFixedWidth(34)
            up_button.setToolTip("上移")
            up_button.setEnabled(index > 0)
            up_button.clicked.connect(lambda _=False, fid=favorite.id: self._move_favorite(fid, -1))
            row.addWidget(up_button)

            down_button = QPushButton("↓")
            down_button.setObjectName("secondary")
            down_button.setFixedWidth(34)
            down_button.setToolTip("下移")
            down_button.setEnabled(index < len(favorites) - 1)
            down_button.clicked.connect(lambda _=False, fid=favorite.id: self._move_favorite(fid, 1))
            row.addWidget(down_button)

            menu_button = QPushButton("⋯")
            menu_button.setObjectName("secondary")
            menu_button.setFixedWidth(36)
            menu_button.setToolTip("更多操作")
            menu_button.clicked.connect(lambda _=False, fid=favorite.id, button=menu_button:
                                        self._show_item_menu(fid, button))
            row.addWidget(menu_button)
            if favorite.id == self.selected_favorite_id:
                card.setStyleSheet("QFrame#modernCard { border: 1px solid #2563eb; }")
            self.rows_by_id[favorite.id] = card
            self.list_layout.addWidget(card)
        self.list_layout.addStretch(1)

        if self._pending_focus_action and self.selected_favorite_id:
            action, self._pending_focus_action = self._pending_focus_action, None
            from PyQt5.QtCore import QTimer
            QTimer.singleShot(0, lambda: self._run_focused_action(action))
        elif self.selected_favorite_id in self.rows_by_id:
            self.list_scroll.ensureWidgetVisible(self.rows_by_id[self.selected_favorite_id])

    def _clear_rows(self):
        while self.list_layout.count():
            item = self.list_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.hide()
                widget.deleteLater()
        self.rows_by_id = {}

    def _run_focused_action(self, action):
        if action == "rename":
            self._prompt_rename(self.selected_favorite_id)
        elif action == "update_path":
            self._choose_new_path(self.selected_favorite_id)
        elif action == "remove":
            self._remove_favorite(self.selected_favorite_id)

    def _choose_folder(self):
        path = QFileDialog.getExistingDirectory(self, "添加常用文件夹")
        if path:
            self._add_path(path)

    def _add_path(self, path):
        before = self.destinations.list_favorites()
        normalized = Path(path).expanduser().resolve()
        duplicate = next((item for item in before if item.path == normalized), None)
        try:
            favorite = self.destinations.add_favorite(normalized)
        except (NotADirectoryError, ValueError) as exc:
            self._notify(str(exc), "warning")
            return None
        self.selected_favorite_id = favorite.id
        self.refresh()
        if duplicate:
            self._notify("已经是常用文件夹", "info")
        else:
            self._notify("已添加常用文件夹", "success")
            self.favorites_changed.emit()
        return favorite

    def _prompt_rename(self, favorite_id):
        favorite = self.destinations.get_favorite(favorite_id)
        if not favorite:
            return
        dialog = ModernTextInputDialog("重命名", "输入 1 到 40 个字符", favorite.name, self)
        if dialog.exec_() == ModernDialog.Accepted:
            self._rename_favorite(favorite_id, dialog.input.text())

    def _rename_favorite(self, favorite_id, name):
        try:
            updated = self.destinations.rename_favorite(favorite_id, name)
        except ValueError as exc:
            self._notify(str(exc), "warning")
            return None
        if updated is None:
            return None
        self.selected_favorite_id = favorite_id
        self.refresh()
        self._notify("名称已更新", "success")
        self.favorites_changed.emit()
        return updated

    def _choose_new_path(self, favorite_id):
        favorite = self.destinations.get_favorite(favorite_id)
        current = str(favorite.path) if favorite else ""
        path = QFileDialog.getExistingDirectory(self, "修改常用文件夹路径", current)
        if path:
            self._update_path(favorite_id, path)

    def _update_path(self, favorite_id, path):
        try:
            updated = self.destinations.update_favorite_path(favorite_id, path)
        except (NotADirectoryError, ValueError) as exc:
            self._notify(str(exc), "warning")
            return None
        if updated is None:
            return None
        self.selected_favorite_id = favorite_id
        self.refresh()
        self._notify("文件夹路径已更新", "success")
        self.favorites_changed.emit()
        return updated

    def _confirm_remove(self, favorite):
        dialog = ModernConfirmDialog(
            "移除常用文件夹", f"从常用文件夹中移除‘{favorite.name}’？不会删除实际文件夹。", self,
        )
        return dialog.exec_() == ModernDialog.Accepted

    def _remove_favorite(self, favorite_id):
        favorite = self.destinations.get_favorite(favorite_id)
        if not favorite or not self._confirm_remove(favorite):
            return False
        if not self.destinations.remove_favorite(favorite_id):
            return False
        self.selected_favorite_id = None
        self.refresh()
        self._notify("已从常用文件夹中移除", "success")
        self.favorites_changed.emit()
        return True

    def _move_favorite(self, favorite_id, offset):
        favorites = self.destinations.list_favorites()
        index = next((i for i, item in enumerate(favorites) if item.id == favorite_id), None)
        if index is None:
            return False
        target = index + offset
        if target < 0 or target >= len(favorites):
            return False
        ordered_ids = [item.id for item in favorites]
        ordered_ids[index], ordered_ids[target] = ordered_ids[target], ordered_ids[index]
        self.destinations.reorder_favorites(ordered_ids)
        self.selected_favorite_id = favorite_id
        self.refresh()
        self.favorites_changed.emit()
        return True

    def _open_favorite(self, favorite_id):
        favorite = self.destinations.get_favorite(favorite_id)
        if not favorite or not favorite.exists:
            self._notify("该文件夹路径失效，请修改路径后再打开。", "warning")
            return False
        return QDesktopServices.openUrl(QUrl.fromLocalFile(str(favorite.path)))

    def _copy_path(self, favorite_id):
        favorite = self.destinations.get_favorite(favorite_id)
        if not favorite:
            return False
        QApplication.clipboard().setText(str(favorite.path))
        self._notify("路径已复制", "success")
        return True

    def _show_item_menu(self, favorite_id, button):
        favorite = self.destinations.get_favorite(favorite_id)
        if not favorite:
            return
        menu = QMenu(self)
        open_action = menu.addAction("打开")
        open_action.setEnabled(favorite.exists)
        rename_action = menu.addAction("重命名")
        update_action = menu.addAction("修改路径")
        copy_action = menu.addAction("复制路径")
        menu.addSeparator()
        up_action = menu.addAction("上移")
        down_action = menu.addAction("下移")
        favorites = self.destinations.list_favorites()
        index = next(i for i, item in enumerate(favorites) if item.id == favorite_id)
        up_action.setEnabled(index > 0)
        down_action.setEnabled(index < len(favorites) - 1)
        menu.addSeparator()
        remove_action = menu.addAction("移除")
        chosen = menu.exec_(button.mapToGlobal(button.rect().bottomLeft()))
        if chosen == open_action:
            self._open_favorite(favorite_id)
        elif chosen == rename_action:
            self._prompt_rename(favorite_id)
        elif chosen == update_action:
            self._choose_new_path(favorite_id)
        elif chosen == copy_action:
            self._copy_path(favorite_id)
        elif chosen == up_action:
            self._move_favorite(favorite_id, -1)
        elif chosen == down_action:
            self._move_favorite(favorite_id, 1)
        elif chosen == remove_action:
            self._remove_favorite(favorite_id)

    def _notify(self, text, level="info"):
        self.banner.label.setText(text)
        self.banner.set_level(level)
        self.banner.show()
