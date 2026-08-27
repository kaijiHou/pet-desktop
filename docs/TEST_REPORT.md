# TEST_REPORT.md — 测试报告

> 原则：所有结论必须来自真实执行的命令。未执行的一律标 NOT RUN / NOT TESTED。
> 验收状态只允许：PASS / FAIL / NOT TESTED / BLOCKED。

---

## 原项目测试现状

**原项目没有自动化测试。**

- 仓库内无任何 test 文件、无 tests/ 目录、无 pytest/unittest 配置。
- 上游 `.gitignore` 显式忽略 `test_*.py`（测试不进版本库）。
- 无 CI 配置。

## Phase 1 Baseline 执行结果（2026-08-12）

### 启动

| 项目 | 状态 |
|---|---|
| 原项目启动（main.py → pet_window_web.PetWindow → QWebEngineView → clippy.html） | PASS（synthetic asset；page+sheet ready 4.68s，首次测量 run 2.93s） |
| 真实官方角色素材 | BLOCKED（upstream asset missing，KI-01/KI-10） |

详细逐项结果：`docs/baseline/baseline_smoke_test.md`（19 PASS / 1 FAIL / 2 NOT TESTED）。
唯一 FAIL = KI-11 上游 wheelEvent float bug（滚轮缩放必现 TypeError），Phase 1 按约束不修。

### 资源实测（原 WebEngine 主轨 + synthetic asset，psutil 统计完整进程树：python 主进程 + 2 个 QtWebEngineProcess/Chromium 子进程）

| 场景 | 样本数 | Avg CPU | Peak CPU | Avg RSS | Peak RSS | 进程数 |
|---|---|---|---|---|---|---|
| A. idle 1 min | 59 | 9.77% | 38.4% | 402.6 MB | 405.9 MB | 3 |
| B. idle 5 min（A+B 累计窗口） | 296 | 7.74% | 38.4% | 311.6 MB | 408.6 MB | 3 |
| C. 动画播放（8 组循环 30s） | 30 | 8.91% | 16.9% | 169.6 MB | 191.2 MB | 3 |
| D. Settings+Chat 对话框+提醒触发 | 22 | 15.42% | 67.6% | 136.3 MB | 150.3 MB | 3 |

原始采样：`docs/baseline/baseline_process_metrics.json`（358 样本）；汇总：`baseline_process_metrics.txt`。

**读数说明**（任务书 §16）：
- CPU% 为进程树求和，psutil 非阻塞采样，新进程首样本 warm-up 计 0（轻微低估）；10s 启动窗口已剔除。结论仅用于"修改前 vs 修改后"趋势比较。
- RSS 随时间下降（405→133 MB）是 Chromium 渲染进程在静置期释放/压缩内存的真实行为，非测量误差；各场景 Peak 才是该场景的真实上限。
- **素材为 synthetic**：CPU/RAM 反映原程序架构（尤其 Chromium/QWebEngine 固定开销 ~130-150 MB），不代表真实官方 sprite 的最终渲染性能。
- 场景 D 的 Peak CPU 67.6% 来自对话框首次构建+提醒触发的瞬时开销。

## 测试历史

（按 Phase 追加）

### Phase 1（2026-08-12）

- `scripts/smoke_baseline.py` — 原程序功能性 smoke（真实构建 PetWindow，驱动原事件处理器）：**19 PASS / 1 FAIL**
- `scripts/measure_baseline.py` — 进程树资源采样，四场景完成（见上表）
- 外部服务：AI API NOT TESTED（no key，UI 初始化+无 Key 错误路径已测）；Google OAuth NOT TESTED（no credentials，模块初始化已测）

### Phase 2（2026-08-12）— 正式 pytest 框架

**套件总结果：`pytest tests -v` → 89 passed, 1 xfailed, 6.25s**（pytest 9.1.1，venv 内执行，fresh 两次一致）

