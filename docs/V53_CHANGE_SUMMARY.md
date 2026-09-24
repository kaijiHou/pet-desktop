# V5.3 Change Summary

## 1. Baseline

Baseline HEAD: `6f62ca5af962f7485147cb6543e73072a4866471`
Summary scope implementation HEAD: `b937a9166372025ac436d461a8f122545babea67`
Branch: `master`
Date: `2026-09-24`
Environment: Windows x64; PowerShell 7; Python 3.11.15; Qt 5.15.2 / PyQt 5.15.11
GUI automation availability: Qt Windows-plugin widget rendering is available; real desktop interaction was not performed.

## 2. 本轮目标

在不重做 V5.2 DestinationService 的前提下，收口失效路径反馈、超长名称、当前 Explorer 固定、Pet/托盘快捷入口与 Pocket 多选目标操作。补全实时刷新、性能/兼容边界测试，并让发布摘要与 Git 实际 A/M/D/R 状态对账。

## 3. 修改前问题

- V53-01：QuickPanel 点击失效路径静默返回；管理入口没有聚焦修复提示。
- V53-02：QuickPanel 名称未按实际可用宽度截断；同一 refresh 可能多次触发路径检查。
- V53-03：没有经确认的一键固定当前 Explorer 文件夹入口。
- V53-04：Pet 右键和托盘菜单没有共享常用文件夹快捷子菜单。
- V53-05：Pocket 多选 Copy/Move 与混合成功/失败引用更新缺少完整合同。
- V53-06：相同损坏 JSON 重复启动可持续生成备份；发布审计此前未核对 Git status。
- V53-07：管理列表按钮密集；V5.2 文档存在 Git status 错记及无依据归因。

## 4. 本轮实际修改

### V53-01 失效路径反馈与名称截断
- 修改内容：失效项目左键进入管理窗定位项并说明修复方式；长名用 `QFontMetrics.elidedText()` 按按钮空间截断，tooltip 保留全名/路径。
- 修改文件：`quick_panel.py`、`favorite_folders_ui.py`。
- 修改前：失效点击无响应；名称可能挤压两列。
- 修改后：即时给出修复入口；QuickPanel 保持固定宽度与可读网格。
- 根因：失效分支仅返回 false，显示文本没有依据可用宽度计算。
- 实现：管理窗接收 focus/message；按钮按图标及边距扣除可用文本宽度。

### V53-02 当前 Explorer 固定与状态反馈
- 修改内容：新增“固定当前文件夹/选择其他文件夹”入口；读取后确认路径与名称，重复路径定位已有收藏。
- 修改文件：`quick_panel.py`、`explorer.py`、`favorite_folders_ui.py`、`pet_window.py`。
- 修改前：常用目录需要重新打开选择器查找。
- 修改后：确认后通过原共享添加流程写入；无 Explorer/非普通目录给出不同说明。
- 根因：产品只有手工选目录的入口。
- 实现：只调用 `ExplorerService.current_directory()`；没有启用 `ActiveExplorerWatcher`。

### V53-03 Pet/托盘快捷菜单与面板刷新
- 修改内容：右键与托盘菜单共享同一个 service，至多列前 8 项；超量进入管理，失效路径禁用打开。
- 修改文件：`pet_window.py`、`pocket_window.py`、`quick_panel.py`。
- 修改前：Pet 菜单没有文件夹快捷入口；操作变化依赖重新打开面板。
- 修改后：一处 service 驱动 QuickPanel、Pocket、管理窗、右键和托盘；管理操作实时刷新。
- 根因：菜单入口缺失，需有验证覆盖跨窗体生命周期。
- 实现：复用 `self.destination_service` 与 `favorites_changed` 通知。

