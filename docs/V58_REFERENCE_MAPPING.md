# V5.8 参考图 → 主题映射（REFERENCE MAPPING）

来源：用户提供的 `pet-desktop-v58-theme-reference-pack.zip`（25 张图 + README + 还原需求），
解包于 `%TEMP%\v58-ref`（包本身不入库）。调色板由 PIL 中位切分量化提取（前 8 主色 + 占比），
全部 25 张图已逐张查看。本文档是 V5.8 实现的视觉规范与映射依据。

## A. 主题映射（16 套 = 可爱 8 + 炫酷 8）

产品内只用"可爱 / 炫酷"两个分类名（禁"男生/女生"字样）。主题 id 沿用 ui_skin 现有
5 个预设 id（保护用户已保存的选择），新增 11 个。

### 可爱（cute）

| # | 主题名 | id | QuickPanel 参考图 | 日历参考图 | 主色速记（accent / bg / card） |
|---|--------|----|-------------------|-----------|------------------------------|
| 01 | 樱花甜心 | `sakura`（沿用） | cute_quickpanel/樱花甜心小迪助手界面.png | cute_calendar/a_soft_pastel_pink_cream_kawaii_ui_design_screensh.png | #F27BA7 / #FFF6FA / #FFFFFF |
| 02 | 奶油花园 | `garden`（新） | cute_quickpanel/小迪助手_温馨工作桌面面板.png | 暂无单独日历图，按可爱日历总样图延展 | #6E9165 / #FEFAF2 / #FFFFFF（奶油底+鼠尾草绿） |
| 03 | 月光薰衣草 | `taro`（沿用） | cute_quickpanel/梦幻紫罗兰小迪助手面板.png | 同上延展 | #9B7EDE / #F8F5FD / #FFFFFF |
| 04 | 晴空云朵 | `sky`（沿用） | cute_quickpanel/梦幻云朵小迪助手界面.png | 同上延展 | #4A90D9 / #F3F8FD / #FFFFFF |
| 05 | 蜜桃奶茶 | `cream`（沿用改名） | cute_quickpanel/暖心奶茶风小迪助手界面.png | 同上延展 | #C98A4B / #FFFBF2 / #FFFFFF（奶茶焦糖） |
| 06 | 森系童话 | `forest`（新） | cute_quickpanel/梦幻森林小迪助手界面.png | 同上延展 | #4E7A46 / #FCF6EA / #FFFFFF（深林绿+象牙） |
| 07 | 柠檬薄荷 | `mint`（沿用） | cute_quickpanel/柠檬薄荷小迪助手界面.png | 同上延展 | #34B78F / #F2FBF7 / #FFFFFF |
| 08 | 玫瑰莓夜 | `berry_night`（新，暗色可爱） | cute_quickpanel/玫瑰莓夜_小迪助手仪表盘.png | 同上延展 | #E88A96 / #3B212F / #52283A（深莓底+玫瑰粉） |

### 炫酷（cool，全部深色）

| # | 主题名 | id | QuickPanel 参考图 | 日历参考图 | 主色速记（accent / bg / card / glow） |
|---|--------|----|-------------------|-----------|--------------------------------------|
| 01 | 暗夜赛博 | `cyber_night`（新） | cool_quickpanel/赛博霓虹小迪助手界面.png | cool_calendar/小迪助手未来感工作日历.png | #3FA9F5 / #0C1625 / #12203A / 青 |
| 02 | 深海脉冲 | `deep_pulse`（新） | cool_quickpanel/深海霓虹小迪助手界面.png | cool_calendar/霓虹海境工作日历.png | #2E9BE6 / #01204B / #062F65 / 海蓝 |
| 03 | 赤焰机能 | `ember_tech`（新） | cool_quickpanel/赤黑未来工作助手仪表盘.png | cool_calendar/赛博红黑风工作日历界面.png | #E23B3B / #0F0E11 / #1A1417 / 红 |
| 04 | 极光脉冲 | `aurora_pulse`（新） | cool_quickpanel/极光脉冲智能助手界面.png | cool_calendar/霓虹极光工作日历界面.png | #4F8DF9 / #0A122A / #14224A / 极光蓝 |
| 05 | 钛灰锋芒 | `titanium`（新） | cool_quickpanel/小迪助手_钛金属工作台.png | cool_calendar/小迪助手_未来工作日历.png | #7FA8D9 / #171D25 / #232C39 / 钢蓝 |
| 06 | 黑曜流光 | `obsidian_gold`（新） | cool_quickpanel/黑金奢华小迪助手界面.png | cool_calendar/黑金霓虹工作日历仪表盘.png | #E8C268 / #090909 / #1C1713 / 金 |
| 07 | 风暴电光 | `storm_volt`（新） | cool_quickpanel/霓虹风小迪助手工作台.png | cool_calendar/霓虹工作日历界面.png | #C8F542 / #06111B / #102131 / 荧光绿 |
| 08 | 午夜霓虹 | `midnight_neon`（新） | cool_quickpanel/霓虹赛博小迪助手界面.png | cool_calendar/霓虹赛博朋克工作日历界面.png | #7C5CFF / #050719 / #131040 / 品红-青 |

