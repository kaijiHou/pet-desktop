"""Modern monthly work calendar backed by :class:`WorkCalendarService`."""

from __future__ import annotations

import calendar
from datetime import date, datetime, timedelta

from PyQt5.QtCore import Qt, pyqtSignal, QTime, QTimer
from PyQt5.QtWidgets import (
    QCalendarWidget, QGridLayout, QHBoxLayout, QLabel,
    QSpinBox, QVBoxLayout, QWidget, QFrame, QAbstractSpinBox,
)

from .model import WORKDAY, REST, ADJUSTED_WORKDAY, LEAVE, WorkDayRecord
import ui_skin
from ui.modern import (ModernDialog, PrimaryButton, SecondaryButton, Card,
                       StatCard, SectionTitle, InlineBanner, ModernTimeField,
                       ModernLineEdit, ModernComboBox)
from ui.modern import ModernDialog, PrimaryButton, SecondaryButton, Card, StatCard, SectionTitle, InlineBanner, ModernTimeField, ModernLineEdit, ModernComboBox

STATUS_LABELS = {WORKDAY: "工作日", REST: "休息日", ADJUSTED_WORKDAY: "调休上班", LEAVE: "请假"}


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
        self._hovered = False
        self.setObjectName("calendarDayCell")
        self.setMinimumSize(72, 64)
        self.setCursor(Qt.PointingHandCursor)
        layout = QVBoxLayout(self); layout.setContentsMargins(7, 5, 7, 4); layout.setSpacing(1)
        top = QHBoxLayout(); top.setContentsMargins(0, 0, 0, 0)
        self.day_label = QLabel(str(day.day)); self.day_label.setStyleSheet("font-weight:700;")
        top.addWidget(self.day_label); top.addStretch()
        self.dot = QLabel("●"); self.dot.setVisible(bool(record)); top.addWidget(self.dot)
        layout.addLayout(top)
        self.status_label = QLabel(detail.get("display_label", detail.get("label", "")) if in_month else "")
        self.status_label.setWordWrap(True); layout.addWidget(self.status_label)
        self._apply_style(False)

    def _apply_style(self, selected):
        """Cell colors from the active skin (V5.8: status washes + today ring)."""
        p = ui_skin.palette()
        status = self.detail.get("status")
        if not self.in_month:
            bg = p["bg"]
        elif status == REST:
            bg = ui_skin._tint(p["danger"], p["card"], 0.20)
        elif status == ADJUSTED_WORKDAY:
            bg = ui_skin._tint(p["info"], p["card"], 0.20)
        elif status == LEAVE:
            bg = ui_skin._tint(p["warn"], p["card"], 0.20)
        else:
            bg = p["card"]
        if selected:
            bg = ui_skin._tint(p["accent"], p["card"], 0.26)
        elif self._hovered and self.in_month:
            bg = p["tint_light"]
        if selected or self.is_today:
            border, width = p["accent"], 2
        elif self._hovered:
            border, width = p["tint_border"], 1
        else:
            border, width = p["border"], 1
        self.setStyleSheet(f"QFrame#calendarDayCell{{background:{bg};border:{width}px solid {border};border-radius:12px;}}")
        day_fg = (p["muted"] if not self.in_month
                  else {REST: p["danger"], ADJUSTED_WORKDAY: p["info"], LEAVE: p["warn"]}.get(status, p["text"]))
        self.day_label.setStyleSheet(f"color:{day_fg};font-weight:700;")
        self.dot.setStyleSheet(f"color:{p['ok']};font-size:9px;")
        status_fg = p["muted"] if not self.in_month else day_fg
        self.status_label.setStyleSheet(f"color:{status_fg};font-size:10px;font-weight:600;")

    def set_selected(self, selected): self._apply_style(selected)
    def enterEvent(self, event):
        self._hovered = True
        self._apply_style(self.day == getattr(self.parent(), "_selected_day", None))
        super().enterEvent(event)
    def leaveEvent(self, event):
        self._hovered = False
        self._apply_style(self.day == getattr(self.parent(), "_selected_day", None))
        super().leaveEvent(event)
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
        weekday_color = ui_skin.palette()["muted"]
        weekdays = QHBoxLayout(); weekdays.setContentsMargins(5, 0, 5, 0)
        for text in ("一", "二", "三", "四", "五", "六", "日"):
            label = QLabel(text); label.setAlignment(Qt.AlignCenter); label.setStyleSheet(f"color:{weekday_color};font-size:11px;font-weight:600;"); weekdays.addWidget(label)
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
            if widget:
                # hide() first: deleteLater needs an event-loop turn, and a
                # deferred cell must never paint at its stale position.
                widget.hide(); widget.deleteLater()
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
        super().__init__("工作日历", "节假日 · 调休 · 加班记录", parent, min_width=900, min_height=650, resizable=True)
        self.resize(980, 720)
        # Kept hidden solely for V3 integrations that probe for a month-grid
        # child; all visible rendering is ModernMonthCalendar below.
        self._legacy_calendar = QCalendarWidget(self); self._legacy_calendar.hide()
        self._build_ui()
        self._refresh()

    def _build_ui(self):
        p = ui_skin.palette()
        nav = QHBoxLayout()
        self.month_label = QLabel(); self.month_label.setStyleSheet(f"color:{p['text']};font-size:17px;font-weight:800;")
        self.prev_button = SecondaryButton("上月"); self.next_button = SecondaryButton("下月"); self.today_button = SecondaryButton("今天")
        self.prev_button.setToolTip("查看上个月"); self.next_button.setToolTip("查看下个月")
        self.prev_button.clicked.connect(lambda: self._change_month(-1)); self.next_button.clicked.connect(lambda: self._change_month(1)); self.today_button.clicked.connect(self._go_today)
        self.rules_button = SecondaryButton("排班规则")
        self.rules_button.setToolTip("工作日计算规则")
        self.rules_button.clicked.connect(self._toggle_rules)
        nav.addWidget(self.month_label); nav.addStretch(); nav.addWidget(self.rules_button); nav.addWidget(self.prev_button); nav.addWidget(self.next_button); nav.addWidget(self.today_button)
        self.add_body(_layout_widget(nav))

        stats_row = QHBoxLayout(); self.stat_cards = {}
        for key, title in (("workdays", "📅 应出勤"), ("recorded", "✅ 已记录"), ("overtime", "⏱ 累计加班"), ("meal", "🍚 餐补"), ("estimated", "💰 预计本月收入")):
            card = StatCard(title); self.stat_cards[key] = card; stats_row.addWidget(card)
        self.add_body(_layout_widget(stats_row))

        split = QHBoxLayout(); left = QVBoxLayout()
        self.calendar = ModernMonthCalendar(self.service, self._selected_day, self); self.calendar.day_selected.connect(self._on_clicked); left.addWidget(self.calendar)
        split.addLayout(left, 3)
        self.detail_card = Card(); detail = QVBoxLayout(self.detail_card); detail.setContentsMargins(16, 14, 16, 14)
        detail.addWidget(SectionTitle("日期详情")); self.detail_title = QLabel(); self.detail_title.setStyleSheet(f"color:{p['text']};font-size:18px;font-weight:700;"); detail.addWidget(self.detail_title)
        self.weekday_label = QLabel(); self.holiday_label = QLabel(); self.status_label = QLabel(); self.source_label = QLabel(); self.source_label.setObjectName("muted"); self.source_label.setWordWrap(True)
        for label in (self.weekday_label, self.holiday_label, self.status_label, self.source_label): detail.addWidget(label)
        detail.addSpacing(5)
        detail.addWidget(QLabel("下班时间"))
        self.clock_label = QLabel("未记录"); self.clock_label.setStyleSheet(f"color:{p['amount']};font-size:15px;font-weight:700;")
        detail.addWidget(self.clock_label)
        picker_col = QVBoxLayout(); picker_col.setSpacing(6)
        self.picker_row = QHBoxLayout(); self.picker_row.setSpacing(6)
        self.picker_hour = ModernComboBox(); self.picker_hour.addItems([f"{h:02d} 时" for h in range(24)])
        self.picker_minute = ModernComboBox(); self.picker_minute.addItems([f"{m:02d} 分" for m in range(60)])
        self.picker_row.addWidget(self.picker_hour); self.picker_row.addWidget(self.picker_minute)
        self.picker_btn_row = QHBoxLayout(); self.picker_btn_row.setSpacing(6)
        self.picker_ok = SecondaryButton("确定"); self.picker_ok.clicked.connect(self._picker_confirmed)
        self.picker_cancel = SecondaryButton("取消"); self.picker_cancel.clicked.connect(self._picker_cancel)
        self.picker_btn_row.addWidget(self.picker_ok); self.picker_btn_row.addWidget(self.picker_cancel)
        picker_col.addLayout(self.picker_row); picker_col.addLayout(self.picker_btn_row)
        picker_host = QWidget(); picker_host.setLayout(picker_col); picker_host.setStyleSheet("background: transparent;")
        picker_host.hide(); detail.addWidget(picker_host)
        self.picker_host = picker_host
        self._clock_selection = None   # 用户通过"选时间"指定的时刻；None = 跟随按钮语义
        clock_row = QHBoxLayout()
        self.record_out_button = PrimaryButton("下班打卡"); self.record_out_button.clicked.connect(self._save_clock_out); self.save_clock_button = self.record_out_button; clock_row.addWidget(self.record_out_button)
        self.pick_time_button = SecondaryButton("选时间…"); self.pick_time_button.clicked.connect(self._pick_clock_time); clock_row.addWidget(self.pick_time_button); detail.addLayout(clock_row)
        self.note_edit = ModernLineEdit(); self.note_edit.setPlaceholderText("给这一天写备注"); detail.addWidget(self.note_edit)
        note_row = QHBoxLayout()
        self.note_button = SecondaryButton("添加备注"); self.note_button.clicked.connect(self._save_note); self.save_note_button = self.note_button; note_row.addWidget(self.note_button)
        self.cancel_note_button = SecondaryButton("取消"); self.cancel_note_button.clicked.connect(self._cancel_note); self.cancel_note_button.hide(); note_row.addWidget(self.cancel_note_button); detail.addLayout(note_row)
        self.note_edit.textChanged.connect(lambda _t: self.cancel_note_button.show())
        self.record_metrics_label = QLabel(); self.record_metrics_label.setObjectName("muted"); self.record_metrics_label.setWordWrap(True); detail.addWidget(self.record_metrics_label)
        self.status = ModernComboBox(); [(self.status.addItem(label, value)) for label, value in (("恢复自动判断", "auto"), ("工作日", WORKDAY), ("休息日", REST), ("调休上班", ADJUSTED_WORKDAY), ("请假", LEAVE))]; detail.addWidget(self.status)
        self.apply_status_button = PrimaryButton("应用日期状态"); self.apply_status_button.clicked.connect(self._apply_status); detail.addWidget(self.apply_status_button)
        detail.addStretch(); split.addWidget(self.detail_card, 2); self.add_body(_layout_widget(split))

        self.advanced_card = Card(); self._rules_expanded = False; adv = QVBoxLayout(self.advanced_card)
        self.cycle_info_label = QLabel("国庆调休周按官方安排；2026-10-12 起周六按大小周交替：10-12 所在周是小周（10/17 上班），下周大周（10/24 休息），逐周交替。")
        self.cycle_info_label.setWordWrap(True); self.cycle_info_label.setObjectName("muted"); adv.addWidget(self.cycle_info_label)
        override_row = QHBoxLayout(); override_row.addWidget(QLabel("本月工资计算工作日数")); self.month_override_spin = QSpinBox(); self.month_override_spin.setRange(0, 31); self.month_override_spin.setSpecialValueText("自动"); self.month_override_spin.setButtonSymbols(QAbstractSpinBox.NoButtons); self.month_override_spin.setMinimumHeight(38); override_row.addWidget(self.month_override_spin); self.save_override = SecondaryButton("保存按月覆盖"); self.save_override.clicked.connect(self._save_manual_count); override_row.addWidget(self.save_override); self.restore_override = SecondaryButton("恢复自动"); self.restore_override.clicked.connect(lambda: self._restore_manual_count()); override_row.addWidget(self.restore_override); override_row.addStretch(); adv.addLayout(override_row)
        self.advanced_card.setVisible(False); self.add_body(self.advanced_card)
        self.warning_banner = InlineBanner(); self.add_body(self.warning_banner)
        self.legend_label = QLabel(self._legend_text()); self.legend_label.setObjectName("muted"); self.legend_label.setWordWrap(True); self.add_body(self.legend_label)
        cancel = SecondaryButton("关闭"); cancel.clicked.connect(self.reject); self.add_footer(cancel)
        self.summary = _TextCompat(self); self.summary.setVisible(False)
        self.detail = _TextCompat(self); self.detail.setVisible(False)

    def _legend_text(self):
        """Colored-dot legend (rich text) matching the cell status washes."""
        p = ui_skin.palette()

        def dot(color):
            return f'<span style="color:{color};">●</span>'

        return (f"{dot(p['ok'])} 已记录打卡　{dot(p['info'])} 调休/小周上班　"
                f"{dot(p['danger'])} 休息日/大周休息　{dot(p['muted'])} 非本月日期　"
                f"｜数据源：holiday-cn / 国务院")

    def _displayed_month(self): return self.calendar.month()
    def _privacy(self): return self.service.settings.privacy_mode
    def _amount(self, value): return "已隐藏" if self._privacy() else f"¥{value:.2f}"

    def _refresh(self):
        year, month = self._displayed_month(); summary = self.service.month_summary(year, month); self.month_label.setText(f"{year}年{month}月")
        key = f"{year:04d}-{month:02d}"; manual = key in self.service.calendar.workday_count_overrides
        self.stat_cards["workdays"].set_value(f"{summary['workday_count']} 天", "手动覆盖" if manual else "自动按节假日/大小周计算")
        self.stat_cards["recorded"].set_value(f"{summary['recorded_workdays']} 天")
        self.stat_cards["overtime"].set_value(f"{summary['overtime_minutes']//60}h{summary['overtime_minutes']%60:02d}m")
        card_amount = lambda value: "••••••" if self._privacy() else f"¥{value:.2f}"
        self.stat_cards["meal"].set_value(f"{summary['meal_count']} 次", card_amount(summary['meal_allowance']))
        self.stat_cards["estimated"].set_value(card_amount(summary['estimated_total']))
        self.month_override_spin.setValue(self.service.calendar.workday_count_overrides.get(f"{year:04d}-{month:02d}", 0))
        source = self.service.calendar.holiday_data_status(year)
        if source == "weekday_fallback":
            self.warning_banner.label.setText("该年份暂无官方节假日数据；工作日按工作日规则与大小周推算。")
            self.warning_banner.set_level("warning"); self.warning_banner.show()
        else:
            self.warning_banner.label.setText("官方节假日/调休优先；大小周从 2026-10-12 起交替。人工修改仅作用于选中日期。")
            self.warning_banner.set_level("success"); self.warning_banner.show()
        self.calendar.refresh(); self.calendar.set_selected_day(self._selected_day); self._show_day_detail()
        amt = self._amount
        self.summary.setText(f"{year}年{month}月 月度统计\n本月应出勤 {summary['workday_count']} 天 · 已记录工作日 {summary['recorded_workdays']} 天 · 累计加班 {summary['overtime_minutes']//60}h{summary['overtime_minutes']%60:02d}m\n前25h加班费 {amt(summary['first_25h_pay'])} · 超25h加班费 {amt(summary['over_25h_pay'])} · 餐补 {summary['meal_count']} 次 / {amt(summary['meal_allowance'])}\n预计本月总收入 {amt(summary['estimated_total'])}")

    def _show_day_detail(self):
        for button in (self.record_out_button, self.note_button, self.apply_status_button):
            self._reset_action_feedback(button)
        day = self._selected_day; detail = self.service.calendar.status_detail_for(day); record = self.service.record_for(day)
        self.detail_title.setText(f"{day.month}月{day.day}日")
        self.weekday_label.setText(day.strftime("%Y年%m月%d日 · %A").replace("Monday", "星期一").replace("Tuesday", "星期二").replace("Wednesday", "星期三").replace("Thursday", "星期四").replace("Friday", "星期五").replace("Saturday", "星期六").replace("Sunday", "星期日"))
        self.holiday_label.setText(detail["display_label"] if detail.get("holiday_name") else "无节假日标记")
        self.status_label.setText(f"状态：{detail['label']}" + (" · 手动" if detail["is_manual"] else " · 自动"))
        source_names = {"official": "官方离线数据", "user": "用户数据", "manual": "手动覆盖", "weekday_fallback": "默认规则（周一至五）", "work_cycle": "大小周规则"}
        source_text = f"来源：{source_names.get(detail['source'], detail['source'])}" + (f"（{detail['official_year']}）" if detail.get("official_year") else "")
        if detail["source"] in {"official", "user"} and detail.get("holiday_name") and detail.get("paper_url"):
            # §29: never surface raw paper URLs in the UI — name the source.
            source_text += " · 国务院办公厅放假安排"
        self.source_label.setText(source_text)
        is_today = day == self.service._now().date()
        self.record_out_button.setText("下班打卡" if is_today else "补卡下班")
        self.record_out_button._idle_text = self.record_out_button.text()   # 反馈复位基准跟随文案
        if self._clock_selection is not None:
            self.clock_label.setText(f"将记录 {self._clock_selection:%H:%M}")
        elif record and record.actual_clock_out:
            self.clock_label.setText(f"{record.actual_clock_out:%H:%M}（点打卡可改）")
        else:
            self.clock_label.setText("未记录")
        self.note_edit.setText(record.note if record else "")
        idx = self.status.findData("auto" if not detail["is_manual"] else detail["status"]); self.status.setCurrentIndex(max(0, idx))
        if not record:
            self.record_metrics_label.setText("加班：—　餐补：—　备注：—")
            text = f"{day.month}月{day.day}日 · 状态：{detail['display_label']}\n尚无下班记录"
        else:
            out = record.actual_clock_out.strftime("%H:%M") if record.actual_clock_out else "未记录"
            self.record_metrics_label.setText(f"下班：{out}　加班：{record.overtime_minutes//60}h{record.overtime_minutes%60:02d}m\n餐补：{self._amount(record.meal_allowance)}　备注：{record.note or '—'}")
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
        value = self.status.currentData(); self.service.restore_day_status_auto(self._selected_day) if value == "auto" else self.service.set_day_status(self._selected_day, value); self._refresh(); self._show_action_feedback(self.apply_status_button, "已应用 ✓")
    def _save_clock_out(self):
        """下班打卡：今天未选时间 → 打当前电脑时间；选了时间 → 记所选。"""
        day = self._selected_day
        if self._clock_selection is not None:
            t = self._clock_selection
        elif day == self.service._now().date():
            t = self.service._now().time()
        else:
            self._show_action_feedback(self.record_out_button, "先点选时间")
            return
        self.service.edit_clock_out(day, datetime(day.year, day.month, day.day, t.hour, t.minute))
        self._clock_selection = None
        self._refresh(); self._show_action_feedback(self.record_out_button, "已记录 ✓")

    def _pick_clock_time(self):
        """在详情面板内展开 时/分 下拉（无独立窗口）。打开时默认选中合理时刻。"""
        if not self.picker_host.isVisible():
            day = self._selected_day
            record = self.service.record_for(day)
            base = (record.actual_clock_out if record and record.actual_clock_out
                    else (self.service._now() if day == self.service._now().date()
                          else datetime(day.year, day.month, day.day, 18, 0)))
            self.picker_hour.setCurrentIndex(base.hour)
            self.picker_minute.setCurrentIndex(base.minute)
        visible = self.picker_host.isVisible()
        self.picker_host.setVisible(not visible)
        self.pick_time_button.setText("收起" if not visible else "选时间…")

    def _picker_confirmed(self):
        """读取内嵌下拉并立即补卡。0:00 不是有效下班时间，拒绝。
        时间早于下班时间 → 警告后仍记录（工资按提前离开时刻冻结）。"""
        day = self._selected_day
        h = self.picker_hour.currentIndex()
        m = self.picker_minute.currentIndex()
        if h == 0 and m == 0:
            self._show_action_feedback(self.picker_ok, "请选有效时间")
            return
        chosen = self.service._now().time() if day == self.service._now().date() and (h, m) == (
            self.service._now().hour, self.service._now().minute) else None
        if h < self.service.settings.work_end.hour or (
                h == self.service.settings.work_end.hour and m < self.service.settings.work_end.minute):
            self._show_action_feedback(self.record_out_button, "⚠ 未到下班时间，已按提前下班记录")
        self.service.edit_clock_out(day, datetime(day.year, day.month, day.day, h, m))
        self._clock_selection = None
        self.picker_host.hide()
        self.pick_time_button.setText("选时间…")
        self._refresh(); self._show_action_feedback(self.record_out_button, "已记录 ✓")

    def _picker_cancel(self):
        self.picker_host.hide()
        self.pick_time_button.setText("选时间…")

    def _save_note(self):
        day = self._selected_day; record = self.service.record_for(day) or WorkDayRecord(day, self.service.status_for(day)); record.note = self.note_edit.text().strip(); self.service.records[day.isoformat()] = record; self.service._save_records(); self._refresh(); self._show_action_feedback(self.note_button, "备注已保存 ✓")

    def _show_action_feedback(self, button, text):
        if not hasattr(button, "_idle_text"):
            button._idle_text = button.text()
        button._feedback_token = getattr(button, "_feedback_token", 0) + 1
        token = button._feedback_token
        button.setText(text); button.setProperty("feedback", "success")
        button.style().unpolish(button); button.style().polish(button)
        timer = getattr(button, "_feedback_timer", None)
        if timer is None:
            timer = QTimer(button); timer.setSingleShot(True)
            timer.timeout.connect(lambda b=button: self._reset_action_feedback(b, getattr(b, "_feedback_token", 0)))
            button._feedback_timer = timer
        timer.start(1600)

    @staticmethod
    def _reset_action_feedback(button, token=None):
        if not hasattr(button, "_idle_text"):
            return
        if token is not None and token != getattr(button, "_feedback_token", 0):
            return
        timer = getattr(button, "_feedback_timer", None)
        if timer is not None:
            timer.stop()
        button._feedback_token = getattr(button, "_feedback_token", 0) + 1
        button.setText(button._idle_text); button.setProperty("feedback", "")
        button.style().unpolish(button); button.style().polish(button)
    def _cancel_note(self):
        record = self.service.record_for(self._selected_day); self.note_edit.setText(record.note if record else "")
    def _save_manual_count(self):
        year, month = self._displayed_month(); self.service.calendar.set_month_workday_override(year, month, self.month_override_spin.value() or None); self._refresh()

    def _restore_manual_count(self):
        year, month = self._displayed_month(); self.service.calendar.set_month_workday_override(year, month, None); self._refresh()

    def _toggle_rules(self):
        self._rules_expanded = not self._rules_expanded
        self.advanced_card.setVisible(self._rules_expanded)


def _layout_widget(layout):
    widget = QWidget(); widget.setLayout(layout); return widget

