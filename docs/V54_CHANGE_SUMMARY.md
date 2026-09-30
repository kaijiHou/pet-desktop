# V5.4 Change Summary

## 1. Baseline

Baseline HEAD: `3349d7137e5e31b894ab1dd31d656d4728cc1939`
Summary scope implementation HEAD: `f0aeebbe8b2e1a3d3a2bd11a10e6ab43c60e5f70`
Branch: `master`
Date: `2026-09-30`
Environment: Windows 10.0.19045 x64 / Python 3.11.15 (uv cpython) / PyQt5 5.15.11 / Pillow
GUI automation availability: 真实 Windows Qt 平台渲染与进程级探针可用；未使用 computer-use 操控用户桌面。

## 2. 本轮目标

1. 按公司大小周安排日历（上一会话交付，本轮收口入库）。
2. 界面可读性修复：工资卡饱和粉、次要文字对比度不足（用户直接反馈）。
3. 皮肤系统：预设 + 自定义 + 右键即时切换（用户要求"风格可以右键切换"）。
4. 动画播放速度可调（用户提问"播放速度能调吗"）。
5. 全局交互卡顿根治（用户反馈"右键每一个点击都很卡"）。
6. 发布准备：LICENSE、版本号、启动脚本、发行包。

## 3. 修改前问题

- V54-01：公司大小周周六被默认规则判为休息日；无循环起点与标签。（上一会话发现）
- V54-02：工资卡呈大块饱和粉，浅色文字不可读；`_tint` 混色比例语义写反（应为 12% 主题色 + 白底）。（用户截图）
- V54-03：QuickPanel 收藏排版挤压分隔线、控件状态反馈弱。（上一会话发现）
- V54-04：`DynamicPackRenderer._compute_global_bbox` 用 QImage.pixelColor 逐像素扫整张 1536×1872 图，455 万次 sip 调用，每次渲染器加载 ~4.3s——设置页两个预览即 8.7s，所有带预览的窗口秒开变秒卡。（cProfile 实证）
- V54-05：文件口袋每次打开同步 spawn PowerShell 解析资源管理器路径，~0.6s 阻塞。（cProfile 实证）
- V54-06：首次点击任一功能需现场导入重量级模块（~1s 冷启动）。
- V54-07：动画速度写死（idle 200ms/帧、其余 150ms/帧），不可调。
- V54-08：界面风格写死，用户要求可切换、可自定义。
- V54-09：仓库无 LICENSE，无法合规公开发布；版本号停在 V5.3。

## 4. 本轮实际修改

### V54-01 大小周日历（上一会话完成，本轮入库）
- 修改内容：2026-10-12 起大/小周周六交替；官方节假日与手工 override 仍优先。
- 修改文件：`wage/calendar_service.py`、`wage/ui_calendar.py`、`docs/WAGE_RULES.md`、`docs/WAGE_CALENDAR_ARCHITECTURE.md`。
- 根因/实现：固定循环起始周 + 周型判定，并入 status_for 与 detail 渲染。

### V54-02 皮肤系统
- 修改内容：`ui_skin.py` —— 5 套预设（樱花粉/奶油黄/薄荷绿/天空蓝/香芋紫）+ 用户自定义（存 data/ui_skins.json，只需选强调色+底色，其余自动调配）；右键"🎨 皮肤"子菜单即时切换并持久化 config.ui_skin；QuickPanel/theme/tokens 全链路从调色板取色。
- 修改文件：`ui_skin.py`(A)、`ui_skin_dialog.py`(A)、`pet_window.py`、`quick_panel.py`、`theme.py`、`ui/modern/tokens.py`、`ui/modern/dialog.py`、`config.py`。
- 修改前：风格硬编码。修改后：切换即时生效、重启保持。
- 根因：无集中配色源。实现：palette() 派生色（tint/对比度自动加深）+ skinChanged 信号 + _legacy_bridge 推平 theme/tokens 全局。

### V54-03 对比度修复（上一会话公式修正 + 本轮验收闭环）
- 修改内容：tint_light 等=12% 主题色+白；新增 text_soft/_darken_for_contrast 次要文字加深链；5 套皮肤真实渲染 WCAG 对比度采样全部 ≥4.5（门槛 3.0），截图入库 docs/screenshots/v54/。
- 修改文件：`ui_skin.py`、`quick_panel.py`、`tests/unit/test_v54_skin_contrast.py`(A)、`docs/screenshots/v54/*`(A)。

