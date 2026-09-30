# V5.4 Change Summary

## 1. Baseline

Baseline HEAD: `3349d7137e5e31b894ab1dd31d656d4728cc1939`
Summary scope implementation HEAD: `3349d7137e5e31b894ab1dd31d656d4728cc1939`（当前实现仍在未提交工作区）
Branch: `master`
Date: `2026-09-24`
Environment: Windows x64 / Python 3.11 / PyQt5 5.15.11
GUI automation availability: isolated Qt Windows-platform rendering available; real desktop interaction not performed.

## 2. 本轮目标

按用户公司的大小周安排日历：国庆调休周之后，第一周大周、第二周小周、之后交替。
收口工作日历的导航与操作反馈，并解决 QuickPanel 三条收藏挤压分隔线、层级生硬、按钮缺少明显交互状态的问题。

## 3. 修改前问题

- V54-01：公司大小周周六被工作日历默认规则视为休息日；缺少可验证的循环起点与大小周标签。
- V54-02：日历操作反馈弱，用户难以确认是否已点击成功；月历与详情按钮状态辨识度不足。
- V54-03：QuickPanel 第三条常用文件夹可能挤住下方分隔线；三条以上内容密集，管理按钮像普通文字，亮蓝色主按钮过于突兀。
- V54-04：小工具标题“今日助手”缺少产品识别感；用户最终指定显示名为“小迪助手”。

## 4. 本轮实际修改

### V54-01 大小周日历
- 修改内容：2026-10-12 起，以该周为循环起点，大周周六上班、小周周六休息，逐周交替；手工状态及官方节假日/调休仍优先。
- 修改文件：`wage/calendar_service.py`、`wage/ui_calendar.py`、`docs/WAGE_RULES.md`、`docs/WAGE_CALENDAR_ARCHITECTURE.md`。
- 修改前：周一至周五兜底规则会把全部周六判为休息日。
- 修改后：2026-10-17 大周上班、10-24 小周休息、10-31 大周上班；官方 10-10 调休上班日保留，2026 年 10 月应出勤 20 天。
- 根因：日历未表达公司大小周循环。
- 实现：新增固定循环起始周和交替周型判定，保持已有日期优先级。

### V54-02 日历操作与反馈
- 修改内容：补充上月/下月/今天导航、大小周规则说明、日期 hover/选中状态和操作完成状态提示。
- 修改文件：`wage/ui_calendar.py`、`ui/modern/tokens.py`、`theme.py`。
- 修改前：按钮状态和记录完成情况不明显，标签背景造成条带感。
- 修改后：hover、pressed、focus、disabled 及成功状态更清楚；标签背景透明。
- 根因：控件依赖基础主题，缺少日历专用交互反馈。
- 实现：在按钮样式和操作回调中补状态样式与短暂完成提示。

### V54-03 QuickPanel 视觉与收藏排版
- 修改内容：标题改为“小迪助手”；建立徽记/副标题/工资信息卡片层级；主操作改为柔和深绿，管理按钮采用可辨识描边胶囊，加号和收藏项补 hover/pressed/focus；收藏区使用独立网格行和滚动容器。
- 修改文件：`quick_panel.py`、`tests/smoke/test_favorite_folders_gui.py`、`scripts/capture_v54_quick_panel.py`。
- 修改前：标题像直接粘贴的默认标题，亮蓝主按钮抢眼，管理入口视觉不明确，第三条收藏可能压住分隔线。
- 修改后：面板层级与控件状态一致，三条收藏占两行且与文件口袋分隔线分开。
- 根因：面板宽度/间距不足，控件复用通用标题和主按钮默认样式。
- 实现：只在 QuickPanel 内设置局部样式，固定 320px 宽，最高 520px 并可滚动。

## 5. 文件级变化

`git status --short`（本轮最终清单）：

```text
M docs/ARCHITECTURE.md
M docs/DEVELOPMENT_LOG.md
M docs/TEST_REPORT.md
M docs/WAGE_CALENDAR_ARCHITECTURE.md
M docs/WAGE_RULES.md
M quick_panel.py
M tests/smoke/test_favorite_folders_gui.py
M tests/smoke/test_v48_ui_contracts.py
M tests/unit/test_v47_calendar_contract.py
M theme.py
M ui/modern/tokens.py
M wage/calendar_service.py
M wage/ui_calendar.py
A docs/V54_CHANGE_SUMMARY.md
A docs/V54_REAL_ACCEPTANCE.md
A docs/screenshots/v54/目录说明.md
A docs/screenshots/v54/v54-calendar-success-feedback-polished.png
A docs/screenshots/v54/v54-calendar-success-feedback.png
A docs/screenshots/v54/v54-quick-panel-redesign-final.png
A docs/screenshots/v54/v54-quick-panel-redesign.png
A docs/screenshots/v54/v54-quick-panel-three-favorites.png
A docs/screenshots/v54/v54-work-calendar-october.png
A scripts/capture_v54_quick_panel.py
```

各测试、文档和截图文件随对应功能更新；`v54-quick-panel-redesign-final.png` 是标题“小迪助手”的最终隔离预览。此摘要本身列为新增文件。

## 6. 新增功能

- 2026-10-12 起大小周周六轮换判断与日历标记。
- 日历记录按钮的即时成功反馈。
- QuickPanel 三条以上常用文件夹的分行展示和局部视觉层级。

## 7. 修复 Bug

- 修复大小周周六均按休息日处理的问题。
- 修复 QuickPanel 收藏第三项挤压下方文件口袋分隔线的问题。
- 补足日历及面板按钮的 hover、pressed、focus 与完成反馈。

## 8. 删除/弃用

无。

## 9. 测试

| 命令 | 结果 | 耗时 | 状态 |
|---|---:|---:|---|
| `python -m pytest tests -q` | **414 passed** | **245.17s** | PASS |
| `python -m pytest tests/smoke/test_favorite_folders_gui.py tests/smoke/test_v3_assistant_ui.py tests/smoke/test_v48_ui_contracts.py -q` | **33 passed** | **3.15s** | PASS |
| `python scripts/capture_v54_quick_panel.py` | `v54-quick-panel-redesign-final.png`, 320×480 | 2s | PASS |
| `git diff --check` | no whitespace errors | — | PASS |

## 10. 真实验收

- 隔离 Qt Windows-platform renders: PASS（静态控件图已检查；渲染图 PASS 不等于用户对最终视觉的确认）。
- 大小周日期合同与测试: PASS。
- 用户桌面实机鼠标 hover/click、屏幕 DPI、真实 Explorer: NOT TESTED。
- 本轮未使用 computer-use 控制用户电脑。

## 11. Release

- Final repository HEAD: `3349d7137e5e31b894ab1dd31d656d4728cc1939`（本轮改动仍为未提交工作区内容）。
- Release built from Git HEAD: pending（本轮未构建 Release）。
- Artifact ZIP SHA256: pending（本轮未生成 ZIP）。
- Build time: 不适用。

## 12. Remaining Known Issues

- 最终外观已按反馈更新并提供预览图；真实屏幕尺寸/DPI下仍需用户实际查看。
- 用户自定义角色素材导入流程未在本轮实际操作。

## 13. 本轮未完成项

未提交、推送或构建 Release；未进行真实桌面鼠标、DPI、Explorer 验收。

## 14. Commit 列表

无。本轮改动尚未提交；基线 HEAD 为 `3349d7137e5e31b894ab1dd31d656d4728cc1939`。

## 15. 最终状态

PARTIAL（功能、文档、隔离预览和回归均完成；仍未提交/推送或做真实桌面验收）。
