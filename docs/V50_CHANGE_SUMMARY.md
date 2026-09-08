# V5.0 Change Summary

> 依据 docs/CHANGE_SUMMARY_TEMPLATE.md；本文件随开发实时更新，与代码同一轮 commit/push。

## 1. Baseline

Baseline HEAD: 8ac41a74c3733cf55bdb3de93341e25d81d8b945（v4.9 收尾 commit；经 ghfast.top 镜像 fetch 确认与远端 master 一致）
Branch: master
Date: 2026-09-08
Environment: Windows 10.0.19045 x64 / Python 3.11.15 (uv cpython) / PyQt5 5.15.11 / Pillow / PyInstaller
GUI automation availability: 本会话工具链存在 computer-use，但用户在本会话内已明确"别用电脑控制"（真实约束，非虚构）；按任务书 §4B 采用真实 Windows Qt 平台 + QWidget.grab() 真实渲染截图。

## 2. 本轮目标

1. 建立永久版本级 CHANGE_SUMMARY 规范（模板 + V50 实例 + 开发日志规则）。
2. 把 V4.9 遗留的视觉 NOT TESTED 尽可能变成真实证据：真实渲染截图 6 张 + sanity 校验 + 逐张人工审查（V50_UI_REVIEW）。
3. Build identity：EXE 自查版本（V5.0 · git 短 SHA），manifest 严格区分 git_sha 与 zip_sha256。
4. fallback 加固（§20/21/22）、resize/layout 契约（§14/15）、timer 泄漏契约升级（§24）。
5. Fresh EXE ≥15 分钟 soak；最终 release candidate（§47-49 的 A/B/Z 模型）。

## 3. 修改前问题

- V50-01：真实 Windows UI 视觉验收全部 NOT TESTED。根因：V4.9 轮无可用 GUI 路径。证据：docs/V49_REAL_ACCEPTANCE.md。
- V50-02：Explorer 真实 RMDIR GUI 验收 NOT TESTED。同上。
- V50-03：V4.9 无独立 Change Summary。证据：git log 8ac41a7。
- V50-04：Git SHA 与 Artifact SHA 混淆（"candidate SHA 692f6fac" 实为 ZIP SHA256 前缀）。证据：commit 8ac41a7 message。
- V50-05：EXE 无版本标识，无法发现"旧包"混淆。证据：无 build_info 机制。
- V50-06：release/manifest.json 无 version/git_sha。证据：V4.9 manifest。
- V50-07：fallback 幂等/防覆盖/emergency 兜底未验证。证据：V4.9 仅一测。
- V50-08（本轮发现的真实 Bug）：PS5 `Set-Content -Encoding UTF8` 写 BOM 导致 EXE 内 build_info.json 被 json.load 拒读，EXE 日志回落 git_sha=dev。证据：解压副本日志 `app_version=V5.0 git_sha=dev`。
- V50-09（看图发现的真实缺陷）：日历月格刷新依赖 deleteLater 的 DeferredDelete 时序，未删除的旧 cell 会在旧 geometry 继续绘制（批量刷新/慢机器可复现叠影）。证据：r1 截图两层月份。
- V50-10（看图发现）：日历详情"来源"显示裸 gov.cn 链接且溢出截断；标题栏 □/× 按钮几乎不可见；待机"取消"按钮常驻。

## 4. 本轮实际修改

### V50-03 Change Summary 规范（commit 65a4eb9 内）
- 修改内容：新增模板与本文件；DEVELOPMENT_LOG 写入永久规则（每个大版本必须有 Vxx_CHANGE_SUMMARY.md）。
- 修改文件：docs/CHANGE_SUMMARY_TEMPLATE.md(A)、docs/V50_CHANGE_SUMMARY.md(A)、docs/DEVELOPMENT_LOG.md(M)。

### V50-05/06 Build identity（commit 65a4eb9 + 7f93749）
- 修改内容：构建时生成 build_info.json（version/git_sha/build_time，无 BOM）→ spec 打包 → 运行时只读（不调 git）；启动日志输出 identity 与 effective character；Settings 数据区底部"版本 V5.0 · <short sha>"；manifest 增加 version/git_sha/zip_sha256/build_time。
- 修改文件：app_version.py(A)、scripts/build_release.ps1(M)、pet-desktop.spec(M)、main.py(M)、pet_window.py(M)、.gitignore(M)。
- 根因/实现：见 V50-08；读取端 utf-8-sig 兜底 + 写入端 `[System.IO.File]::WriteAllText(..., UTF8Encoding($false))`。

