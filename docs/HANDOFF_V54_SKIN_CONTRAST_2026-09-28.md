# pet-desktop 界面配色与可读性修复转接（2026-09-28）

## 任务与边界

- 项目：`D:/pet-desktop`，Git 分支 `master`，检查时 HEAD 为 `3349d71 docs: finalize V5.3 release records`。
- 用户当前目标：修复小迪助手/工资卡的粉色背景过饱和、文字看不清，以及次要文字对比度不足；完成运行中的真实界面验收。
- 用户明确要求：**人物形象已经改好，千万不要动角色、精灵图或角色处理脚本。** 不要运行 `scripts/align_custom_character_sheets.py`，也不要改 `data/characters/`、`character_v4/` 中的文件。
- 用户此前要求不要用 computer-use 操作其电脑。可用项目代码、命令行和无鼠标键盘占用的验证方式；不要使用 CUA。
- 用户最后取消了“先 commit”的安排。本次转接没有 commit、push，也没有改业务代码。继续工作时保护当前脏工作区，不要重置或覆盖用户修改。

## 现象与证据

- 用户截图：`D:/Temp/codex-clipboard-c6af9e35-f731-4c9c-99ce-db712ecb9f3d.png`。小迪助手的工资卡呈大块饱和粉色，浅色状态/说明文字难辨，禁用按钮也不清晰。
- 用户指出 `_tint` 的参数语义曾写反：`tint_light` 应为 12% 主题色 + 88% 白，却曾呈现为 88% 主题色 + 12% 白。
- **当前磁盘代码已经包含这一公式修正，但运行效果尚未验收。** `ui_skin.py:137-149` 中 `tint_light = _tint(accent, "#FFFFFF", 0.12)`，`_tint` 实现为 `accent * accent_ratio + base * (1 - accent_ratio)`。当前樱花粉计算结果：`section_bg=#feeaf2`、`tint_light=#fdeff4`、`text_soft=#c5688b`。截图中的深粉可能来自旧进程或另一处样式覆盖；这只是待核查假设，不能当作已证实结论。
- 当前预设 `sakura` 的 `muted=#C9A2B2`（`ui_skin.py:42`），在白色/浅粉底上偏浅；`quick_panel.py:22-26` 的说明文字分别使用 `muted` 和 `text_soft`。`text_soft=#c5688b` 也需要按实际背景测对比度。用户特别要求次要文字加深一级。

## 关键代码路径

- `ui_skin.py`：预设色、`palette()`、`_tint()`、`_legacy_bridge()`、`set_skin()`；目前为**未跟踪文件**，不可假定已进入 Git。
- `quick_panel.py`：`_panel_qss()` 定义工资卡、标题/次要文字/按钮颜色；`QuickPanel._apply_skin()` 响应皮肤切换。
- `theme.py` 和 `ui/modern/tokens.py`：全局 Qt 样式及新对话框样式，会受 `_legacy_bridge()` 更新。
- `pet_window.py:1504-1505`：启动时调用 `ui_skin.initialize()`；`pet_window.py:1274-1295`：皮肤菜单与切换。
- `tests/smoke/test_v54_skin_system.py`：当前有 5 个皮肤系统测试，但没有直接覆盖浅色混色比例和文字对比度；该文件也是未跟踪状态。

## 当前工作区状态

检查时 `git status --short --untracked-files=all` 显示多处未提交改动。与本任务最相关的是 `quick_panel.py`、`theme.py`、`ui/modern/tokens.py`、`pet_window.py`、`config.py` 的修改，以及未跟踪的 `ui_skin.py`、`ui_skin_dialog.py`、`tests/smoke/test_v54_skin_system.py`。此外，工资日历、常用文件夹、V5.4 文档/截图与 `scripts/align_custom_character_sheets.py` 也有未提交内容，均需保留。`data/` 被 `.gitignore` 忽略，角色图片不出现在常规 `git status` 中；尤其不要据此误以为可以重建或覆盖它们。

## 新对话应完成的工作

1. 先核对当前文件与运行进程是否一致。必要时按用户可见方式重启本项目桌面助手，验证截图现象是否仍复现；不要使用 computer-use。
2. 若仍过饱和，沿 `ui_skin.palette()` → `quick_panel._panel_qss()` → Qt 实际样式追查覆盖来源，修真正的生效路径。不要再次把已经正确的 `_tint` 公式反转。
3. 调深 `muted`、`text_soft` 或具体次要文字规则，使工资卡状态、明细、面板说明和禁用按钮在浅色皮肤上可读；保留用户所选皮肤的视觉方向。检查五套预设和自定义皮肤，至少覆盖樱花粉。
4. 做针对性的自动化校验（混色比例、文字对比度、皮肤切换）和真实界面验收，向用户报告实际结果。截图应放在 `docs/screenshots/` 的明确目录中并附目录说明，避免堆在项目根目录。
5. 全程不触碰人物形象。新对话可以完成 UI 代码和测试，但不要自行 commit/push；用户最后的要求是先转接。

## 可直接用于新对话的任务说明

在当前本地项目 `D:/pet-desktop` 的现有脏工作区上继续。先读 `docs/HANDOFF_V54_SKIN_CONTRAST_2026-09-28.md`，修复小迪助手工资卡饱和粉色和浅色文字看不清的问题，并做真实界面验收。当前 `ui_skin.py` 的 `_tint` 公式在磁盘上已是 `accent * ratio + base * (1-ratio)`，但截图仍显示深粉，需检查运行进程或样式覆盖；同时把次要文字调深并验证对比度。人物形象、`data/characters/`、`character_v4/`、`scripts/align_custom_character_sheets.py` 绝对不要动。不要用 computer-use，不要重置现有改动，不要 commit/push。模型使用 GPT-6 Sol，高推理强度。
