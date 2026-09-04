# V4.8 Real Windows Acceptance

状态只使用：PASS / FAIL / NOT TESTED / BLOCKED。

本轮代码、离屏构造、数据契约和 fresh release 已完成；由于用户明确要求不使用 Computer Use/电脑控制，以下项目诚实记为 NOT TESTED，不以离屏截图冒充真机结果。

| 项目 | 状态 | 证据/备注 |
|---|---|---|
| Settings fresh EXE 截图 | NOT TESTED | 需真实 Windows 窗口 |
| Wage Settings fresh EXE 截图 | NOT TESTED | 需真实 Windows 窗口 |
| 2026 年 9 月日历截图 | NOT TESTED | 代码契约为 22 天 |
| 2026 年 10 月日历截图 | NOT TESTED | 代码契约为 18 天 |
| 角色库截图 | NOT TESTED | 动态预览链已自动化 |
| Settings/Gallery/Desktop 一致性截图 | NOT TESTED | 需真实渲染对比 |
| DPI 100% | NOT TESTED | 无电脑控制 |
| DPI 125% | NOT TESTED | 无电脑控制 |
| DPI 150% | NOT TESTED | 无电脑控制 |
| 右边/下边/右下角 resize | NOT TESTED | hit-test 有自动化契约 |
| Explorer RMDIR | NOT TESTED | 保留 ShellWatcher 回归套件 |

建议用户手动运行 fresh EXE 后，将截图放入 `D:\pet-desktop\.tmp\v48-acceptance\screenshots\`：
`v48-settings.png`、`v48-wage-settings.png`、`v48-calendar-september.png`、`v48-calendar-october.png`、`v48-character-gallery.png`、`v48-character-consistency.png`。
