# ModernDialog 行为契约

状态：PASS（代码与自动化契约） / NOT TESTED（真实 Windows 鼠标拖拽）

## 尺寸与标题栏

- `resizable=False` 时只保留拖动标题栏；`resizable=True` 时启用 7px 边缘和四角 hit-test。
- 左/右边使用水平光标，上/下边使用垂直光标，角落使用对角光标。
- 实际 geometry 始终尊重 `minimumSize`，并按当前屏幕 `availableGeometry` 限制最大尺寸。
- 可调整窗口显示最大化/还原按钮；标题栏双击也会切换状态。最大化后再次拖动标题栏会恢复普通窗口再移动。

## 页面配置

| 页面 | resizable | 最大化/还原 |
|---|---:|---:|
| 工作日历 | PASS | PASS |
| 角色管理 | PASS | PASS |
| 设置 | PASS | PASS |
| 工资与工作时间 | PASS | PASS |

真实 Windows 的拖右边、下边、右下角和 DPI 100%/125%/150% 检查：NOT TESTED（本轮不使用电脑控制）。
