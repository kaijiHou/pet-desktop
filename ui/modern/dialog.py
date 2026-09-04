from PyQt5.QtCore import Qt, QPoint, QEvent, QRect
from PyQt5.QtWidgets import QDialog, QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QApplication
from .tokens import BASE_QSS


class ModernDialog(QDialog):
    """Frameless rounded dialog with one shared title bar and footer."""
    def __init__(self, title="", subtitle="", parent=None, *, min_width=520, min_height=0,
                 resizable=False):
        super().__init__(parent)
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setMinimumWidth(min_width)
        if min_height: self.setMinimumHeight(min_height)
        self.resizable = bool(resizable)
        self._resize_margin = 7
        self._resize_edges = Qt.Edges()
        self._resize_origin = None
        self._resize_geometry = None
        self._normal_geometry = None
        self.setMouseTracking(True)
        self.setStyleSheet(BASE_QSS)
        outer = QVBoxLayout(self); outer.setContentsMargins(6, 6, 6, 6)
        self.card = QFrame(); self.card.setObjectName("modernCard")
        outer.addWidget(self.card)
        root = QVBoxLayout(self.card); root.setContentsMargins(20, 16, 20, 16); root.setSpacing(12)
        self.title_bar = QFrame(); title_layout = QHBoxLayout(self.title_bar); title_layout.setContentsMargins(0, 0, 0, 0)
        title_col = QVBoxLayout(); title_col.setSpacing(2)
        self.title_label = QLabel(title); self.title_label.setObjectName("title"); title_col.addWidget(self.title_label)
        self.subtitle_label = QLabel(subtitle); self.subtitle_label.setObjectName("subtitle"); self.subtitle_label.setVisible(bool(subtitle)); title_col.addWidget(self.subtitle_label)
        title_layout.addLayout(title_col); title_layout.addStretch()
        self.max_button = QPushButton("□"); self.max_button.setFixedSize(30, 30)
        self.max_button.setToolTip("最大化")
        self.max_button.setVisible(self.resizable)
        self.max_button.clicked.connect(self._toggle_maximize)
        title_layout.addWidget(self.max_button)
        self.close_button = QPushButton("×"); self.close_button.setFixedSize(30, 30); self.close_button.clicked.connect(self.reject); title_layout.addWidget(self.close_button)
        root.addWidget(self.title_bar)
        self.body = QVBoxLayout(); self.body.setSpacing(10); root.addLayout(self.body, 1)
        self.footer = QHBoxLayout(); self.footer.addStretch(); root.addLayout(self.footer)
        self._drag_pos = None
        self.title_bar.mousePressEvent = self._title_press
        self.title_bar.mouseMoveEvent = self._title_move
        self.title_bar.mouseDoubleClickEvent = self._title_double_click
        self.card.installEventFilter(self)
        self.title_bar.installEventFilter(self)

    def add_body(self, widget): self.body.addWidget(widget)
    def add_footer(self, widget): self.footer.addWidget(widget)

    def _title_press(self, event):
        if event.button() == Qt.LeftButton:
            if self.isMaximized():
                self._toggle_maximize()
                self._drag_pos = QPoint(self.width() // 2, 18)
            else:
                self._drag_pos = event.globalPos() - self.frameGeometry().topLeft()

    def _title_move(self, event):
        if self._drag_pos is not None and event.buttons() & Qt.LeftButton: self.move(event.globalPos() - self._drag_pos)

    def _title_double_click(self, event):
        if event.button() == Qt.LeftButton and self.resizable:
            self._toggle_maximize()

    def set_resizable(self, value):
        self.resizable = bool(value)
        self.max_button.setVisible(self.resizable)

    def _toggle_maximize(self):
        if not self.resizable:
            return
        if self.isMaximized():
            self.showNormal()
            if self._normal_geometry:
                self.setGeometry(self._normal_geometry)
            self.max_button.setText("□")
            self.max_button.setToolTip("最大化")
        else:
            self._normal_geometry = self.geometry()
            self.showMaximized()
            self.max_button.setText("❐")
            self.max_button.setToolTip("还原")

    def _hit_test(self, pos):
        if not self.resizable:
            return Qt.Edges()
        r, m = self.rect(), self._resize_margin
        edges = Qt.Edges()
        if pos.x() <= r.left() + m: edges |= Qt.LeftEdge
        if pos.x() >= r.right() - m: edges |= Qt.RightEdge
        if pos.y() <= r.top() + m: edges |= Qt.TopEdge
        if pos.y() >= r.bottom() - m: edges |= Qt.BottomEdge
        return edges

    @staticmethod
    def _cursor_for(edges):
        left, right = bool(edges & Qt.LeftEdge), bool(edges & Qt.RightEdge)
        top, bottom = bool(edges & Qt.TopEdge), bool(edges & Qt.BottomEdge)
        if (left and top) or (right and bottom): return Qt.SizeFDiagCursor
        if (right and top) or (left and bottom): return Qt.SizeBDiagCursor
        if left or right: return Qt.SizeHorCursor
        if top or bottom: return Qt.SizeVerCursor
        return Qt.ArrowCursor

    def _resize_from_global(self, global_pos):
        if not self._resize_geometry or not self._resize_edges:
            return
        delta = global_pos - self._resize_origin
        g = QRect(self._resize_geometry)
        if self._resize_edges & Qt.LeftEdge: g.setLeft(g.left() + delta.x())
        if self._resize_edges & Qt.RightEdge: g.setRight(g.right() + delta.x())
        if self._resize_edges & Qt.TopEdge: g.setTop(g.top() + delta.y())
        if self._resize_edges & Qt.BottomEdge: g.setBottom(g.bottom() + delta.y())
        min_w, min_h = self.minimumWidth(), self.minimumHeight()
        if g.width() < min_w:
            if self._resize_edges & Qt.LeftEdge: g.setLeft(g.right() - min_w + 1)
            else: g.setRight(g.left() + min_w - 1)
        if g.height() < min_h:
            if self._resize_edges & Qt.TopEdge: g.setTop(g.bottom() - min_h + 1)
            else: g.setBottom(g.top() + min_h - 1)
        screen = QApplication.screenAt(global_pos) or self.screen()
        if screen:
            avail = screen.availableGeometry()
            g.setWidth(min(g.width(), avail.width()))
            g.setHeight(min(g.height(), avail.height()))
        self.setGeometry(g)

    def eventFilter(self, obj, event):
        if self.resizable and obj in (self.card, self.title_bar):
            if event.type() == QEvent.MouseMove:
                pos = obj.mapTo(self, event.pos())
                if self._resize_edges:
                    self._resize_from_global(event.globalPos())
                    return True
                self.setCursor(self._cursor_for(self._hit_test(pos)))
            elif event.type() == QEvent.MouseButtonPress and event.button() == Qt.LeftButton:
                edges = self._hit_test(obj.mapTo(self, event.pos()))
                if edges:
                    self._resize_edges = edges
                    self._resize_origin = event.globalPos()
                    self._resize_geometry = self.geometry()
                    return True
            elif event.type() == QEvent.MouseButtonRelease and self._resize_edges:
                self._resize_edges = Qt.Edges(); self._resize_origin = None; self._resize_geometry = None
                return True
        return super().eventFilter(obj, event)


class ModernConfirmDialog(ModernDialog):
    def __init__(self, title, message, parent=None):
        super().__init__(title, parent=parent, min_width=380)
        label = QLabel(message); label.setWordWrap(True); self.add_body(label)
        self.cancel_button = QPushButton("取消"); self.cancel_button.clicked.connect(self.reject)
        self.confirm_button = QPushButton("确定"); self.confirm_button.setObjectName("primary"); self.confirm_button.clicked.connect(self.accept)
        self.add_footer(self.cancel_button); self.add_footer(self.confirm_button)


class ModernTextInputDialog(ModernDialog):
    def __init__(self, title, prompt="", value="", parent=None):
        from PyQt5.QtWidgets import QLineEdit
        super().__init__(title, parent=parent, min_width=380)
        self.input = QLineEdit(value); self.input.setPlaceholderText(prompt); self.add_body(self.input)
        cancel = QPushButton("取消"); cancel.clicked.connect(self.reject); confirm = QPushButton("确定"); confirm.setObjectName("primary"); confirm.clicked.connect(self.accept); self.add_footer(cancel); self.add_footer(confirm)


class ModernTimeDialog(ModernTextInputDialog):
    pass
