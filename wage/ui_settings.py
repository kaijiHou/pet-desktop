"""Modern wage settings; day counts are read-only and come from the calendar."""

from PyQt5.QtCore import QTime
from PyQt5.QtWidgets import QCheckBox, QFormLayout, QHBoxLayout, QLabel, QVBoxLayout

from ui.modern import ModernDialog, PrimaryButton, SecondaryButton, Card, SectionTitle, InlineBanner, ModernMoneyField, ModernTimeField, ModernSelect


class WageSettingsDialog(ModernDialog):
    def __init__(self, service, parent=None):
        self.service = service
        super().__init__("工资与工作时间", "自动按中国节假日与调休计算每日收入", parent, min_width=520, resizable=True)
        self.resize(560, 540)
        self._build_ui()

    def _build_ui(self):
        settings = self.service.settings
        form_card = Card(); form = QFormLayout(form_card); form.setContentsMargins(16, 14, 16, 14); form.setVerticalSpacing(10)
        self.enabled = QCheckBox("启用收入统计"); self.enabled.setChecked(settings.enabled); form.addRow("状态", self.enabled)
        self.salary = ModernMoneyField(settings.monthly_salary); form.addRow("月工资", self.salary)
        self.work_start = _time(settings.work_start); form.addRow("上班时间", self.work_start)
        self.lunch_start = _time(settings.lunch_start); form.addRow("午休开始", self.lunch_start)
        self.lunch_end = _time(settings.lunch_end); form.addRow("午休结束", self.lunch_end)
        self.interval = ModernSelect(); [(self.interval.addItem(label, value)) for label, value in (("关闭", 0), ("每 10 分钟", 10), ("每 30 分钟", 30), ("每 60 分钟", 60), ("每 120 分钟", 120))]; idx = self.interval.findData(settings.income_interval_minutes); self.interval.setCurrentIndex(max(0, idx)); form.addRow("收入提示", self.interval)
        self.privacy = QCheckBox("隐私模式（隐藏所有金额）"); self.privacy.setChecked(settings.privacy_mode); form.addRow("隐私", self.privacy)
        self.privacy.stateChanged.connect(lambda _state: self._apply_privacy())
        self.add_body(form_card)

        calendar_card = Card(); cal_layout = QVBoxLayout(calendar_card); cal_layout.setContentsMargins(16, 13, 16, 13); cal_layout.addWidget(SectionTitle("本月工作日"))
        row = QHBoxLayout(); self.workdays_label = QLabel(); self.workdays_label.setStyleSheet("font-size:22px;font-weight:700;"); row.addWidget(self.workdays_label); self.auto_badge = QLabel("自动"); self.auto_badge.setStyleSheet("background:#dcfce7;color:#047857;padding:4px 8px;border-radius:10px;font-weight:600;"); row.addWidget(self.auto_badge); row.addStretch(); self.calendar_button = SecondaryButton("查看工作日历"); self.calendar_button.clicked.connect(self._open_calendar); row.addWidget(self.calendar_button); cal_layout.addLayout(row)
        self.migration_banner = InlineBanner(); self.migration_banner.set_level("info"); cal_layout.addWidget(self.migration_banner)
        if settings.legacy_manual_workday_count is not None and self.service.consume_legacy_migration_notice():
            self.migration_banner.label.setText(f"已保留旧版手工天数 {settings.legacy_manual_workday_count} 作为审计记录，当前计算以工作日历为准。")
        else:
            self.migration_banner.hide()
        self.add_body(calendar_card)

        info = QLabel("规则：17:30 后计入加班；累计加班前 25 小时按 15 元/小时，之后按 25 元/小时；20:00 及以后下班并确认可计餐补。")
        info.setWordWrap(True); info.setObjectName("muted"); self.add_body(info)
        now = self.service._now().date(); notes = []
        for day in self.service.calendar.month_days(now.year, now.month):
            detail = self.service.calendar.status_detail_for(day)
            if detail.get("holiday_name"):
                notes.append(f"{day.month}月{day.day}日 {detail['display_label']}")
        self.calendar_note = QLabel("；".join(notes) + f"。本月自动计算应出勤 {self.service.calendar.workday_count(now.year, now.month)} 天。" if notes else f"本月自动计算应出勤 {self.service.calendar.workday_count(now.year, now.month)} 天。")
        self.calendar_note.setWordWrap(True); self.calendar_note.setObjectName("muted"); self.add_body(self.calendar_note)
        cancel = SecondaryButton("取消"); cancel.clicked.connect(self.reject); save = PrimaryButton("保存"); save.clicked.connect(self._save); self.add_footer(cancel); self.add_footer(save)
        self._refresh_workdays()
        self._apply_privacy()

    def _apply_privacy(self):
        hidden = self.privacy.isChecked()
        self.salary.setEnabled(not hidden)
        if hidden:
            self.salary.lineEdit().setText("••••••")
        else:
            self.salary.setValue(self.salary.value())

    def _refresh_workdays(self):
        now = self.service._now().date(); key = f"{now.year:04d}-{now.month:02d}"
        count = self.service.calendar.workday_count(now.year, now.month); manual = key in self.service.calendar.workday_count_overrides
        self.workdays_label.setText(f"{count} 天"); self.auto_badge.setText("手动" if manual else "自动")
        self.calendar_note.setText((self.calendar_note.text().split("。本月", 1)[0] if "。本月" in self.calendar_note.text() else self.calendar_note.text()).rstrip("。") + f"。本月{ '手动覆盖' if manual else '自动计算' }应出勤 {count} 天。")

    def _open_calendar(self):
        from .ui_calendar import WorkCalendarDialog
        WorkCalendarDialog(self.service, self).exec_(); self._refresh_workdays()

    def _save(self):
        self.service.update_settings(enabled=self.enabled.isChecked(), monthly_salary=str(self.salary.value()), work_start=self.work_start.time().toString("HH:mm"), lunch_start=self.lunch_start.time().toString("HH:mm"), lunch_end=self.lunch_end.time().toString("HH:mm"), income_interval_minutes=self.interval.currentData(), privacy_mode=self.privacy.isChecked())
        self.accept()


def _time(value):
    return ModernTimeField(QTime(value.hour, value.minute))
