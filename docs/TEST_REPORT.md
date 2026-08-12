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
