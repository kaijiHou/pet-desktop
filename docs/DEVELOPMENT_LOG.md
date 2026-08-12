# DEVELOPMENT_LOG.md — pet-desktop 二开开发日志

> 边做边写。每个阶段完成后立即追加。格式见任务书 §2。

---

## 2026-08-12 (一) - Phase 0：项目与环境审计

### 目标

找到/获取项目、检测已有环境、通读全部代码、输出架构分析，不做业务代码修改。

### 开始状态

- Git commit：本地无仓库，需从上游克隆。
- 工作区状态：D:\pet-desktop 不存在（曾出现一次克隆超时残留的幽灵目录，已确认清空）。
- 当前测试状态：无。

### 实际操作

执行过的重要命令：

```text
git --version                                    → git version 2.41.0.windows.1
python --version / where.exe python              → PATH 中仅 Microsoft Store 空壳
uv --version                                     → uv 0.11.28
uv python list                                   → 可用 cpython-3.11.15 (D:\hermes-agent\python\)、3.10/3.9.7(anaconda)
df -h /d ; df -h /c                              → D 盘剩 107G；C 盘仅 1.2G（99% 占用）
git clone https://github.com/claramiadevira/pet-desktop  → 失败（443 超时）
git clone https://ghfast.top/https://github.com/claramiadevira/pet-desktop  → 成功
cd /d/pet-desktop && git status / git rev-parse HEAD / git log
```

修改文件：

* 无（Phase 0 禁止改业务代码）

新增文件：

* docs/ARCHITECTURE.md（架构审计，15 节）
* docs/DEVELOPMENT_LOG.md（本文件）
* docs/TEST_REPORT.md（初始状态：原项目无测试）
* docs/KNOWN_ISSUES.md（9 条已知问题）

删除文件：

* 无

### 修改原因

- 选 `D:\pet-desktop` 作为项目根（任务书建议位置之一，路径最短清晰）。
- 克隆走 ghfast.top 镜像：GitHub 直连在本机网络下 443 超时，镜像可用；此事实记入 KNOWN_ISSUES KI-05。
- Python 环境决策：不新装 Python（任务书 §0.6），复用 uv 已有的 cpython 3.11.15；虚拟环境 Phase 1 建到 D:\pet-desktop\.venv。

### 遇到的问题

1. GitHub 直连克隆超时（21s 后 Failed to connect）。
2. 首次镜像克隆超时重试期间出现"D:\pet-desktop already exists"但 bash/Python 均查不到该目录的幽灵状态。
3. PATH 无真实 Python / pip。

### 根因

1. 本机网络无法直连 github.com:443（国内常见）。
2. 第一次克隆进程在超时窗口内创建了目录又被清理竞争干扰；最终确认目录已不存在，重新克隆到 D:\pet-src 成功后同盘 mv 归位，规避路径锁。
3. 系统只装了 Microsoft Store python 存根；真实解释器由 uv/anaconda 管理，不在 PATH。

### 解决方案

1. 使用 `https://ghfast.top/<原地址>` 镜像克隆成功。
2. 先克隆到 D:\pet-src\pet-desktop，再 `mv` 到 D:\pet-desktop（同盘瞬时移动），随后验证 git 状态干净。
3. Phase 1 用 `uv venv --python 3.11.15` 在项目内建虚拟环境。

### 验证

```text
git status        → working tree clean, branch master up to date with origin/master
git rev-parse HEAD → 5f0afa57f4a7f19b8460f5e97f4c575375dea38b
git log --oneline  → 仅 1 个 commit（Initial commit: Clippy Desktop Pet）
```

代码通读结果：全部 9 个 .py（2334 行）+ README + 3 个启动脚本 + .gitignore + clippy.html 均已完整阅读，要点写入 ARCHITECTURE.md。

### 回归

无（Phase 0 未改代码）。

### 当前状态

- 仓库：D:\pet-desktop，master @ 5f0afa5，工作区干净（除本次新增 docs/）。
- 关键发现：
  1. 素材全缺（sheet/animations.json 被 .gitignore 排除）→ 基线运行必须先解决（KI-01）。
  2. 渲染双轨：WebEngine（主）+ 原生 PyQt5/PIL（legacy），43 组 Clippy 动画数据内嵌在 clippy.html，与 README 的 animations.json 格式同构，可导出复用。
  3. WebEngine 唯一用途是角色渲染（全库已搜索确认），原生轨接管后可删 → 低资源核心收益。
  4. 待删：ai_engine.py、calendar_service.py、ChatDialog、openai/google 依赖、C:\Users\clara 硬编码脚本。
  5. 可复用：窗口骨架/拖动/缩放/托盘/气泡/逐帧链式定时器/winsound 音效/Config 机制。
  6. 原项目无自动化测试。