| 层 | 命令 | 结果 |
|---|---|---|
| unit | `pytest tests/unit -q` | 77 passed, 6.04s |
| integration | `pytest tests/integration -q` | 3 passed, 0.65s |
| smoke（含 GUI + KI-11） | `pytest tests/smoke -q` | 9 passed, 1 xfailed, 5.43s |
| **全套** | `pytest tests -v` | **89 passed, 1 xfailed, 6.25s** |

覆盖内容（全部 characterization，固定上游当前行为，不含任何新业务逻辑）：

| 测试文件 | 对象 | 要点 |
|---|---|---|
| unit/test_config.py | Config | 默认值、set/save 持久化、重读合并、缺失文件回退、**损坏文件静默回退**（当前真实行为，未修） |
| unit/test_animation_metadata.py | 动画元数据 | 基于 clippy.html 真实源提取：43 组 / 1227 帧 / 帧 `[x,y,duration]` / 全帧对齐 124×93 网格 / duration 非负（实测恰 1 帧为 0：IdleSideToSide[25]，如实刻画） |
| unit/test_animation_selection.py | 动画选择 | ANIM_* 12 组均非空字符串列表；`_random_anim` 恒返回组内元素；JS 端 `setAnimation` 对未知名为静默 no-op（源码断言） |
| unit/test_reminder_service.py | Reminder 现状 | tick 驱动、默认 30min、触发即重置、disabled 不触发、间隔下限 1min 钳制、日历提醒 15min 周期 + 同事件只通知一次 + 异常吞掉 |
| unit/test_applog.py | 日志基础 | 文件创建+写入、RotatingFileHandler 上限配置、setup 幂等不叠加 handler、不可写目录降级不抛 |
| unit/test_paths.py | paths 模块 | project root/log/temp 全部项目内，无 C 盘硬编码 |
| unit/test_test_environment.py | 测试环境自检 | TEMP/TMP 指向 D 盘 .tmp/tests、测试产物被 git 忽略、测试文件本身不被忽略 |
| integration/test_subsystem_wiring.py | Reminder×Config | 间隔修改跨 Config 重载存活；animations.json 与 clippy.html 源一致性 |
| smoke/test_gui_smoke.py | GUI 构造 | **真实 windows 平台**（offscreen 会 segfault，见 KI-12）：PetWindow/SettingsDialog/ChatDialog 构造不 show；右键菜单项（exec_ 被拦截）；无网络（Chat 不调 chat()，无凭据不 OAuth） |
| smoke/test_ki11_wheel_zoom.py | KI-11 | `xfail(strict=True)` 稳定复现 float→setGeometry TypeError；修复后会 XPASS 强制提醒 |

**原 Baseline Smoke 回归（Phase 2 结束时重跑）：`scripts/smoke_baseline.py` → 19 PASS / 1 FAIL，与 Phase 1 基线一字不差，唯一 FAIL 仍是 KI-11（TypeError 报错文本相同）。**

外部服务边界（沿用 Phase 1 原则）：AI API NOT TESTED（无 key，仅构造路径）；Google OAuth NOT TESTED（无凭据，`authenticate()` 返回 False 已测）。

日志接入实测：`main.py` 启动 8s → `logs/app.log` 出现 `startup: pet-desktop launching (python 3.11.15)`。

业务代码零改动确认：`git diff 5f0afa5 --stat -- <8 个业务 .py>` 为空；本阶段唯一被修改的业务侧文件是入口 wrapper `main.py`（+26/-1，纯日志，异常原样 re-raise）。

### Phase 3（2026-08-12）— 删除 AI Chat / OpenAI

范围严格限制为 AI Chat/OpenAI；Google Calendar、喝水提醒、WebEngine 主渲染轨与桌宠交互均保留。

| 层 | 命令 | 结果 |
|---|---|---|
| 针对性 | `pytest tests/unit/test_ai_removal.py tests/unit/test_config.py tests/smoke/test_gui_smoke.py -q` | **23 passed** |
| unit | `pytest tests/unit -q` | **81 passed** |
| integration | `pytest tests/integration -q` | **3 passed** |
| smoke | `pytest tests/smoke -q` | **9 passed, 1 xfailed**（KI-11） |
| 全套 | `pytest tests -q` | **93 passed, 1 xfailed** |
| GUI regression | `PYTHONUTF8=1 python scripts/smoke_baseline.py` | **19 PASS / 1 FAIL**；唯一 FAIL 仍为 KI-11 |