### V54-04 渲染器 bbox 性能
- 修改内容：`_compute_global_bbox` 由逐像素 pixelColor 改为 numpy 单次向量化（帧即格片，整图并集等价）。
- 修改文件：`character_v4/renderer.py`。
- 修改前：设置页构造 4382ms。修改后：441ms。根因：455 万次跨语言调用。实现：np.nonzero(alpha>10) 一次取 min/max。

### V54-05 资源管理器路径解析缓存 + 异步
- 修改内容：ExplorerService 增加 20s TTL 解析缓存与 resolve_is_fresh 探针；PocketWindow 快照过期时走后台线程，窗口先开、路径后填（signal 回 UI）。
- 修改文件：`explorer.py`、`pocket_window.py`。
- 修改前：文件口袋 1259ms。修改后：首次 104ms、TTL 内 11ms。

### V54-06 冷启动预载
- 修改内容：启动 4s 后空闲预载 wage.ui_*/gallery/favorite/ui_skin_dialog 等模块。
- 修改文件：`pet_window.py`。
- 修改前：首次点击功能卡 ~1s。修改后：预载后首次即常速。

### V54-07 动画速度
- 修改内容：AnimationPlayer.set_speed（运行中生效不重帧）；DynamicPackRenderer.set_speed 委托；设置页"动画速度"下拉（慢 0.6/正常 1.0/快 1.5/很快 2.0）持久化 config.animation_speed；单图语义动画与 sheet 轨同步倍率；倍率钳制 0.25~4.0。
- 修改文件：`character_v4/animation.py`、`character_v4/renderer.py`、`pet_window.py`、`config.py`、`tests/smoke/test_v54_animation_speed.py`(A)。

### V54-08 发布准备
- 修改内容：MIT LICENSE（含 holiday-cn MIT 归属声明）；版本号升 V5.4（app_version + build 脚本）；桌面启动/停止脚本实测（防重复启动守卫）。
- 修改文件：`LICENSE`(A)、`app_version.py`、`scripts/build_release.ps1`。

### V54-09 测试确定性
- 修改内容：两个依赖真实时钟/日期的历史测试改确定性（固定 now_provider；用日历服务找真工作日，避开 9/25 中秋类节假日）；三处 emoji 改名后的陈旧精确断言改包含式；v43 启动测试与用户真实配置隔离。
- 修改文件：`tests/smoke/test_v2_1_correctness.py`、`tests/smoke/test_v3_assistant_ui.py`、`tests/smoke/test_favorite_folders_gui.py`、`tests/smoke/test_v43_startup.py`。

### V54-10 可爱风界面（上一会话完成，本轮入库）
- 修改内容：菜单/面板 emoji 化、粉系 QMenu、QuickPanel"小迪助手"层级重排。
- 修改文件：`pet_window.py`、`quick_panel.py`、`theme.py`、`ui/modern/tokens.py`、`scripts/capture_v54_quick_panel.py`(A)、`docs/screenshots/v54/*`(A)。

## 5. 文件级变化

`git diff --name-status 3349d71..HEAD`（本摘要文件自身由审计器豁免）：

```text
A LICENSE
M app_version.py
M character_v4/animation.py
M character_v4/renderer.py
M config.py
M docs/ARCHITECTURE.md
M docs/DEVELOPMENT_LOG.md
A docs/HANDOFF_V54_SKIN_CONTRAST_2026-09-28.md
M docs/TEST_REPORT.md
A docs/V54_REAL_ACCEPTANCE.md
M docs/WAGE_CALENDAR_ARCHITECTURE.md
M docs/WAGE_RULES.md
A docs/screenshots/v54/README.md
A docs/screenshots/v54/skin-cream-panel.png
A docs/screenshots/v54/skin-mint-panel.png
A docs/screenshots/v54/skin-sakura-panel.png
A docs/screenshots/v54/skin-sky-panel.png
A docs/screenshots/v54/skin-taro-panel.png
A docs/screenshots/v54/v54-calendar-success-feedback-polished.png
A docs/screenshots/v54/v54-calendar-success-feedback.png
A docs/screenshots/v54/v54-quick-panel-redesign-final.png
A docs/screenshots/v54/v54-quick-panel-redesign.png
A docs/screenshots/v54/v54-quick-panel-three-favorites.png
A docs/screenshots/v54/v54-skin-contrast-shown-widget-sakura-full.png
A docs/screenshots/v54/v54-skin-contrast-shown-widget-sakura.png
A docs/screenshots/v54/v54-work-calendar-october.png
A docs/screenshots/v54/目录说明.md
M explorer.py
M favorite_folders_ui.py
M pet_window.py
M pocket_window.py
M quick_panel.py
M scripts/build_release.ps1
A scripts/align_custom_character_sheets.py
A scripts/capture_v54_quick_panel.py
M tests/smoke/test_favorite_folders_gui.py
M tests/smoke/test_v2_1_correctness.py
M tests/smoke/test_v3_assistant_ui.py
M tests/smoke/test_v43_startup.py
M tests/smoke/test_v48_ui_contracts.py
A tests/smoke/test_v54_animation_speed.py
A tests/smoke/test_v54_skin_system.py
M tests/unit/test_v47_calendar_contract.py
A tests/unit/test_v54_skin_contrast.py
M theme.py
M ui/modern/dialog.py
M ui/modern/tokens.py
A ui_skin.py
A ui_skin_dialog.py
M wage/calendar_service.py
M wage/ui_calendar.py
```

