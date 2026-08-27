"""Monthly work-calendar dialog with manual status overrides."""

from datetime import date
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QPushButton, QSpinBox, QListWidget, QListWidgetItem, QDialogButtonBox
from .model import WORKDAY, REST, ADJUSTED_WORKDAY, LEAVE


class WorkCalendarDialog(QDialog):
    def __init__(self, service, parent=None):
        super().__init__(parent); self.service = service; self.setWindowTitle("工时日历"); self.resize(420, 500)
        now = date.today(); self.year, self.month = now.year, now.month; root=QVBoxLayout(self)
        self.summary = QLabel(); root.addWidget(self.summary); self.list = QListWidget(); root.addWidget(self.list)
        self.status = QComboBox(); self.status.addItem("恢复自动判断", "auto"); self.status.addItem("工作日", WORKDAY); self.status.addItem("休息日", REST); self.status.addItem("调休上班", ADJUSTED_WORKDAY); self.status.addItem("请假", LEAVE)
        row=QHBoxLayout(); row.addWidget(self.status); apply_btn=QPushButton("应用到选中日期"); apply_btn.clicked.connect(self._apply); row.addWidget(apply_btn); root.addLayout(row)
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

