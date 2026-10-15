# pet-desktop V5.10 玫瑰月夜可爱风首批素材接入报告

Final HEAD: 见 git log（本报告所在 commit）　Baseline HEAD: `37633bc`（V5.8 收尾）

## 本次只做了什么

- **只处理 4 张素材**：`玫瑰花饰的粉色笔记本小助手.png`、`浪漫玫瑰月夜阳台书桌.png`、
  `梦幻玫瑰情书飘带横幅.png`、`樱粉玫瑰梦幻界面图标组.png`（来源：会话图片缓存，经验证为
  原尺寸原始 RGBA，字节级拷贝入库，未重压缩）。
- **只做 rose_moon 这一套主题**（玫瑰月夜，归入"可爱"分类，暗色），不扩其他 15 套。
- **只先落地 QuickPanel**（日历页/其他弹层未接素材，保持 V5.8 状态）。
- 顺带修复一个真实 bug：对话气泡白底硬编码 + 深色皮肤浅色字 → 看不清（见下）。

## 4 张素材（assets/ui_themes/rose_moon/）

| 文件 | 内容 | 接入位置 |
|---|---|---|
| `avatar.png`（1254×1254） | 玫瑰花饰+粉色笔记本的角色插画 | QuickPanel 顶部头像（32×32 显示，源尺寸不变） |
| `hero_scene.png`（1672×941） | 玫瑰月夜阳台书桌场景 | "今日已赚"主卡背景插画层（QLabel 底层+scrim 渐变+真实控件在上） |
| `pocket_banner.png`（2172×724） | 玫瑰情书礼盒飘带横幅 | "打开文件口袋"横幅底层（真实按钮铺满可点击） |
| `icon_sheet.png`（2172×724） | 8 枚同风格图标母板 | 切分为 `icons/{close,plus,folder,pocket,bell,calendar,clock,rose}.png` |

## 固定尺寸（后续补素材沿用）

- avatar 类：**1254×1254**；hero 场景类：**1672×941**；横幅类（含图标组母板）：**2172×724**。
- 程序内按显示尺寸缩放，源文件不动。

## 接入情况

- **顶部头像**：✅ rose_moon 激活时 `_mark` 用 avatar 图（无素材主题回退 emoji）。
- **主收入卡**：✅ hero_scene 作为 `wageCard` 背景层（`QLabel setScaledContents` +
  `QSizePolicy.Ignored`，布局不给它撑高度），上覆主题色 scrim 渐变（左重右轻）保证
  状态胶囊/金额/明细可读；文字与金额仍是真实控件渲染。
- **文件口袋横幅**：✅ pocket_banner 为 `pocketBanner` 底层，`pocketBannerBtn` 透明铺满、
  整条可点击；无素材主题回退原渐变胶囊钮。
- **图标**：✅ 8 枚切图全部接入——关闭×、＋（两处）、文件夹节头+收藏 chip、口袋节头+
  横幅钮、铃铛节头+我的提醒、日历钮、时钟钮、玫瑰角饰；替换掉了此前的 emoji 与系统
  黄色文件夹图标（QFileIconProvider 仅作无素材主题的兜底）。

## QuickPanel 结果

- 已实现：插画头像 + hero 场景工资卡 + 插画口袋横幅 + 全套母板风格图标 +
  玫瑰月夜调色板（深玫瑰紫/酒红/暖粉金，`ui_skin.PRESETS["rose_moon"]`，category=cute/dark）。
- 仍差：日历页（WorkCalendarDialog）未接该套素材；提醒横幅/设置页横幅等待补素材后按
  2172×724 体系接入；hero 文字区左侧在极亮处对比度仍可再调。
- **是否已摆脱"只换颜色"**：是——头像/场景/横幅三层插画 + 切图图标都是本套素材渲染，
  截图见 `docs/screenshots/v510/rose-moon-quickpanel-rose_moon.png`（320×564）与
  `rose-moon-dpi125-*.png`（400×683，125% 无裁切）、`rose-moon-theme-picker.png`
  （主题中心里 rose_moon 预览卡直接用 hero 缩略图，当前 ✓ 徽标）。

## 顺带修复（真实 bug）

- `bubble_window.py` 对话气泡底色此前硬编码近白 + 文字色跟随皮肤：深色皮肤下浅粉字打在
  白底上看不清（用户截图反馈"检测到xxx文件"）。现改为底色/边框/文字全部取自
  `ui_skin.palette()`——深色皮出深底浅字、浅色皮出白底深字；零 paintEvent 架构未动
  （QImage 离屏渲染，IME 安全）。测试：暗皮中心亮度 <120、亮皮 >200（`test_v58_themes`）。

## 测试

- 全量 `.venv\Scripts\python.exe -m pytest tests -q` → **486 passed, 1 skipped**（含新增
  `tests/smoke/test_v510_rose_moon.py` 8 项：素材尺寸/RGBA 校验、8 图标切图非空、rose_moon
  注册、面板四素材渲染、按钮真实可点击+真实数据显示、切换持久化、无素材主题回退不变、
  零 paintEvent 红线；及气泡跟肤测试）。
- 点击：日历/口袋按钮 click→stub 记录断言 ✓；数据显示：口袋条目/提醒为真实文本控件 ✓。
- 主题切换：rose_moon 持久化到 config ✓；切换到无素材主题回退 V5.8 样式 ✓。
- DPI：125% 实像素截图 400×683 无裁切 ✓（100% 主图同目录）。
- 数据隔离：全部测试走 conftest `theme_env` 六重定向沙盒，未触碰真实 data/。

## 文档

- 本报告（V510_ROSE_MOON_THEME_SUMMARY.md）；DEVELOPMENT_LOG 2026-10-15 节追加；
  KNOWN_ISSUES V5.10 节追加。V5.8 的 16 套主题与文档保持不变，产品内现在共 17 套。

## Remaining Known Issues

- 玫瑰月夜仅 QuickPanel 接了素材；日历页/其他弹层仍是该主题的纯调色板样式（素材到位后按
  同管线接入）。
- hero 卡文字压图处的对比度已用 scrim 保证 ≥4.5 门禁，但底部明细行压在插画亮部时视觉上
  仍偏忙，如需更干净可在素材侧提供"左侧留白版"场景图（同尺寸 1672×941）。
- 图标组切图为位图（母板即位图），如需 SVG 需重绘；当前 18-20px 显示清晰。
- EXE 级真机视觉/DPI 验收延续项目边界，仍 NOT TESTED。

## 以后给图能不能直接加（用户问题，答：能）

- **同风格补图**：按固定尺寸（头像 1254²、场景 1672×941、横幅 2172×724）生成后发我，直接
  丢进 `assets/ui_themes/rose_moon/` 对应文件名（avatar/hero_scene/pocket_banner/icon_sheet）
  即生效，代码零改动；新图标放入 icon_sheet 后我重新切图。
- **全新一套风格**：发 1-4 张同规格素材 + 想要的底色氛围（或我来提色），我注册新主题 id
  + 调色板即可，QuickPanel 自动吃到（缺哪类素材就自动回退该类的 emoji/渐变兜底）。
- **新槽位**（如提醒横幅、日历页眉、设置页横幅）：每类新槽位需要少量面板代码，素材到位
  即可按 2172×724 体系逐个接入。
