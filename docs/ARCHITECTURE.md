# ARCHITECTURE.md — pet-desktop 二次开发架构分析

> Phase 0 审计输出。
> Baseline commit：`5f0afa57f4a7f19b8460f5e97f4c575375dea38b`（master，唯一 commit，工作区干净）。
> 上游仓库：`claramiadevira/pet-desktop`（Clippy Desktop Pet，MIT）。
> 审计时间：2026-08-12。

---

## 1. 原项目目录结构

```
D:\pet-desktop\                     (克隆自上游，全部 < 100KB，无二进制素材)
├── main.py                   15 行   入口，导入 pet_window_web.main
├── pet_window_web.py        766 行   ★ 当前主窗口（WebEngine 渲染版）
├── pet_window.py            703 行   legacy 主窗口（原生 PyQt5+PIL 渲染版，main.py 未引用）
├── pet_sprite.py            170 行   原生版 sprite 加载器（PIL 裁帧，仅 4 个动画）
├── config.py                 89 行   JSON 配置（Path.home()/desktop-pet/config.json）
├── calendar_service.py      165 行   Google Calendar OAuth（待删）
├── reminder_service.py       98 行   喝水+会议提醒（5 秒 tick 轮询）
├── sounds.py                101 行   winsound Beep 音效（无外部音频文件）
├── assets/
│   └── clippy.html          24 KB    Canvas 渲染器，JS 内嵌 43 组动画帧表
├── launch_mochi.bat           8 行   启动脚本（硬编码 C:\Users\clara）
├── Mochi.vbs                  5 行   静默启动（硬编码 C:\Users\clara）
├── add_to_startup.bat         8 行   开机自启（硬编码 C:\Users\clara）
├── README.md                113 行
└── .gitignore                         关键：忽略了 sprite/动画/测试/配置
```

**注意：仓库不含任何 sprite 图片、animations.json、音效文件**（全被 .gitignore 排除，README 明确说要用户自备）。

---

## 2. 程序入口

- `main.py` → `from pet_window_web import main` → 创建 `QApplication` + `PetWindow(config)` + `app.exec_()`。
- 启动前设置 `Qt.AA_ShareOpenGLContexts`（WebEngine 必需）。
- `app.setQuitOnLastWindowClosed(False)`（靠托盘驻留）。
- `pet_window.py` 有独立 `main()`（原生渲染版），但 **当前无任何代码引用它**——属于 legacy 保留代码。

---

## 3. GUI 架构（pet_window_web.py）

| 组件 | 实现 | 可复用性 |
|---|---|---|
| 窗口骨架 | `QWidget` + `FramelessWindowHint \| WindowStaysOnTopHint \| Tool` + `WA_TranslucentBackground` + `WA_ShowWithoutActivating` | ✅ 直接复用 |
| 拖动 | `mousePressEvent` 记 `globalPos - topLeft` 偏移，`mouseMoveEvent` 跟随，`mouseReleaseEvent` 存 `pet_x/pet_y` 到 config | ✅ 直接复用 |
| 滚轮缩放 | `wheelEvent`，scale ∈ [1,6] 步进 0.5，`setFixedSize` + webview geometry + JS `setScale()` | ⚠️ 复用（注意 KI-11：setGeometry 传 float 必现 TypeError，接管时修复） |
| 右键菜单 | `QMenu.exec_()` 同步分发 | ✅ 复用（菜单项重构） |
| 托盘 | `QSystemTrayIcon` + 代码绘制图标 + 菜单 | ✅ 复用（菜单项重构） |
| 气泡 | 独立 top-level `QLabel` 窗口，QPainter 手绘 Win95 边框，20ms QTimer 打字机效果 | ✅ 直接复用 |
| 设置 | `SettingsDialog` Win95 stylesheet（Water/Calendar 组） | ✅ Phase 3 已移除 OpenAI 组 |

定时器（`_setup_timers`）：
- `_remind_timer` 5000ms → `reminder.tick(5)`（轮询）
- `_idle_timer` 60000ms → 30 秒无活动进睡眠（Web 版阈值 30s）
- `_idle_variety_timer` 8~15s 随机 → 换 idle 动画变体

---

## 4. 动画架构（双轨制）

### 4.1 WebEngine 轨（当前主轨）