### V50-07 fallback 三级链（commit 65a4eb9）
- 修改内容：requested pack 失败/缺失 → WARNING + 回退内置 ghost（且持久化 effective id，重启不再警告）；ghost 也失败 → WARNING emergency → 保留现有渲染/单模式，绝不白屏。
- 修改文件：pet_window.py（_load_dynamic_renderer 重构）。
- 测试：tests/smoke/test_v50_fallback.py 3 项。

### V50-01 真实渲染截图链（commit 65a4eb9）
- 修改内容：scripts/capture_v50_ui.py（windows 平台、隔离数据目录、--date 固定时钟、测试月薪 11200、6 张 widget.grab PNG）+ scripts/validate_v50_screenshots.py（存在/尺寸/非全透明/非单色/大小下限）+ 人工逐张审查 docs/V50_UI_REVIEW.md。
- 结果：r1 6/6（修正校验器颜色语义后）；发现 V50-09/10 → 修复 → r2 6/6。

### V50-09/10 日历与标题栏视觉修复（commit 65a4eb9）
- 修改内容：refresh() takeAt 后立即 hide() 再 deleteLater（叠影根除）；详情来源改"国务院办公厅放假安排"人话（去裸 URL）；待机"取消"按钮隐藏、编辑时出现（timeChanged/textChanged 触发）；新增 titleButton QSS（对比度+hover）。
- 修改文件：wage/ui_calendar.py、ui/modern/dialog.py、ui/modern/tokens.py。

### V50-08 PowerShell 7 纪律（commit 7f93749）
- 修改内容：app_version utf-8-sig 读取；build 脚本 noBOM 写入；构建/verify 全部改 pwsh 7；规则写入用户全局记忆。

### V50-11 契约测试（commit f6062b4）
- 修改内容：fallback 3 测；detect_resize_edge 纯函数 8 方向单测（ui/modern/dialog.py 抽取）；WorkCalendar 1200×800 与最小尺寸 layout 契约；Settings×20/Gallery×20 timer 泄漏契约；V50 docs 存在性契约。
- 修改文件：tests/smoke/test_v50_fallback.py(A)、tests/smoke/test_v50_resize_and_docs.py(A)、ui/modern/dialog.py(M)。

## 5. 文件级变化（git diff --name-status 8ac41a74..HEAD 真实输出）

```
M	.gitignore                      # 忽略生成的 build_info.json
A	app_version.py                  # 运行时只读构建身份（V50-05/08）
A	docs/CHANGE_SUMMARY_TEMPLATE.md # 永久规范模板（V50-03）
M	docs/DEVELOPMENT_LOG.md         # 永久规则 + V5.0 条目
A	docs/V50_CHANGE_SUMMARY.md      # 本文件
A	docs/V50_REAL_ACCEPTANCE.md     # 本轮真实验收
A	docs/V50_UI_REVIEW.md           # 截图逐张人工审查
M	main.py                         # 启动日志输出 build identity
M	pet-desktop.spec                # 打包 build_info.json
M	pet_window.py                   # fallback 三级链 + identity 日志 + Settings 版本行
M	scripts/build_release.ps1       # build_info 生成(noBOM) + manifest 扩展
A	scripts/capture_v50_ui.py       # 真实渲染截图采集
A	scripts/soak_v50.py             # EXE soak 采样
A	scripts/validate_v50_screenshots.py # 截图 sanity 校验
A	tests/smoke/test_v50_fallback.py    # §20/21/22
A	tests/smoke/test_v50_resize_and_docs.py # §14/15/24/37
M	ui/modern/dialog.py             # detect_resize_edge 抽取 + titleButton
M	ui/modern/tokens.py             # titleButton QSS
M	wage/ui_calendar.py             # 叠影修复 + 来源人话 + 取消按钮 + 行紧凑化
19 files changed, 1037 insertions(+), 42 deletions(-)
```

## 6. 新增功能

- EXE/Settings/启动日志的 build identity（V5.0 · <short sha>）。
- 真实渲染 UI 截图采集 + sanity 校验 + soak 采样三件验收基础设施。

