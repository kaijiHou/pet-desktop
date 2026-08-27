"""Compact first-run/settings dialog for local wage tracking."""

from PyQt5.QtCore import Qt, QTime
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QFormLayout, QCheckBox, QDoubleSpinBox, QTimeEdit, QComboBox, QSpinBox, QDialogButtonBox, QLabel


class WageSettingsDialog(QDialog):
    def __init__(self, service, parent=None):
        super().__init__(parent); self.service = service; self.setWindowTitle("工资与工作时间"); self.setMinimumWidth(360)
        root = QVBoxLayout(self); form = QFormLayout()
        s = service.settings
        self.enabled = QCheckBox("启用今日收入统计"); self.enabled.setChecked(s.enabled); root.addWidget(self.enabled)
        self.salary = QDoubleSpinBox(); self.salary.setRange(0, 99999999); self.salary.setDecimals(2); self.salary.setValue(float(s.monthly_salary)); self.salary.setSuffix(" 元/月")
        self.work_start = QTimeEdit(QTime(s.work_start.hour, s.work_start.minute)); self.work_start.setDisplayFormat("HH:mm")
        self.lunch_start = QTimeEdit(QTime(s.lunch_start.hour, s.lunch_start.minute)); self.lunch_start.setDisplayFormat("HH:mm")
        self.lunch_end = QTimeEdit(QTime(s.lunch_end.hour, s.lunch_end.minute)); self.lunch_end.setDisplayFormat("HH:mm")
        self.interval = QComboBox(); self.interval.addItem("关闭", 0); [self.interval.addItem(f"每 {n} 分钟", n) for n in (10, 30, 60, 120)]; self.interval.setCurrentIndex(max(0, [0,10,30,60,120].index(s.income_interval_minutes)))
        self.privacy = QCheckBox("隐私模式（隐藏所有金额）"); self.privacy.setChecked(s.privacy_mode)
        self.workdays = QSpinBox(); self.workdays.setRange(0, 31); self.workdays.setSpecialValueText("按日历自动计算"); self.workdays.setValue(s.manual_workday_count or 0)
        for label, widget in (("月工资", self.salary), ("上班时间", self.work_start), ("午休开始", self.lunch_start), ("午休结束", self.lunch_end), ("收入提示", self.interval), ("工资计算工作日数", self.workdays)):
            form.addRow(label, widget)
        form.addRow("", self.privacy); root.addLayout(form); root.addWidget(QLabel("规则：17:30 后加班；20:00 及以后下班确认餐补。"))
        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel); buttons.accepted.connect(self._save); buttons.rejected.connect(self.reject); root.addWidget(buttons)

    def _save(self):
        self.service.update_settings(enabled=self.enabled.isChecked(), monthly_salary=str(self.salary.value()), work_start=self.work_start.time().toString("HH:mm"), lunch_start=self.lunch_start.time().toString("HH:mm"), lunch_end=self.lunch_end.time().toString("HH:mm"), income_interval_minutes=self.interval.currentData(), privacy_mode=self.privacy.isChecked(), manual_workday_count=(self.workdays.value() or None))
        self.accept()

