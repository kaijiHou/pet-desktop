# V5.0 Change Summary

> 本文件从 V5.0 开工即创建，随开发实时更新，最终与代码同一轮 commit/push。
> 格式承自 docs/CHANGE_SUMMARY_TEMPLATE.md。

## 1. Baseline

Baseline HEAD: 8ac41a74c3733cf55bdb3de93341e25d81d8b945
Branch: master
Date: 2026-09-08
Environment: Windows 10.0.19045 x64 / Python 3.11.15 (uv cpython) / PyQt5 5.15.11 / Pillow
GUI automation availability: 本会话工具链中存在 computer-use，但用户在本轮 V4.9 会话内已明确表示"别用电脑控制"——该禁止为当前上下文真实存在，非虚构；因此本轮回退到任务书 §4B 方案：真实 Windows Qt GUI（windows 平台，非 offscreen）+ QWidget.grab() 采集真实渲染截图；鼠标 resize / 系统 DPI / Explorer GUI 操作如实 NOT TESTED。

## 2. 本轮目标

1. 建立永久的版本级 CHANGE_SUMMARY 规范（模板 + V50 实例 + 开发日志规则）。
2. 把 V4.9 遗留的"真实 Windows 视觉闭环 NOT TESTED"尽可能变成真实证据：真实渲染截图（Settings / Wage Settings / Calendar 9月 / 10月 / Gallery / 角色一致性）+ 图像 sanity 校验 + 逐张人工审查。
3. Build identity：EXE 可自查版本（V5.0 · git 短 SHA），杜绝"改了但打开是旧包"的混淆；release manifest 明确区分 git_sha 与 zip_sha256。
4. fallback 加固（restart 幂等 / 有效自定义角色不覆盖 / ghost 损坏 emergency 兜底）与泄漏契约升级。
5. Fresh EXE ≥15 分钟 soak；最终 release candidate。

## 3. 修改前问题

- V50-01：真实 Windows UI 视觉验收全部 NOT TESTED（V49_REAL_ACCEPTANCE）。根因：V4.9 轮无可用 GUI 自动化路径。证据：docs/V49_REAL_ACCEPTANCE.md。
- V50-02：Explorer RMDIR 真实 GUI 验收 NOT TESTED。同上。
- V50-03：V4.9 无独立 Change Summary（只有 DEVELOPMENT_LOG/TEST_REPORT 等四件套）。根因：流程未要求。证据：git log 8ac41a7。
- V50-04：Git SHA 与 Artifact SHA 混淆风险——V4.9 commit message "record final v4.9 candidate SHA 692f6fac" 实为 ZIP SHA256 前缀。证据：git show 8ac41a7。
- V50-05：Fresh EXE 无法自查构建版本；EXE 与仓库 HEAD 可能不一致而无从发现。证据：无 build_info 机制。
- V50-06：release/manifest.json 只有 name/format/entrypoint/zip/sha256/built_at，无 version 与 git_sha。证据：release/manifest.json。
- V50-07：fallback 幂等性未验证（restart 后是否重复 warning）、有效自定义角色是否可能被覆盖未验证、ghost 自身损坏时是否白屏未验证。证据：V4.9 仅一测。

## 4. 本轮实际修改

（随开发实时更新；最终版本见下）

### V50-03 Change Summary 规范
- 修改内容：新增 docs/CHANGE_SUMMARY_TEMPLATE.md 与本文件；DEVELOPMENT_LOG 写入永久规则。
- 修改文件：docs/CHANGE_SUMMARY_TEMPLATE.md(A)、docs/V50_CHANGE_SUMMARY.md(A)、docs/DEVELOPMENT_LOG.md(M)。
- 根因/实现：见 §2.1；模板固定章节结构，后续版本复制即用。

### V50-05 Build identity
- 修改内容：构建时生成 build_info.json（version/git_sha/build_time），spec 打包进 EXE；启动日志输出 app version/build id；Settings 数据区底部显示"版本 V5.0 · <short sha>"。
- 修改文件：scripts/build_release.ps1(M)、pet-desktop.spec(M)、app_version.py(A)、main.py(M)、pet_window.py(M)。
- 修改前：EXE/源码均无版本标识。修改后：运行时只读 build_info.json（Frozen 与源码态都有合理取值）。

### V50-06 release manifest 扩展
- 修改内容：manifest 增加 version / git_sha（构建时记录的真实 commit）/ zip_sha256 / build_time。
- 修改文件：scripts/build_release.ps1(M)。

### V50-07 fallback 加固
- 修改内容/文件/测试：见 §4 后续更新与 tests/smoke/test_v50_fallback.py。

### V50-01 真实渲染截图链
- 修改内容：新增 scripts/capture_v50_ui.py（windows 平台、临时数据目录、--date 支持、widget.grab 输出 6 张 PNG）与 scripts/validate_v50_screenshots.py（存在性/尺寸/非全透明/非单色/大小阈值）；人工逐张审查输出 docs/V50_UI_REVIEW.md。
- 修改文件：scripts/capture_v50_ui.py(A)、scripts/validate_v50_screenshots.py(A)、docs/V50_UI_REVIEW.md(A)。

### V50-08 resize/layout 契约
- 修改内容：WorkCalendar 程序化 resize 大/小两档 layout 契约；ModernDialog 抽 detect_resize_edge 纯函数并单测 8 方向。
- 修改文件：tests/...、theme.py 或 modern_dialog 实现文件（以实际 diff 为准）。

## 5. 文件级变化

（最终由 `git diff --name-status V50_BASELINE_HEAD..HEAD` 真实输出回填）

## 6. 新增功能

- EXE 内部 build/version 标识（V5.0 · <short sha>，启动日志 + Settings 数据区）。
- 真实渲染 UI 截图与校验脚本（验收基础设施）。

## 7. 修复 Bug

（以最终审计为准回填）

## 8. 删除/弃用

- ActiveExplorerWatcher 继续保持 disabled（历史 segfault，任务书 §19），KNOWN_ISSUES 保留条目。

## 9. 测试

（实时回填：命令/结果/耗时/PASS-FAIL）

## 10. 真实验收

（实时回填；状态只允许 PASS / FAIL / NOT TESTED / BLOCKED）

## 11. Release

- Final repository HEAD: （docs 最终 commit 后回填）
- Release built from Git HEAD: （代码冻结 commit 后回填）
- Artifact ZIP SHA256: （build 后回填）
- Build time: （回填）

## 12. Remaining Known Issues

（回填）

## 13. 本轮未完成项

（回填）

## 14. Commit 列表

（`git log --oneline 8ac41a74..HEAD` 回填）

## 15. 最终状态

PARTIAL（进行中；收尾时复核）