## 7. 修复 Bug

- V50-08：BOM 致 build_info 拒读（EXE 显示 git_sha=dev）→ 双端修复，EXE 实测日志正确。
- V50-09：日历月格叠影（DeferredDelete 时序）→ hide() 先行，r2 截图确认。
- V50-10：裸 URL 溢出、标题栏按钮不可见、待机取消按钮噪音 → 全部修复，r2 确认。

## 8. 删除/弃用

- ActiveExplorerWatcher 继续保持 disabled（历史 segfault；任务书 §19），无代码变化。
- 无其他删除。

## 9. 测试

| 命令 | 结果 | 耗时 |
|---|---|---|
| `pytest tests -q`（A'=7f93749 全量） | **370 passed** | 4m05s |
| `pytest tests/smoke/test_v50_fallback.py tests/smoke/test_v50_resize_and_docs.py -q` | 9 passed | 2m52s |
| `pytest tests/smoke/test_v48_ui_contracts.py tests/smoke/test_v49_contracts.py tests/unit/test_statutory_calendar.py -q` | 17 passed | 1m05s |
| `scripts/validate_v50_screenshots.py`（r2） | 6/6 PASS | <1s |
| 日历/工资契约脚本（9月22天/10月18天/日薪） | PASS | <1s |

## 10. 真实验收

| 项 | 状态 |
|---|---|
| Settings / Wage Settings / Calendar 9月 / 10月 / Gallery / 一致性 真实渲染截图 | PASS（6/6 sanity + 人工审查，见 V50_UI_REVIEW；r2 为最终版） |
| 9月22天 / 10月18天 / 补班/休息标记 | PASS（截图+契约双证） |
| 角色一致性（same pack + same aspect） | PASS（same_id/aspect 契约 + 人工比对） |
| 鼠标 resize 手感 | NOT TESTED（有 layout 契约与 detect_resize_edge 单测，不等价） |
| Windows 真实 DPI 100%/125% | NOT TESTED（不用 QT_SCALE_FACTOR 冒充） |
| Explorer 真实 RMDIR | NOT TESTED（不用 SHChangeNotify 自发消息冒充） |
| Fresh EXE build/verify | PASS（单进程/响应/无 WebEngine） |
| EXE build identity 日志 | PASS（`app_version=V5.0 git_sha=7f9374…`） |
| EXE soak ≥15 分钟 | PASS（15min 同 PID 零崩溃，RSS 79→18MB，CPU 9.9s；idle 场景如实记录） |

## 11. Release（§49 A/B/Z 模型）

- Release built from Git HEAD: **7f9374904a24631ba5cdf1acf6b61260205035c8**（commit A'，代码+测试冻结）
- Artifact ZIP SHA256: **d8c6573882b4c7b36ad68f41d631f9f82d3285c500541448acccf338448e2b4e**
- Build time: 2026-09-08T18:46:22+08:00
- Final repository HEAD: 本文件所在 docs commit（B；git log 首行，仅文档）
- 注：manifest 内 version=V5.0、git_sha=A'、zip_sha256 与上一致；文档 commit B 不改代码，EXE 属 A'。

## 12. Remaining Known Issues

- 鼠标 resize 手感 / 真实 DPI / Explorer 真实 RMDIR：NOT TESTED（无 GUI 自动化；清单在 V50_REAL_ACCEPTANCE）。
- 遗留观察（本轮不动）：收入提示 combo 原生箭头感、Gallery 单条目留白、"恢复默认"层级弱（V50_UI_REVIEW P2）。
- ActiveExplorerWatcher 保持 disabled（历史 segfault）。

## 13. 本轮未完成项

- 无（视觉三项为环境受限的 NOT TESTED，非未完成；soak 若仅 15 分钟如实标注）。

## 14. Commit 列表（git log --oneline 8ac41a74..HEAD）

```
7f93749 fix: read BOM'd build_info.json and write it BOM-less; standardize on PowerShell 7
f6062b4 test: v5.0 fallback/resize/timer contracts + UI review and real acceptance docs
65a4eb9 feat: v5.0 build identity, fallback hardening, real-render UI capture
```

## 15. 最终状态

DONE（视觉三项 NOT TESTED 为环境约束下的诚实记录，已给出用户回填清单；其余核心门槛全部 PASS）