Phase 3 新增 `unit/test_ai_removal.py`，固定以下边界：`ai_engine.py` 不存在；生产窗口无 `AIEngine/ChatDialog/_open_chat/play_chat`；默认配置无 OpenAI/personality 键；加载旧配置会剔除并从磁盘清理相关键，同时把旧 `ai_name` 保值迁移为 `pet_name`；当前 `requirements.txt` 不含 OpenAI SDK。GUI smoke 同时确认 Settings 无 API 控件、右键菜单无聊天入口，而 Calendar/Reminder 服务仍正常持有。

原 Phase 1 baseline 证据保留在 `docs/baseline/`，不被后续运行覆盖；Phase 3 smoke 原始输出写 `docs/phase3_smoke_output.txt`。Google OAuth 仍为 NOT TESTED（无凭据），符合本阶段不改 Calendar 的边界。

### Phase 4（2026-08-12）— 删除 Google Calendar / OAuth

范围严格限制为 Calendar/OAuth 删除及其 Reminder 会议分支；喝水提醒、WebEngine 主渲染和桌宠交互保留。

| 层 | 命令 | 结果 |
|---|---|---|
| 针对性 | `pytest test_calendar_removal.py + config/reminder/gui -q` | **36 passed** |
| unit | `pytest tests/unit -q` | **81 passed** |
| integration | `pytest tests/integration -q` | **3 passed** |
| smoke | `pytest tests/smoke -q` | **9 passed, 1 xfailed**（KI-11） |
| 全套 | `pytest tests -q` | **93 passed, 1 xfailed** |
| GUI regression | `PYTHONUTF8=1 python scripts/smoke_baseline.py` | **20 PASS / 1 FAIL**；唯一 FAIL 为 KI-11 |

新增 `unit/test_calendar_removal.py`，验证服务文件、OAuth 路径常量、Calendar config/UI/窗口/Reminder 引用和当前运行依赖全部移除；旧配置键从磁盘清理。喝水 Reminder 原有触发、禁用、间隔更新和跨 Config 重载测试全部保留并通过。Phase 4 原始 smoke 输出见 `docs/phase4_smoke_output.txt`。

### Phase 5（2026-08-12）— 本地日期+时间提醒

| 层 | 命令 | 结果 |
|---|---|---|
| unit + integration | `pytest tests/unit tests/integration -q` | **89 passed** |
| smoke | `pytest tests/smoke -q` | **11 passed, 1 xfailed**（KI-11） |
| 全套 | `pytest tests -q` | **100 passed, 1 xfailed** |
| GUI regression | `python scripts/smoke_baseline.py` | **20 PASS / 1 FAIL**；唯一 FAIL 为 KI-11 |

新增 Reminder CRUD/持久化/损坏数据/排序/next-due/一次触发/重启防重/snooze 契约，以及旧 water 配置清理边界。GUI smoke 验证新增对话框构造、提醒列表删除、菜单入口；脚本实测到期项触发 ALERT、内容气泡和音效路径，且最近到期 singleShot timer 正常激活。原始输出见 `docs/phase5_smoke_output.txt`。

### Phase 6（2026-08-12）— Pocket 引用型数据层

| 层 | 命令 | 结果 |
|---|---|---|
| Pocket targeted | `pytest tests/unit/test_pocket_service.py -q` | **12 passed** |
| 全套 | `pytest tests -q` | **112 passed, 1 xfailed**（KI-11） |
| GUI regression | `python scripts/smoke_baseline.py` | **20 PASS / 1 FAIL**；唯一 FAIL 为 KI-11 |

新增 12 项测试覆盖空存储、文件/目录引用、源文件零改动、缺失路径拒绝、路径去重、移除、重启、损坏/坏条目、动态 exists、隐藏失效项和清理失效引用。Phase 6 未改 GUI，原有 Reminder 与桌宠回归完整保留。

