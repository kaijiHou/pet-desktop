"""Monthly work calendar: a real month grid with statutory + manual status,
day details and the full monthly statistics panel."""

from datetime import date, datetime

from PyQt5.QtCore import Qt, QDate
from PyQt5.QtGui import QColor, QTextCharFormat
from PyQt5.QtWidgets import (QComboBox, QDialog, QGridLayout, QHBoxLayout, QLabel,
                             QLineEdit, QPushButton, QSpinBox, QTextBrowser,
                             QVBoxLayout, QCalendarWidget, QInputDialog, QFrame)

from .model import WORKDAY, REST, ADJUSTED_WORKDAY, LEAVE

STATUS_LABELS = {
    WORKDAY: "工作日",
    REST: "休息日",
    ADJUSTED_WORKDAY: "调休上班",
    LEAVE: "请假",
}
STATUS_COLORS = {
    WORKDAY: QColor("#1f2023"),
    REST: QColor("#d94040"),
    ADJUSTED_WORKDAY: QColor("#2b62d9"),
    LEAVE: QColor("#c07f00"),
}


class WorkCalendarDialog(QDialog):
    def __init__(self, service, parent=None):
        super().__init__(parent)
        self.service = service
        self.setWindowTitle("工时日历")
        self.resize(760, 620)
        self._selected_day = service._now().date()
        root = QVBoxLayout(self)

        self.summary = QTextBrowser()
        self.summary.setMaximumHeight(170)
        self.summary.setOpenExternalLinks(False)
        root.addWidget(self.summary)

        mid = QHBoxLayout()
        self.calendar = QCalendarWidget()
        self.calendar.setGridVisible(True)
        self.calendar.setVerticalHeaderFormat(QCalendarWidget.NoVerticalHeader)
        self.calendar.clicked.connect(self._on_clicked)
        self.calendar.currentPageChanged.connect(lambda *_: self._refresh())
        mid.addWidget(self.calendar, 3)

        right = QVBoxLayout()
        self.detail = QTextBrowser()
        self.detail.setMinimumWidth(260)
        right.addWidget(self.detail, 1)

        self.status = QComboBox()
        for label, value in (("恢复自动判断", "auto"), ("工作日", WORKDAY),
                             ("休息日", REST), ("调休上班", ADJUSTED_WORKDAY), ("请假", LEAVE)):
            self.status.addItem(label, value)
        apply_btn = QPushButton("修改日期状态")
        apply_btn.clicked.connect(self._apply_status)
        edit_btn = QPushButton("修改下班时间")
        edit_btn.clicked.connect(self._edit_clock_out)
        today_btn = QPushButton("今天")
        today_btn.clicked.connect(self._go_today)
        note_btn = QPushButton("备注")
        note_btn.clicked.connect(self._edit_note)
        for w in (apply_btn, edit_btn, note_btn, today_btn):
            right.addWidget(w)
        mid.addLayout(right, 2)
        root.addLayout(mid)

        row = QHBoxLayout()
        self.workdays = QSpinBox()
        self.workdays.setRange(0, 31)
        self.workdays.setSpecialValueText("自动")
        self.workdays.setValue(service.calendar.manual_workday_count or 0)
        save = QPushButton("保存工资计算工作日数")
        save.clicked.connect(self._save_manual_count)
        row.addWidget(QLabel("工资计算工作日数"))
        row.addWidget(self.workdays)
        row.addWidget(save)
        row.addStretch()
        root.addLayout(row)
        self._refresh()

    # ── data → UI ──
    def _displayed_month(self):
        y, m = self.calendar.yearShown(), self.calendar.monthShown()
        return y, m

    def _privacy(self):
        return self.service.settings.privacy_mode

    def _refresh(self):
        year, month = self._displayed_month()
        s = self.service.month_summary(year, month)
        hide = self._privacy()

        def amt(value):
            return "已隐藏" if hide else f"¥{value:.2f}"

        lines = [
            f"<b>{year}年{month}月 月度统计</b>",
            f"本月应出勤 {s['workday_count']} 天 · 已记录工作日 {s['recorded_workdays']} 天 · "
            f"累计加班 {s['overtime_minutes'] // 60}h{s['overtime_minutes'] % 60:02d}m",
            f"前25h加班费 {amt(s['first_25h_pay'])} · 超25h加班费 {amt(s['over_25h_pay'])} · "
            f"餐补 {s['meal_count']} 次 / {amt(s['meal_allowance'])}",
            f"本月合同基础工资 {amt(s['monthly_salary'])} · 截至今日工作价值 {amt(s['worked_value_to_date'])}",
            f"已确认加班费 {amt(s['confirmed_overtime_pay'])} · 已确认餐补 {amt(s['confirmed_meal_allowance'])} · "
            f"<b>预计本月总收入 {amt(s['estimated_total'])}</b>",
        ]
        self.summary.setHtml("<br>".join(lines))
        self._paint_month(year, month)
        self._show_day_detail()

    def _paint_month(self, year, month):
        # reset formats painted for previous pages so marks never leak
        for qd in getattr(self, "_formatted_dates", set()):
            self.calendar.setDateTextFormat(qd, QTextCharFormat())
        self._formatted_dates = set()
        for day in self.service.calendar.month_days(year, month):
            qd = QDate(day.year, day.month, day.day)
            fmt = QTextCharFormat()
            status = self.service.status_for(day)
            fmt.setForeground(STATUS_COLORS.get(status, fmt.foreground()))
            record = self.service.record_for(day)
            tooltip_parts = [STATUS_LABELS.get(status, status)]
            if record and record.actual_clock_out:
                font = fmt.font()
                font.setBold(True)
                fmt.setFont(font)
                tooltip_parts.append(f"下班 {record.actual_clock_out:%H:%M}")
            if record and record.meal_allowance > 0:
                tooltip_parts.append("餐补")
            fmt.setToolTip(" · ".join(tooltip_parts))
            self.calendar.setDateTextFormat(qd, fmt)
            self._formatted_dates.add(qd)

    def _show_day_detail(self):
        day = self._selected_day
        status = self.service.status_for(day)
        record = self.service.record_for(day)
        hide = self._privacy()

        def amt(value):
            return "已隐藏" if hide else f"¥{value:.2f}"

        head = f"<b>{day.month}月{day.day}日</b> · 状态：{STATUS_LABELS.get(status, status)}"
        if not record:
            self.detail.setHtml(head + "<br>尚无下班记录")
            return
        out = record.actual_clock_out.strftime("%H:%M") if record.actual_clock_out else "未记录"
        overtime = f"{record.overtime_minutes // 60}h{record.overtime_minutes % 60:02d}m"
        note = record.note or "—"
        resolved = "（已确认未加班）" if record.resolved_no_overtime and not record.actual_clock_out else ""
        self.detail.setHtml(
            head + resolved + "<br>"
            f"下班：{out}<br>"
            f"加班：{overtime} · 加班费：{amt(record.overtime_pay)}<br>"
            f"餐补：{amt(record.meal_allowance)}<br>"
            f"备注：{note}"
        )

    # ── actions ──
    def _on_clicked(self, qdate):
        self._selected_day = date(qdate.year(), qdate.month(), qdate.day())
        self._show_day_detail()

    def _go_today(self):
        today = self.service._now().date()
        self.calendar.setSelectedDate(QDate(today.year, today.month, today.day))
        self._selected_day = today
        self._refresh()

    def _apply_status(self):
        day = self._selected_day
        value = self.status.currentData()
        if value == "auto":
            self.service.calendar.restore_auto(day)
        else:
            self.service.calendar.set_override(day, value)
        self._refresh()

    def _edit_clock_out(self):
        day = self._selected_day
        record = self.service.record_for(day)
        initial = record.actual_clock_out.strftime("%H:%M") if record and record.actual_clock_out else "18:00"
        value, ok = QInputDialog.getText(self, "修改下班时间", "时间（HH:MM）", QLineEdit.Normal, initial)
        if not ok:
            return
        try:
            hour, minute = [int(p) for p in value.strip().split(":", 1)]
            self.service.edit_clock_out(day, datetime(day.year, day.month, day.day, hour, minute))
            self._refresh()
        except (ValueError, TypeError):
            self.detail.setHtml("时间格式应为 HH:MM")

    def _edit_note(self):
        day = self._selected_day
        record = self.service.record_for(day)
        text, ok = QInputDialog.getText(self, "备注", f"{day.month}月{day.day}日 备注",
                                        QLineEdit.Normal, record.note if record else "")
        if not ok:
            return
        if record is None:
            from .model import WorkDayRecord
            record = WorkDayRecord(day, self.service.status_for(day))
        record.note = text.strip()
        self.service.records[day.isoformat()] = record
        self.service._save_records()
        self._refresh()

    def _save_manual_count(self):
        self.service.calendar.set_manual_workday_count(self.workdays.value() or None)
        self._refresh()
