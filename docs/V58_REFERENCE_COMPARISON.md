# V5.8 参考图 ↔ 程序截图 对照（REFERENCE COMPARISON）

对照方法：每主题渲染 QuickPanel（320×571 逻辑像素）与工作日历（980×892），
与压缩包参考图逐项比对布局语言、卡片、按钮、装饰、文本层级。
截图在 `docs/screenshots/v58/`；参考图文件名见 `docs/V58_REFERENCE_MAPPING.md`。

## 通用对照（全部 16 套）

| 参考图视觉点 | 程序落点 | 还原情况 |
|---|---|---|
| 渐变 hero 工资卡（状态胶囊+大金额+明细） | wageCard qlineargradient + panelStatus 胶囊 + panelAmount 19pt | ✅ 结构一致 |
| 卡片右侧装饰插画 | panelDecor 主题 emoji（每主题 deco 键） | ⚠️ 以 emoji 代替插画 |
| 主按钮=大胶囊、次按钮=浅底胶囊、层级分明 | panelPrimary 渐变胶囊 / panelSecondary chip 胶囊 | ✅（文字色按对比度门禁，个别主题深色字） |
| 分区间留白+emoji 节头+管理胶囊+圆形＋ | 去横线、panelSectionTitle+panelManager/panelIconButton | ✅ |
| 双列文件夹 chip 卡+名称+› | QToolButton chip 网格 | ✅ |
| 提醒=色点+时间+内容胶囊行 | panelRow chip 行 | ⚠️ 色点未单独渲染（时间前缀代替） |
| 无外层滚动、底部轻入口"我的提醒" | 保留原结构 | ✅ |
| 真实控件渲染（非贴图） | 全部 QLabel/QSS/QPushButton | ✅ |

## 工作日历对照

| 参考图视觉点 | 程序落点 | 还原情况 |
|---|---|---|
| 月份导航+排班规则/上月/下月/今天 | 原结构+17px/800 月份标题 | ✅ |
| 5 张摘要卡（emoji 图标+数字层级） | StatCard 标题加 emoji | ✅ |
| 月历格：状态底色洗色+状态词+今天环+已记录点 | CalendarDayCell 全调色板化（danger/info/warn 洗色、accent 环、ok 点） | ✅ |
| 右侧详情：键值+主色打卡钮+次钮+备注+状态下拉+应用钮 | 原结构+Primary/Secondary 分层 | ✅ |
| 彩色圆点图例 | legend 富文本彩点 | ✅ |
| 深色主题可读性 | tokens 深色化+明暗双向对比度门禁 ≥4.5 | ✅（测试覆盖） |

## 逐主题速记（截图文件名 ↔ 参考图）

- sakura ↔ 樱花甜心小迪助手界面 / a_soft_pastel_pink_cream…（粉洗色 ✓）
- garden ↔ 小迪助手_温馨工作桌面面板（奶油底+鼠尾草绿 ✓）
- taro ↔ 梦幻紫罗兰小迪助手面板（薰衣草紫 ✓）
- sky ↔ 梦幻云朵小迪助手界面（天蓝 ✓）
- cream ↔ 暖心奶茶风小迪助手界面（奶茶焦糖 ✓）
- forest ↔ 梦幻森林小迪助手界面（深林绿 ✓）
- mint ↔ 柠檬薄荷小迪助手界面（薄荷绿 ✓）
- berry_night ↔ 玫瑰莓夜_小迪助手仪表盘（暗莓底+玫瑰粉 ✓）
- cyber_night ↔ 赛博霓虹 / 小迪助手未来感工作日历（深蓝+青 ✓）
- deep_pulse ↔ 深海霓虹 / 霓虹海境（海蓝 ✓）
- ember_tech ↔ 赤黑未来 / 赛博红黑风（红黑 ✓）
- aurora_pulse ↔ 极光脉冲 / 霓虹极光（极光蓝 ✓）
- titanium ↔ 钛金属 / 小迪助手_未来工作日历（钢蓝 ✓）
- obsidian_gold ↔ 黑金奢华 / 黑金霓虹（黑金 ✓）
- storm_volt ↔ 霓虹风 / 霓虹工作日历（荧光绿 ✓）
- midnight_neon ↔ 霓虹赛博 / 霓虹赛博朋克（靛紫霓虹 ✓）

## 仍有差异（汇总）

1. 插画级装饰（人物/机器人/场景图）以主题 emoji 代替——程序禁止整页贴图，属预期取舍；
2. 主题中心预览卡 132px 内金额文字被视觉压缩（"今日已赚 ¥75…"），完整金额在真实面板可见；
3. 长状态词（"国庆节·休息"）在 72px 格内换行；参考图格子更宽；
4. 部分亮强调色主题（风暴电光/黑曜流光）主按钮为深色文字（对比度门禁），参考图为白字；
5. 参考图的赛博发光/光斑纹理无法用 QSS 表达，以强调色+渐变近似；
6. 可爱 7 套日历为"面板图+总样图"延展结果（无单独参考图，见 MAPPING §A 规则）。
