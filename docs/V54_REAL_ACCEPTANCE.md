# V5.4 Real Acceptance

日期：2026-09-24  
基线 HEAD：`3349d7137e5e31b894ab1dd31d656d4728cc1939`  
分支：`master`

| 验收项 | 状态 | 证据 / 边界 |
|---|---|---|
| 全量回归 | PASS | `python -m pytest tests -q`：414 passed / 245.17s |
| QuickPanel、助手与日历定向 UI 合同 | PASS | 33 passed / 3.15s；覆盖 QuickPanel、工资助手与日历按钮反馈 |
| 大小周日历 | PASS | 10-17 大周上班、10-24 小周休息、10-31 大周上班；2026-10-10 官方调休上班优先 |
| 三条常用文件夹排版合同 | PASS | `tests/smoke/test_favorite_folders_gui.py`；两行网格、独立分隔线、管理按钮交互样式 |
| 最终 QuickPanel 隔离渲染 | PASS | `docs/screenshots/v54/v54-quick-panel-redesign-final.png`，320×480；合成数据，不是用户桌面截图 |
| 工作日历、成功状态隔离渲染 | PASS | V54 截图目录中 PNG 已生成并检查；不作为真实鼠标验收 |
| 真实显示器视觉质量、鼠标 hover/click、DPI | NOT TESTED | 静态 QWidget render 不等价于用户屏幕、实际输入或 DPI 验收 |
| 真实 Explorer 打开/固定目录 | NOT TESTED | 本轮未操作真实 Explorer |
| Release package / fresh extract startup | NOT TESTED | 本轮没有构建 Release |

本轮没有使用 computer-use 控制用户电脑。代码、文档和截图仍在未提交工作区；版本文档审计需在形成提交后按 Release 流程运行。

## 2026-09-28 配色复核

- 当前无运行中的 `pet-desktop` 进程，用户先前的饱和粉截图无法对应当前磁盘代码中的进程；未重启完整桌面宠物，以免读取或处理用户已完成的人物素材。
- 修复后樱花粉工资卡背景 `#FEF2F6`，显示后的 Qt 控件截图见 `docs/screenshots/v54/v54-skin-contrast-shown-widget-sakura-full.png`。主操作按钮保留深粉色，说明与禁用操作使用更深的文字。
- `python -m pytest tests/unit/test_v54_skin_contrast.py -q`：9 passed。覆盖五套预设、明暗与旧版浅字自定义皮肤、混色比例、文字/金额/按钮对比度与面板皮肤切换。
- `QScreen.grabWindow` 在当前会话返回纯黑窗口图，无法完成显示器合成画面验收；失败图移至 `.tmp/v54-skin-contrast-validation/`。显示后的控件抓图不验证真实屏幕 DPI、鼠标交互或完整桌面宠物流程。
