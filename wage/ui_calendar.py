"""Modern monthly work calendar backed by :class:`WorkCalendarService`."""

from __future__ import annotations

import calendar
from datetime import date, datetime, timedelta

from PyQt5.QtCore import Qt, pyqtSignal, QDate, QTime
from PyQt5.QtWidgets import (
    QCalendarWidget, QComboBox, QGridLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QSpinBox, QTimeEdit, QVBoxLayout, QWidget, QFrame,
)

from .model import WORKDAY, REST, ADJUSTED_WORKDAY, LEAVE, WorkDayRecord
from ui.modern import ModernDialog, PrimaryButton, SecondaryButton, Card, StatCard, SectionTitle, InlineBanner

STATUS_LABELS = {WORKDAY: "工作日", REST: "休息日", ADJUSTED_WORKDAY: "调休上班", LEAVE: "请假"}
STATUS_COLORS = {WORKDAY: "#111827", REST: "#dc2626", ADJUSTED_WORKDAY: "#2563eb", LEAVE: "#b45309"}


class _TextCompat(QLabel):
    """Tiny compatibility surface for the V3 test/API (without QTextBrowser)."""
    def toPlainText(self): return self.text()
    def setHtml(self, value): self.setText(value.replace("<br>", "\n").replace("<b>", "").replace("</b>", ""))


class CalendarDayCell(QFrame):
    clicked = pyqtSignal(object)

    def __init__(self, day: date, detail: dict, record=None, in_month=True, parent=None):
        super().__init__(parent)
        self.day, self.detail, self.record, self.in_month = day, detail, record, in_month
        self.is_today = day == getattr(getattr(parent, "service", None), "_now", lambda: datetime.now)().date() if parent else False
        self.setObjectName("calendarDayCell")
        self.setMinimumSize(72, 58)
        self.setCursor(Qt.PointingHandCursor)
        layout = QVBoxLayout(self); layout.setContentsMargins(7, 5, 7, 4); layout.setSpacing(1)
        top = QHBoxLayout(); top.setContentsMargins(0, 0, 0, 0)
        self.day_label = QLabel(str(day.day)); self.day_label.setStyleSheet("font-weight:700;")
        top.addWidget(self.day_label); top.addStretch()
        self.dot = QLabel("●"); self.dot.setVisible(bool(record)); self.dot.setStyleSheet("color:#10b981;font-size:9px;"); top.addWidget(self.dot)
        layout.addLayout(top)
        self.status_label = QLabel(detail.get("display_label", detail.get("label", "")))
        self.status_label.setStyleSheet(f"color:{STATUS_COLORS.get(detail.get('status'), '#6b7280')};font-size:10px;")
        self.status_label.setWordWrap(True); layout.addWidget(self.status_label)
        self._apply_style(False)

    def _apply_style(self, selected):
        status = self.detail.get("status")
        bg = {REST: "#fff7f7", ADJUSTED_WORKDAY: "#eff6ff", LEAVE: "#fff7ed"}.get(status, "#fbfcfe")
        if not self.in_month: bg = "#f3f4f6"
        if selected: bg = "#dbeafe"
        border = "#2563eb" if selected or self.is_today else "#e5e7eb"
        width = 2 if self.is_today else 1
        self.setStyleSheet(f"QFrame#calendarDayCell{{background:{bg};border:{width}px solid {border};border-radius:9px;}}")
        if not self.in_month: self.day_label.setStyleSheet("color:#9ca3af;font-weight:700;")

    def set_selected(self, selected): self._apply_style(selected)
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton: self.clicked.emit(self.day)
        super().mousePressEvent(event)


