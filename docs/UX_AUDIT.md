# UX_AUDIT.md — V2 重构前用户体验审计

> 审计时间：2026-08-26 · 分支：ux-redesign-v2 · baseline HEAD：`72ea430`
> 证据：`docs/ui-before/`（8 张截图，程序化 widget.grab + 全屏实拍）
> 审计方式：真实运行当前版本 + 全量源码阅读 + 截图目检

---

## 0. 审计环境

- 源码版 `python main.py` 实际启动 ✓（进程驻留、托盘出现）
- 全屏截图确认角色渲染为**红色调试块**（synthetic sheet 首格带 "0,0"/"r0c0" 标签），底部永久显示 "Clippy"
- 测试基线：167 passed（重构前最后一次全量）

---

## 1. 逐项问题清单

| # | 区域 | 现状 | 问题 | 严重度 |
|---|------|------|------|--------|
| A1 | 角色本体 | 无用户素材时显示红色调试格 / "ADD ART" 占位 | 完全不像桌宠，像工程测试图 | 🔴 |
| A2 | 角色素材系统 | 要求用户自制 124×93、43 槽位 sprite sheet | 普通用户不可能完成 | 🔴 |
| A3 | 角色名称 | paintEvent 永久绘制 "Clippy" 于脚底 | Demo 感；与实际形象无关 | 🟡 |
| B1 | 右键菜单 | "➕ Add Reminder / ⏰ My Reminders / 📥 Pocket / ⚙️ Settings / ✖️ Keluar" | 英文+emoji；**Keluar 是印尼语**；无快捷面板入口 | 🔴 |
| B2 | 托盘菜单 | 与角色菜单重复 + "😴 / 🙋 Pet State" 子菜单 | 开发调试菜单暴露给用户；语言混杂 | 🔴 |
| B3 | 托盘图标 | 代码硬编码画橙色猫脸 | 与实际角色（任意 PNG）完全无关 | 🟡 |
| C1 | Pocket 布局 | 7+4+3+2 共 **16 个按钮**平铺四行 | 功能堆砌，主操作淹没 | 🔴 |
| C2 | Pocket 模态 | `_open_pocket()` 用 `exec_()` | 阻塞；无法与 Explorer 来回拖放 | 🔴 |
| C3 | Pocket 条目 | 两行裸路径 `📄 汇报.docx\nD:\work\report.docx` | 无系统图标、路径不 elide、窗口被撑大 | 🟡 |
| C4 | Pocket 多选 | 仅单项操作（`selected_item()` 取单个） | 批量复制/移动/移除不可用 | 🟡 |
| C5 | 成功反馈 | `QMessageBox.information("Copy complete...")` 模态弹窗 | 每次操作弹窗，极度烦人 | 🔴 |
| C6 | 空状态 | "Pocket is empty. Drag files or folders onto Clippy." | 英文；提 Clippy | 🟡 |
| D1 | 当前 Explorer 检测 | 点击按钮时 `GetForegroundWindow()` | **前台窗口是 Pocket 对话框自身**→ 永远匹配不到 Explorer 窗口 → 主功能几乎必然报 "Explorer unavailable" | 🔴 致命 |
| D2 | Explorer 失败反馈 | `QMessageBox.warning` 模态 | 应按钮置灰+行内提示，而非点击后弹错 | 🟡 |
| E1 | 新建提醒 | 裸 QFormLayout（Reminder/Date/Time + Save/Cancel） | 英文；无快捷时间；placeholder 提 Clippy | 🔴 |
| E2 | 提醒列表 | 裸 QListWidget + Delete 按钮 | 无分组（今天/明天）、无编辑、无稍后提醒（service 已支持 snooze 但 UI 未暴露） | 🟡 |
| F1 | Settings | 一个 QLabel + OK/Cancel，标题 "🐱 Mochi Settings" | **空壳**；Mochi/Clippy 名称不一致；无任何真实设置 | 🔴 |
| G1 | 气泡 | 30ms 逐字打字机 + 棕色描边 | 无意义持续重绘；视觉风格陈旧 | 🟡 |
| G2 | 气泡文案 | "Hai! 👋"、"😴 Zzz... aku tidur dulu ya~" | 印尼语 | 🔴 |
| H1 | 拖入反馈 | 仅 drop 后气泡文字 | dragEnter 无视觉变化，用户不知道可以拖 | 🔴 |
| H2 | 滚轮缩放 | wheelEvent 无条件改大小 | 极易误操作；无设置开关 | 🟡 |
| H3 | 单击/拖动 | mousePress 立即进入拖动；单击无任何动作；双击才 "Hai!" | 无快捷面板；单击语义缺失 | 🔴 |
| I1 | 首次启动 | 印尼语欢迎气泡 | 无引导，新用户不知道能干什么 | 🔴 |
| I2 | 语言一致性 | 英文 + 印尼语 + emoji + Clippy/Mochi 混用 | 全局混乱 | 🔴 |
| J1 | 文件事件 | 仅监听 Pocket 内显式目录 | 用户最初需求"Explorer 删除文件→动画"未覆盖全局 | 🟡 |
| J2 | 事件动画 | 直接映射 Clippy 动画名 | 无 debounce；连续删除 N 文件播 N 次 | 🟡 |
| K1 | 视觉风格 | Win95 棕色描边、默认灰按钮、无主题体系 | 各窗口各自 setStyleSheet（仅右键菜单有一段） | 🟡 |

