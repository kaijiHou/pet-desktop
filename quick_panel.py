"""Quick panel — lightweight floating summary opened by clicking the pet.

Shows pocket items + upcoming reminders. Follows the pet on drag (move_near
with live=True).
"""
from PyQt5.QtCore import Qt, QTimer, QPoint, QRect
from PyQt5.QtGui import QFont, QColor
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame,
)
import theme


class QuickPanel(QWidget):
    ITEM_PREVIEW = 5

    def __init__(self, pet_window, parent=None):
        super().__init__(parent)
        self.pet = pet_window
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.setMinimumWidth(260)
        self.setMaximumWidth(320)
        self.setMaximumHeight(420)
        self._build_ui()
        self._refresh()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)

        card = QFrame()
        card.setObjectName("card")
        card.setStyleSheet(f"""
            QFrame#card {{
                background: {theme.BG_CARD};
                border: 1px solid {theme.BORDER};
                border-radius: {theme.RADIUS}px;
            }}
        """)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(12, 10, 12, 10)
        card_layout.setSpacing(8)

        # Top bar (title + close)
        topbar = QHBoxLayout()
        top_title = QLabel("快捷面板")
        top_title.setObjectName("title")
        self.panel_close_btn = QPushButton("✕")
        self.panel_close_btn.setObjectName("flat")
        self.panel_close_btn.setFixedSize(24, 24)
        self.panel_close_btn.setToolTip("关闭")
        self.panel_close_btn.clicked.connect(self.hide)
        topbar.addWidget(top_title); topbar.addStretch(); topbar.addWidget(self.panel_close_btn)
        card_layout.addLayout(topbar)

        # ── Pocket section ──
        hdr = QHBoxLayout()
        self.pocket_title = QLabel("文件口袋")
        self.pocket_title.setObjectName("title")
        self.pocket_count = QLabel("0")
        self.pocket_count.setStyleSheet(f"color: {theme.ACCENT}; font-weight: 600;")
        hdr.addWidget(self.pocket_title); hdr.addStretch(); hdr.addWidget(self.pocket_count)
        card_layout.addLayout(hdr)

        self.pocket_items_layout = QVBoxLayout()
        self.pocket_items_layout.setSpacing(2)
        card_layout.addLayout(self.pocket_items_layout)

        self.empty_label = QLabel("暂无内容 · 拖文件到角色即可暂存")
        self.empty_label.setWordWrap(True)
        self.empty_label.setStyleSheet(f"color: {theme.TEXT_MUTED}; font-size: 8pt;")
        card_layout.addWidget(self.empty_label)

        self.open_pocket_btn = QPushButton("打开完整口袋")
        self.open_pocket_btn.setObjectName("primary")
        self.open_pocket_btn.clicked.connect(self._open_pocket)
        card_layout.addWidget(self.open_pocket_btn)

        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet(f"background: {theme.BORDER}; max-height: 1px;")
        card_layout.addWidget(sep)

        # ── Reminders section ──
        hdr2 = QHBoxLayout()
        self.remind_title = QLabel("新建提醒")
        self.remind_title.setObjectName("title")
        self.remind_btn = QPushButton("+")
        self.remind_btn.setObjectName("primary")
        self.remind_btn.setFixedSize(28, 28)
        self.remind_btn.clicked.connect(self._open_add_reminder)
        hdr2.addWidget(self.remind_title); hdr2.addStretch(); hdr2.addWidget(self.remind_btn)
        card_layout.addLayout(hdr2)

        self.remind_items_layout = QVBoxLayout()
        self.remind_items_layout.setSpacing(2)
        card_layout.addLayout(self.remind_items_layout)

        self.no_remind_label = QLabel("暂无提醒")
        self.no_remind_label.setStyleSheet(f"color: {theme.TEXT_MUTED}; font-size: 8pt;")
        card_layout.addWidget(self.no_remind_label)

        self.open_reminders_btn = QPushButton("我的提醒")
        self.open_reminders_btn.setObjectName("flat")
        self.open_reminders_btn.clicked.connect(self._open_reminders)
        card_layout.addWidget(self.open_reminders_btn)

        root.addWidget(card)

    def refresh(self):
        self._refresh()

    def _refresh(self):
        items = self.pet.pocket.list_items()
        self.pocket_count.setText(str(len(items)))
        self.empty_label.setVisible(len(items) == 0)

        while self.pocket_items_layout.count():
            child = self.pocket_items_layout.takeAt(0)
            w = child.widget()
            if w:
                w.deleteLater()
        for item in items[: self.ITEM_PREVIEW]:
            name = item.name if item.exists else f"{item.name} [missing]"
            lbl = QLabel(f"  {name}")
            lbl.setStyleSheet(f"font-size: 8pt; color: {theme.TEXT}; padding: 1px 0;")
            self.pocket_items_layout.addWidget(lbl)
        if len(items) > self.ITEM_PREVIEW:
            lbl = QLabel(f"  还有 {len(items) - self.ITEM_PREVIEW} 项...")
            lbl.setStyleSheet(f"font-size: 8pt; color: {theme.TEXT_MUTED};")
            self.pocket_items_layout.addWidget(lbl)

        reminders = self.pet.reminder.list_reminders()
        self.no_remind_label.setVisible(len(reminders) == 0)
        while self.remind_items_layout.count():
            child = self.remind_items_layout.takeAt(0)
            w = child.widget()
            if w:
                w.deleteLater()
        for rem in reminders[:3]:
            txt = f"  {rem.due_at:%m-%d %H:%M}  {rem.content}"
            lbl = QLabel(txt)
            lbl.setStyleSheet(f"font-size: 8pt; color: {theme.TEXT}; padding: 1px 0;")
            lbl.setWordWrap(True)
            self.remind_items_layout.addWidget(lbl)
        if len(reminders) > 3:
            lbl = QLabel(f"  还有 {len(reminders) - 3} 条提醒...")
            lbl.setStyleSheet(f"font-size: 8pt; color: {theme.TEXT_MUTED};")
            self.remind_items_layout.addWidget(lbl)

    def _open_pocket(self):
        self.pet._open_pocket()
        self.hide()

    def _open_add_reminder(self):
        self.pet._open_add_reminder()
        self._refresh()

    def _open_reminders(self):
        self.pet._open_reminders()
        self._refresh()

    def showNear(self, pet_window):
        self.move_near(pet_window.geometry(), live=False, screen=pet_window.screen())

    def move_near(self, anchor_rect, live=False, screen=None):
        """Position the panel beside the anchor rect; live=True won't steal focus."""
        from PyQt5.QtWidgets import QApplication
        pet_rect = anchor_rect
        scr = screen or QApplication.screenAt(pet_rect.center()) or QApplication.primaryScreen()
        avail = scr.availableGeometry()
        self.adjustSize()
        pw = max(self.sizeHint().width() + 16, self.width())
        ph = max(self.sizeHint().height() + 16, self.height())
        x = pet_rect.right() + 8
        y = pet_rect.top()
        if x + pw > avail.right():
            x = pet_rect.left() - pw - 8
        if y + ph > avail.bottom():
            y = avail.bottom() - ph - 8
        if y < avail.top():
            y = avail.top()
        self.setGeometry(x, y, pw, ph)
        if not live:
            self.show()
            self.raise_()
            self.activateWindow()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.hide()

    def focusOutEvent(self, event):
        QTimer.singleShot(150, self._check_focus_close)

    def _check_focus_close(self):
        if not self.isActiveWindow() and not self.pet.geometry().intersects(self.geometry()):
            self.hide()