### Phase 7（2026-08-12）— 拖入角色加入 Pocket

| 层 | 命令 | 结果 |
|---|---|---|
| GUI targeted | `pytest tests/smoke/test_gui_smoke.py -q` | **13 passed** |
| 全套 | `pytest tests -q` | **115 passed, 1 xfailed**（KI-11） |
| GUI regression | `python scripts/smoke_baseline.py` | **21 PASS / 1 FAIL**；唯一 FAIL 为 KI-11 |

新增拖入契约验证：两个窗口均启用 drop 且不引用复制/移动 API；真实主窗口接受本地 file URL、拒绝远程 URL；文件与目录批量加入 Pocket，源内容保持不变。原始 smoke 输出见 `docs/phase7_smoke_output.txt`。

### Phase 8（2026-08-12）— Pocket 列表窗口

| 层 | 命令 | 结果 |
|---|---|---|
| Pocket + GUI targeted | `pytest test_pocket_service.py test_gui_smoke.py -q` | **27 passed** |
| 全套 | `pytest tests -q` | **117 passed, 1 xfailed**（KI-11） |
| GUI regression | `python scripts/smoke_baseline.py` | **21 PASS / 1 FAIL**；唯一 FAIL 为 KI-11 |

GUI 测试覆盖列表显示、复制路径、移除引用不删原文件、missing 标识与清理、角色右键 Pocket 入口。外部打开/Explorer 定位不在自动化中触发；剪贴板使用 fake，避免污染用户会话。

### Phase 9（2026-08-12）— 从 Pocket 拖出

| 层 | 命令 | 结果 |
|---|---|---|
| 全套 | `pytest tests -q` | **120 passed, 1 xfailed**（KI-11） |

新增标准拖出测试：有效引用生成 `QMimeData.urls`，URL 为本地文件且往返路径一致；源文件保持存在；missing 引用返回 no mime；源码边界确认使用 QDrag + CopyAction 且无 shutil copy/move。真实 Windows shell 拖放端到端标记为 Phase 17 人工验收。

### Phase 10（2026-08-12）— 复制到 / 移动到

| 层 | 命令 | 结果 |
|---|---|---|
| File ops targeted | `pytest tests/unit/test_file_ops.py -q` | **10 passed** |
| 全套 | `pytest tests -q` | **132 passed, 1 xfailed**（KI-11） |

覆盖文件/目录复制、移动、默认自动编号不覆盖、skip、缺失源、非法目标、批量部分失败、非法策略与目录自包含保护。GUI 集成验证 Copy 保留 Pocket 原引用，Move 后引用更新到实际新路径。全部真实文件变更限定在 D 盘测试临时目录。

### Phase 11（2026-08-12）— 常用目的地

| 层 | 命令 | 结果 |
|---|---|---|
| Favorites targeted | `pytest tests/unit/test_destinations.py -q` | **7 passed** |
| 全套 | `pytest tests -q` | **140 passed, 1 xfailed**（KI-11） |

覆盖空状态、目录添加与重启、文件/缺失拒绝、去重、移除引用不删目录、missing 状态、损坏存储。GUI 集成验证收藏列表与快捷 Copy，并确认移除收藏后目录仍存在。

### Phase 12（2026-08-12）— 最近目的地

| 层 | 命令 | 结果 |
|---|---|---|
| Destination + GUI targeted | `pytest test_destinations.py test_gui_smoke.py -q` | **31 passed** |
| 全套 | `pytest tests -q` | **145 passed, 1 xfailed**（KI-11） |

覆盖新近顺序、重用置顶去重、10 条上限、清空不影响 favorites；GUI 验证成功操作自动记录并可清空，目标目录仍存在。

### Phase 13（2026-08-12）— 当前 Explorer 目录

| 层 | 命令 | 结果 |
|---|---|---|
| Explorer + GUI targeted | `pytest test_explorer.py test_gui_smoke.py -q` | **25 passed** |
| 全套 | `pytest tests -q` | **150 passed, 1 xfailed**（KI-11） |

