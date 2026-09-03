# 工资与工作日历架构（V4.7）

## 单一权威

`WorkCalendarService` 是工资日数的唯一正常来源：人工日期覆盖 → 用户 `data/holidays.json` → 随程序发布的 holiday-cn 离线数据 → 周一至周五兜底。`WageCalculator.salary_workday_count(day)` 只调用 `calendar.workday_count(day.year, day.month)`。

旧版 `manual_workday_count` 只迁移到 `legacy_manual_workday_count` 审计字段；正常设置界面不再提供全局 SpinBox。确需公司特殊口径时，在工作日历高级区写入 `workday_count_overrides` 的 `YYYY-MM` 项。

## 日期元数据

`status_detail_for(day)` 同时返回状态、中文展示、节假日名称、来源、官方年份、是否手动和国务院文件链接。`isOffDay=false` 显示为“国庆补班”等调休文案，而不是普通“国庆节”。没有官方年份时，界面显示橙色兜底提示。

## 界面与计算

工作日历是 42 格 `ModernMonthCalendar`，每格 `CalendarDayCell` 只读显示状态/记录点；右侧详情提供状态、下班时间和备注内联编辑。顶部 StatCard 与 `WageService.month_summary()` 同源，隐私模式只替换金额展示，不改变 Decimal 计算。
