"""Today earnings window with privacy-aware display and clock-out action."""

from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame, QInputDialog
import theme


class TodayWageWindow(QWidget):
    def __init__(self, service, parent=None):
        super().__init__(None); self.service = service; self.pet = parent
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Tool | Qt.WindowStaysOnTopHint); self.setAttribute(Qt.WA_TranslucentBackground); self.setAttribute(Qt.WA_ShowWithoutActivating); self.setMinimumWidth(300)
        root = QVBoxLayout(self); root.setContentsMargins(0,0,0,0); card = QFrame(); card.setObjectName("card"); card.setStyleSheet(f"QFrame#card {{ background: {theme.BG_CARD}; border: 1px solid {theme.BORDER}; border-radius: {theme.RADIUS}px; }}"); lay = QVBoxLayout(card); lay.setContentsMargins(16,14,16,14)
        top = QHBoxLayout(); t = QLabel("今日已赚"); t.setObjectName("title"); close = QPushButton("✕"); close.setObjectName("flat"); close.clicked.connect(self.hide); top.addWidget(t); top.addStretch(); top.addWidget(close); lay.addLayout(top)
        self.amount = QLabel("未配置"); self.amount.setStyleSheet(f"font-size: 22pt; font-weight: 700; color: {theme.ACCENT};"); self.detail = QLabel(""); self.detail.setWordWrap(True); self.progress = QLabel(""); self.clock_btn = QPushButton("下班打卡"); self.clock_btn.setObjectName("primary"); self.clock_btn.clicked.connect(self._clock_out)
        self.reveal_btn = QPushButton("临时显示金额"); self.reveal_btn.setObjectName("flat"); self.reveal_btn.clicked.connect(self._toggle_reveal); self.reveal_btn.hide()
        lay.addWidget(self.amount); lay.addWidget(self.detail); lay.addWidget(self.progress); lay.addWidget(self.clock_btn); lay.addWidget(self.reveal_btn); root.addWidget(card)
        self._reveal = False
        self._timer = QTimer(self); self._timer.setInterval(1000); self._timer.timeout.connect(self.refresh)

    def _toggle_reveal(self):
        self._reveal = not self._reveal
        self.refresh()

    def refresh(self):
        if not self.service.configured:
            self.amount.setText("未配置"); self.detail.setText("请先设置工资与工作时间"); self.progress.clear(); self.clock_btn.setEnabled(False); self.reveal_btn.hide(); return
        snap = self.service.current_breakdown(); rec = self.service.record_for(); self.clock_btn.setEnabled(snap.overtime_minutes > 0 and rec is None)
        if self.service.settings.privacy_mode and not self._reveal:
            self.amount.setText(f"今日进度 {snap.progress}%"); self.detail.setText(f"距下班进度 · 已加班 {snap.overtime_minutes // 60}h{snap.overtime_minutes % 60:02d}m"); self.progress.clear(); self.reveal_btn.show(); return
        self.reveal_btn.setText("恢复隐藏" if self._reveal else "临时显示金额")
        if self._reveal: self.reveal_btn.show()
        else: self.reveal_btn.setVisible(self.service.settings.privacy_mode)
        self.amount.setText(f"¥{snap.total_earned:.2f}"); self.detail.setText(f"正常工资  ¥{snap.base_earned:.2f}\n加班      ¥{snap.overtime_pay:.2f}\n餐补      ¥{snap.confirmed_meal_allowance:.2f}"); self.progress.setText(f"进度 {snap.progress}%")

    def show_near(self, anchor, screen=None):
        self.move_near(anchor, screen=screen, live=False)

    def move_near(self, anchor, screen=None, live=False):
        from PyQt5.QtWidgets import QApplication
        scr = screen or QApplication.screenAt(anchor.center()) or QApplication.primaryScreen(); avail = scr.availableGeometry(); self.adjustSize(); w,h=self.sizeHint().width()+16,self.sizeHint().height()+16; x=anchor.right()+8; y=anchor.top()
        if x+w-1>avail.right(): x=anchor.left()-w-8
        if y+h-1>avail.bottom(): y=avail.bottom()-h+1
        self.setGeometry(max(avail.left(), min(x,avail.right()-w+1)), max(avail.top(), min(y,avail.bottom()-h+1)), w,h)
        if not live:
            self.show(); self.raise_(); self._timer.start()

    def _clock_out(self):
        if self.pet is not None: self.pet._clock_out()
        self.refresh()
    def hideEvent(self, event): self._reveal = False; self._timer.stop(); super().hideEvent(event)
    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape: self.hide()