测试用注入 runner 覆盖精确 foreground HWND 查询、无前台窗口不启动查询、无匹配/错误、输出路径不存在；GUI 用 fake Explorer 验证文件确实复制到返回目录。真实 Shell COM 前台切换留 Phase 17 人工验收。

### Phase 14（2026-08-12）— Windows 文件事件

| 层 | 命令 | 结果 |
|---|---|---|
| Watcher targeted | `pytest tests/unit/test_file_watch.py -q` | **3 passed** |
| 全套 | `pytest tests -q` | **153 passed, 1 xfailed**（KI-11） |

覆盖五种 Windows action 解析、只接受显式已存在目录、重复 watch 去重、事件 callback 与 stop；源码断言使用 ReadDirectoryChangesW 且无 sleep 轮询。GUI 验证拖入目录进入 watched set。真实 Windows 文件事件 burst 与 rename 配对留 Phase 17 人工验收。

### Phase 15（2026-08-12）— 事件到动画

| 层 | 命令 | 结果 |
|---|---|---|
| Events targeted | `pytest tests/unit/test_events.py -q` | **3 passed** |
| 全套 | `pytest tests -q` | **157 passed, 1 xfailed**（KI-11） |

覆盖具体映射、category fallback、idle fallback、无动画返回 None 与 dispatcher typed event；GUI 验证 Windows removed 解析为真实存在的 EmptyTrash 动画。Reminder/Pocket/FileOperation/Windows producer 均接入 dispatcher。

### Phase 16（2026-08-12）— 原生渲染与资源优化

| 层 | 命令 | 结果 |
|---|---|---|
| 全套 | `pytest tests -q` | **159 passed**（0 xfail） |
| Native GUI smoke | `python scripts/smoke_native.py` | **15 PASS / 0 FAIL** |
| Native metrics 30s | `python scripts/measure_native.py` | **avg CPU 1.25%, peak 3.0%, avg RSS 78.7MB, peak 79.5MB, 1 process** |
| WebEngine import probe | `find_spec('PyQt5.QtWebEngineWidgets')` | **None** |

新增 native placeholder/WebEngine removal 边界与事件动画回落测试；动画元数据测试改为跟踪 JSON 唯一源，GUI offscreen 全通过，KI-11 缩放测试从 strict xfail 转为普通 PASS。对比 Phase 1 WebEngine idle 3 进程、avg RSS 311.6–402.6MB、peak 408.6MB，原生轨内存下降约 75–80%。原始 smoke 和指标见 `docs/phase16_smoke_output.txt`、`docs/phase16_native_metrics.json`。

### Phase 17（2026-08-12）— 完整回归与真实 Windows 验收

| 层 | 命令/方式 | 结果 |
|---|---|---|
| Unit | `pytest tests/unit -q` | **136 passed** |
| Integration | `pytest tests/integration -q` | **2 passed** |
| GUI Smoke | `pytest tests/smoke -q` | **24 passed** |
| Full | `pytest tests -q` | **162 passed**（0 xfail） |
| 真实平台 acceptance | `python scripts/acceptance_phase17.py` | **9 PASS / 0 FAIL** |
| 稳定性 60s | `measure_native.py --duration 60` | **1 process; avg CPU 1.35%; peak 3.0%; avg RSS 82.0MB; peak 87.0MB** |
| 真实 Explorer COM | 指定前台 Explorer + `current_directory()` | **PASS**（存在目录，中文路径可用） |
| Pocket 跨窗口鼠标拖出 | `manual_drag_acceptance.py` + 用户真实鼠标拖放 | **PASS**（目标副本存在，源文件保留） |

真实 acceptance 覆盖原生可见绘制/截图、拖动、整数缩放、本地提醒、Pocket 引用、真实复制、真实移动、Win32 五类目录事件和无 WebEngine 运行时。验收数据均在 `D:\pet-desktop\.tmp\tests`。跨窗口鼠标拖出随后由用户真实操作闭环，结果 PASS；底层 QMimeData 本地 file URL、QDrag CopyAction 与源文件保持存在也由正式 smoke 覆盖。

