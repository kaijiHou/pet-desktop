# CHANGES — pet-desktop 变更总账（唯一记录文档）

> 规矩（用户 2026-10-27 定）：**所有改动记录只追加到本文件**，按日期倒序、按 commit 分条、
> 写到文件级明细。不再为单个任务新建 Vxx 文档（用户任务书里明确点名要的交付文档除外）。
> DEVELOPMENT_LOG.md 继续作为叙事与踩坑记录，两处同步追加但不新建。

---

## 2026-10-27（本轮会话，commit 4de6cdb → b1c3036）

### 修复类
- **工作日历弹窗风暴（用户报告"点一次弹十几个白框"）**，两个根因、两次修复：
  - `963b23a`：`ui/modern/dialog.py` ModernDialog 的 subtitle_label / max_button
    **先 setVisible 后 addWidget** → 无父控件以顶层窗口闪现。改为先挂父再显示。
  - `971ab34`：真凶（真机追踪 48 次闪现实证）——`wage/ui_calendar.py` 日历格"●"打卡点
    在**悬空布局**（addLayout 之前）上 addWidget，未挂父即 setVisible；每条打卡记录闪一窗
    （15 天记录×2 遍刷新）。改为创建时挂父 `QLabel("●", self)`。
  - 配套：`toplevel_trace.py`（新）+ `pet_window.py` 挂钩 + `PET_AUTO_OPEN_CALENDAR=1`
    自动开日历，顶层窗口 Show 全量写 `logs/toplevel_trace.log`；回归测试
    `test_dialog_construction_spawns_no_toplevel_windows`。
- **日历背景与桌面脱节**：`wage/ui_calendar.py` 卡片改半透明（`QColor(card).setAlpha(200)`
  HexArgb 覆写 modernCard），合成验证图 `docs/screenshots/v516/`。
- **状态胶囊外边框**：`quick_panel.py` panelStatus 去 border。
- **日历"小周上班"底色发白**：状态洗色 0.12 → 0.20（休息/调休/请假三态）。
- **海盐珍珠 hero 卡"中间发白"**：scrim 按明暗分级——暗皮 (210/115/25)、亮皮 (80/45/10)，
  `ui_skin.resolve_palette`。
- 顺带：日历"排班规则/图例"两处旧大小周文案修正（754c4a2）；resolve_palette 重复 tint 块清理。

### 功能类
- **大小周相位修正**（4de6cdb，用户 10-15 口径）：锚点周 10-12 = 小周（10/17 班、10/24 休、
  10/31 班），10 月应出勤 19 → 20 天、日薪 700.00；`calendar_service._work_cycle_info`
  翻转奇偶，测试/文档同步。
- **主题系统大改**：
  - `ade3f19`：ui_skin 预设 5 → 16（可爱8/炫酷8）+ 明暗双向对比度派生 + 渐变/发光/状态色/
    chip/deco token；`tokens.base_qss` 深色化。
  - `cbe7ea0` QuickPanel、`e93e918` 工作日历按参考图重做（渐变 hero 卡/胶囊按钮/chip 行/
    状态洗色格/彩点图例）。
  - `c7ac513` 主题中心 `ui_theme_picker.py`（预览卡网格+✓当前徽标）。
  - `30f1881` **回滚**：用户裁定 16 套"只是换颜色"全删，经典五套恢复原名原色，
    主题中心去页签重做 3 列大卡。
  - 素材主题管线落地并接入 **10 套**（`assets/ui_themes/<id>/` 四件套：avatar 1254² /
    hero_scene 1672×941 / pocket_banner 2172×724 / 图标组）：`03da099` rose_moon 玫瑰月夜（暗）、
    `152e179` mint_pearl 薄荷珍珠（亮）、`d832f25` cyber_night 暗夜赛博（暗）/ spring_study
    春日花语（亮）/ aurora_cyber 极光冰晶（暗）/ sea_salt_pearl 海盐珍珠梦境（亮）、
    `b8988d1` autumn_lantern 枫叶暖灯 / snowy_starlight 雪夜星灯 / sakura_lantern 樱花灯影 /
    moonlit_coast 月夜海城（后四包自带切图，按名映射拷入）。
  - 当前产品内 **15 套主题**：经典五套（原名原色）+ 10 套素材主题。
- **点击空白处自动关闭页面**（b1c3036，用户需求）：ModernDialog 新增
  `changeEvent(ActivationChange)` 失活即 reject；激活门闩 + `activeWindow` 为空才关，
  堆叠子弹窗/点桌宠不误关；`close_on_blur` 可按页关闭。
