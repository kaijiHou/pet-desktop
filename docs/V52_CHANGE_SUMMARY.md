# V5.2 Change Summary

> 依据 `docs/CHANGE_SUMMARY_TEMPLATE.md`；本轮持续更新。Git commit SHA 与 Artifact ZIP SHA256 分开记录。

## 1. Baseline

Baseline HEAD: `1f73669ec879f024e288f9463e688d8780b127f7`
Branch: `master`
Date: `2026-09-24`
Environment: Windows 10.0.19045 x64 / Python 3.11.15 / PyQt5 5.15.11 / Qt 5.15.2
GUI automation availability: available；遵循用户明确要求，不使用电脑控制工具，也未操作屏幕或鼠标。

## 2. 本轮目标

1. 将既有 `DestinationService` favorite 正式呈现为中文“常用文件夹”，不增加第二套服务或数据模型。
2. 让 PetWindow、QuickPanel、Pocket 和管理窗共享一个服务实例，并维持 Recent 独立语义。
3. 完善路径失效恢复、排序、持久化与 Copy/Move 安全边界，补全自动化合同和版本文档。

## 3. 修改前问题

- V52-01：favorite 只有底层 add/remove 与 Pocket 右键菜单，没有独立管理窗、自定义名或顺序；根因是 `FavoriteDestination` 只有 id/path/name/added_at。证据：基线 `destinations.py`；本轮服务测试覆盖升级合同。
- V52-02：QuickPanel 没有常用目录入口；Pocket 可自行创建另一份 DestinationService，界面没有常用/最近的分区目标区。根因是服务实例未由 PetWindow统一持有并注入。证据：基线 `quick_panel.py` / `pocket_window.py`。
- V52-03：对源文件当前父目录执行 Copy/Move 会走重名自动编号，生成非预期副本。证据：基线 `file_ops.py`；新增同目录 skip 回归。
- V52-04：目的地 JSON 读取失败时静默回退为空，没有 warning 或原文备份。证据：基线 `DestinationService._load()`。
- V52-05：根驱动器默认显示名没有盘符友好化；测试临时目录实际位于 `tests/.tmp`，不符合仓库根 `.tmp` 隔离要求。证据：新加 root-name 与 test-environment 合同。

## 4. 本轮实际修改

### V52-01 DestinationService 与持久化
- 修改内容：favorite 加 order、改名、改路径、全量严格重排、最多新增 20 条；无 version 的 v1 按原数组次序读取，保存为 version 2；根目录默认名显示如 `D盘`。
- 修改文件：`destinations.py`、`tests/unit/test_destinations.py`。
- 修改前：favorite 无自定义名和稳定顺序操作；存储无 schema version。
- 修改后：同一个 `data/destinations.json` 保存 v2；路径更新保留 id/name/order；无效路径记录不被删除。
- 根因：现有 favorite 模型不足以承载正式管理 UX。
- 实现：使用 dataclass replace 更新不可变条目；原子 temp→replace 写入不变。

### V52-02 管理窗口与 QuickPanel
- 修改内容：新增 Modern `FavoriteFoldersDialog`，覆盖添加、重复提示、改名、路径修复、复制路径、上下排序、安全移除与失效状态；QuickPanel 展示最多 6 条、空状态和查看全部入口。
- 修改文件：`favorite_folders_ui.py`、`quick_panel.py`、`tests/smoke/test_favorite_folders_gui.py`。
- 修改前：无一等常用文件夹 UI。
- 修改后：QuickPanel 通过 `QDesktopServices.openUrl` 打开有效目录；打开不记 Recent，右键保留失效目录的修复操作。
- 根因：favorite 只作为底层目的地菜单存在。
- 实现：复用 `ui/modern` tokens、Card、ModernDialog、ModernTextInputDialog 与 InlineBanner。