### 下一步

Phase 1：建立基线。
1. `uv venv .venv --python 3.11.15`（D 盘），`pip install PyQt5 Pillow pytest`（PIP_CACHE_DIR 指 D 盘）。
2. 解决 sprite sheet 缺失（自备或程序化生成占位角色 sheet，坐标与 animations.json 对齐）。
3. 启动原项目（WebEngine 版）目视验证：显示/拖动/缩放/动画/右键/睡眠/提醒。
4. 记录 BASELINE_COMMIT、依赖版本、原版 Idle CPU/RAM。
5. 提交 baseline commit：`chore: establish project baseline`。

---

## 2026-08-12 (二) - Phase 1：建立可重复、可测量的原项目 Baseline

### 目标

在不修改原业务代码的前提下，建立可启动、可人工验收、可测 CPU/RAM、可重复复现的原项目基线。不提前实现后续功能。

### 开始状态

- Git：HEAD=7170124（Phase 0 docs commit），上游基线 5f0afa5，工作区干净。
- UPSTREAM_BASELINE_COMMIT=5f0afa5，PHASE0_DOC_COMMIT=7170124（已记入 docs/baseline/baseline_environment.txt）。
- 依赖：未安装；venv：不存在；素材：缺失（KI-01）。

### 实际操作

执行过的重要命令：

```text
# 会话级环境变量（每个新终端都先执行，未写系统永久变量）
export UV_CACHE_DIR=D:/pet-desktop/.cache/uv PIP_CACHE_DIR=D:/pet-desktop/.cache/pip
export TEMP=D:/pet-desktop/.tmp TMP=D:/pet-desktop/.tmp
uv venv .venv --python 3.11.15                    → D:\pet-desktop\.venv（已验证解释器路径在 D 盘）
uv pip install --python .venv/Scripts/python.exe PyQt5 PyQtWebEngine Pillow \
    openai google-api-python-client google-auth-oauthlib pytz pytest psutil
uv pip list --python .venv/Scripts/python.exe     → 真实版本记入 docs/baseline/baseline_environment.txt
.venv/Scripts/python.exe scripts/gen_synthetic_assets.py   → sheet 3348x3162 + animations.json（43组/1227帧，校验通过）
.venv/Scripts/python.exe scripts/smoke_baseline.py         → 19 PASS / 1 FAIL
.venv/Scripts/python.exe scripts/measure_baseline.py       → 四场景进程树采样 358 样本，约 6 分钟
```

修改文件：

* `.gitignore` — 追加 `.venv/ .cache/ .tmp/ logs/`（环境卫生，任务书 §25 允许；原文件已有 assets 素材排除，synthetic PNG 天然不进库）

新增文件：

* `scripts/gen_synthetic_assets.py` — synthetic sheet 生成 + clippy.html ANIMS 机械导出（不改坐标/duration/命名，导出后逐组校验帧数与抽验坐标）
* `scripts/smoke_baseline.py` — 原程序功能性 smoke（真实构建 PetWindow，走原事件处理器）
* `scripts/measure_baseline.py` — 进程树资源采样器（含 Chromium 子进程）
* `requirements-baseline.txt` — 实测可用版本清单（KI-06 处置）
* `docs/baseline/baseline_environment.txt` / `baseline_smoke_test.md` / `baseline_process_metrics.txt` / `baseline_process_metrics.json` / `smoke_output.txt`

删除文件：无。业务代码改动：无（git diff 确认 9 个 .py 原样）。

### 修改原因

- 依赖按"全部 import + README + 启动需要"确定最小集：主轨需要 PyQt5+PyQtWebEngine；openai/google/pytz 是 ai_engine/calendar_service 的模块级 import，main.py 启动路径必然经过（Phase 1 不得绕过，任务书 §4）；pytest/psutil 为测量与后续测试框架。
- synthetic 素材部署到 `~/desktop-pet/assets/`（C 盘，460KB）：原代码 ASSETS_DIR 固定指向用户目录（KI-02），Phase 1 禁止改业务代码改路径，只能按原预期路径放置；占用极小且已记录。
- 提醒验证用 `reminder.tick(31*60)` 直接喂累计秒数越过 30min 阈值：不改默认代码逻辑、不需等 30 分钟、验证后立即结束进程（任务书 §10 最小测试配置）。

