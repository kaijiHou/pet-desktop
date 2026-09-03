from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QHBoxLayout, QLabel, QPushButton, QFrame


class ModernTitleBar(QFrame):
    def __init__(self, title="", subtitle="", on_close=None, parent=None):
        super().__init__(parent)
        self.title_label = QLabel(title); self.title_label.setObjectName("title")
        self.subtitle_label = QLabel(subtitle); self.subtitle_label.setObjectName("subtitle"); self.subtitle_label.setVisible(bool(subtitle))
        self.close_button = QPushButton("×"); self.close_button.setFixedSize(30, 30)
        if on_close: self.close_button.clicked.connect(on_close)
        layout = QHBoxLayout(self); layout.setContentsMargins(0, 0, 0, 0); layout.addWidget(self.title_label); layout.addStretch(); layout.addWidget(self.close_button)


TitleBar = ModernTitleBar
