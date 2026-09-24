# V5.2 真实验收记录

日期：2026-09-24
基线：`1f73669ec879f024e288f9463e688d8780b127f7`
分支：`master`

本轮有可用的 UI 自动化工具，但遵循用户“不使用 Computer Use、其正在操作电脑”的明确要求，没有控制真实桌面、鼠标或 Explorer。以下区分自动化调用契约与真实 Windows 桌面结果。

| 验收项 | 状态 | 证据 / 边界 |
|---|---|---|
| DestinationService v1 兼容、version 2 保存、重启持久化、排序与路径修复 | PASS | `tests/unit/test_destinations.py` |
| 管理窗口空状态、添加/改名/排序/失效显示/修复/安全移除 | PASS | `tests/smoke/test_favorite_folders_gui.py`；通过 Qt 控件行为合同验证，不作像素级结论 |
| QuickPanel 前 6 项、数量入口、空状态与目录打开调用参数 | PASS | `tests/smoke/test_favorite_folders_gui.py`；通过捕获 `QDesktopServices.openUrl` 的目标路径验证 |
| Pocket 使用共享服务、复制/移动到常用目录、Recent 记录与移动引用更新 | PASS | `tests/smoke/test_favorite_folders_gui.py`、`tests/smoke/test_pocket_window_gui.py`；所有操作均在 `.tmp/tests/` 隔离目录 |
| 完整 pytest 回归 | PASS | `pwsh -NoProfile -ExecutionPolicy Bypass -File scripts/build_release.ps1` 内执行 `.venv\Scripts\python.exe -B -m pytest tests -q`：390 passed / 270.36s |
| QuickPanel 实际弹出 Windows Explorer 并打开正确目录 | NOT TESTED | 自动化只验证传给 `QDesktopServices.openUrl` 的本地路径；没有启动或控制真实 Explorer |
| 真实 Windows 字体、布局和截图人工审查 | NOT TESTED | 本轮未捕获桌面截图；Qt 控件合同不等价于人工视觉验收 |
| 真实鼠标右键、拖动/排序手感、DPI 缩放 | NOT TESTED | 未进行鼠标或屏幕控制；排序使用上移/下移按钮 |
| 真实网络盘/移动盘断连与恢复 | NOT TESTED | 普通本地隔离目录覆盖失效/恢复语义；没有操作实际网络盘或移动盘 |
| ActiveExplorerWatcher 状态 | PASS | V5.2 未触碰该模块，PetWindow 继续保持 `self._explorer_watcher = None` |
| Fresh V5.2 Release 启动与黑盒验证 | PASS | `scripts/verify_release.ps1` 从新解压目录启动：running/responding、animation catalog、user assets、build identity log 均 true；WebEngine 文件 0；退出码 0 |

本轮没有生成“真实桌面截图”文件，也没有把自动截图或 Qt offscreen 构造冒充为人工视觉 PASS。

Release 证据：构建源 Git commit `172272b75bdadf02331805e310b0520e4e85022b`；`release/DesktopPet-windows-x64.zip` 为 46,827,176 bytes，SHA256 `76f269deded01038f4079fd08573b29d5294789013ed58fdaf421b45e7048f58`。Git SHA 与 ZIP SHA256 是不同标识，已分别记录于 `V52_CHANGE_SUMMARY.md`。