### 遇到的问题

1. 首次 smoke 中"角色可见 FAIL"——检查时机早于 sheet 异步加载完成。
2. 滚轮缩放在真实 wheelEvent 下抛 TypeError。
3. `du`/`find` 遍历 C 盘 AppData 大目录超时。
4. 上游无 requirements 且模块级 import openai/google——缺任何一个 main.py 直接 ImportError。

### 根因

1. 测试脚本缺陷：sheet 加载是异步的，固定 pump 4s 不够；改为轮询 `sheet !== null`（最长 20s）。
2. **上游真实 bug（KI-11）**：`wheelEvent` 把 float 传给 `setGeometry`，scale 非整数时必现；异常在 `setScale()` JS 下发之前抛出，导致窗口/webview 尺寸错位。Phase 1 按约束不修。
3. 工具选择问题：改用目录一层 `ls -lt` 时间戳判断写入归属，不做全树遍历。
4. 上游代码结构如此；已装 openai==3.0.0、google-api-python-client==2.198.0 等保证原版可启动。

### 解决方案

1. smoke 脚本改轮询等待，复跑全绿（该项转 PASS）。
2. KI-11 登记为 🔴，留待 Phase 2 渲染轨接管时消除。
3. C 盘污染判定改证据法：`LOCALAPPDATA/uv/cache` 顶层时间戳全部为 7/30、8/11 历史遗留 → 今日 0 写入。
4. 完整安装原版启动所需全部依赖。

### 验证

```text
git status                  → 仅 .gitignore 修改 + scripts/ docs/ requirements-baseline.txt 新增，业务 .py 零改动
smoke_baseline.py           → 19 PASS / 1 FAIL（KI-11）
measure_baseline.py         → 四场景完成，358 样本，进程数恒为 3（主进程+2 Chromium 子进程）
```

Baseline 资源实测（进程树求和，含 Chromium 子进程；详见 TEST_REPORT.md）：

| 场景 | Avg CPU | Peak CPU | Avg RSS | Peak RSS |
|---|---|---|---|---|
| idle 1min | 9.77% | 38.4% | 402.6 MB | 405.9 MB |
| idle 5min 累计 | 7.74% | 38.4% | 311.6 MB | 408.6 MB |
| 动画播放 | 8.91% | 16.9% | 169.6 MB | 191.2 MB |
| 对话框+提醒 | 15.42% | 67.6% | 136.3 MB | 150.3 MB |

### C 盘污染检查

- .venv → D:\pet-desktop\.venv ✓；uv cache → D:\pet-desktop\.cache\uv ✓；pip 未使用（uv 安装）；TEMP/TMP → D:\pet-desktop\.tmp ✓
- C:\Users\13772\AppData\Local\uv\cache：全部历史遗留（7/30、8/11），今日 0 写入 ✓
- C:\Users\13772\desktop-pet：460KB（原代码固定运行时路径，非缓存）
- C 盘剩余：1.2G，与 Phase 0 相同 ✓

### 当前状态

- 原项目可在本机重复启动：`.venv/Scripts/python.exe main.py`（素材已就位）。
- KI-01 状态更新为"已用 synthetic asset 解决机制验证，真实素材永久 BLOCKED"；新增 KI-10、KI-11。
- ARCHITECTURE.md 修正一处 Phase 0 判断（wheelEvent 并非可直接复用，含 float bug）。

### 下一步

Phase 2：建立正式测试框架（tests/ + pytest 配置，处理 KI-07 的 .gitignore 放行）+ 程序日志基础。**不提前删除 AI Chat / Calendar。**

---

## 2026-08-12 (三) - Phase 2：正式测试框架 + 测试基础设施 + 程序日志基础

### 目标

在不开发产品功能的前提下，建立正式 pytest 测试框架、可复用测试基础设施、程序日志基础，为 Phase 3 起的每次业务修改提供回归保护。**不删除 AI/Calendar/WebEngine，不切 legacy 渲染，不重构 Reminder。**

### 开始状态