### V52-03 PetWindow / Pocket 共享目的地
- 修改内容：PetWindow 创建唯一 DestinationService，传给 QuickPanel、PocketWindow 和管理窗；Pocket 增加常用/最近/当前 Explorer 目标区，成功操作刷新 recent；成功 Move 更新 Pocket 引用。
- 修改文件：`pet_window.py`、`pocket_window.py`、相关 smoke 测试。
- 修改前：生产链路没有共享服务实例，Pocket 没有清楚分离的目标区。
- 修改后：管理变更直接刷新已打开的 UI；所有 copy/move 仍走 FileOperationService。
- 根因：目的地服务实例创建与界面未集中协调。
- 实现：PetWindow 直接信号刷新，不增加全局事件总线。

### V52-04 文件操作与测试隔离
- 修改内容：源目录与目标目录相同的 Copy/Move 明确返回 skipped；修正 pytest 根路径，所有测试数据落在仓库根 `.tmp/tests/`。
- 修改文件：`file_ops.py`、`tests/conftest.py`、`tests/unit/test_file_ops.py`、`tests/unit/test_test_environment.py`。
- 修改前：同目录操作可能触发自动改名产生副本；夹具路径实际在 `tests/.tmp`。
- 修改后：no-op 不写磁盘；正式测试根为 `D:\pet-desktop\.tmp\tests\`。
- 根因：缺少 same-directory 分支；根目录取值少一级父目录。
- 实现：执行文件操作前比较 resolved `source.parent` 和 `destination`。

### V52-05 损坏数据、版本标识与文档审计
- 修改内容：损坏 JSON warning + 时间戳原文备份；版本显示和 release manifest 升为 V5.2；新增发布文档审计脚本。
- 修改文件：`destinations.py`、`app_version.py`、`scripts/build_release.ps1`、`scripts/audit_release_docs.py`。
- 修改前：损坏数据静默清空；release identity 为 V5.0；没有 V5.2 文档 completeness audit。
- 修改后：原始坏文件不覆写，manifest 区分 git_sha 和 zip_sha256，审计器检查 15 节和必须文件。
- 根因：容错与发布材料缺少可追踪信息。
- 实现：备份使用 `xb` 唯一新文件；build_info 无 BOM 写入；审计输出 `Missing=0`。

## 5. 文件级变化

基线：`1f73669ec879f024e288f9463e688d8780b127f7`。相对于基线的最终 `git diff --name-status <BASELINE>..HEAD`：

```text
M app_version.py
M destinations.py
A docs/ARCHITECTURE.md
M docs/DEVELOPMENT_LOG.md
A docs/FAVORITE_FOLDERS.md
M docs/KNOWN_ISSUES.md
M docs/TEST_REPORT.md
A docs/V52_CHANGE_SUMMARY.md
A docs/V52_REAL_ACCEPTANCE.md
A favorite_folders_ui.py
M file_ops.py
M pet_window.py
M pocket_window.py
M quick_panel.py
A scripts/audit_release_docs.py
M scripts/build_release.ps1
A scripts/release_artifacts.py
M scripts/verify_release.ps1
M tests/conftest.py
A tests/smoke/test_favorite_folders_gui.py
M tests/smoke/test_pocket_window_gui.py
M tests/unit/test_destinations.py
M tests/unit/test_file_ops.py
A tests/unit/test_release_artifacts.py
M tests/unit/test_test_environment.py
```

文档文件：架构/开发日志/已知问题/测试报告分别记录子系统、实现过程、限制和测试证据；新增使用指南、真实验收记录及本变更摘要。代码文件用途逐项见 §4；测试覆盖服务兼容与持久化、UI 合同、文件操作安全、发布包校验。

## 6. 新增功能

- 常用文件夹显示名、路径修复、排序与安全移除；QuickPanel 快捷打开。
- Pocket 的常用、最近与当前 Explorer 三类 Copy/Move 目标。
- version 2 持久化、v1 兼容、损坏源文件备份与发布文档审计。

## 7. 修复 Bug

- 同目录 Copy/Move 以前会被重名策略改成额外副本；现明确跳过。
- 损坏 `destinations.json` 不再静默丢弃诊断信息或被覆盖；会 warning 并保留时间戳备份。
- pytest 临时根从错误的 `tests/.tmp` 修正为仓库根 `.tmp/tests`。

## 8. 删除/弃用

- 无业务功能删除。`ActiveExplorerWatcher` 未改动，继续 disabled。
- 未加入第二 favorite service、拖拽排序、智能排序或 AI 推荐。

## 9. 测试

| 命令 | 结果 | 耗时 |
|---|---|---|
| `.venv\Scripts\python.exe -B -m pytest tests -q`（build_release.ps1 clean build 内执行） | **390 passed** | **270.36s / PASS** |
| `.venv\Scripts\python.exe -B -m pytest tests/unit/test_destinations.py tests/unit/test_file_ops.py tests/smoke/test_favorite_folders_gui.py tests/smoke/test_pocket_window_gui.py -q` | **49 passed** | **1.52s / PASS** |
| `.venv\Scripts\python.exe -B scripts/audit_release_docs.py` | **Missing=0** | **0.108s / PASS**（最终文档补齐后复验） |
| `pwsh -NoProfile -ExecutionPolicy Bypass -File scripts/build_release.ps1` | PyInstaller clean build + 上述 full suite；V5.2 ZIP 46,827,176 bytes | **约 5 分钟 / PASS** |
| `pwsh -NoProfile -ExecutionPolicy Bypass -File scripts/verify_release.ps1` | Fresh extract、启动、身份日志、目录与 WebEngine 黑盒检查全通过 | **9.56s / PASS** |

## 10. 真实验收

| 项 | 状态 |
|---|---|
| 服务/UI 合同与隔离 Copy/Move | PASS（见上述测试） |
| QuickPanel 传给 `QDesktopServices.openUrl` 的目录参数 | PASS（mock 调用合同） |
| 真实 Explorer 打开、人工截图审查、真实鼠标/DPI/网络盘拔插 | NOT TESTED（未进行桌面控制，详见 `docs/V52_REAL_ACCEPTANCE.md`） |
| Fresh EXE 启动/黑盒检查 | PASS（running/responding、animation catalog、user assets、V5.2 build identity log 均 PASS；WebEngine 文件 0） |

## 11. Release

- Final repository HEAD: 此 Change Summary 所在文档提交（精确 HEAD 在最终交付报告中记录；不在提交内容中递归写入自身 SHA）。
- Release built from Git HEAD: **172272b75bdadf02331805e310b0520e4e85022b**。
- Artifact ZIP SHA256: **76f269deded01038f4079fd08573b29d5294789013ed58fdaf421b45e7048f58**。
- Build time: `2026-09-24T10:42:50.5382453+08:00`；manifest 与 zip 校验一致。
- Artifact: `release/DesktopPet-windows-x64.zip`（46,827,176 bytes），format `windows-x64-one-folder`。

## 12. Remaining Known Issues

- 真实 Explorer 打开、真实屏幕视觉/鼠标/DPI/网络盘断连行为均 NOT TESTED。
- 已有 favorites 超过 20 条时保留全部旧数据；新增被禁用，不静默截断。
- 离线网络/移动盘路径检查依赖同步 `Path.is_dir()` 与平台图标提供器，慢盘可能等待系统 I/O；列为后续 P1 异步优化。
- `ActiveExplorerWatcher` 继续 disabled。

## 13. 本轮未完成项

- 真实 Windows Explorer/视觉/鼠标/DPI/网络盘手工验收未执行；没有生成或伪造截图。
- 真实 Explorer 打开、屏幕视觉/鼠标/DPI/网络盘拔插人工验收仍待用户手动完成；本轮依用户要求未操作桌面。

## 14. Commit 列表

`git log --oneline 1f73669ec879f024e288f9463e688d8780b127f7..HEAD`（代码 commit；本 Change Summary 文档 commit 随后补录）：

```text
172272b feat: productize shared favorite folders
```

## 15. 最终状态

DONE（代码、自动化全回归、fresh release 黑盒验证、文档审计均通过；真实 Windows Explorer/视觉/鼠标/DPI/网络盘人工验收明确保留为 NOT TESTED，详见 §10 与验收记录）。
