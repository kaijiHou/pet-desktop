"""Monthly work-calendar dialog with manual status overrides."""

from datetime import date
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QPushButton, QSpinBox, QListWidget, QListWidgetItem, QInputDialog, QLineEdit
from .model import WORKDAY, REST, ADJUSTED_WORKDAY, LEAVE


class WorkCalendarDialog(QDialog):
    def __init__(self, service, parent=None):
        super().__init__(parent); self.service = service; self.setWindowTitle("工时日历"); self.resize(420, 500)
        now = date.today(); self.year, self.month = now.year, now.month; root=QVBoxLayout(self)
        self.summary = QLabel(); root.addWidget(self.summary); self.list = QListWidget(); self.list.currentItemChanged.connect(lambda *_: self._show_day_detail()); root.addWidget(self.list)
        self.detail = QLabel("选择日期查看明细"); self.detail.setWordWrap(True); root.addWidget(self.detail)
        self.status = QComboBox(); self.status.addItem("恢复自动判断", "auto"); self.status.addItem("工作日", WORKDAY); self.status.addItem("休息日", REST); self.status.addItem("调休上班", ADJUSTED_WORKDAY); self.status.addItem("请假", LEAVE)
        row=QHBoxLayout(); row.addWidget(self.status); apply_btn=QPushButton("应用到选中日期"); apply_btn.clicked.connect(self._apply); row.addWidget(apply_btn); edit_btn=QPushButton("修改下班时间"); edit_btn.clicked.connect(self._edit_clock_out); row.addWidget(edit_btn); root.addLayout(row)
        self.workdays=QSpinBox(); self.workdays.setRange(0,31); self.workdays.setSpecialValueText("自动"); self.workdays.setValue(service.calendar.manual_workday_count or 0); save=QPushButton("保存工作日数"); save.clicked.connect(lambda: service.calendar.set_manual_workday_count(self.workdays.value() or None)); row2=QHBoxLayout(); row2.addWidget(QLabel("工资计算工作日数")); row2.addWidget(self.workdays); row2.addWidget(save); root.addLayout(row2)
        self._refresh()

    def _refresh(self):
        self.list.clear(); count=self.service.calendar.workday_count(self.year,self.month); self.summary.setText(f"{self.year}年{self.month}月 · 本月应出勤 {count} 天")
        for day in self.service.calendar.month_days(self.year,self.month):
            item=QListWidgetItem(f"{day:%m-%d %a}  {self.service.calendar.status_for(day)}"); item.setData(Qt.UserRole, day); self.list.addItem(item)
    def _apply(self):
        item=self.list.currentItem()
        if not item: return
        day=item.data(Qt.UserRole); value=self.status.currentData()
        self.service.calendar.restore_auto(day) if value == "auto" else self.service.calendar.set_override(day,value); self._refresh()

    def _show_day_detail(self):
        item = self.list.currentItem()
        if not item:
            return
        day = item.data(Qt.UserRole); record = self.service.record_for(day)
        if not record:
            self.detail.setText(f"{day:%m月%d日} · 状态：{self.service.calendar.status_for(day)}\n尚无下班记录")
            return
        out = record.actual_clock_out.strftime("%H:%M") if record.actual_clock_out else "未记录"
        self.detail.setText(f"{day:%m月%d日} · 状态：{record.workday_status}\n下班：{out}  加班：{record.overtime_minutes // 60}h{record.overtime_minutes % 60:02d}m  加班费：¥{record.overtime_pay:.2f}\n餐补：¥{record.meal_allowance:.2f}\n备注：{record.note or '—'}")

    def _edit_clock_out(self):
        item = self.list.currentItem()
        if not item:
            return
        day = item.data(Qt.UserRole); record = self.service.record_for(day)
        initial = record.actual_clock_out.strftime("%H:%M") if record and record.actual_clock_out else "18:00"
        value, ok = QInputDialog.getText(self, "修改下班时间", "时间（HH:MM）", QLineEdit.Normal, initial)
        if not ok:
            return
        try:
            hour, minute = [int(p) for p in value.strip().split(":", 1)]
            from datetime import datetime
            self.service.edit_clock_out(day, datetime(day.year, day.month, day.day, hour, minute))
            self._refresh(); self._show_day_detail()
        except (ValueError, TypeError):
            self.detail.setText("时间格式应为 HH:MM")