- Git：HEAD=1d89c85（Phase 1 baseline + smoke 刷新），工作区干净。上游基线 5f0afa5。
- 测试：无正式测试套件（仅 Phase 1 ad-hoc smoke 脚本）。
- 日志：无（程序无任何 logging 接入）。

### 实际操作

执行过的重要命令：

```text
# Git Fresh Check（每阶段开始必做）
git status / git rev-parse HEAD / git log --oneline -3 / git diff --stat
  → HEAD=1d89c85, working tree clean

# 定位 .gitignore 对 tests/ 的影响（KI-07 根因）
git check-ignore tests                      → exit=1（tests/ 本身未被忽略）
git check-ignore tests/test_example.py      → exit=0（被忽略！）
git check-ignore -v tests/test_example.py   → .gitignore:24:test_*.py（全局规则，无目录锚定）

# 逐文件读源码做 characterization（config.py / reminder_service.py / main.py / pet_window_web.py / clippy.html）
# 数据事实核查（animations.json：43 组 / 1227 帧 / 恰 1 个 duration=0 帧 / 全帧对齐 124x93 网格）
# GUI 构造可行性探测（见"遇到的问题"，probe_offscreen*.py 共 9 个探针，均在 .tmp/ 未入库）

# 正式测试（venv 内 pytest 9.1.1）
.venv/Scripts/python.exe -m pytest tests/unit -q          → 77 passed, 6.04s
.venv/Scripts/python.exe -m pytest tests/integration -q   → 3 passed, 0.65s
.venv/Scripts/python.exe -m pytest tests/smoke -q         → 9 passed, 1 xfailed, 5.43s
.venv/Scripts/python.exe -m pytest tests -v               → 89 passed, 1 xfailed, 6.25s

# 原 Baseline Smoke 回归
.venv/Scripts/python.exe scripts/smoke_baseline.py        → 19 PASS / 1 FAIL（与基线一字不差）

# 日志接入实测
.venv/Scripts/python.exe main.py（后台启动 8s）→ logs/app.log 写入 startup 行 ✓

# 业务代码零改动确认
git diff 5f0afa5 --stat -- config.py pet_window_web.py ... sounds.py → 空（8 个业务文件全零改动）
```

修改文件：

* `.gitignore` — 全局 `test_*.py` 改为目录锚定 `/test_*.py`（放行 tests/，KI-07 根因修复）
* `main.py` — 入口 wrapper 接入 applog（behavior-preserving：异常记录后原样 re-raise，退出码不变）

新增文件：

* `pytest.ini` — testpaths=tests；markers：unit/integration/gui/baseline/smoke；`--strict-markers`
* `tests/conftest.py` — D 盘 temp 隔离（TEMP/TMP→.tmp/tests，`isolated_config` monkeypatch CONFIG_DIR，`qapp` 单例）
* `tests/smoke/conftest.py` — `pet_window` fixture（真实平台、构造不 show、隐藏 tray）
* `tests/unit/test_config.py` — Config characterization（默认值/持久化/损坏回退，10 tests）
* `tests/unit/test_animation_metadata.py` — 动画元数据（43 组/帧结构/网格对齐/duration，基于真实 HTML 源）
* `tests/unit/test_animation_selection.py` — ANIM_* 分组与 _random_anim 选择逻辑（不构造 GUI）
* `tests/unit/test_reminder_service.py` — Reminder 当前行为（tick 驱动/触发/禁用/日历，16 tests）
* `tests/unit/test_applog.py` — 日志基础（文件创建/rotation 配置/幂等/不可写降级）
* `tests/unit/test_paths.py` — 路径模块（无 C 盘硬编码）
* `tests/unit/test_test_environment.py` — 测试环境自检（temp 在 D 盘/产物被 git 忽略）
* `tests/integration/test_subsystem_wiring.py` — Reminder+Config 持久化联动 / animations.json 与 HTML 源一致性
* `tests/smoke/test_gui_smoke.py` — GUI 构造 smoke（真实平台，9 tests）
* `tests/smoke/test_ki11_wheel_zoom.py` — KI-11 自动化（strict xfail，稳定 XFAIL）
* `applog.py` — 日志基础（stdlib logging + RotatingFileHandler，D:\pet-desktop\logs\app.log）
* `paths.py` — 统一路径常量（project root/log dir/temp dir，无 C 盘硬编码）

删除文件：无。业务代码改动：仅 main.py 入口 wrapper（+26/-1，纯日志接入）。