- `assets/clippy.html`：单 `<canvas>`，JS 内嵌 `ANIMS` 对象——**43 组 Clippy 动画**，格式 `{ "AnimName": [[x, y, duration_ms], ...] }`，帧尺寸 124×93。
- `requestAnimationFrame` 循环按帧 duration 切帧；Python 侧通过 `page().runJavaScript("setAnimation('xxx')")` / `setScale(n)` 控制。
- Python 侧动画分组映射（`pet_window_web.py` L521-533）：
  `ANIM_IDLE`(7) / `ANIM_TALKING`(4) / `ANIM_ALERT`(2) / `ANIM_SLEEP`(1: IdleSnooze) / `ANIM_THINKING` / `ANIM_SEARCHING` / `ANIM_WAVE` / `ANIM_LOOK*` / `ANIM_WRITING`(Writing/Print/Save) / `ANIM_HIDE` / `ANIM_CONGRATULATE`。
- 43 个动画全名单：Alert, CheckingSomething, Congratulate, **EmptyTrash**, Explain, GestureDown/Left/Right/Up, GetArtsy, GetAttention, GetTechy, GetWizardy, GoodBye, Greeting, Hearing_1, Hide, Idle1_1, IdleAtom, IdleEyeBrowRaise, IdleFingerTap, IdleHeadScratch, IdleRopePile, IdleSideToSide, IdleSnooze, LookDown/Left/Right/Up(+4 斜向), **Print**, Processing, RestPose, **Save**, **Searching**, **SendMail**, Show, Thinking, Wave, **Writing**。
  （加粗的 EmptyTrash/Save/SendMail/Searching/Writing/Print/Gesture* 等可映射到我们的 DELETE/COPY/MOVE/RECEIVE/GIVE 等新状态——素材层面比任务书预期更充裕。）

### 4.2 原生轨（legacy，未启用）

- `pet_sprite.py`：PIL 打开 sheet → 逐像素去 magic pink (255,0,255) → 裁帧 → LANCZOS 缩放 → `_cache` 缓存。
- 硬编码 `ANIMATIONS` dict **只有 4 组**：idle / talking / alert / sleep（帧坐标与 Clippy 官方 sheet 一致）。
- `pet_window.py` 用 `QTimer.setSingleShot(True)` **逐帧链式调度**（每帧按自己 duration 排下一帧，clamp 16~2000ms）——天然变帧率、无固定 FPS，正是低资源需要的机制。

### 4.3 关键缺口

- **`assets/animations.json` 不存在**（被 .gitignore 排除）。README 定义其格式为 `{ "AnimationName": [[x, y, duration_ms], ...] }`——与 clippy.html 内嵌 ANIMS **完全同构**。
- **结论：Phase 2 将 clippy.html 内嵌 ANIMS 原样导出为 `assets/animations.json`**，供原生渲染器加载。这不是新造格式，是补上 README 承诺的文件。

---

## 5. 配置系统（config.py）

- `Config` 类：`dict(DEFAULT_CONFIG)` + JSON 文件合并；`set()` 每次立即落盘。
- **路径：`CONFIG_DIR = Path.home() / "desktop-pet"` → C 盘用户目录，必须迁移到 D 盘**（Phase 2 用 PathManager 统一）。
- `DEFAULT_CONFIG` 现有键：`pet_scale/pet_x/pet_y`、`water_interval_min/water_enabled`、`calendar_*`、`pet_name`。Phase 3 已移除 OpenAI 与 personality 键，并把旧 `ai_name` 迁移为 `pet_name`；旧配置加载时会清除并重写遗留键，避免本地 API key 残留。
- 附带 `OAUTH_FILE/CREDENTIALS_FILE` 常量（随 Calendar 删除）。

---

## 6. 原有提醒机制（reminder_service.py）

- 无独立线程：主窗口每 5s 调 `tick(5)`，内部累加秒数：
  - 喝水：累加到 `water_interval_min*60` → 触发 `on_water_reminder(msg)` 回调（5 条随机印尼语文案）。
  - 日历：累加到 15min → `calendar.check_events_to_remind()`。
- 触发后 PetWindow：`set_state(ALERT)` + 音效 + 气泡 + 3s 后回 IDLE。
- **无持久化、无用户自定义提醒、无 snooze/complete、无到期时间计算**。
- 可复用部分：回调式接口（`on_xxx`）、config 开关模式。轮询式 tick 整个替换为"下一条到期时间定时器"（任务书 §37）。

---