`character_v4/renderer.py`、`character_v4/animation.py` 为纯性能/速度接口改动，不改变任何视觉与角色素材；`explorer.py`、`pocket_window.py` 为异步化改造，语义不变。

## 6. 新增功能

- 皮肤系统（5 预设 + 自定义 + 右键切换 + 持久化）。
- 动画速度设置（慢/正常/快/很快，实时生效）。
- 大小周日历循环（上一会话交付）。
- 桌面启动/停止脚本（防重复启动）。

## 7. 修复 Bug

- 渲染器 bbox 逐像素扫描致所有带预览窗口卡 4~8s（V54-04）。
- 资源管理器路径同步解析阻塞口袋打开 0.6s（V54-05）。
- 工资卡饱和粉不可读（V54-02/03，用户截图实证）。
- 两个历史测试的时钟/日期偶发失败（V54-09）。

## 8. 删除/弃用

无。

## 9. 测试

| 命令 | 结果 | 耗时 | 状态 |
|---|---:|---:|---|
| `pytest tests -q`（发布前全量） | **433 passed** | 61.9s | PASS |
| `pytest tests/unit/test_v54_skin_contrast.py tests/smoke/test_v54_skin_system.py -q` | 15 passed | 0.7s | PASS |
| `pytest tests/smoke/test_v54_animation_speed.py -q` | 4 passed | 6.3s | PASS |
| `pytest tests/smoke/test_pocket_window_gui.py tests/unit/test_explorer.py -q` | 16 passed | 0.7s | PASS |
| 真实平台耗时探针（右键菜单/设置/口袋/日历/工资设置） | 全部 <500ms | — | PASS |
| 5 皮肤 WCAG 对比度采样 | 4.5~6.5（门槛 3.0） | — | PASS |

## 10. 真实验收

- 真实 Windows Qt 平台渲染（非 offscreen）：PASS（皮肤 5 张面板截图 + 对比度采样入库 docs/screenshots/v54/）。
- 进程级耗时探针（cProfile + perf_counter）：PASS（数据见第 4 节各项"修改前/后"）。
- 桌面启动器（启动/停止/防重复）：PASS（双击路径实测）。
- 真实鼠标/DPI/Explorer GUI 操作：NOT TESTED（未使用 computer-use）。
- 用户角色素材（棕发眼镜女孩三包）切割与替换：由用户确认过的前序轮次完成，本轮未触碰。

## 11. Release

- Final repository HEAD: 本文件所在 commit（docs B，仅文档）。
Release built from Git HEAD: 90e6e8b4649203bff628ca2053a5efca6a6fc19b
Artifact ZIP SHA256: 9acf59731d354ef7bb45ebdc3d601d8cca7e93fc6b5c2c12b063a0fbd214bf39
- Build time: pending（构建完成后回填）。
- 版本：V5.4；Git commit SHA 与 Artifact ZIP SHA256 分开标注，禁止混称。

## 12. Remaining Known Issues

- 真实鼠标手感 / 系统 DPI / Explorer GUI 验收未做（无 computer-use）。
- 收入提示 QComboBox 原生箭头感、Gallery 单条目留白（P2 遗留观察）。
- ActiveExplorerWatcher 保持 disabled（历史 segfault）。

## 13. 本轮未完成项

无（NOT TESTED 项为环境约束下的诚实记录）。

## 14. Commit 列表

```
f0aeebb feat: v5.4 — skins, animation speed, lag fixes and release prep
```

## 15. 最终状态

DONE（代码/测试/文档/发布准备全部完成；Release 字段为 pending，待本 commit 基础上构建后由 docs commit B 回填真实值）
