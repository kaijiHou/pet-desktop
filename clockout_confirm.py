"""Pretty clock-out confirmation popup — pure QLabel/QPushButton + QSS.

No custom Python paintEvent anywhere (the IME re-entrancy crash carrier);
everything is C++-painted. confirm() shows the chip above the pet, runs a
local event loop and returns True only when 确定打卡 is clicked; 取消,
clicking elsewhere, Esc or ~6s of silence returns False.
"""

from PyQt5.QtCore import Qt, QEventLoop, QTimer
from PyQt5.QtWidgets import (QApplication, QFrame, QHBoxLayout, QLabel,
                             QPushButton, QVBoxLayout, QWidget)

import ui_skin


class ClockoutConfirmPopup(QWidget):
    """Modal-feel confirm chip anchored above the pet's head."""

    AUTO_CLOSE_MS = 6000

    def __init__(self):
        super().__init__(None)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Tool | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.setAttribute(Qt.WA_QuitOnClose, False)
        self.setFocusPolicy(Qt.NoFocus)
        self.confirmed_flag = False
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        self.card = QFrame()
        self.card.setObjectName("clockoutCard")
        root.addWidget(self.card)
        lay = QVBoxLayout(self.card)
        lay.setContentsMargins(18, 14, 18, 14)
        lay.setSpacing(10)
        self.title = QLabel()
        self.title.setAlignment(Qt.AlignCenter)
        self.title.setStyleSheet("font-size: 15pt; font-weight: 800;")
        self.sub = QLabel()
        self.sub.setAlignment(Qt.AlignCenter)
        self.sub.setObjectName("muted")
        lay.addWidget(self.title)
        lay.addWidget(self.sub)
        buttons = QHBoxLayout()
        buttons.setSpacing(10)
        self.no_btn = QPushButton("取消")
        self.no_btn.setObjectName("secondary")
        self.no_btn.clicked.connect(self._answer_no)
        self.yes_btn = QPushButton("确定打卡")
        self.yes_btn.setObjectName("primary")
        self.yes_btn.clicked.connect(self._answer_yes)
        buttons.addWidget(self.no_btn)
        buttons.addWidget(self.yes_btn)
        lay.addLayout(buttons)
        self._loop = None
        self.hide()

    # ── answers ──
    def _answer_yes(self):
        self.confirmed_flag = True
        self._finish()

    def _answer_no(self):
        self.confirmed_flag = False
        self._finish()

    def _finish(self):
        self.confirmed_flag = getattr(self, "confirmed_flag", False)
        if self._loop is not None:
            self._loop.quit()

    def keyPressEvent(self, event):
        # Esc = 不打卡
        if event.key() == Qt.Key_Escape:
            self._answer_no()
        else:
            super().keyPressEvent(event)

    def confirm(self, text: str, sub: str, anchor_rect, screen=None) -> bool:
        """Show above *anchor_rect* and block until answered. True = 打卡。"""
        p = ui_skin.palette()
        self.card.setStyleSheet(f"""
            QFrame#clockoutCard {{
                background: {p['card']}; border: 2px solid {p['accent']};
                border-radius: 18px;
            }}
            QLabel {{ background: transparent; }}
            QLabel#muted {{ color: {p['muted']}; }}
            QPushButton#primary {{ background: {p['accent']}; color: white;
                border: none; border-radius: 11px; padding: 8px 18px; font-weight: 700; }}
            QPushButton#primary:hover {{ background: {p['accent_hover']}; }}
            QPushButton#secondary {{ background: {p['tint_light']}; color: {p['text']};
                border: 1px solid {p['border']}; border-radius: 11px; padding: 8px 16px; }}
            QPushButton#secondary:hover {{ background: {p['menu_highlight']}; }}
        """)
        self.title.setText(text)
        self.sub.setText(sub)
        self.adjustSize()
        screen = screen or QApplication.screenAt(anchor_rect.center()) or self.screen()
        if screen is not None:
            avail = screen.availableGeometry()
            x = anchor_rect.center().x() - self.width() // 2
            y = anchor_rect.top() - self.height() - 8
            x = max(avail.left(), min(x, avail.right() - self.width() + 1))
            y = max(avail.top() + 2, min(y, avail.bottom() - self.height() + 1))
            self.move(x, y)
        self.confirmed_flag = False
        self.show()
        self.raise_()
        self.activateWindow()
        QTimer.singleShot(self.AUTO_CLOSE_MS, self._answer_no)
        self._loop = QEventLoop()
        self._loop.exec_()
        self._loop = None
        self.hide()
        return self.confirmed_flag


def clockout_popup_texts(service):
    """(title, sub) for the confirm chip; warns before work_end."""
    now = service._now()
    snap = service.current_breakdown()
    hide = service.settings.privacy_mode
    amount = f"当前已赚 ¥{snap.total_earned:.2f}" if not hide else f"当前进度 {snap.progress}%"
    if now.time() < service.settings.work_end:
        amount = f"⚠ 还没到 {service.settings.work_end:%H:%M} 下班时间\n" + amount
    return f"{now:%H:%M} 下班打卡？", amount


def confirm_clockout(service, pet) -> bool:
    """Shared entry: pretty confirm chip anchored to the pet; True = 打卡。"""
    title, sub = clockout_popup_texts(service)
    popup = getattr(pet, "_confirm_popup", None)
    if popup is None:
        popup = ClockoutConfirmPopup()
        pet._confirm_popup = popup
    return popup.confirm(title, sub,
                         pet.visible_pet_global_rect(), pet.screen())