## 7. AI Chat（Phase 3 已删除）

- `ai_engine.py` 与 `ChatDialog` 已删除，两个窗口实现均不再构造 AI 客户端。
- 托盘/右键聊天项已删除；双击角色改为本地挥手问候，托盘双击改为显示角色并挥手。
- Settings 不再出现 API Key/Model，欢迎语不再引导配置 API key。
- 当前 `requirements.txt` 不含 `openai`；`requirements-baseline.txt` 保留 Phase 1 历史环境事实。

---

## 8. Google Calendar 实现（待删）

- `calendar_service.py`：`google-auth-oauthlib` InstalledAppFlow 本地服务器授权（`run_local_server(port=0, open_browser=True)`），token 存 `CONFIG_DIR/credentials/token.json`。
- `get_upcoming_events` 拉未来 12h 事件；`check_events_to_remind` 按分钟差过滤。
- 入口：`_init_calendar()`（启动时按 config 授权）、托盘"📅 Cek Jadwal"、右键"Jadwal Hari Ini"、SettingsDialog Calendar 组、`reminder._check_calendar`。

---

## 9. PyQtWebEngine 用途排查（任务书 §9 要求的引用全库搜索结论）

全库搜索 `WebEngine` / `QWebEngineView` 结果：

| 位置 | 用途 |
|---|---|
| `pet_window_web.py` L21 import，L294 `QWebEngineView` | **唯一用途：加载 clippy.html 渲染角色 canvas** |
| `main.py` L11 `AA_ShareOpenGLContexts` | 仅为 WebEngine 服务 |

SettingsDialog、气泡、托盘均为原生 Qt 控件。**结论：WebEngine 唯一用途仍是角色渲染**。原项目自带完整的原生渲染轨（pet_window.py + pet_sprite.py），因此原生轨接管后 PyQtWebEngine 可整体移除——这正是"低资源"目标的关键（省去常驻 Chromium）。

---

## 10. 可复用模块

1. **PetWindow 窗口骨架**：窗口 flags、拖动、滚轮缩放、托盘、右键菜单框架、enterEvent 唤醒。
2. **气泡子系统**：独立窗口 + 打字机 + 自动消失，完整复用。
3. **原生渲染轨**：`pet_window.py` 逐帧链式 QTimer（变帧率）+ `pet_sprite.py` 裁帧/缓存。
4. **clippy.html 的 43 组动画数据** → 导出为 `animations.json`。
5. **sounds.py**：纯 winsound.Beep，零依赖零音频文件。
6. **Config JSON 机制**（路径换掉、键清理）。
7. **ReminderService 回调模式**（重写为通用 Reminder 时保留 on_fire 回调形态）。
8. Win95 stylesheet（SettingsDialog 的样式常量，Pocket/Reminder UI 可沿用风格）。

---

## 11. 应删除模块

| 对象 | 处置 |
|---|---|
| `ai_engine.py` | ✅ Phase 3 已整文件删除 |
| `calendar_service.py` | 整文件删除 |
| `pet_window_web.py` | 气泡/菜单/拖动等逻辑移植到原生窗口后删除 |
| `assets/clippy.html` | 导出 ANIMS 为 animations.json 后删除 |
| `ChatDialog`、SettingsDialog 的 OpenAI 组 | ✅ Phase 3 已删除；Calendar 组留待 Phase 4 |
| config 中 openai_*/ai_personality | ✅ Phase 3 已删除并迁移旧配置；calendar_* 留待 Phase 4 |
| `launch_mochi.bat` / `Mochi.vbs` / `add_to_startup.bat` | 删除（硬编码 C:\Users\clara，后续如需再重做） |
| 依赖：openai | ✅ Phase 3 已从当前运行清单删除；Google/WebEngine 依赖按后续阶段删除 |

---

## 12. 应新增模块

