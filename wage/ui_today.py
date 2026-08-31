"""Today earnings window with privacy-aware display and clock-out action."""

from datetime import datetime, timedelta

from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
                             QFrame)

import anchor
import theme


class TodayWageWindow(QWidget):
    def __init__(self, service, parent=None):
        super().__init__(None)
        self.service = service
        self.pet = parent
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Tool | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.setMinimumWidth(300)
        root = QVBoxLayout(self); root.setContentsMargins(0, 0, 0, 0)
        card = QFrame(); card.setObjectName("card")
        card.setStyleSheet(f"QFrame#card {{ background: {theme.BG_CARD}; border: 1px solid {theme.BORDER}; border-radius: {theme.RADIUS}px; }}")
        lay = QVBoxLayout(card); lay.setContentsMargins(16, 14, 16, 14)
        top = QHBoxLayout(); t = QLabel("今日已赚"); t.setObjectName("title")
        close = QPushButton("✕"); close.setObjectName("flat"); close.clicked.connect(self.hide)
        top.addWidget(t); top.addStretch(); top.addWidget(close); lay.addLayout(top)
        self.amount = QLabel("未配置")
        self.amount.setStyleSheet(f"font-size: 22pt; font-weight: 700; color: {theme.ACCENT};")
        self.detail = QLabel(""); self.detail.setWordWrap(True)
        self.progress = QLabel(""); self.progress.setWordWrap(True)
        self.clock_btn = QPushButton("下班打卡"); self.clock_btn.setObjectName("primary")
        self.clock_btn.clicked.connect(self._clock_out)
        self.reveal_btn = QPushButton("临时显示金额"); self.reveal_btn.setObjectName("flat")
        self.reveal_btn.clicked.connect(self._toggle_reveal); self.reveal_btn.hide()
        for w in (self.amount, self.detail, self.progress, self.clock_btn, self.reveal_btn):
            lay.addWidget(w)
        root.addWidget(card)
        self._reveal = False
        self._timer = QTimer(self); self._timer.setInterval(1000)
        self._timer.timeout.connect(self.refresh)

    def _toggle_reveal(self):
        self._reveal = not self._reveal
        self.refresh()

    # ── text builders ──
    def _tier_state(self, snap):
        """(current rate label, eta datetime or None, remaining minutes)."""
        prior = self.service.prior_overtime_minutes_before(snap.date)
        month_minutes = prior + snap.overtime_minutes
        tier1 = self.service.calculator().OVERTIME_TIER_1_MINUTES
        if month_minutes >= tier1:
            return "25元/h", None, 0
        remaining = tier1 - month_minutes
        eta = datetime.combine(snap.date, self.service.settings.overtime_start) + timedelta(minutes=remaining)
        return "15元/h", eta, remaining

    def refresh(self):
        svc = self.service
        if not svc.configured:
            self.amount.setText("未配置")
            self.detail.setText("请先设置工资与工作时间")
            self.progress.clear()
            self.clock_btn.setEnabled(False)
            self.reveal_btn.hide()
            return
        now = svc._now()
        snap = svc.current_breakdown()
        rec = svc.record_for()
        hide = svc.settings.privacy_mode and not self._reveal

        def amt(value):
            return "已隐藏" if hide else f"¥{value:.2f}"

        clocked = rec is not None and rec.actual_clock_out is not None
        self.clock_btn.setEnabled(snap.overtime_minutes > 0 and not clocked)
        month_minutes = svc.prior_overtime_minutes_before(snap.date) + snap.overtime_minutes

        if clocked:
            out = rec.actual_clock_out
            self.amount.setText(f"{out:%H:%M} 下班")
            self.detail.setText(
                f"今日加班 {rec.overtime_minutes // 60}h{rec.overtime_minutes % 60:02d}m · "
                f"本月累计 {month_minutes // 60}h{month_minutes % 60:02d}m\n"
                f"今日加班费 {amt(rec.overtime_pay)} · 餐补 {amt(rec.meal_allowance)} · "
                f"今日已赚 {amt(snap.total_earned)}")
            self.progress.setText("下班打卡已记录")
        elif snap.overtime_minutes > 0:
            tier, eta, remaining = self._tier_state(snap)
            lines = [f"已加班 {snap.overtime_minutes // 60}h{snap.overtime_minutes % 60:02d}m · "
                     f"本月累计 {month_minutes // 60}h{month_minutes % 60:02d}m · 当前 {tier}"]
            self.amount.setText("加班中" if hide else amt(snap.total_earned))
            if eta is not None:
                if remaining <= 6 * 60:   # reachable in one overtime evening
                    lines.append(f"将在 {eta:%H:%M} 后进入 25元/h 档")
                else:
                    lines.append(f"距 25元/h 档还差 {remaining // 60}h{remaining % 60:02d}m 加班")
            if snap.expected_meal_allowance > 0:
                lines.append("餐补预计 +¥30" if not hide else "餐补预计 +（已隐藏）")
            self.detail.setText("\n".join(lines))
            self.progress.setText(f"距离 17:30 已过 {snap.overtime_minutes // 60}h{snap.overtime_minutes % 60:02d}m")
        else:
            minutes_to_go = int(max(0, (datetime.combine(snap.date, svc.settings.overtime_start) - now)
                                    .total_seconds()) // 60)
            self.amount.setText(f"今日进度 {snap.progress}%" if hide else amt(snap.total_earned))
            self.detail.setText(f"正常工资 {amt(snap.base_earned)} · 加班 {amt(snap.overtime_pay)} · "
                                f"餐补 {amt(snap.confirmed_meal_allowance)}")
            self.progress.setText(f"今日进度 {snap.progress}% · 距离 17:30 还有 "
                                  f"{minutes_to_go // 60}小时{minutes_to_go % 60:02d}分")

        self.reveal_btn.setText("恢复隐藏" if self._reveal else "临时显示金额")
        if hide:
            self.reveal_btn.show()
        else:
            self.reveal_btn.setVisible(svc.settings.privacy_mode)

    def show_near(self, anchor_rect, screen=None):
        self.move_near(anchor_rect, screen=screen, live=False)

    def move_near(self, anchor_rect, screen=None, live=False):
        self.adjustSize()
        w, h = self.sizeHint().width() + 16, self.sizeHint().height() + 16
        self.resize(w, h)
        anchor.place_panel(self, anchor_rect, screen=screen)
        if not live:
            self.show(); self.raise_(); self._timer.start()

    def _clock_out(self):
        if self.pet is not None:
            self.pet._clock_out()
        self.refresh()

    def hideEvent(self, event):
        self._reveal = False
        self._timer.stop()
        super().hideEvent(event)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.hide()
