# V5.3 Real Acceptance

日期：2026-09-24
基线：`6f62ca5af962f7485147cb6543e73072a4866471`
分支：`master`

自动化合同、隔离 Qt 控件渲染、真实 Windows 桌面验收分开记录。演示输入均位于仓库 `.tmp/v53-demo/`，未使用真实用户文件夹。

| 验收项 | 状态 | 证据 / 边界 |
|---|---|---|
| `pytest tests -q` 完整回归 | PASS | 正式 clean release build 内 412 passed / 263.96s |
| 失效 favorite 左键提示并进入定位修复 | PASS | `tests/smoke/test_favorite_folders_gui.py`；Qt 行为合同，不打开真实桌面 |
| QuickPanel 长名称、两列、前六项及查看全部 | PASS | 控件状态合同与 `quick-panel-favorites.png`；截图只证明隔离控件渲染 |
| 固定当前 Explorer 的确认、命名、重复路径、错误状态 | PASS | 注入 `ExplorerService.current_directory()` stub 的合同测试 |
| Pet 右键与托盘菜单共享 service、最多八项、失效项禁用 | PASS | `tests/smoke/test_favorite_folders_gui.py`；openUrl 目标参数由测试捕获 |
| Pocket 多项 Copy/Move、混合失败引用及 Recent 去重 | PASS | `tests/smoke/test_pocket_favorites_multi.py`，文件均在 pytest 隔离目录 |
| QuickPanel/Pocket 对管理变更实时刷新 | PASS | 重命名、排序、移除、新增行为合同 |
| 单次 refresh 对每个 favorite 最多检查一次 `exists` | PASS | QuickPanel 与管理窗探测次数合同 |
| 同一损坏 JSON 备份幂等、旧数据 >20 项保留、Windows 大小写路径及 D: 根目录契约 | PASS | `tests/unit/test_destinations.py`（Windows-only 的根盘/大小写场景按环境可用性执行） |
| 四张 Qt Windows 平台渲染图 | PASS | 由 `scripts/capture_v53_screenshots.py` 生成并静态检查；未显示顶层窗，非桌面截图 |
| 人工真实显示器视觉质量 | NOT TESTED | 静态图检查不等价于显示器、字体/DPI 与交互验收；详情见 `V53_UI_REVIEW.md` |
| QuickPanel 真正启动 Windows Explorer 打开目录 | NOT TESTED | `QDesktopServices.openUrl` 参数合同 PASS；本轮未触发真实 Explorer |
| 从当前 Explorer 真实读取并固定目录 | NOT TESTED | stub 合同 PASS；未操作真实 Explorer 窗口 |
| 真实 Windows DPI 100%/125%/150%、鼠标右键/菜单手感 | NOT TESTED | 未进行真实输入设备验收 |
| 断连网络盘/移动盘卡顿 | NOT TESTED | 未拔除或访问真实网络盘；同步探测的限制记录于 `KNOWN_ISSUES.md` |
| ActiveExplorerWatcher | PASS | 仍为 disabled；V5.3 只调用一次性 `ExplorerService.current_directory()` |
| Fresh V5.3 release 启动与身份检查 | PASS | 独立解压启动：running/responding、动画目录、用户素材目录、日志与 build identity 均 true；WebEngine 文件数 0 |

最终 release 源 Git SHA、ZIP SHA256、审计计数及实际测试耗时记录于 `V53_CHANGE_SUMMARY.md`。任何未通过真实桌面操作验证的项目继续标为 `NOT TESTED`。