| 模块 | 职责 |
|---|---|
| `paths.py` (PathManager) | PROJECT_ROOT/DATA_DIR/CONFIG_DIR/LOG_DIR/TEMP_DIR 统一常量，默认 D:\pet-desktop |
| `logsetup.py` | logs/app.log RotatingFileHandler；禁止逐帧日志 |
| `reminder_service.py` v2 | Reminder 数据模型（content/due/repeat/snooze）、JSON 持久化、next-due 单次定时器、唤醒补检查 |
| `reminder_ui.py` | 添加提醒对话框、我的提醒列表、到期气泡（完成/稍后提醒） |
| `pocket_service.py` | 引用型条目 {id,path,name,item_type,added_at}、exists 检查、JSON 持久化、去重、清理失效 |
| `pocket_ui.py` | 口袋浮动窗口：列表、打开/定位/复制路径、右键菜单、拖出（QMimeData file URLs） |
| `file_ops.py` (FileOperationService) | shutil 复制/移动 + 全套异常处理 + 同名冲突策略 + 部分失败报告 |
| `destinations.py` (DestinationService) | 常用位置（增删）+ 最近位置（去重/置顶/上限 10/清空） |
| `explorer.py` | COM IShellWindows 获取前台 Explorer 当前目录 |
| `events.py` (EventDispatcher + AnimationController) | WindowsEvent/PocketEvent/ReminderEvent/FileOperationEvent → 动画名 → fallback 链（specific→generic→idle）+ 缺失日志 |
| `file_watch.py` | ReadDirectoryChangesW 事件驱动监听（仅监听用户指定的口袋相关目录，不扫全盘） |
| 拖入支持 | PetWindow `dragEnterEvent/dropEvent` 接收 `text/uri-list` → RECEIVE_FILE 动画 + 入口袋 |
| 测试包 `tests/` | pytest，unit/integration/smoke 分层 |

---

## 13. 风险点

1. **sprite sheet 不在仓库**（.gitignore 排除，README 要求自备）。没有 `clippy_sheet.png` 程序只有透明空窗口。且 Clippy 是微软版权形象，README 声明不可再分发。→ 需要自备/生成一张 sheet；若自绘角色，animations.json 的帧坐标必须与新 sheet 布局一致（Phase 1 处理基线运行时解决）。
2. **clippy.html 的加载路径是 `CONFIG_DIR/assets/clippy.html`**（L30 `ASSETS_DIR = CONFIG_DIR / "assets"`），不是项目 assets/——即原版也要先把素材复制到 `~/desktop-pet/assets/` 才能显示。迁移时统一用 PathManager 的项目内 assets。
3. **GitHub 直连失败**（443 超时），本次经 `ghfast.top` 镜像克隆成功。后续 fetch/pull 都要走镜像。
4. **原生轨与待删模块耦合**：`pet_window.py` import 了 ai_engine/calendar_service，删除后需同步改造该文件（正好是我们要的主文件）。
5. **硬编码污染**：`pet_sprite.py` `__main__` 写死 `C:/Users/clara/Desktop/`；三个 bat/vbs 写死 `C:\Users\clara\...`。
6. **config 写 C 盘**（`Path.home()/desktop-pet`）。
7. 无 requirements.txt / pyproject.toml，依赖版本全部未钉死；README 只给了一句 pip install 清单。
8. `.gitignore` 忽略 `test_*.py`——上游故意不跟踪测试，我们的 tests/ 需要调整忽略规则。
9. `pet_sprite.py` 初始化逐像素扫描整张 sheet 去粉色，大 sheet 有一次性启动开销（可接受，但记录在案）。

---

## 14. 低资源优化点

1. **移除 WebEngine/Chromium**：原主轨常驻一个 Chromium 渲染进程（典型 150~300MB RAM）。切原生 QPixmap 渲染后只剩单 Python 进程。这是最大一笔节省。
2. **逐帧链式定时器**（原生轨已有）：每帧按 duration 排下一帧，无固定 FPS；idle 动画中静态帧 duration 可到 900~1200ms，接近"不动时不重绘"。
3. 进一步优化（Phase 16）：idle 循环播完一轮后停在静态帧，用低频 timer 偶尔触发小动作，替代持续逐帧链。
4. **提醒调度**：删 5s tick，改为"算出下一条到期时间 → 单个 singleShot timer"；系统唤醒后补扫一次。
5. **文件监听**：ReadDirectoryChangesW 事件驱动，无事件时零 CPU；绝不递归扫盘。
6. Phase 3 已移除 OpenAI SDK；Google SDK 留待 Phase 4，WebEngine 留待原生轨接管。
7. 帧缓存按 (state, idx, scale) 有界（当前 scale 档位数 × 帧数，MB 级）。

---

## 15. 初步开发顺序

按任务书 Phase 0→18 执行，结合本项目实际的决策点：