### 延展规则（写进实现，源于需求 §八）

- 有对应页面参考图 → 优先按图还原。
- 可爱 02~08 无单独日历图 → 日历继承**同主题 QuickPanel 的色彩/按钮语法/装饰气质**，
  页面结构按**可爱日历总样图**延展（同主题面板图 = 第一参考，同类别日历总样图 = 第二参考）。
- 炫酷 8 套两页都有对应图，按图各自还原。

## B. 当前代码相关文件（实现前审计结论）

- `ui_skin.py` — 12 键调色板 + 5 预设 + 自定义持久化（data/ui_skins.json）+ `_legacy_bridge`
  推送到 `theme.*` / `ui.modern.tokens.*`；`palette()` 派生 tint/action/focus。**派生全是亮色
  假设**（`_darken_for_contrast`、白底 tint），深色主题会把文字压成黑 → 需改明暗双向。
- `theme.py` — 全局 QSS（app_qss），颜色来自被 bridge 的模块全局。
- `ui/modern/tokens.py` — modern 对话框 QSS；`ui/modern/dialog.py` ModernDialog（无 paintEvent，
  半透明靠 #modernCard QSS）；`cards.py` StatCard/SectionTitle；`buttons.py`/`inputs.py`。
- `quick_panel.py` — 320px 面板：头部（🎀+标题+×）、工资卡（状态/金额/明细/设置钮）、双按钮、
  常用文件夹（管理+＋+双列）、文件口袋、下个提醒、我的提醒；`_panel_qss(p)` 从皮肤取色；
  无外层滚动（别加回）；5 分钟自刷新。
- `wage/ui_calendar.py` — WorkCalendarDialog（ModernDialog，每次打开新构造）= 月份导航 +
  5 张 StatCard + ModernMonthCalendar（42 格 CalendarDayCell）+ 右侧详情卡（打卡/选时间/备注/
  状态下拉）+ 规则卡 + 图例。`CalendarDayCell._apply_style` 现在硬编码亮色。
- 主题选择入口：pet_window `_add_skin_menu`（右键 🎨 皮肤子菜单，checkable）+ ui_skin_dialog
  （自定义编辑器）。
- 测试契约：`tests/unit/test_v54_skin_contrast.py`（参数化跑遍 PRESETS：对比度≥4.5、tint 公式）、
  `tests/smoke/test_v54_skin_system.py`（bridge/持久化/面板重漆）、`test_v48_ui_contracts.py`
  与 `test_v31_wage_ui.py`（record_out_button 纯文本"下班打卡/补卡下班"，不可加图标后缀）。

## C. 现状差异（参考图 vs 现有实现）

只差颜色的地方（换 token 即可）：
- 工资卡底色、金额色、按钮填充、菜单/边框 —— 现有 token 全覆盖。

结构/形态差异（必须重做，仅换色不算还原）：
1. **工资卡**：参考图是"状态胶囊 → 特大金额 → 两行明细 + 右侧装饰母题"的渐变 hero 卡，
   圆角更大；现状是平铺 section_bg 直角层次，无渐变无装饰。
2. **按钮体系**：参考图主按钮=大胶囊（渐变+左侧图标圆片+右侧"›"），次按钮=浅底胶囊；
   现状 panelPrimary/panelSecondary 是小圆角矩形，视觉无差异层级。
3. **分区语言**：参考图区块间用留白+小节头（emoji+粗体+右侧 管理 胶囊/圆形＋），**无横线**；
   现状有 1px 分隔线（去线，留白替代）。
4. **文件夹条目**：参考图双列胶囊卡（emoji 图标+名称+›）；现状 QToolButton 接近，但底色/
   圆角/悬停按图调整；炫酷风条目是深色玻璃卡。
5. **提醒条目**：参考图是"色点+时间+内容+›"的整行胶囊；现状裸文本 QLabel。
6. **头部**：参考图标题旁有主题小emoji、×是圆钮；现状接近，按主题换装饰 emoji。
7. **日历月历格**：参考图格内=大号日期数字+状态词/角标，节假日有底色洗色+小标签，今天=高亮
   描边环，选中=实底环；现状格子太小(72×64)、状态词小、无角标语法 → 重排格内层级。
8. **日历摘要卡**：参考图带 emoji 图标方块+主次（"预计本月收入"在可爱图里同级，炫酷图里
   也是并列5卡）→ StatCard 加图标+数字层级微调。
9. **日历详情卡**：参考图"下班打卡"是主色钮、"选时间…"次钮，键值行带小图标 → 按钮主次调整
   （文案不动，测试钉了纯文本）。
10. **图例**：参考图底部彩色圆点+词 → 图例改彩色圆点行。
11. **圆角/间距语言**：可爱=大圆角(16-22px)+舒展；炫酷=深色玻璃卡+1px 霓虹描边+发光强调色。

禁止事项自查：不整页贴图、真实控件渲染、不动 data/、不改 tests 钉死的文案、复用 ui_skin
单一架构（扩展 token，不建第二套 ThemeManager）。
