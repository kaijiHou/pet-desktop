"""Character Gallery — dialog for selecting and managing character packs."""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QFont, QPixmap, QImage
from PyQt5.QtWidgets import QLabel, QListWidget, QListWidgetItem, QFileDialog, QGroupBox, QVBoxLayout, QHBoxLayout
from ui.modern import ModernDialog, PrimaryButton, SecondaryButton, DangerButton, InlineBanner

from character_v4.registry import CharacterRegistry, CharacterEntry

LOGGER = logging.getLogger("pet.character.gallery")


class CharacterGalleryDialog(ModernDialog):
    """Modal dialog for character selection and management."""

    def __init__(self, registry: CharacterRegistry, current_id: str, parent=None):
        super().__init__("角色管理", "统一管理动态角色包与单图角色", parent, min_width=560, min_height=520)
        self.registry = registry
        self.current_id = current_id
        self.selected_id = current_id
        self._entries: list[CharacterEntry] = []
        self._build_ui()
        self._load_entries()
        self._select_current()

    def _build_ui(self):
        layout = self.body

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
        self.btn_use = PrimaryButton("使用")
        self.btn_use.clicked.connect(self._on_use)
        self.btn_import_dynamic = SecondaryButton("导入动态角色包")
        self.btn_import_dynamic.clicked.connect(self._on_import_dynamic)
        self.btn_import_image = SecondaryButton("导入单图")
        self.btn_import_image.clicked.connect(self._on_import_image)
        self.btn_delete = DangerButton("删除")
        self.btn_delete.clicked.connect(self._on_delete)
        btn_layout.addWidget(self.btn_use)
        btn_layout.addWidget(self.btn_import_dynamic)
        btn_layout.addWidget(self.btn_import_image)
        btn_layout.addWidget(self.btn_delete)
        layout.addLayout(btn_layout)

        self.notice = InlineBanner(); self.notice.hide(); layout.addWidget(self.notice)
        btn_cancel = SecondaryButton("取消"); btn_cancel.clicked.connect(self.reject); self.add_footer(btn_cancel)
        btn_ok = PrimaryButton("确定"); btn_ok.clicked.connect(self.accept); self.add_footer(btn_ok)

    def _notify(self, text, level="info"):
        self.notice.label.setText(text); self.notice.set_level(level); self.notice.show()

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
            self._notify(f"已导入：{entry.display_name}", "success")
        else:
            self._notify("角色包无效或导入失败", "warning")

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
            self._notify(f"已导入图片：{name}", "success")
        except ValueError as exc:
            self._notify(str(exc), "warning")

    def _on_delete(self):
        """Delete the selected user-installed character."""
        item = self.list_widget.currentItem()
        if not item:
            return
        char_id = item.data(Qt.UserRole)
        entry = self.registry.resolve(char_id)
        if entry and entry.is_builtin:
            self._notify("内置角色不能删除", "warning")
            return
        if char_id == self.current_id:
            self._notify("当前正在使用的角色不能删除，请先切换角色", "warning")
            return
        self.registry.remove(char_id)
        self._load_entries()
        self._notify(f"已删除：{entry.display_name if entry else char_id}", "success")
