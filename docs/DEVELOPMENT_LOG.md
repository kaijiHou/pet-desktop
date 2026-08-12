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