### 修改原因

- `.gitignore` 全局 `test_*.py` 规则（Phase 0 预判的 KI-07）经 `git check-ignore -v` 证实会忽略 `tests/test_example.py`，导致正式测试文件无法入库。改为 `/test_*.py`（目录锚定）仅拦截根目录散落测试，放行 tests/。
- `main.py` 接入日志是唯一的最小侵入点：入口 wrapper 记录启动/退出/未捕获异常，异常原样 re-raise 保证退出码与上游一致；业务代码（pet_window_web.py 等 8 个文件）零改动，`git diff 5f0afa5` 验证为空。
- GUI 测试用真实平台而非 offscreen（见"根因"第 1 条）；`QMenu.exec_` 用 monkeypatch 拦截（同 Phase 1 ad-hoc smoke 技术）避免阻塞。

### 遇到的问题

1. GUI smoke 首次探测 segfault（exit 139）。
2. 需确认 ChatDialog/Calendar 构造是否触发真实网络请求。
3. animations.json 存在 duration=0 帧，不能盲目断言 `duration>0`。

### 根因

1. **offscreen 平台下 `QWebEngineView.page()` 必 segfault**——Chromium 内核需要真实 OpenGL context，offscreen 默认不提供（`AA_ShareOpenGLContexts`+软件 GL 标志均无效）。经 probe_offscreen1~10 逐步二分定位：崩溃点精确在 `web.page()` 访问，与 `setBackgroundColor` 无关；真实 windows 平台全生命周期（构造→page()→正常退出）exit 0。故 GUI 测试改用真实平台、构造但不 show。
2. ChatDialog 构造仅接线控件，`.chat()` 从未被调用 → 无 OpenAI 请求；`~/desktop-pet/credentials/` 不存在 → `calendar.authenticate()` 安全返回 False，无 OAuth。两者均经代码阅读+实测确认。
3. 上游真实数据：`IdleSideToSide[25]` 帧 duration=0（43 组中恰 1 帧）。characterization test 按真实情况刻画，不为绿而改断言。

### 解决方案

1. GUI 测试全部在真实平台运行，`pet_window` fixture 构造后不 show、teardown 隐藏 tray 再 close，避免扰民。
2. 网络边界在 characterization 层明确标注 NOT TESTED（同 Phase 1 原则）。
3. duration 断言改为"非负 + 网格对齐"，并单独记录唯一 0-duration 帧的存在。

### 验证

```text
pytest tests -v                              → 89 passed, 1 xfailed, 6.25s（KI-11 strict XFAIL 稳定复现）
scripts/smoke_baseline.py                    → 19 PASS / 1 FAIL（与 Phase 1 基线一字不差，唯一 FAIL 仍为 KI-11）
main.py 后台启动 8s                          → logs/app.log 写入 "startup: pet-desktop launching (python 3.11.15)"
git diff 5f0afa5 --stat -- <8 业务 .py>      → 空（业务代码相对上游零改动）
git check-ignore tests/unit/__pycache__/...  → 命中 __pycache__/ 规则，缓存不入库
安全扫描（grep api_key/secret/token/…）       → 仅空字符串断言 + 已忽略 .pyc，无真实密钥
```

### C 盘污染检查