| Phase | 内容 | 本项目关键点 |
|---|---|---|
| 0 | 审计 | 本文档 |
| 1 | Baseline | venv 建 D 盘；装 PyQt5/Pillow；**先解决 sprite sheet 缺失**才能目视验证；记录原版 Idle CPU/RAM（含 Chromium 开销作对照） |
| 2 | 测试框架+日志+PathManager | 导出 animations.json；pytest 骨架；paths.py 全 D 盘 |
| 3 | 删 AI Chat | ✅ ai_engine.py、ChatDialog、openai 运行依赖、config 键、菜单项均已删除 |
| 4 | 删 Google Calendar | calendar_service.py、OAuth、菜单项、依赖 |
| 5 | 通用 Reminder | JSON 持久化 + next-due timer + snooze/complete；V1 单次，重复视成本 |
| 6 | Pocket 数据层 | 引用模型 + 持久化 + 失效检测 |
| 7 | 拖入角色 | PetWindow dropEvent + RECEIVE 动画 |
| 8 | Pocket UI | 列表窗 + 右键菜单 |
| 9 | 拖出到 Explorer | QMimeData urls 标准拖放 |
| 10 | 复制到/移动到 | file_ops + 冲突/异常全套 |
| 11 | 常用目的地 | favorites |
| 12 | 最近目的地 | recents 去重/上限 |
| 13 | 当前 Explorer 目录 | COM IShellWindows |
| 14 | Windows 文件事件 | ReadDirectoryChangesW |
| 15 | 事件→动画 | EventDispatcher/AnimationController + fallback |
| 16 | 资源优化 | 移除 PyQtWebEngine（此时原生轨已完全接管）、idle 停帧 |
| 17 | 完整回归 | 全量 pytest + 手工验收清单 |
| 18 | 打包 | PyInstaller，build/dist/release 全 D 盘，clean build |

> 说明：WebEngine 的移除放在原生渲染完全接管并回归通过之后，避免中间态没有可用渲染器。Phase 3 仅删除 AI Chat；Calendar 按 Phase 4 单独处理。

---

## 16. Phase 2 产出：测试框架 + 日志基础（2026-08-12 就位）

```
D:\pet-desktop\
├── pytest.ini               testpaths=tests；markers: unit/integration/gui/baseline/smoke；--strict-markers
├── tests/
│   ├── conftest.py          D 盘 temp 纪律：TEMP/TMP→.tmp/tests；isolated_config（monkeypatch CONFIG_DIR）；qapp 单例
│   ├── unit/                77 tests：Config / 动画元数据 / 动画选择 / Reminder / applog / paths / 测试环境自检
│   ├── integration/         3 tests：Reminder×Config 持久化联动；animations.json ↔ clippy.html 源一致性
│   └── smoke/               9 tests + 1 xfail：GUI 构造（真实平台）；KI-11 strict xfail
├── applog.py                stdlib logging + RotatingFileHandler（1MB×3 备份），日志写 paths.LOG_DIR
└── paths.py                 统一路径常量（PROJECT_ROOT / LOG_DIR / TEMP_DIR，无 C 盘硬编码）
```

**测试设计原则（Phase 3 起必须遵守）：**

1. Characterization first：先固定上游当前行为（包括已确认的 bug 与缺陷行为，如 Config 损坏静默回退、duration=0 帧），再改代码。
2. 测试 temp 一律走 `isolated_config` / `.tmp/tests/`，conftest 在 import 时就把 TEMP/TMP 指到 D 盘。
3. GUI 测试用**真实 windows 平台**——`QWebEngineView.page()` 在 offscreen 下必 segfault（KI-12，Chromium 需要真实 OpenGL context）。fixture 构造但不 show，teardown 隐藏托盘。
4. 阻塞式 `QMenu.exec_` / 对话框 `exec_` 用 monkeypatch 拦截，绝不在测试线程里真跑。
5. 已登记历史问题用 `xfail(strict=True)` 固定（当前仅 KI-11）：修复后会 XPASS 失败，强制同步更新标记与文档。禁止为凑绿删测试/放宽断言/滥用 skip。

**日志现状**：`main.py` 入口 wrapper 已接入 applog（startup / exit / uncaught exception 三类生命周期记录，异常原样 re-raise 保持退出码不变）。业务模块尚未逐点接入——Phase 3 删除/改造模块时顺带补 `logger = logging.getLogger(__name__)`。日志文件：`logs/app.log`（RotatingFileHandler，已 gitignore）。