- 顺带：对话气泡跟随皮肤（`5f33969`，后由并行会话升级为用户自选样式 bubble_style）；
  排班规则/图例彩色圆点化。

### 并行会话（同仓另一 ZCode 会话的活，未提交部分留在工作区）
- hand-in-hand-duo 双人形象安装脚本、bubble_style 自选气泡、日历面板重塑（状态色边框/
  滚动容器/加班点）、设置页滚动+置顶、提醒日历等 —— 其提交时机由它自行决定；
  971ab34 因快照自洽带入了 ui_calendar/pet_window/cards/tokens/menu/__init__ 的当前态。

### 测试
- 全量走势：457 → 563 passed（含并行会话新增测试）；本轮会话新增：v58 主题契约、
  v510/v511/v512-513/v514-518 素材主题参数化、气泡跟肤、弹窗风暴回归、失活关闭。
- 遗留红点：并行会话半成品 `test_character_gallery_layout` 2 项失败（非本会话范围）。

## 2026-10-15（上一轮，commit 至 37633bc）

- 大小周口径与主题大改的前置版本，明细见上方 2026-10-27 分条（同一会话连续工作），
  历史叙事见 DEVELOPMENT_LOG.md 2026-10-15 各节。

## 2026-10-27（续2，commit 至本次）

### 面板点侧边自动关闭（用户需求）
- 新增 `blur_watch.py` `ClickOutsideWatch`：面板是 WA_ShowWithoutActivating 免激活窗口，
  Qt 收不到落在桌面/其他应用的点击 → 用 WinAPI 轮询左键，**按下→松开边沿**落在保留区外
  且光标下无本进程控件（widgetAt is None）才触发。点桌宠/我们自己的其他面板/对话框不会误关。
- 接入三面板：`quick_panel.py`（保留区=自身+桌宠）、`pocket_window.py`、`wage/ui_today.py`
  （保留区=自身）；各自 show 时启动、hideEvent 停止。单测 `tests/unit/test_blur_watch.py`
  3 项（外点触发一次/内点不触发/自家控件上不触发）。

### 提醒面板：可编辑 + 焕新（用户报告"加了的提醒改不了，面板丑"）
- 根因：编辑功能一直存在但**只藏在右键菜单里**，无任何可见入口；且列表对话框是未主题化的
  裸 QDialog。
- `reminder_ui.py`：ReminderListDialog 迁移到 ModernDialog（主题卡+失活自动关）；
  新增可见"**编辑**"按钮（选中即启用）+ **双击条目直接编辑**（复用新建对话框预填，保存=
  更新）；条目高度 36px、分组头 30px。`ui/modern/tokens.py` base_qss 新增 QListWidget 全局
  样式（圆角/选中色/hover），提醒列表与全项目列表统一。
- 截图 docs/screenshots/v518/reminder-panel-moonlit.png（月夜海城主题）。

### 测试
- 全量 **565 passed, 1 skipped**；唯一红点仍是并行会话半成品 test_character_gallery_layout
  2 项（非本会话范围）。修复 blur_watch 导入错误（QCursor 在 QtGui 不在 QtCore，曾致 65 失败）。

## 2026-10-30（用户报告"宠物不出来 + kanban.db-wal 气泡弹了一中午"）

### 宠物隐形（根因在配置，非渲染）
- 真实配置：`pet_scale=1.0`（原为 3）+ `pet_x=2944`（超出主屏宽，宠物在屏幕外/不在线的副屏上）。
  渲染器离屏试渲染正常（双人包 V2 1536×2288 合法，idle 帧非空 alpha 与旧包相当）。
- 修复：config 恢复 `pet_scale=3.0`、`pet_x=1400`、`pet_y=300`；原 config 已备份到
  `.tmp/config-backup-20261030-140502.json`。

### kanban.db-wal 气泡刷屏（`pet_window._emit_file_feedback`）
- 根因：看板应用持续写 SQLite 预写日志（kanban.db-wal/-shm），每次变更都走到气泡层；
  未知动作还触发 `semantic=None` 警告刷屏（app.log 累计 493 条）。
- 修复三件：①噪音后缀（.db-wal/.db-shm/.db-journal/.tmp/.crdownload/.part）静默跳过；
  ②同路径同动作 10 秒节流；③未知动作给安全语义 RENAME_FILE（None 警告清零）。