- 测试 temp 全部经 conftest 指到 `D:\pet-desktop\.tmp\tests\`；TEMP/TMP 在 conftest import 时重设。
- 探针脚本 probe_offscreen*.py 均在 `.tmp/`（已 gitignore），未入库、未写 C 盘。
- `~/desktop-pet/`（C 盘）仅 Phase 1 的 460KB synthetic sheet，本阶段 0 新增。
- C 盘剩余仍 1.2G，无变化。

### 当前状态

- 正式测试框架就位：89 passed + 1 xfailed，unit/integration/smoke 三层，markers 已注册。
- 程序日志基础就位：applog.py + paths.py，main.py 已接入，实测写盘。
- KI-11 已自动化（strict xfail），修复后将强制 XPASS 失败提醒移除标记。
- KI-07（.gitignore 忽略测试）已根因修复。
- 业务代码相对上游基线 5f0afa5 零改动。

### 下一步

Phase 3：按任务书推进（删除 AI Chat / Calendar / WebEngine，切换渲染轨等）。**本阶段不执行。**

---

## 2026-08-12 (三) - Phase 3：删除 AI Chat / OpenAI

### 目标与边界

只删除 AI Chat/OpenAI。保留 Google Calendar、Reminder、WebEngine 主渲染轨、拖动/缩放/睡眠/气泡/托盘等行为；不提前做 Phase 4 或渲染器迁移。

### Red → Green

先新增 `tests/unit/test_ai_removal.py` 并调整 GUI/config 测试，首跑得到 **7 failed, 16 passed**：失败准确覆盖 `ai_engine.py`、OpenAI 配置、AI client、Settings 控件与菜单入口。实现完成后同一组变为 **23 passed**。

### 实际修改

- 删除 `ai_engine.py`；两个窗口实现同步删除 `AIEngine`、`ChatDialog`、AI client、聊天入口与聊天音效。
- Settings 删除 API Key/Model；欢迎语删除 API key 引导。
- 双击角色保留为纯本地挥手问候；托盘双击改为显示角色并挥手，不再打开聊天。
- `config.py` 删除 OpenAI/personality 默认键和访问属性，将角色名键从 `ai_name` 迁移为 `pet_name`；加载旧配置时保留角色名、剔除 AI 遗留键并重写，防止旧 API key 继续留在磁盘。
- 新建当前 `requirements.txt`，不含 OpenAI；`requirements-baseline.txt` 保留历史环境事实。
- 从项目 `.venv` 实际卸载 `openai==3.0.0`，`importlib.util.find_spec('openai')` 返回 `None`；官方 OpenAI 文档检索未改变本地验收边界。
- smoke/性能脚本移除 ChatDialog 调用；baseline 历史结果不再被后续 smoke 覆盖。
- README 与架构、测试、已知问题文档同步。

### 验证

```text
pytest AI-removal/config/GUI target → 23 passed
pytest tests/unit -q               → 81 passed
pytest tests/integration -q        → 3 passed
pytest tests/smoke -q              → 9 passed, 1 xfailed
pytest tests -q                    → 93 passed, 1 xfailed
scripts/smoke_baseline.py          → 19 PASS / 1 FAIL（仅 KI-11）
```

首次 smoke 因终端 GBK 无法输出提醒 emoji 中断；设置 `PYTHONUTF8=1` 后完整执行。另发现 smoke 受上次持久化的 half-step scale 影响会偶尔绕过 KI-11，已在 harness 中固定整数起点，确保该已知问题稳定复现；未修改生产缩放逻辑。

### 下一步

Phase 4：删除 Google Calendar/OAuth 及其依赖。尚未执行。

---

## 2026-08-12 (三) - Phase 4：删除 Google Calendar / OAuth

### 范围

只删除 Google Calendar/OAuth 及 Reminder 的会议分支；不提前实现 Phase 5 的通用本地提醒，不切换 WebEngine 渲染轨。

### Red → Green

先新增 Calendar 删除边界测试并调整 GUI/config 期望，首跑 **8 failed, 17 passed**。实现后 Calendar/config/Reminder/GUI 针对性集合为 **36 passed**。

### 修改

- 删除 `calendar_service.py`。
- 两套窗口删除 CalendarService、授权初始化、Settings Calendar 组、托盘/右键日程入口和会议回调。
- `reminder_service.py` 删除 Calendar 参数、15 分钟检查分支、会议去重集合与会议 callback；水提醒逻辑保持。
- `config.py` 删除 OAuth 路径常量和 Calendar 默认键；旧 `calendar_*` 加载后自动剔除并重写。
- 当前 `requirements.txt` 和项目 venv 删除 `google-api-python-client`、`google-auth-oauthlib`、`pytz`；三项模块探测均为 `None`。
- 不自动删除用户真实 OAuth 文件，避免越权破坏用户数据。
- README、测试脚本及四份文档同步。

### 验证

```text
targeted Calendar/config/Reminder/GUI → 36 passed
pytest tests/unit -q                  → 81 passed
pytest tests/integration -q           → 3 passed
pytest tests/smoke -q                 → 9 passed, 1 xfailed
pytest tests -q                       → 93 passed, 1 xfailed
scripts/smoke_baseline.py             → 20 PASS / 1 FAIL（仅 KI-11）
```

### 下一步

Phase 5：将旧喝水 Reminder 重构为本地日期+时间提醒。尚未执行。

---

## 2026-08-12 (三) - Phase 5：本地日期+时间提醒

### 范围

将固定间隔喝水提醒替换为完全本地的单次提醒：用户填写内容、日期和时间，可查看与删除；不接云服务、不提前做 Pocket。

### Red → Green

先把 Reminder 测试改写为新契约，首跑得到 **2 failed, 10 passed, 14 errors**，失败覆盖新构造参数、CRUD、持久化、一次性到期语义与配置遗留。实现后全套为 **100 passed, 1 xfailed**。

### 修改

- `reminder_service.py` 新增 Reminder 数据模型、本地 JSON 持久化、排序 CRUD、损坏数据容错、next-due、一次性触发、重启防重与 snooze。
- 新增 `reminder_ui.py`：Add Reminder 采集内容/日期/时间；My Reminders 展示待办并删除。
- WebEngine 主窗口与原生备用窗口同步接入：托盘/右键新增 Add Reminder、My Reminders；到期时 ALERT 动画、提示音和内容气泡。
- 删除 5 秒轮询，改为最近到期项的 `QTimer(singleShot=True)`；应用恢复 Active 时补查睡眠期间到期项。
- 删除喝水设置、回调、音效命名和配置默认值；旧 `water_*` 键启动后自动从磁盘清理。
- smoke 测试的运行数据改到 `.tmp/smoke/`，提醒测试不触碰用户真实文件；原 Phase 4 证据保持不变。

### 验证

```text
pytest tests/unit tests/integration -q → 89 passed
pytest tests/smoke -q                 → 11 passed, 1 xfailed
pytest tests -q                       → 100 passed, 1 xfailed
scripts/smoke_baseline.py             → 20 PASS / 1 FAIL（仅 KI-11）
```

### 下一步

Phase 6：实现 Pocket 引用型数据层。尚未执行。

---

## 2026-08-12 (三) - Phase 6：Pocket 引用型数据层

### 范围

只实现 Pocket 的领域模型与本地持久化；不接窗口、不实现拖入/拖出，也不进行真实文件复制、移动或删除。

### Red → Green

先新增 `test_pocket_service.py`，首跑在收集阶段按预期因模块不存在失败。实现后 12 项 Pocket 契约全绿，全套增至 **112 passed, 1 xfailed**。

### 修改

- 新增 `PocketItem`：`id/path/name/item_type/added_at`，并提供动态 `exists` 状态。
- 新增 `PocketService`：加入文件/目录、路径去重、列出、移除引用、清理失效引用、重启持久化。
- 路径规范为绝对路径，Windows 大小写差异不会产生重复条目。
- `pocket.json` 使用临时文件 + replace 写入；损坏根数据回退为空，坏条目跳过。
- 测试明确验证源文件内容不变且没有任何副本产生。

### 验证

```text
pytest tests/unit/test_pocket_service.py -q → 12 passed
pytest tests -q                             → 112 passed, 1 xfailed
scripts/smoke_baseline.py                   → 20 PASS / 1 FAIL（仅 KI-11）
```

### 下一步

Phase 7：让 PetWindow 接收文件/目录拖入并写入 Pocket，引出 RECEIVE 动画。尚未执行。

---

## 2026-08-12 (三) - Phase 7：拖入角色加入 Pocket

### 范围

在两个 PetWindow 实现本地文件/目录拖入，调用 Phase 6 Pocket 引用服务并展示接收反馈；不实现 Pocket 列表窗口和拖出。

### Red → Green

先扩充 GUI smoke，得到 **3 failed, 10 passed**：窗口未持有 Pocket、未启用 drop、事件落到 Qt 默认实现。实现后新增 GUI/边界测试全部通过，全套 **115 passed, 1 xfailed**。

### 修改与验证

- `setAcceptDrops(True)`；dragEnter 只接受存在的本地 file URL。
- drop 支持文件和目录批量加入、重复识别和部分失败；源文件不复制、不移动。
- WebEngine 轨播放 `Save` 接收动画并显示 Pocket 结果气泡；原生轨使用 alert fallback。
- smoke fixture 隔离 `POCKET_FILE`；脚本真实驱动 drop handler，验证 2 个引用且源文件内容不变。

```text
pytest tests -q                   → 115 passed, 1 xfailed
scripts/smoke_baseline.py         → 21 PASS / 1 FAIL（仅 KI-11）
```

### 下一步

Phase 8：实现 Pocket 列表窗口与右键操作。尚未执行。

---

## 2026-08-12 (三) - Phase 8：Pocket 列表窗口

### 范围与修改

- 新增 `PocketDialog`，展示文件/目录引用及 missing 状态。
- 提供打开、资源管理器定位、复制路径、移除引用、清理失效引用；双击打开，右键菜单提供常用项。
- 主/备用 PetWindow 的托盘与右键菜单均新增 Pocket 入口。
- `PocketService.get()` 为 UI 通过稳定 ID 取条目，不让 UI 持有列表索引。
- 删除/清理操作只改 JSON；测试确认原文件仍在。剪贴板在测试中用 fake 隔离，Open/Explorer 不实际触发。

### 验证

```text
pytest Pocket service + GUI targeted → 27 passed
pytest tests -q                      → 117 passed, 1 xfailed
scripts/smoke_baseline.py            → 21 PASS / 1 FAIL（仅 KI-11；菜单含 Pocket）
```

### 下一步

Phase 9：从 Pocket 用标准 `QMimeData` file URL 拖出到 Explorer。尚未执行。

---

## 2026-08-12 (三) - Phase 9：从 Pocket 拖出

### 修改

- 新增 `PocketListWidget` 并启用 drag。
- 有效引用转换为标准本地 file URL，`QDrag.exec_(Qt.CopyAction)` 交由 Explorer/Desktop 处理。
- missing 引用不生成 mime data，空选择不启动 QDrag。
- 无 shutil、无源文件写入、无 Pocket 数据变化。

### 验证

```text
pytest tests -q → 120 passed, 1 xfailed
```

自动化验证 URL 的本地路径往返、CopyAction 源码边界、源文件仍存在与 missing 拒绝。真实鼠标拖到 Explorer 的端到端人工体验留 Phase 17。

### 下一步

Phase 10：实现显式“复制到 / 移动到”文件操作服务与冲突/异常报告。尚未执行。

---

## 2026-08-12 (三) - Phase 10：复制到 / 移动到

### 修改

- 新增 `file_ops.py` 与结构化 OperationReport。
- 文件/目录复制和移动；默认同名自动编号，可显式 skip，永不覆盖。
- 缺失源、非法目标、OS 错误逐项报告；批量部分失败继续执行。
- 拒绝目录复制/移动进自身后代。
- Pocket UI 增加 Copy To / Move To；移动成功同步引用到真实新路径。

### 验证

```text
pytest tests/unit/test_file_ops.py -q → 10 passed
pytest tests -q                       → 132 passed, 1 xfailed
```

所有真实文件操作仅在 `D:\pet-desktop\tests\.tmp\` 隔离目录内执行；覆盖文件、目录、冲突、移动、缺失源、坏目标、部分失败、自包含保护与 Pocket 引用同步。

### 下一步

Phase 11：常用目的地（favorites）。尚未执行。

---

## 2026-08-12 (三) - Phase 11：常用目的地

新增 `destinations.py` favorites 持久化；支持已有目录加入、去重、重启、移除引用、missing 状态和损坏文件回退。Pocket UI 增加收藏目录选择与快捷 Copy/Move；删除收藏不删除目录。

```text
pytest tests/unit/test_destinations.py -q → 7 passed
pytest tests -q                          → 140 passed, 1 xfailed
```

下一步 Phase 12：记录最近目的地（去重置顶、上限 10、清空）。尚未执行。

---

## 2026-08-12 (三) - Phase 12：最近目的地

成功 Copy/Move 后记录目标目录，重复路径移到首位且不重复，历史上限 10；UI 可直接 Copy/Move to Recent 或清空历史。失败/取消不记录，missing 不执行，清空不影响 favorites 与磁盘目录。

```text
pytest destinations + GUI targeted → 31 passed
pytest tests -q                    → 145 passed, 1 xfailed
```

下一步 Phase 13：获取当前前台 Explorer 目录并作为快捷目标。尚未执行。

---

## 2026-08-12 (三) - Phase 13：当前 Explorer 目录

实现 foreground HWND → Shell.Application window 精确匹配，只返回真实存在目录；无 Explorer/虚拟位置/COM 失败返回 None，不伪造 fallback。Pocket 新增 Copy/Move to Explorer，成功后进入 recents。未新增 pywin32/comtypes 依赖。

```text
pytest explorer + GUI targeted → 25 passed
pytest tests -q                → 150 passed, 1 xfailed
```

下一步 Phase 14：Windows 文件事件监听。尚未执行。
