"""Non-blocking 'yesterday had no clock-out' prompt with three actions."""

from datetime import datetime, time

from PyQt5.QtCore import QTime, Qt
from PyQt5.QtWidgets import (QDialog, QHBoxLayout, QLabel, QPushButton,
                             QTimeEdit, QVBoxLayout)

import theme


class MissingClockoutDialog(QDialog):
    """昨天没有记录下班时间 — [补记时间] [昨天未加班] [稍后].

    补记时间 / 昨天未加班 permanently resolve the day; 稍后 (or closing the
    dialog) only dismisses it for this session.
    """

    def __init__(self, service, day, parent=None):
        super().__init__(parent)
        self.service = service
        self.day = day
        self.resolved = False
        self.setWindowFlags(Qt.Dialog | Qt.WindowStaysOnTopHint)
        self.setWindowTitle("补记下班时间")
        lay = QVBoxLayout(self)
        lay.addWidget(QLabel(f"{day.month}月{day.day}日 没有记录下班时间"))
        row = QHBoxLayout()
        row.addWidget(QLabel("时间"))
        now = QTime.currentTime()
        self.time_edit = QTimeEdit(now)
        self.time_edit.setDisplayFormat("HH:mm")
        row.addWidget(self.time_edit)
        lay.addLayout(row)
        buttons = QHBoxLayout()
        backfill = QPushButton("补记时间")
        backfill.setObjectName("primary")
        backfill.clicked.connect(self._backfill)
        no_ot = QPushButton("昨天未加班")
        no_ot.clicked.connect(self._no_overtime)
        later = QPushButton("稍后")
        later.setObjectName("flat")
        later.clicked.connect(self._later)
        buttons.addWidget(backfill)
        buttons.addWidget(no_ot)
        buttons.addWidget(later)
        lay.addLayout(buttons)

    def _backfill(self):
        t = self.time_edit.time()
        moment = datetime.combine(self.day, time(t.hour(), t.minute()))
        self.service.record_clock_out(moment, self.day)
        self.resolved = True
        self.accept()

    def _no_overtime(self):
        self.service.mark_no_overtime(self.day)
        self.resolved = True
        self.accept()

    def _later(self):
        self.service.mark_missing_clockout_prompt(self.day)
        self.reject()
