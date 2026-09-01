"""Character Gallery — dialog for selecting and managing character packs."""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QFont, QPixmap, QImage
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QListWidget, QListWidgetItem,
    QPushButton, QFileDialog, QMessageBox, QGroupBox,
)

from character_v4.registry import CharacterRegistry, CharacterEntry

LOGGER = logging.getLogger("pet.character.gallery")


class CharacterGalleryDialog(QDialog):
    """Modal dialog for character selection and management."""

    def __init__(self, registry: CharacterRegistry, current_id: str, parent=None):
        super().__init__(parent)
        self.registry = registry
        self.current_id = current_id
        self.selected_id = current_id
        self._entries: list[CharacterEntry] = []
        self.setWindowTitle("角色管理")
        self.setMinimumSize(500, 400)
        self._build_ui()
        self._load_entries()
        self._select_current()

    def _build_ui(self):
        layout = QVBoxLayout(self)

        # Character list
        self.list_widget = QListWidget()
        self.list_widget.currentItemChanged.connect(self._on_selection_changed)
        layout.addWidget(self.list_widget)

        # Preview
        preview_group = QGroupBox("预览")
        preview_layout = QVBoxLayout()
        self.preview_label = QLabel("选择一个角色")
        self.preview_label.setAlignment(Qt.AlignCenter)
        self.preview_label.setFixedHeight(120)
        preview_layout.addWidget(self.preview_label)
        self.info_label = QLabel("")
        self.info_label.setAlignment(Qt.AlignCenter)
        preview_layout.addWidget(self.info_label)
        preview_group.setLayout(preview_layout)
        layout.addWidget(preview_group)

        # Buttons
        btn_layout = QHBoxLayout()
        self.btn_use = QPushButton("使用")
        self.btn_use.clicked.connect(self._on_use)
        self.btn_import_dynamic = QPushButton("导入动态角色包")
        self.btn_import_dynamic.clicked.connect(self._on_import_dynamic)
        self.btn_import_image = QPushButton("导入单图")
        self.btn_import_image.clicked.connect(self._on_import_image)
        self.btn_delete = QPushButton("删除")
        self.btn_delete.clicked.connect(self._on_delete)
        btn_layout.addWidget(self.btn_use)
        btn_layout.addWidget(self.btn_import_dynamic)
        btn_layout.addWidget(self.btn_import_image)
        btn_layout.addWidget(self.btn_delete)
        layout.addLayout(btn_layout)

        # OK/Cancel
        ok_layout = QHBoxLayout()
        ok_layout.addStretch()
        btn_ok = QPushButton("确定")
        btn_ok.clicked.connect(self.accept)
        btn_cancel = QPushButton("取消")
        btn_cancel.clicked.connect(self.reject)
        ok_layout.addWidget(btn_ok)
        ok_layout.addWidget(btn_cancel)
        layout.addLayout(ok_layout)

    def _load_entries(self):
        self._entries = self.registry.all()
        self.list_widget.clear()
        for entry in self._entries:
            item = QListWidgetItem(f"[{entry.source}] {entry.display_name}")
            item.setData(Qt.UserRole, entry.id)
            self.list_widget.addItem(item)

    def _select_current(self):
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            if item.data(Qt.UserRole) == self.current_id:
                self.list_widget.setCurrentItem(item)
                return

    def _on_selection_changed(self, current, _previous):
        if current is None:
            return
        char_id = current.data(Qt.UserRole)
        self.selected_id = char_id
        # Update preview
        entry = self.registry.resolve(char_id)
        if entry:
            self.info_label.setText(f"{entry.display_name}\n{entry.description}")
            # Load first frame as preview
            self._load_preview(entry)

    def _load_preview(self, entry: CharacterEntry):
        if not entry.pack_root:
            return
        try:
            from character_v4.atlas import SpritesheetAtlas
            m = entry.pack_root / "pet.json"
            if not m.exists():
                return
            from character_v4.manifest import CodexPetManifest
            manifest = CodexPetManifest.load(entry.pack_root)
            atlas = SpritesheetAtlas(manifest, entry.pack_root)
            if atlas.load():
                frame = atlas.get_frame("idle", 0)
                if frame:
                    self.preview_label.setPixmap(frame.scaled(
                        100, 100, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        except Exception:
            self.preview_label.setText("无法加载预览")

    def _on_use(self):
        """Select the current character and close."""
        self.accept()

    def _on_import_dynamic(self):
        """Import a dynamic pack from folder or zip."""
        path, _ = QFileDialog.getOpenFileName(
            self, "选择角色包", "",
            "角色包 (pet.json);;ZIP (*.zip);;所有文件 (*)"
        )
        if not path:
            return
        source = Path(path)
        if source.name == "pet.json":
            source = source.parent
        entry = self.registry.install(source)
        if entry:
            self._load_entries()
            # Select the new entry
            for i in range(self.list_widget.count()):
                item = self.list_widget.item(i)
                if item.data(Qt.UserRole) == entry.id:
                    self.list_widget.setCurrentItem(item)
                    break
            QMessageBox.information(self, "导入成功", f"已导入: {entry.display_name}")
        else:
            QMessageBox.warning(self, "导入失败", "角色包无效或导入失败")

    def _on_import_image(self):
        """Import a single image as a character."""
        from character import import_character_image
        from paths import PROJECT_ROOT
        path, _ = QFileDialog.getOpenFileName(
            self, "选择角色图片", "",
            "图片 (*.png *.webp *.jpg *.jpeg)"
        )
        if not path:
            return
        try:
            name = import_character_image(Path(path), PROJECT_ROOT / "assets")
            QMessageBox.information(self, "导入成功", f"已导入图片: {name}")
        except ValueError as exc:
            QMessageBox.warning(self, "导入失败", str(exc))

    def _on_delete(self):
        """Delete the selected user-installed character."""
        item = self.list_widget.currentItem()
        if not item:
            return
        char_id = item.data(Qt.UserRole)
        entry = self.registry.resolve(char_id)
        if entry and entry.is_builtin:
            QMessageBox.information(self, "提示", "内置角色不能删除")
            return
        if char_id == self.current_id:
            QMessageBox.information(self, "提示", "当前正在使用的角色不能删除，请先切换角色")
            return
        reply = QMessageBox.question(
            self, "确认删除",
            f"确定删除角色 '{entry.display_name if entry else char_id}'?",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.registry.remove(char_id)
            self._load_entries()