### V53-04 Pocket 多选与 refresh I/O
- 修改内容：补多选 Copy/Move、混合有效/失效引用更新及 Recent 去重；每个 refresh 缓存一次 exists 结果。
- 修改文件：`pocket_window.py`、`quick_panel.py`、`favorite_folders_ui.py`、`tests/smoke/test_pocket_favorites_multi.py`。
- 修改前：只有单项操作测试，且网络/移动盘可能被重复同步探测。
- 修改后：每个 favorite 每轮 refresh 最多一个 `exists` 查询；执行文件操作时仍重新验证。
- 根因：按钮状态和显示分别读取同一动态路径状态。
- 实现：把每轮探测结果存在局部字典并复用；FileOperationService 继续负责文件操作。

### V53-05 持久化与旧数据兼容
- 修改内容：同一坏 JSON 只备份一次；补 >20 条旧数据保留、Windows 大小写路径重复和盘根目录合同。
- 修改文件：`destinations.py`、`tests/unit/test_destinations.py`。
- 修改前：损坏文件名随时间变化，重复启动会无限堆积同内容副本。
- 修改后：对原始字节计算 SHA-256，以独占创建方式落盘，不覆盖原文件。
- 根因：备份唯一性按时间而非内容判定。
- 实现：内容寻址 backup；旧收藏读取不截断，新增加仍受上限约束。

### V53-06 Git 文档审计与 release
- 修改内容：解析 `git diff --name-status -z -M`；核对 Summary 路径及 A/M/D/R 状态；正式构建要求 PowerShell 7，构建后写入实际 release HEAD/ZIP SHA256 并再次全审。
- 修改文件：`scripts/audit_release_docs.py`、`scripts/build_release.ps1`、`scripts/verify_release.ps1`、`tests/unit/test_audit_release_docs.py`。
- 修改前：Missing=0 只验证文档章节，不代表变更清单与 Git 一致。
- 修改后：审计可参数化复用；正式 build 前状态审计，ZIP 生成后填真实身份并运行严格审计。
- 根因：旧脚本没有读取 Git diff。
- 实现：支持 rename 双路径、空格路径与状态失配报告；`-SkipDocAudit` 仅产生 `.tmp` 开发包。

### V53-07 文档、截图与版本记录
- 修改内容：添加四张合成数据截图与 UI review/验收/变更摘要；纠正 V5.2 文档；明确 V5.1 没有形成 release。
- 修改文件：本 Summary、`V53_REAL_ACCEPTANCE.md`、`V53_UI_REVIEW.md`、四份强制文档、`V52_CHANGE_SUMMARY.md`、`V52_REAL_ACCEPTANCE.md`、`docs/screenshots/v53/`。
- 修改前：没有 V5.3 截图；V5.2 手写状态记录不准确。
- 修改后：静态控件渲染与真实桌面 NOT TESTED 清楚分开；纠错保留为 post-release correction。
- 根因：文档人工清单没有逐项对照 Git 输出，且过度描述真实验收。
- 实现：四图仅用 `.tmp/v53-demo/` 合成目录；V5.2 原始错记不抹去，追加纠错说明。

## 5. 文件级变化

`docs/V53_CHANGE_SUMMARY.md` 自身由审计器排除，避免 self-reference；其余路径与状态须由最终 audit 输出验证。

```text
A docs/V53_CHANGE_SUMMARY.md
M app_version.py
M destinations.py
M docs/ARCHITECTURE.md
M docs/DEVELOPMENT_LOG.md
M docs/KNOWN_ISSUES.md
M docs/TEST_REPORT.md
M docs/V52_CHANGE_SUMMARY.md
M docs/V52_REAL_ACCEPTANCE.md
A docs/V53_REAL_ACCEPTANCE.md
A docs/V53_UI_REVIEW.md
A docs/screenshots/v53/目录说明.md
A docs/screenshots/v53/favorite-folders-missing.png
A docs/screenshots/v53/favorite-folders.png
A docs/screenshots/v53/pocket-favorite-targets.png
A docs/screenshots/v53/quick-panel-favorites.png
M explorer.py
M favorite_folders_ui.py
M pet_window.py
M pocket_window.py
M quick_panel.py
M scripts/audit_release_docs.py
M scripts/build_release.ps1
A scripts/capture_v53_screenshots.py
M scripts/verify_release.ps1
M tests/smoke/test_favorite_folders_gui.py
A tests/smoke/test_pocket_favorites_multi.py
A tests/unit/test_audit_release_docs.py
M tests/unit/test_destinations.py
M tests/unit/test_explorer.py
```

