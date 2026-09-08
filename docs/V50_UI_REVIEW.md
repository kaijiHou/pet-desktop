# V5.0 UI Review（真实截图逐张审查）

截图由 `scripts/capture_v50_ui.py` 在真实 Windows Qt 平台生成（隔离数据目录，测试月薪 11200），
sanity 校验 6/6 PASS。r1 = 修复前，r2 = 修复后（保留最终版本）。

## Settings（v50-settings.png / r2）

状态：rendered screenshot PASS；human review PASS
证据：`.tmp/v50-acceptance/screenshots/r2/v50-settings.png`（470×815）

优点：
- 现代 Card 布局，非原生工具窗口；行为/提醒/数据均为 toggle 行，无 GroupBox 套娃。
- 角色区一眼可读：小幽灵 · 动态角色 · 内置；管理角色（主按钮）/ 导入单图 / 恢复默认层级清晰。
- 大小 slider 不贴边（100% 刻度可见）；按钮全中文；底部新增"版本 V5.0 · dev"（源码态无 build_info 属预期，EXE 显示真实短 SHA）。

问题：
- P1（r1 已修）：标题栏 □/× 几乎不可见（border:0 无色彩继承）→ 新增 `titleButton` 样式，r2 清晰可见。
- P2（遗留观察）：角色区"恢复默认"为 link 样式与两按钮并列，视觉层级略弱；本轮不动（§38：已可用，不为改而改）。

## Wage Settings（v50-wage-settings.png / r2）

状态：rendered screenshot PASS；human review PASS
证据：`r2/v50-wage-settings.png`（560×639）

优点：
- 月工资 11200.00 元/月；本月工作日 **22 天 + 自动徽章（绿）**，只读，无手工 spinbox。
- 规则说明与 9/20 补班、9/25-27 中秋摘要直接可见。
- 控件统一高度/圆角，focus 边框样式统一。

问题：
- P2（遗留观察）：收入提示 QComboBox 箭头仍偏原生；可用但不精致，本轮不动（§34 允许保留）。

## Calendar September（r2 v50-calendar-september.png，980×862）

状态：rendered screenshot PASS；human review PASS（r1 FAIL → 修复后 r2 PASS）

优点：
- 应出勤 **22 天**；9/20 国庆补班（蓝格）；9/25/26/27 中秋节·休息（红格）；文案无截断/重叠。
- 统计卡：已记录 0 天 / 累计加班 0h00m / 餐补 0 次 / 预计 ¥11200.00。
- 详情：9月20日 · 星期日 · 国庆补班 · 状态调休上班 · 自动；来源"官方离线数据（2026）· 国务院办公厅放假安排"——不再显示裸 URL（§29 修复）。

问题（r1 → 修复）：
- P0：r1 月网格把上一次渲染的月份行残留在上方（两层月份）。根因：refresh() 只 deleteLater，
  DeferredDelete 需要事件循环轮次，未删除前旧 cell 仍按旧 geometry 绘制。修复：takeAt 后立即
  hide() 再 deleteLater（`wage/ui_calendar.py` refresh）。真实运行时事件循环通常掩盖该问题，
  但任何批量刷新/慢机器都可能复现——已按产品缺陷修复。r2 单层网格，PASS。
- P1：r1 详情"来源"显示 gov.cn 裸链接且溢出截断 → 改为人话来源名（§29）。
- P2：r1 待机状态"取消"按钮常驻造成视觉噪音 → 仅编辑时出现（value/timeChanged 触发）。

## Calendar October（r2 v50-calendar-october.png）

状态：rendered screenshot PASS；human review PASS

- 切月后统计刷新：应出勤 **18 天**；10/1~7 国庆节·休息（红）；10/10 国庆补班（蓝，选中详情正确：星期六 · 调休上班 · 自动）。
- 无 9 月残留（叠影修复生效）。

## Character Gallery（r2 v50-character-gallery.png）

状态：rendered screenshot PASS；human review PASS

- 列表"小幽灵 · 内置"；预览卡内动态小幽灵（KeepAspectRatio，比例与桌面一致）；名称与描述展示。
- 按钮：使用（主）/ 导入动态角色包 / 导入单图 / 删除（danger）/ 取消 / 确定。

问题：
- P2（遗留观察）：列表区在单条目时大量留白；本轮不动。

## Character Consistency（v50-character-consistency.png）

状态：rendered screenshot PASS；程序化契约 PASS（same_id=True, aspect_match=True）

- 桌面帧（左）与 Settings 预览（右）同 pack（default_dynamic_ghost）、同宽高比；
  颜色/轮廓/眼/手一致；r1 截图中桌面为眨眼帧（动画帧不同，允许）。
- 注：这是辅助证据；真实桌面+Settings 同屏截图仍建议用户补充。

## 汇总

- 修复：P0 ×1（月格叠影）、P1 ×2（裸 URL、标题栏按钮对比度）、P2 ×1（待机取消按钮）。
- 遗留观察（本轮不动）：收入提示 combo 箭头原生感、Gallery 列表留白、恢复默认层级。
- 截图文件不入库（体积与隐私），路径/尺寸/大小已在本文档记录。
