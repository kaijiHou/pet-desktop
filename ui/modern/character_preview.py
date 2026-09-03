"""Character preview that uses the same registry/atlas chain as the desktop pet."""

from pathlib import Path
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPainter, QPixmap, QImage
from PyQt5.QtWidgets import QWidget


class CharacterPreviewWidget(QWidget):
    def __init__(self, registry=None, character_id="default_dynamic_ghost", parent=None):
        super().__init__(parent)
        self.registry = registry
        self.character_id = ""
        self.renderer = None
        self.static_pixmap = QPixmap()
        self.setMinimumSize(92, 92)
        self.set_character_id(character_id)

    def set_character_id(self, character_id):
        if self.renderer:
            self.renderer.stop(); self.renderer.deleteLater(); self.renderer = None
        self.character_id = character_id or ""
        self.static_pixmap = QPixmap()
        if self.registry and self.character_id:
            entry = self.registry.resolve(self.character_id)
            if entry and entry.pack_root:
                try:
                    from character_v4.renderer import DynamicPackRenderer
                    renderer = DynamicPackRenderer(Path(entry.pack_root), scale=0.45, parent=self)
                    if renderer.load():
                        self.renderer = renderer; renderer.frame_changed.connect(self.update)
                except Exception:
                    self.renderer = None
        self.update()

    def set_static_image(self, image):
        if self.renderer:
            self.renderer.stop(); self.renderer.deleteLater(); self.renderer = None
        self.character_id = "single_image"
        if isinstance(image, QPixmap): self.static_pixmap = image
        elif isinstance(image, QImage): self.static_pixmap = QPixmap.fromImage(image)
        else: self.static_pixmap = QPixmap()
        self.update()

    def paintEvent(self, _event):
        painter = QPainter(self); painter.setRenderHint(QPainter.SmoothPixmapTransform)
        if self.renderer and self.renderer.is_loaded:
            frame = self.renderer._player.current_frame if self.renderer._player else None
            if frame: painter.drawPixmap(self.rect(), frame)
        elif not self.static_pixmap.isNull():
            painter.drawPixmap(self.rect(), self.static_pixmap)