人工闭环：运行 `.venv\Scripts\python.exe scripts\manual_drag_acceptance.py`，把 Pocket 中唯一文件拖到自动打开的 `drag-target` Explorer，然后关闭 Pocket。脚本检查目标副本存在且源文件仍存在，结果写到 `.tmp/tests/phase17_drag_result.json`。

2026-08-13 实际结果：`status=PASS`、`target_copy_exists=true`、`source_still_exists=true`。

### Phase 18（2026-08-12）— Windows 打包与发布

| 层 | 命令/方式 | 结果 |
|---|---|---|
| Packaging contract | `pytest tests/unit/test_packaging.py -q` | **4 passed** |
| Full pre-build | `pytest tests -q` | **166 passed** |
| Clean build | `scripts/build_release.ps1` | **PASS** |
| Direct EXE | `release/DesktopPet/DesktopPet.exe`，等待 5s | **PASS**（responsive，单进程，日志生成） |
| Extracted ZIP | `scripts/verify_release.ps1` | **PASS** |
| WebEngine scan | 解压包递归文件名 | **0 files** |
| Artifact | one-folder / ZIP | **109.5 MB / 45,788,195 bytes** |

ZIP SHA-256：`d9a00cd6f1095c25c618e19e724615a07dd8d52e5465bde89b8429b7ee119c06`。manifest 与实际 hash 一致。解压副本具备 `_internal/assets/animations.json`、EXE 同级用户 `assets/`、运行时 `logs/app.log`；没有依赖项目 `.venv`。

## V2（ux-redesign-v2，2026-08-27）— UI/UX 全量重构

**套件总结果：`pytest tests -q` → 191 passed, 0 failed**（V2 全量，新增 24 个测试）

| 层 | 命令/方式 | 结果 |
|---|---|---|
| Full suite | `pytest tests -q` | **191 passed** |
| Performance | `scripts/perf_measure.py <pid>`（60s idle） | avg CPU **0.0%**，peak CPU 0.0%，avg RSS **102.5 MB**，peak RSS 129.9 MB，单进程，**WebEngine=0** |

V2 新增/更新的测试：
- `tests/unit/test_character.py`（17）：单图模式、图片导入/校验/去重、无图 fallback、切换无需重启、动画语义完整性
- `tests/unit/test_events.py`：语义动画名映射、噪声事件不映射到特定动画
- `tests/unit/test_shell_watcher.py`（4）：dispatch/debounce/stop/动作映射
- `tests/unit/test_config.py`：V2 默认值（pet_name=小助手、新行为键）
- `tests/smoke/test_gui_smoke.py`：中文菜单/语义 dispatch/动画结束回 idle
- `tests/smoke/test_ki11_wheel_zoom.py`：V2 滚轮默认关闭/启用行为

**性能 Before/After**：

| 指标 | Before（Phase 1 WebEngine） | After（V2 原生单图） |
|---|---|---|
| 60s idle avg CPU | ~1.35% | **0.0%** |
| 60s idle avg RSS | ~311–402 MB（含 Chromium 子进程） | **102.5 MB** |
| 进程数 | 1 主 + 2 Chromium | **1（WebEngine=0）** |

> 说明：AVG RSS 略高于 100MB 目标，因单图渲染 + Qt 基座 + 快捷面板持留。峰值 129.9MB 出现在动画播放瞬间。CPU 指标大幅优于目标（≤2%）。无 WebEngine/Chromium。

## V2 Release（fresh build，2026-08-27）

- Build：`scripts/build_release.ps1`（clean，非复用旧 EXE）→ **PASS**
- EXE 启动：单进程、46 MB RSS、日志生成、WebEngine/Chromium 扫描 **0 files**
- ZIP：`release/DesktopPet-windows-x64.zip`，45,831,050 bytes
- SHA256：`449b04f88357bd38a80f8139e7031637bd65db965027a90a5d7ae805000b9979`
- manifest.json 与实际 hash 一致；解压副本不含项目 `.venv`

