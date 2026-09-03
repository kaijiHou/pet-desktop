from PyQt5.QtCore import Qt, QPoint
from PyQt5.QtWidgets import QDialog, QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout
from .tokens import BASE_QSS


class ModernDialog(QDialog):
    """Frameless rounded dialog with one shared title bar and footer."""
    def __init__(self, title="", subtitle="", parent=None, *, min_width=520, min_height=0):
        super().__init__(parent)
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setMinimumWidth(min_width)
        if min_height: self.setMinimumHeight(min_height)
        self.setStyleSheet(BASE_QSS)
        outer = QVBoxLayout(self); outer.setContentsMargins(10, 10, 10, 10)
        self.card = QFrame(); self.card.setObjectName("modernCard")
        outer.addWidget(self.card)
        root = QVBoxLayout(self.card); root.setContentsMargins(20, 16, 20, 16); root.setSpacing(12)
        self.title_bar = QFrame(); title_layout = QHBoxLayout(self.title_bar); title_layout.setContentsMargins(0, 0, 0, 0)
        title_col = QVBoxLayout(); title_col.setSpacing(2)
        self.title_label = QLabel(title); self.title_label.setObjectName("title"); title_col.addWidget(self.title_label)
        self.subtitle_label = QLabel(subtitle); self.subtitle_label.setObjectName("subtitle"); self.subtitle_label.setVisible(bool(subtitle)); title_col.addWidget(self.subtitle_label)
        title_layout.addLayout(title_col); title_layout.addStretch()
        self.close_button = QPushButton("×"); self.close_button.setFixedSize(30, 30); self.close_button.clicked.connect(self.reject); title_layout.addWidget(self.close_button)
        root.addWidget(self.title_bar)
        self.body = QVBoxLayout(); self.body.setSpacing(10); root.addLayout(self.body, 1)
        self.footer = QHBoxLayout(); self.footer.addStretch(); root.addLayout(self.footer)
        self._drag_pos = None
        self.title_bar.mousePressEvent = self._title_press
        self.title_bar.mouseMoveEvent = self._title_move

    def add_body(self, widget): self.body.addWidget(widget)
    def add_footer(self, widget): self.footer.addWidget(widget)

    def _title_press(self, event):
        if event.button() == Qt.LeftButton: self._drag_pos = event.globalPos() - self.frameGeometry().topLeft()

    def _title_move(self, event):
        if self._drag_pos is not None and event.buttons() & Qt.LeftButton: self.move(event.globalPos() - self._drag_pos)


class ModernConfirmDialog(ModernDialog):
    def __init__(self, title, message, parent=None):
        super().__init__(title, parent=parent, min_width=380)
        label = QLabel(message); label.setWordWrap(True); self.add_body(label)
        cancel = QPushButton("取消"); cancel.clicked.connect(self.reject); confirm = QPushButton("确定"); confirm.setObjectName("primary"); confirm.clicked.connect(self.accept)
        self.add_footer(cancel); self.add_footer(confirm)


class ModernTextInputDialog(ModernDialog):
    def __init__(self, title, prompt="", value="", parent=None):
        from PyQt5.QtWidgets import QLineEdit
        super().__init__(title, parent=parent, min_width=380)
        self.input = QLineEdit(value); self.input.setPlaceholderText(prompt); self.add_body(self.input)
        cancel = QPushButton("取消"); cancel.clicked.connect(self.reject); confirm = QPushButton("确定"); confirm.setObjectName("primary"); confirm.clicked.connect(self.accept); self.add_footer(cancel); self.add_footer(confirm)


class ModernTimeDialog(ModernTextInputDialog):
    pass