## 6. 新增功能

- QuickPanel 快速固定当前 Explorer 路径、选择其他目录、前六项 elide 与查看全部。
- Pet 右键/托盘共享常用文件夹子菜单（最多 8 项）。
- 失效目录定位、解释与重新关联。

## 7. 修复 Bug

- 失效 favorite 左键无反馈；长名称挤坏窄面板；refresh 重复路径探测；坏 JSON 同内容备份重复增长；Pocket 多项操作引用容易映射错误；文档审计 A/M/D/R 不对账。

## 8. 删除/弃用

管理窗移除行内上下移动按钮，排序仍由“更多”菜单提供。未删除或启用 `ActiveExplorerWatcher`；仍 disabled。

## 9. 测试

| 命令 | 结果 | 耗时 | 状态 |
|---|---:|---:|---|
| `.venv\Scripts\python.exe -B -m pytest tests -q`（正式 build 内） | 将在正式 build 内运行 | 构建日志记录 | NOT TESTED |
| 定向收藏服务、Explorer、审计、Qt UI、Pocket 多选 | 53 passed | 2.75s | PASS |
| `scripts/capture_v53_screenshots.py` | 4 张有效 PNG | 运行结果见最终日志 | PASS |
| build + fresh `verify_release.ps1` | 运行结果见最终日志 | 运行结果见最终日志 | PASS |
| 文档审计 | 正式构建前预审与产物后严格审计尚未运行 | build 日志记录 | NOT TESTED |

## 10. 真实验收

- 4 张隔离 Qt Windows 平台控件渲染图：PASS（静态图已检查）；这不是用户屏幕截图，也不等价于人工视觉质量 PASS。
- QuickPanel `QDesktopServices.openUrl` 路径合同：PASS；真实 Explorer 打开：NOT TESTED。
- 当前 Explorer 固定 stub 合同：PASS；真实 Explorer 读取与固定：NOT TESTED。
- fresh release 解压启动：NOT TESTED（构建完成后运行 `verify_release.ps1`）。
- 真实 DPI、鼠标、网络盘拔插和人工桌面验收：NOT TESTED。
- `ActiveExplorerWatcher`：PASS，仍 disabled。

## 11. Release

Release built from Git HEAD: pending
Artifact ZIP SHA256: pending
Build time: 正式 build 完成后记录于 release manifest 与最终报告。

PowerShell 7 正式构建在 ZIP 创建后自动回填 Release Git HEAD 与 SHA256，再执行完整文档审计。

## 12. Remaining Known Issues

- 同步 `Path.is_dir()` 和系统文件夹图标查询遇到断开网络/移动盘仍可能等待系统 I/O；本轮避免重复探测但未做异步 worker。
- 真实 Explorer、显示器字体/DPI、鼠标体验与网络盘物理断开恢复均 NOT TESTED。
- favorite 数据大于 20 项时旧记录全部保留，新建在上限处禁用，不静默截断。

## 13. 本轮未完成项

真实 Explorer 打开与固定、人工屏幕/DPI/鼠标体验和实际网络盘断连仍待在真实桌面条件下验收；没有伪造 PASS。V5.1 未形成 release，不补录虚构版本。

## 14. Commit 列表

```text
b937a91 fix: stamp verified release identity into V5.3 summary
61567f8 feat: finish v5.3 favorite-folder workflows
```

## 15. 最终状态

PARTIAL（代码、自动化回归与截图已完成；正式 release/verify、最终 Git 审计与远端推送待完成。）
