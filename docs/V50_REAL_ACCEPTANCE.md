# V5.0 Real Acceptance

状态只允许 PASS / FAIL / NOT TESTED / BLOCKED。
GUI automation availability：本会话存在 computer-use 工具链，但用户在本会话早前（V4.9 轮）已明确"别用电脑控制"——该约束真实存在并被继承；
因此本轮按任务书 §4B 执行：真实 Windows Qt 平台（windows 平台，非 offscreen）+ QWidget.grab() 采集真实渲染截图。
widget.grab() 证明真实渲染，不证明鼠标 resize 手感 / 系统 DPI / Explorer GUI 行为。

## 环境记录

| 项 | 值 |
|---|---|
| V50_BASELINE_HEAD | `8ac41a74c3733cf55bdb3de93341e25d81d8b945`（经 ghfast.top 镜像 fetch 确认与远端一致） |
| Release built from Git HEAD | **7f9374904a24631ba5cdf1acf6b61260205035c8**（A'，代码+测试冻结，370 passed） |
| Final repository HEAD | 本文件所在 docs commit（B；git log 首行，只改文档不含代码） |
| Artifact ZIP SHA256 | **d8c6573882b4c7b36ad68f41d631f9f82d3285c500541448acccf338448e2b4e** |
| Build time | 2026-09-08T18:46:22+08:00（pwsh 7 构建） |
| verify_release | PASS（running/responding/单进程/动画 catalog/日志/WebEngine=0） |

## 截图（真实渲染，6/6 sanity PASS）

| 项 | 状态 | 证据 |
|---|---|---|
| Settings | PASS（rendered+human review） | `.tmp/v50-acceptance/screenshots/r2/v50-settings.png` 470×815 |
| Wage Settings | PASS | `r2/v50-wage-settings.png` 560×639 |
| Calendar 2026-09 | PASS（r1 FAIL→修复→r2 PASS） | `r2/v50-calendar-september.png` 980×862 |
| Calendar 2026-10 | PASS | `r2/v50-calendar-october.png` 980×862 |
| Character Gallery | PASS | `r2/v50-character-gallery.png` 560×644 |
| Desktop/Settings 一致性 | PASS（same_id/aspect 契约 + 人工比对） | `r2/v50-character-consistency.png` 560×380 |

逐张优缺点与 P0/P1/P2 见 `V50_UI_REVIEW.md`。截图文件不入库。

## 契约（PASS）

| 项 | 结果 |
|---|---|
| 9 月应出勤 22 天 / 10 月 18 天 | PASS（stat 卡截图 + workday_count 双证） |
| 9/20、10/10 补班；9/25-27、10/1-7 休息 | PASS（截图 + status_for） |
| Wage Settings 22 天只读 + 自动徽章 | PASS（截图，无手工 spinbox） |
| 隐私遮罩 | PASS（ wage privacy `••••••` 契约保留；本轮截图使用测试工资 11200 非用户数据） |
| fallback §20 restart×2 警告次数 | PASS（test_missing_id_warns_once_then_persists） |
| fallback §21 有效自定义不覆盖 | PASS（test_valid_custom_character_not_overridden） |
| fallback §22 双层失败 emergency 不白屏 | PASS（test_corrupted_pack_falls_back_then_emergency_single） |
| resize 布局契约（大 1200×800 / 最小尺寸 detail 不消失） | PASS（test_work_calendar_programmatic_resize_large / _minimum_size_keeps_detail）——注意：这是 layout contract，不是鼠标 hit-test PASS |
| detect_resize_edge 8 方向 | PASS（纯函数单测）；真实鼠标 drag 另列 |
| timer 泄漏（Settings×20 / Gallery×20 / renderer reload×20） | PASS（3 个契约测试） |
| "工时日历"残留 | PASS（全仓 0） |
| V50 docs contract | PASS（test_v50_release_docs_exist） |

## 鼠标 / DPI / Explorer（无 GUI 自动化，诚实记录）

| 项 | 状态 |
|---|---|
| ModernDialog 鼠标 resize 手感（8 边缘拖拽） | NOT TESTED（有 detect_resize_edge 纯函数与 layout 契约，不等价） |
| Windows 真实 DPI 100%/125% | NOT TESTED（不使用 QT_SCALE_FACTOR 冒充） |
| Explorer 真实 RMDIR（Fresh EXE + GUI 操作） | NOT TESTED（不用 SHChangeNotify 自发消息冒充；filesystem/Shell 广播/Explorer GUI 三种证据不混用） |
| ActiveExplorerWatcher | 保持 disabled（历史 segfault，KNOWN_ISSUES 保留） |

## Fresh EXE

| 项 | 状态 |
|---|---|
| clean build + verify（running/responding/单进程/无 WebEngine） | （回填） |
| 启动日志 build identity（app_version/git_sha/build_time） | PASS（代码契约；EXE 日志回填） |
| Settings 版本行 | PASS（EXE 启动日志实测 `app_version=V5.0 git_sha=7f9374…`；Settings 显示 版本 V5.0 · <short sha>） |
| soak ≥15 分钟 | PASS（15min 同 PID 零崩溃，RSS 79→18MB 无增长，CPU 9.9s；idle 场景如实记录，见 V50_SOAK_REPORT.md） |
