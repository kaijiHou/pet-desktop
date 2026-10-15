# V5.8 Change Summary — 按参考图还原主题 UI（16 套主题）

## 1. 参考图从哪里来

用户提供压缩包 `pet-desktop-v58-theme-reference-pack.zip`（25 张参考图 + README + 还原需求 txt），
解包于 `%TEMP%\v58-ref`（临时，已按用户要求清理进回收站，图不入库）。全部 25 张图逐张查看，
PIL 中位切分量化提取每图主色（hex+占比）作为实现依据，完整映射见
`docs/V58_REFERENCE_MAPPING.md`（含每主题的参考图文件名、调色板速记、延展规则）。

## 2. 如何建立主题映射

- 图片文件名语义 + 提取调色板 + 逐张目检 → 16 套主题（可爱 8 + 炫酷 8）一一对应参考图；
- 产品内只用"可爱 / 炫酷"分类名（全程无"男生/女生"字样）；
- 原 5 套预设 id 全部保留（保护用户已存配置），4 套原色不变仅改名归类
  （sakura→樱花甜心、sky→晴空云朵、taro→月光薰衣草、mint→柠檬薄荷），
  "奶油黄"按参考包调整为"蜜桃奶茶"（焦糖色系）；
- 新增 11 套：garden/forest/berry_night（可爱，最后一套为暗色可爱）+
  cyber_night/deep_pulse/ember_tech/aurora_pulse/titanium/obsidian_gold/storm_volt/midnight_neon（炫酷，全暗色）。

## 3. ui_skin 架构扩展（复用，未造第二套）

- `PRESETS` 16 套，每套在 12 个核心色之外带风味键：category/dark、hero_top/hero_bottom
  （工资卡渐变）、primary_top/primary_bottom、glow（霓虹边）、ok/info/warn/danger（日历状态色）、
  chip（条目底）、deco（主题 emoji）；
- `palette()` 派生改为**明暗双向**：`_fit_text` 按背景亮度决定加深/提亮（原 `_darken_for_contrast`
  在深色卡上会把文字压成黑）；tint 系列基色 `tint_base` 亮色皮=白、暗色皮=卡色；
  主按钮色 `action_bg/action_text` 双向门禁（亮强调色如荧光绿/金配深色字，中调强调色配白字），
  全部预设过对比度 ≥4.5 验收（`test_v54_skin_contrast` 参数化 19 例）；
- `ui/modern/tokens.base_qss` 去亮色硬编码，改用 bridge 推送的 SURFACE/HOVER_BG/INPUT_BG/
  FOCUS_RING/ACTION_TEXT/SUCCESS 等 token —— 炫酷深色下对话框、输入框、下拉、tooltip 表面一致；
- 自定义皮肤 `build_custom_colors(accent, bg, dark=False)` 支持暗色自定义；持久化契约不变。

## 4. QuickPanel 如何按图还原

- 工资区改成参考图的 hero 卡：渐变底（hero_top→hero_bottom）+ 状态胶囊（section_bg chip）+
  19pt 大金额 + 右侧主题装饰 emoji（panelDecor，如 🌸🤖🌹）；
- 按钮体系分层：主=渐变胶囊（action 渐变+门禁文字色），次=chip 底胶囊，管理=小胶囊，＋=圆角方块；
- 分区去 1px 横线 → 留白 + 节头（emoji+粗体）+ 右侧"管理/＋"，口袋与提醒条目改 chip 行
  （panelRow），首条提醒有内容时为 chip、空时为弱化文案；
- 头部主题 emoji 随皮肤切换；文件夹双列 chip 卡（圆角 10、hover/focus 亮环）；
- 结构性红线未动：无 paintEvent（纯 QLabel/QSS）、无外层 QScrollArea、5 分钟工资自刷新保留。

## 5. 工作日历如何按图还原

- 月历格全部走调色板：休息日=danger 洗色、调休/小周=info 洗色、请假=warn 洗色、
  非本月=bg 弱化、今天=accent 描边环、选中=accent 洗色环、已记录=ok 色圆点；
  日期数字颜色随状态（休息红/调休蓝），与参考图的"底色+角标"语法一致；
- 详情区按钮主次：下班打卡=主色钮（PrimaryButton，文案不变——测试钉了纯文本）、
  选时间…/添加备注/保存按月覆盖=次钮、应用日期状态=主色钮；
- 摘要 5 卡加 emoji 图标（📅✅⏱🍚💰），月份标题 17px/800；
- 图例改彩色圆点行（ok/info/danger/muted），底部说明与警告横幅不变；
- 对话框表面经 tokens 深色化，深色主题下输入框/下拉/按钮一致。

## 6. 哪些主题有单独日历图，哪些是延展

- 炫酷 8 套两页均有对应参考图，按图各自还原；
- 可爱仅樱花甜心有单独日历总样图；其余 7 套日历按延展规则实现：
  **同主题 QuickPanel 的色彩/按钮/装饰气质 + 可爱日历总样图的页面结构**（规则写入 MAPPING 文档 §A）。

## 7. 主题切换页如何改进

- 新增 `ui_theme_picker.py` 主题中心：🌸 可爱 / ⚡ 炫酷（+🧵 自定义，仅当存在自定义皮肤）页签；
- 每套主题一张预览卡（该皮肤真实调色板渲染的迷你 mockup：hero 渐变+金额+两枚胶囊钮），
  当前主题带"当前 ✓"徽标与强调色描边，点卡片即时切换并持久化；
- 入口：右键菜单 🎨 主题 → "🎨 主题中心…"（原快捷子菜单与自定义编辑器保留）；
- 零 paintEvent（IME 红线），卡片 132×128 定尺寸防裁切。

## 8. 测试与截图

- 全量 `.venv\Scripts\python.exe -m pytest tests -q` → **476 passed, 1 skipped**（其中 V5.8 新增
  8 项：16 预设分类/风味键/切换持久化/面板渲染/日历渲染/主题中心/红线/格子换肤；复跑一次全绿，
  首轮 v49 gallery 计时器测试为负载抖动、单跑即过）；
- 截图 `docs/screenshots/v58/`：16 主题 QuickPanel+日历（32 张）+ before-after（sakura）+
  theme-picker-cute/cool + DPI 125%/150%（QT_SCALE_FACTOR + grab() 实像素渲染，无裁切）；
  全程 `scripts/capture_v58_themes.py` 沙盒（config/reminders/pocket/destinations/wage/ui_skins
  六重定向），未触碰真实 data/。

## 9. 仍存在的差异

见 `docs/V58_REFERENCE_COMPARISON.md` 与 `docs/KNOWN_ISSUES.md` V5.8 节。要点：参考图中的
插画（人物/机器人/场景）以主题 emoji 代替；预览卡金额文字在 132px 卡内被压缩显示；
"国庆节·休息"等长状态词在 72px 格内换行；主按钮文字色由对比度门禁决定（部分主题为深色字，
与参考图的白字略有出入）。