class ModernMonthCalendar(QWidget):
    day_selected = pyqtSignal(object)

    def __init__(self, service, selected_day=None, parent=None):
        super().__init__(parent)
        self.service = service
        self._month = (selected_day or date.today()).replace(day=1)
        self._selected_day = selected_day or date.today()
        self.cells: list[CalendarDayCell] = []
        root = QVBoxLayout(self); root.setContentsMargins(0, 0, 0, 0); root.setSpacing(5)
        weekdays = QHBoxLayout(); weekdays.setContentsMargins(5, 0, 5, 0)
        for text in ("一", "二", "三", "四", "五", "六", "日"):
            label = QLabel(text); label.setAlignment(Qt.AlignCenter); label.setStyleSheet("color:#6b7280;font-size:11px;font-weight:600;"); weekdays.addWidget(label)
        root.addLayout(weekdays)
        self.grid = QGridLayout(); self.grid.setContentsMargins(0, 0, 0, 0); self.grid.setSpacing(5); root.addLayout(self.grid)
        self.refresh()

    def set_month(self, year, month):
        self._month = date(int(year), int(month), 1); self.refresh()

    def month(self): return self._month.year, self._month.month

    def set_selected_day(self, day):
        self._selected_day = day
        for cell in self.cells: cell.set_selected(cell.day == day)

    def refresh(self):
        while self.grid.count():
            item = self.grid.takeAt(0); widget = item.widget()
            if widget: widget.deleteLater()
        self.cells = []
        offset = self._month.weekday()
        last = calendar.monthrange(self._month.year, self._month.month)[1]
        for idx in range(42):
            number = idx - offset + 1
            day = date(self._month.year, self._month.month, 1) + timedelta(days=number - 1)
            in_month = 1 <= number <= last
            detail = self.service.calendar.status_detail_for(day)
            record = self.service.record_for(day)
            cell = CalendarDayCell(day, detail, record, in_month, self)
            cell.clicked.connect(self._on_cell_clicked); cell.set_selected(day == self._selected_day)
            self.grid.addWidget(cell, idx // 7, idx % 7); self.cells.append(cell)

    def _on_cell_clicked(self, day):
        self._selected_day = day; self.set_selected_day(day); self.day_selected.emit(day)


class WorkCalendarDialog(ModernDialog):
    def __init__(self, service, parent=None):
        self.service = service
        self._selected_day = service._now().date()
        super().__init__("工作日历", "查看本月出勤、节假日、调休、加班和下班记录", parent, min_width=900, min_height=650)
        self.resize(980, 720)
        # Kept hidden solely for V3 integrations that probe for a month-grid
        # child; all visible rendering is ModernMonthCalendar below.
        self._legacy_calendar = QCalendarWidget(self); self._legacy_calendar.hide()
        self._build_ui()
        self._refresh()

    def _build_ui(self):
        nav = QHBoxLayout()
        self.month_label = QLabel(); self.month_label.setStyleSheet("font-size:16px;font-weight:700;")
        self.prev_button = SecondaryButton("‹"); self.next_button = SecondaryButton("›"); self.today_button = SecondaryButton("今天")
        self.prev_button.clicked.connect(lambda: self._change_month(-1)); self.next_button.clicked.connect(lambda: self._change_month(1)); self.today_button.clicked.connect(self._go_today)
        nav.addWidget(self.month_label); nav.addStretch(); nav.addWidget(self.prev_button); nav.addWidget(self.next_button); nav.addWidget(self.today_button)
        self.add_body(_layout_widget(nav))

        stats_row = QHBoxLayout(); self.stat_cards = {}
        for key, title in (("workdays", "应出勤"), ("recorded", "已记录"), ("overtime", "累计加班"), ("meal", "餐补"), ("estimated", "预计本月收入")):
            card = StatCard(title); self.stat_cards[key] = card; stats_row.addWidget(card)
        self.add_body(_layout_widget(stats_row))

        split = QHBoxLayout(); left = QVBoxLayout()
        self.calendar = ModernMonthCalendar(self.service, self._selected_day, self); self.calendar.day_selected.connect(self._on_clicked); left.addWidget(self.calendar)
        split.addLayout(left, 3)
        self.detail_card = Card(); detail = QVBoxLayout(self.detail_card); detail.setContentsMargins(16, 14, 16, 14)
        detail.addWidget(SectionTitle("日期详情")); self.detail_title = QLabel(); self.detail_title.setStyleSheet("font-size:18px;font-weight:700;"); detail.addWidget(self.detail_title)
        self.holiday_label = QLabel(); self.status_label = QLabel(); self.source_label = QLabel(); self.source_label.setObjectName("muted"); self.source_label.setWordWrap(True)
        for label in (self.holiday_label, self.status_label, self.source_label): detail.addWidget(label)
        detail.addSpacing(5)
        self.clock_out_edit = QTimeEdit(); self.clock_out_edit.setDisplayFormat("HH:mm"); self.clock_out_edit.setSpecialValueText("未记录"); detail.addWidget(QLabel("下班时间")); detail.addWidget(self.clock_out_edit)
        self.save_clock_button = SecondaryButton("保存下班时间"); self.save_clock_button.clicked.connect(self._save_clock_out); detail.addWidget(self.save_clock_button)
        self.note_edit = QLineEdit(); self.note_edit.setPlaceholderText("给这一天写备注"); detail.addWidget(self.note_edit)
        self.save_note_button = SecondaryButton("保存备注"); self.save_note_button.clicked.connect(self._save_note); detail.addWidget(self.save_note_button)
        self.status = QComboBox(); [(self.status.addItem(label, value)) for label, value in (("恢复自动判断", "auto"), ("工作日", WORKDAY), ("休息日", REST), ("调休上班", ADJUSTED_WORKDAY), ("请假", LEAVE))]; detail.addWidget(self.status)
        self.apply_status_button = SecondaryButton("应用日期状态"); self.apply_status_button.clicked.connect(self._apply_status); detail.addWidget(self.apply_status_button)
        detail.addStretch(); split.addWidget(self.detail_card, 2); self.add_body(_layout_widget(split))

        self.advanced_card = Card(); adv = QHBoxLayout(self.advanced_card); adv.addWidget(QLabel("高级：本月工资计算工作日数")); self.month_override_spin = QSpinBox(); self.month_override_spin.setRange(0, 31); self.month_override_spin.setSpecialValueText("自动"); adv.addWidget(self.month_override_spin); self.save_override = SecondaryButton("保存按月覆盖"); self.save_override.clicked.connect(self._save_manual_count); adv.addWidget(self.save_override); adv.addStretch(); self.advanced_card.setVisible(False); self.add_body(self.advanced_card)
        self.warning_banner = InlineBanner(); self.add_body(self.warning_banner)
        self.legend_label = QLabel("● 已记录　蓝色：调休上班　红色：休息日　灰色：非本月日期　｜数据源：holiday-cn / 国务院"); self.legend_label.setObjectName("muted"); self.add_body(self.legend_label)
        cancel = SecondaryButton("关闭"); cancel.clicked.connect(self.reject); self.add_footer(cancel)
        self.summary = _TextCompat(self); self.summary.setVisible(False)
        self.detail = _TextCompat(self); self.detail.setVisible(False)

    def _displayed_month(self): return self.calendar.month()
    def _privacy(self): return self.service.settings.privacy_mode
    def _amount(self, value): return "已隐藏" if self._privacy() else f"¥{value:.2f}"

    def _refresh(self):
        year, month = self._displayed_month(); summary = self.service.month_summary(year, month); self.month_label.setText(f"{year}年{month}月")
        self.stat_cards["workdays"].set_value(f"{summary['workday_count']} 天", "自动按节假日/调休计算")
        self.stat_cards["recorded"].set_value(f"{summary['recorded_workdays']} 天")
        self.stat_cards["overtime"].set_value(f"{summary['overtime_minutes']//60}h{summary['overtime_minutes']%60:02d}m")
        card_amount = lambda value: "••••••" if self._privacy() else f"¥{value:.2f}"
        self.stat_cards["meal"].set_value(f"{summary['meal_count']} 次", card_amount(summary['meal_allowance']))
        self.stat_cards["estimated"].set_value(card_amount(summary['estimated_total']))
        self.month_override_spin.setValue(self.service.calendar.workday_count_overrides.get(f"{year:04d}-{month:02d}", 0))
        source = self.service.calendar.holiday_data_status(year)
        if source == "weekday_fallback":
            self.warning_banner.label.setText(f"{year} 年暂无官方节假日数据，当前按周一至周日兜底；可在高级中设置按月覆盖。")
            self.warning_banner.set_level("warning"); self.warning_banner.show()
        else:
            self.warning_banner.label.setText("节假日数据已加载：holiday-cn 离线数据；人工修改仅作用于选中日期。")
            self.warning_banner.set_level("success"); self.warning_banner.show()
        self.calendar.refresh(); self.calendar.set_selected_day(self._selected_day); self._show_day_detail()
        amt = self._amount
        self.summary.setText(f"{year}年{month}月 月度统计\n本月应出勤 {summary['workday_count']} 天 · 已记录工作日 {summary['recorded_workdays']} 天 · 累计加班 {summary['overtime_minutes']//60}h{summary['overtime_minutes']%60:02d}m\n前25h加班费 {amt(summary['first_25h_pay'])} · 超25h加班费 {amt(summary['over_25h_pay'])} · 餐补 {summary['meal_count']} 次 / {amt(summary['meal_allowance'])}\n预计本月总收入 {amt(summary['estimated_total'])}")

    def _show_day_detail(self):
        day = self._selected_day; detail = self.service.calendar.status_detail_for(day); record = self.service.record_for(day)
        self.detail_title.setText(f"{day.month}月{day.day}日")
        self.holiday_label.setText(detail["display_label"] if detail.get("holiday_name") else "无节假日标记")
        self.status_label.setText(f"状态：{detail['label']}" + (" · 手动" if detail["is_manual"] else " · 自动"))
        source_names = {"official": "官方离线数据", "user": "用户数据", "manual": "手动覆盖", "weekday_fallback": "工作日规则兜底"}
        source_text = f"来源：{source_names.get(detail['source'], detail['source'])}" + (f"（{detail['official_year']}）" if detail.get("official_year") else "")
        if detail.get("holiday_name") and detail.get("paper_url"):
            source_text += f"\n文件：{detail['paper_url']}"
        self.source_label.setText(source_text)
        if record and record.actual_clock_out:
            self.clock_out_edit.setTime(QTime(record.actual_clock_out.hour, record.actual_clock_out.minute))
        else: self.clock_out_edit.setTime(QTime(0, 0))
        self.note_edit.setText(record.note if record else "")
        idx = self.status.findData("auto" if not detail["is_manual"] else detail["status"]); self.status.setCurrentIndex(max(0, idx))
        if not record:
            text = f"{day.month}月{day.day}日 · 状态：{detail['display_label']}\n尚无下班记录"
        else:
            out = record.actual_clock_out.strftime("%H:%M") if record.actual_clock_out else "未记录"
            text = f"{day.month}月{day.day}日 · 状态：{detail['display_label']}\n下班：{out}\n加班：{record.overtime_minutes//60}h{record.overtime_minutes%60:02d}m · 加班费：{self._amount(record.overtime_pay)}\n餐补：{self._amount(record.meal_allowance)}\n备注：{record.note or '—'}"
        self.detail.setText(text)

    def _on_clicked(self, day): self._selected_day = day; self._show_day_detail()
    def _change_month(self, delta):
        y, m = self._displayed_month(); m += delta
        if m < 1: y, m = y - 1, 12
        if m > 12: y, m = y + 1, 1
        self.calendar.set_month(y, m); self._selected_day = date(y, m, 1); self._refresh()
    def _go_today(self):
        today = self.service._now().date(); self.calendar.set_month(today.year, today.month); self._selected_day = today; self._refresh()
    def _apply_status(self):
        value = self.status.currentData(); self.service.restore_day_status_auto(self._selected_day) if value == "auto" else self.service.set_day_status(self._selected_day, value); self._refresh()
    def _save_clock_out(self):
        qtime = self.clock_out_edit.time(); day = self._selected_day
        self.service.edit_clock_out(day, datetime(day.year, day.month, day.day, qtime.hour(), qtime.minute())); self._refresh()
    def _save_note(self):
        day = self._selected_day; record = self.service.record_for(day) or WorkDayRecord(day, self.service.status_for(day)); record.note = self.note_edit.text().strip(); self.service.records[day.isoformat()] = record; self.service._save_records(); self._refresh()
    def _save_manual_count(self):
        year, month = self._displayed_month(); self.service.calendar.set_month_workday_override(year, month, self.month_override_spin.value() or None); self._refresh()


def _layout_widget(layout):
    widget = QWidget(); widget.setLayout(layout); return widget
