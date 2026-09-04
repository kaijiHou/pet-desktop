"""Character Gallery — dialog for selecting and managing character packs."""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QFont, QPixmap, QImage
from PyQt5.QtWidgets import QLabel, QListWidget, QListWidgetItem, QFileDialog, QVBoxLayout, QHBoxLayout
from ui.modern import ModernDialog, ModernConfirmDialog, PrimaryButton, SecondaryButton, DangerButton, InlineBanner, Card, SectionTitle, CharacterPreviewWidget

from character_v4.registry import CharacterRegistry, CharacterEntry

LOGGER = logging.getLogger("pet.character.gallery")


class CharacterGalleryDialog(ModernDialog):
    """Modal dialog for character selection and management."""
    image_imported = pyqtSignal(str)

    def __init__(self, registry: CharacterRegistry, current_id: str, parent=None):
        super().__init__("角色管理", "统一管理动态角色包与单图角色", parent, min_width=560, min_height=520, resizable=True)
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
        preview_group = Card()
        preview_layout = QVBoxLayout(preview_group); preview_layout.setContentsMargins(16, 13, 16, 13)
        preview_layout.addWidget(SectionTitle("预览"))
        self.preview_label = CharacterPreviewWidget(self.registry, self.current_id, self)
        self.preview_label.setMinimumSize(180, 160); self.preview_label.setMaximumHeight(220)
        preview_layout.addWidget(self.preview_label, 1)
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
        btn_ok = PrimaryButton("确定"); btn_ok.clicked.connect(self._on_use); self.add_footer(btn_ok)

    def _notify(self, text, level="info"):
        self.notice.label.setText(text); self.notice.set_level(level); self.notice.show()

    def _load_entries(self):
        self._entries = self.registry.all()
        self.list_widget.clear()
        for entry in self._entries:
            source_label = {"builtin": "内置", "installed": "已安装", "codex": "Codex 可导入"}.get(entry.source, entry.source)
            item = QListWidgetItem(f"{entry.display_name} · {source_label}")
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
            self._load_preview(entry)

    def _load_preview(self, entry: CharacterEntry):
        if not entry.pack_root:
            return
        try:
            self.preview_label.set_character_id(entry.id)
        except Exception:
            self.info_label.setText("无法加载预览")

    def _on_use(self):
        """Select the current character and close."""
        entry = self.registry.resolve(self.selected_id)
        if entry and entry.source == "codex":
            installed = self.registry.install(entry.pack_root)
            if installed:
                self._load_entries(); self.current_id = self.selected_id = installed.id; self._select_current()
                self._notify("已导入到本机角色库，请再次点击使用", "success")
            else:
                self._notify("角色包无效或导入失败", "warning")
            return
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
        from paths import DATA_DIR
        path, _ = QFileDialog.getOpenFileName(
            self, "选择角色图片", "",
            "图片 (*.png *.webp *.jpg *.jpeg)"
        )
        if not path:
            return
        try:
            from character_import import SingleCharacterImportService
            importer = SingleCharacterImportService(DATA_DIR)
            stored = importer.import_image(Path(path))
            relative = importer.relative_path(stored)
            self.image_imported.emit(relative)
            self._notify(f"已导入图片：{stored.name}", "success")
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
        if entry and entry.source != "installed":
            self._notify("该角色需先导入到本机角色库", "warning")
            return
        if char_id == self.current_id:
            self._notify("当前正在使用的角色不能删除，请先切换角色", "warning")
            return
        confirm = ModernConfirmDialog("删除角色", f"删除角色“{entry.display_name if entry else char_id}”？角色文件将从本应用中移除，此操作不可撤销。", self)
        confirm.confirm_button.setText("删除"); confirm.confirm_button.setObjectName("danger"); confirm.confirm_button.style().unpolish(confirm.confirm_button); confirm.confirm_button.style().polish(confirm.confirm_button)
        if confirm.exec_() != confirm.Accepted:
            return
        self.registry.remove(char_id)
        self._load_entries()
        self._notify(f"已删除：{entry.display_name if entry else char_id}", "success")

    def closeEvent(self, event):
        if hasattr(self, "preview_label"):
            self.preview_label.close()
        super().closeEvent(event)
