# V4.9 Real Windows Acceptance

状态只允许：PASS / FAIL / NOT TESTED / BLOCKED。
本轮约束：用户明确禁止 Computer Use，因此一切需要真实鼠标/屏幕的项如实记 NOT TESTED；
离屏/进程级/数据契约的自动化只作为行为证据，不冒充视觉验收。

## 环境记录（任务书 §2）

| 项 | 值 |
|---|---|
| V49_BASELINE_HEAD | `0e9394509d26339967c70641525c9421309170b7`（v4.8 finish modern ui and preview consistency） |
| Final HEAD | 见 DEVELOPMENT_LOG 本轮条目 |
| Build | `scripts/build_release.ps1`（clean build/dist/release），manifest built_at `2026-09-08T17:24:43+08:00` |
| ZIP SHA256 | 首轮 `851a843c…`；**最终 candidate `692f6facda8801abe0e9a9903ca7121830997811ca434a1d7da64e71a42c6b75`**（审计修复后复建，verify 全 PASS） |
| EXE（验收用） | `.tmp\tests\phase18-extracted-e0da4568…\DesktopPet\DesktopPet.exe`（verify_release.ps1 全新解压副本，非开发目录 build） |
| Config path | 解压副本旁 `data\config.json`（frozen 态 PathManager） |
| verify_release | running=true responding=true process_count=1 animation_catalog=true log_created=true webengine_files=0 |

## Fresh EXE 启动与 10 分钟运行（PASS）

- 启动日志确认：`mode=dynamic_pack`、`Atlas loaded: spritesheet.webp (1536×1872)`、9 组动画全提取、`Dynamic renderer loaded: 小幽灵`。
- RSS：起点 79.9MB → 5min 68.2MB → 10min 36.2MB（工作集被系统回收，无增长趋势）。
- CPU：10 分钟累计 7.3s（≈1% 单核，idle 动画 200ms/帧）。
- 进程数全程 1；期间无 crash、无 Paint error 刷屏。
- 结束方式：taskkill（验收脚本管理）。

## 真机截图（NOT TESTED — 无电脑控制）

| 截图 | 状态 | 用户操作 |
|---|---|---|
| v49-settings.png | NOT TESTED | Settings 窗口 |
| v49-wage-settings.png | NOT TESTED | 工资与工作时间 |
| v49-calendar-september.png | NOT TESTED | 工作日历 2026-09 |
| v49-calendar-october.png | NOT TESTED | 切 2026-10 |
| v49-character-gallery.png | NOT TESTED | 管理角色 |
| v49-character-consistency.png | NOT TESTED | 桌宠+Settings 同屏 |
| v49-calendar-resized-large.png | NOT TESTED | 拖大日历 |
| v49-calendar-resized-small.png | NOT TESTED | 缩到最小 |

截好放入 `D:\pet-desktop\.tmp\v49-acceptance\screenshots\` 后按 §“截图审查流程”逐张回填。

## 数据契约（PASS — 自动化证据，非视觉）

| 项 | 结果 |
|---|---|
| 2026-09 应出勤 | 22 天（workday_count(2026,9)） |
| 2026-10 应出勤 | 18 天 |
| 9/20 国庆补班 | adjusted_workday |
| 9/25~27 中秋 | rest |
| 10/1~7 国庆 | rest |
| 10/10 国庆补班 | adjusted_workday |
| 日薪 9 月（月薪 11200） | 509.09 = 11200/22 |
| 日薪 10 月 | 622.22 = 11200/18 |
| fallback 年份文案 | "该年份尚无内置法定节假日数据，当前仅按周一至周五估算。"（ui_calendar.py:181） |
| 数据源文案 | "数据源：holiday-cn / 国务院"（无 raw URL） |

## 本轮审计修复（PASS + 回归测试）

| 项 | 修复 | 测试 |
|---|---|---|
| item 55 角色不存在 fallback | `selected_character_id="missing_pet"` 启动时回退内置小幽灵、日志记录 requested/fallback、effective id 持久化 | tests/smoke/test_v49_contracts.py::test_stale_character_id_falls_back_to_builtin_ghost |
| item 36 工时日历→工作日历 | QuickPanel 按钮改名；全仓用户可见字符串 0 残留 | test_quick_panel_uses_work_calendar_naming |
| item 17/58 预览 timer 泄漏 | （既有逐次 stop+disconnect+deleteLater 链）加 20 次重载契约：动画 timer 数不增长 | test_gallery_switch_20x_no_timer_leak |

## 契约复核 PASS（代码级）

- 英文按钮：Save/Cancel/OK/Delete/Import/Reset/Use 零残留（应用自有 UI 全中文）。
- 隐私遮罩：Wage Settings 隐私勾选 → 月工资显示 `••••••`（ui_settings.py `_apply_privacy`）。
- 单图 portable：config 存相对名 → 按 DATA_DIR / DATA_DIR/character_images / assets 顺序解析（test_single_image_import_is_portable、test_character_controller_reads_portable_image_path）。
- 内联编辑器：日历详情"记录下班/添加备注"为右栏内联按钮+输入，无 QInputDialog/QMessageBox。
- 窗口单例：Settings/Calendar 均为模态 exec_()，打开期间不可能重复开第二个；Gallery 是 Settings 子窗口。

## 回归（PASS）

- Reminder/Pocket/Shell/integration 定向套件：39 passed。
- 工资全量（含 25h 阶梯、餐补、漏打卡、法定日历）：55 passed。
- Full suite：361 passed（V4.8 基线 358 + 本轮 3 个新契约）。
- Explorer 真实 RMDIR：NOT TESTED（无电脑控制；ShellWatcher 回归套件覆盖消息链）。

## 性能/泄漏契约（PASS — 行为级）

- EXE 10 分钟：RSS/CPU 如上，无泄漏。
- 窗口/预览泄漏：test_gallery_switch_20x_no_timer_leak（20 次重载后动画 timer 数不增长）。
- 20 次开关 Settings/Calendar 的真实手感与 DPI：NOT TESTED（模态单例在代码层防重复窗口）。

## DPI / resize 手感 / 颜色对比度

NOT TESTED（需真实屏幕交互）。等待用户截图后按 §五/§十二/§十三/§十四/§四十六 清单逐项回填。

## 截图审查流程（用户提供截图后）

1. 每张截图对照任务书对应章节的检查点逐条核对；
2. 发现问题 → 登记 KNOWN_ISSUES → 最小修复 + contract test → fresh rebuild → 回填该截图项；
3. 全部 PASS 才允许把对应 NOT TESTED 改 PASS；绝不以自动化代替视觉结论。