## V2.2 紧急交互修复（2026-08-27）

基线：`8648f96ce5bc506969fc850d49b9d0430b818bcc`。目标仓库：`kaijiHou/pet-desktop`，分支：`v2.2-interaction-fix`。

| 层 | 命令/方式 | 结果 |
|---|---|---|
| ShellWatcher targeted | `pytest tests/unit/test_shell_watcher.py -q` | **6 passed** |
| V2.2 interaction targeted | `pytest tests/smoke/test_v22_interactions.py -q` | **15 passed** |
| Full suite | `pytest tests -q --tb=short` | **222 passed** |
| 真实 Explorer drag-in | release EXE + 鼠标 | **NOT TESTED** |
| 真实 Explorer Delete | release EXE + 鼠标 | **NOT TESTED** |
| 真实 EXE 缩放/面板 | release EXE + 鼠标 | **NOT TESTED** |

ShellWatcher 定向集成测试使用真实 `SHChangeNotifyRegister`、非零注册 ID 和真实 `SHChangeNotify` 广播，验证 NewDelivery Lock 解包及 Qt signal；它不冒充普通 Explorer 鼠标删除验收。完整清单见 `docs/V22_REAL_ACCEPTANCE.md`。

### V2.2 fresh release

`scripts/build_release.ps1` 在文档提交后再次 clean 构建，随后 `scripts/verify_release.ps1` 从新 ZIP 副本启动：**PASS**（单进程、responsive、动画 catalog、user assets、日志均存在、WebEngine 文件 0）。ZIP 为 48,251,780 bytes，SHA-256 为 `e719a87009e6962e944e0073d594e8edab5570175e289565699a33ed75f2fd5b`，manifest 与文件一致。

## V3 当前回归（2026-08-27）

| 层 | 命令/方式 | 结果 |
|---|---|---|
| Wage/Calendar targeted | `.venv\\Scripts\\python.exe -m pytest tests/unit/test_wage_calculator.py tests/unit/test_character.py -q` | **26 passed** |
| V2.2 interaction regression | `.venv\\Scripts\\python.exe -m pytest tests/smoke/test_v22_interactions.py -q` | **15 passed** |
| GUI construction regression | `.venv\\Scripts\\python.exe -m pytest tests/smoke/test_gui_smoke.py -q` | **16 passed** |
| 真实 Windows 视觉/Explorer | 手动 acceptance | **NOT TESTED**（本轮遵循不使用电脑控制） |

V3 完整套件、fresh release 和手动清单在本阶段后续 commit 追加；在此之前不宣称 V3 完成。

打卡修改和月历明细补齐后复跑：完整套件 **230 passed in 8.27s**；`wage/ui_settings.py`、`wage/ui_today.py`、`wage/ui_calendar.py` 离屏构造通过。真实 Windows 视觉/Explorer 仍为 **NOT TESTED**。

## V3 fresh release

- `scripts/build_release.ps1`：clean build **PASS**，测试阶段 **230 passed**。
- `scripts/verify_release.ps1`：全新解压副本启动 **PASS**；单进程、响应、动画目录、可替换素材目录、日志均存在，WebEngine/Chromium 文件 **0**。
- ZIP：`release/DesktopPet-windows-x64.zip`，48,298,928 bytes。
- SHA256：`498697aca1c14fc4d0b54012b8e7da8592b0e354b97ed75ed08bb4d74c78adf8`，manifest 一致。
- Explorer/鼠标视觉/真实提醒：**NOT TESTED**（遵循本轮不使用电脑控制）。

最终 anchor follow-up 后再次 clean build：230 passed；verify release 全部黑盒检查通过。最终 ZIP 48,300,152 bytes，SHA256 `78a052e07ec9c0fef7ee66c227bec16bd582de1596628a05cc7c2ebfd8b9fd1c`，manifest 一致。真实 Explorer/鼠标视觉/提醒仍 **NOT TESTED**。
