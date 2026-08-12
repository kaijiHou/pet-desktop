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