## 2. 致命发现：D1 详述

`ExplorerService.current_directory()` 用 `GetForegroundWindow()` 取前台窗口再匹配 Shell Explorer 窗口。但用户点击 "Copy to Explorer" 按钮时，**前台窗口是 Pocket 对话框本身**（模态 `exec_` 更是锁定焦点），`Shell.Windows()` 里不可能有匹配 → 返回 None → 弹 "No active File Explorer folder was found"。

**结论：当前"复制/移动到当前文件夹"这一核心卖点在真实使用路径上基本不可用**（仅托盘菜单等罕见路径可能碰巧工作）。V2 必须：
1. Pocket 改非模态浮窗；
2. 检测改为"枚举所有 Explorer 窗口，取**最近的/非自身**的那个"，而不是匹配前台；
3. 打开 Pocket 时记录调用瞬间的 Explorer 目录作为快照兜底。

## 3. Before 截图清单（docs/ui-before/）

| 文件 | 内容 | 已确认问题 |
|---|---|---|
| desktop-full.png | 全屏实拍（角色在桌面上） | 红色调试块 + Clippy 标签 |
| pet.png | 角色 widget.grab | 调试格 "0,0"/"r0c0" |
| context-menu.png | 右键菜单 | 英文+emoji+印尼语 |
| pocket-empty.png | 空口袋 | 英文空状态 |
| pocket-with-files.png | 3 个文件的口袋 | 16 按钮平铺、裸路径、蓝头灰身 |
| add-reminder.png | 新建提醒 | 裸表单、英文 |
| reminder-list.png | 提醒列表 | 裸列表 |
| settings.png | 设置 | 空壳（仅 OK/Cancel） |

## 4. V2 目标映射（问题 → 任务书章节）

| V2 动作 | 解决的审计项 |
|---|---|
| 默认中性角色 + 单图片模式（§5-8） | A1 A2 A3 |
| 全中文 + theme.py（§9 29 30） | B1 I2 G2 K1 C6 E1 |
| 点击/拖动阈值 + 快捷面板（§10-12） | H3 |
| Pocket 非模态重构 + 多选 + 主操作（§13-18 22 23） | C1-C5 D2 |
| Explorer 检测修复（§15） | **D1** |
| Reminder/Settings 重做（§24-26） | E1 E2 F1 |
| 拖入高亮 + badge + toast（§19 20 22） | H1 C5 |
| 托盘统一 + app.ico（§32 33） | B2 B3 |
| Shell watcher + 前台过滤 + debounce（§36-38） | J1 J2 |
| 单图动画语义组（§7） | J2 配套 |

## 5. 复用清单（不动底层）

以下服务经代码审读确认**无需重写**，仅 UI 层重接：
- `PocketService`（引用寄存/持久化/missing 标记）✓
- `FileOperationService`（copy/move/rename 冲突策略）✓ —— 已天然支持 list 入参，多选可直接用
- `ReminderService`（持久化/snooze/next_due）✓ —— snooze 已有，UI 补入口即可
- `DestinationService`（favorites/recents）✓
- `FileWatchService` + `ReadDirectoryChangesW`（Pocket 目录监听）✓
- `EventDispatcher`/`AnimationController`（信号边界+映射）✓ —— 映射表需为单图模式扩展语义名
- `ExplorerService` —— 保留 PowerShell Shell.Application 方案，**改查询策略**（见 D1）
