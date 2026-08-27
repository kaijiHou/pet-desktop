# KNOWN_ISSUES.md — 已知问题登记

> 状态标记：🔴 阻塞 / 🟠 需在后续 Phase 解决 / 🟡 接受并记录

---

## KI-01 🟠 sprite sheet 与 animations.json 不在仓库

上游 .gitignore 排除了 `assets/clippy_sheet.png`、`assets/animations.json`、`assets/sprites/`、`assets/sounds/`，README 明确"角色素材自备"。当前 assets/ 只有一个 clippy.html。
**影响**：不补素材，任何渲染轨都显示不出角色。
**处置**：Phase 1 基线阶段解决（自备或程序化生成占位 sheet）；Phase 2 从 clippy.html 内嵌 ANIMS 导出 animations.json（43 组，格式与 README 定义一致）。

## KI-02 🟠 clippy.html 加载路径指向用户目录而非项目目录

`pet_window_web.py` L30：`ASSETS_DIR = CONFIG_DIR / "assets"`（即 `~/desktop-pet/assets/`）。原版必须手动把素材复制到用户目录才能渲染。
**处置**：PathManager 统一后，素材路径固定为项目内 `D:\pet-desktop\assets\`。

## KI-03 ✅ config 默认写 C 盘（Phase 17 已修复）

`config.py` L11：`CONFIG_DIR = Path.home() / "desktop-pet"`。
**处置**：Phase 17 由 PathManager 正式接管，开发态写项目 `data/`，冻结态写可执行文件旁 `data/`。

## KI-04 ✅ 上游脚本硬编码原作者路径（Phase 17 已清理）

`launch_mochi.bat` / `Mochi.vbs` / `add_to_startup.bat` / `pet_sprite.py __main__` 均含 `C:\Users\clara\...`。
**处置**：三个启动脚本已删除；pet_sprite 原生实现不含作者路径。

## KI-05 🟡 GitHub 直连失败

`git clone https://github.com/...` 在本机 443 超时。
**处置**：已用镜像 `https://ghfast.top/<github-url>` 克隆成功。后续 fetch/pull 同样走镜像。remote origin 目前指向镜像地址。

## KI-06 🟠 无依赖清单、版本未钉死

仓库没有 requirements.txt / pyproject.toml，仅 README 一行：`pip install PyQt5 PyQtWebEngine Pillow openai google-api-python-client pytz`。
**处置**：Phase 1 建立 requirements.txt 并记录实测可用版本；删除模块后同步裁剪。

## KI-07 ✅ .gitignore 忽略测试文件（Phase 2 已修复）

上游 `.gitignore` 含全局 `test_*.py`（无目录锚定），导致 tests/ 下的测试文件被忽略。Phase 2 经 `git check-ignore -v` 定位到 `.gitignore:24:test_*.py`，已改为目录锚定 `/test_*.py`（仅拦截根目录散落测试，放行 tests/），并验证 `git add -n tests/` 全部可入库。

## KI-08 🟡 Windows 文件事件的语义限制（预告，Phase 14 正式验证）

ReadDirectoryChangesW 只能报告"某路径发生 FILE_ACTION_REMOVED 等动作"，无法区分触发来源（Explorer 右键删除 / 命令行 del / 其他进程）。实现时将严格区分"确认事实"与"推断"，不为展示效果伪造事件来源（任务书 §31）。

## KI-09 🟡 PATH 中无真实 Python

系统 PATH 的 `python` 是 Microsoft Store 空壳，无 `py` launcher，无裸 pip。可用解释器：uv 管理的 cpython 3.11.15（D:\hermes-agent\python\）与 D:\anaconda（3.9.7，偏旧）。
**处置**：Phase 1 已用 uv 以 3.11.15 在 `D:\pet-desktop\.venv` 建虚拟环境，不新装 Python。

## KI-10 🟡 Baseline 只能使用 synthetic asset 验证渲染机制（KI-01 的 Phase 1 结论）

上游仓库缺少 README 要求的外部 sprite sheet（`clippy_sheet.png` 被 .gitignore 排除，且 Clippy 形象受微软版权保护、README 声明不可再分发），**真实原版角色视觉不可复现**。
**处置**：Phase 1 用 `scripts/gen_synthetic_assets.py` 生成 synthetic placeholder sheet（3348x3162，每帧带编号与几何标识，肉眼可辨切帧）部署到原代码固定的运行时路径 `~/desktop-pet/assets/`。所有"角色可见/动画切帧 PASS"结论**仅针对渲染机制**，不代表真实官方素材的视觉效果。性能数据同理：可用于衡量原架构（尤其 Chromium/WebEngine 开销），不代表真实 sprite 的最终渲染性能。

## KI-11 ✅ 上游 wheelEvent 滚轮缩放 TypeError（Phase 16 已修复）

`pet_window_web.py` L640：`self.web.setGeometry(10, 10, 124 * self._scale_val, 93 * self._scale_val)` —— `setFixedSize` 处已 `int()`，但 `setGeometry` 的两个尺寸参数是 float。`_scale_val` 步进 0.5，**任何一次滚轮缩放在 scale 为非整数时必然抛**：
```text
TypeError: setGeometry(...): argument 3 has unexpected type 'float'
```
异常发生在 `self._js(f"setScale(...)")` **之前**，因此：① 窗口固定尺寸更新成功、② webview 几何尺寸未更新、③ JS 缩放未下发 —— 每次滚轮后 webview 与窗口尺寸错位一层。smoke 实测 scale 3.5→4.0 时必现（见 docs/baseline/smoke_output.txt）。
**处置**：Phase 16 原生轨接管后不再向 Qt geometry 传 float；测试已改为普通 PASS 并验证 scale/窗口尺寸同步。

## KI-12 ✅ QWebEngine offscreen segfault（Phase 16 随 WebEngine 移除关闭）

`QWebEngineView.page()` 在 `QT_QPA_PLATFORM=offscreen` 下必现段错误（exit 139）。经 probe_offscreen1~10 逐步二分：崩溃点精确在 `web.page()` 访问本身（与 `setBackgroundColor` 无关）；`AA_ShareOpenGLContexts` + 软件 GL 标志均无效。根因：Chromium 内核需要真实 OpenGL context，offscreen 平台默认不提供。真实 `windows` 平台下构造→page()→正常退出全生命周期 exit 0。
**影响**：GUI 测试无法用 offscreen 隔离，只能在真实平台运行（构造但不 show，teardown 隐藏 tray）。
**处置**：Phase 16 删除 WebEngine/Chromium，GUI 套件恢复 Qt offscreen，问题不再适用。

## Phase 3 状态更新

- AI Chat/OpenAI 已按计划完整删除；未新增 Known Issue。
- KI-11 未顺手修复，仍由 strict xfail 固定；Phase 3 smoke 唯一 FAIL 仍为该问题。
- KI-12 不变：WebEngine 仍是当前渲染轨，因此 GUI 测试继续使用真实 Windows 平台。
- 旧 config 中可能保存的 OpenAI 凭据在下一次 `Config()` 加载时会被剔除并立即重写文件；测试已验证磁盘中不再保留旧值。

## Phase 4 状态更新

- Google Calendar/OAuth 已完整删除；未新增 Known Issue。
- 旧 config 的 `calendar_*` 键会自动清理。为避免未经授权删除用户数据，本阶段不删除用户目录中可能存在的 OAuth token/credentials 文件。
- KI-11 仍是唯一回归失败并继续由 strict xfail 固定；KI-12 不变，因为 WebEngine 仍为当前渲染轨。

## Phase 5 状态更新

- 固定间隔喝水提醒已被本地日期+时间提醒替代；旧配置的 `water_*` 键会自动清理。
- Reminder 存储损坏时安全回退为空，单条坏记录会跳过并写 warning；未新增阻塞问题。
- KI-11 仍是唯一 GUI 回归失败；KI-12 不变，WebEngine 尚未移除。

## Phase 6 状态更新

- Pocket 数据层只保存引用，remove/cleanup 不碰目标文件；未新增破坏性文件操作风险。
- 目标文件可能被外部改名、移动或删除；当前以 `exists=False` 如实标记，无法自动追踪新路径。这是引用模型的预期边界，Phase 14 文件事件只能提升实时性，不能保证跨卷追踪身份。
- KI-11、KI-12 状态不变；Phase 6 未触碰 GUI 渲染轨。

## Phase 7 状态更新

- Qt file URL 拖入文件/目录已实测；网页 URL 和不存在路径会拒绝。部分路径失败时其余有效项仍能加入。
- 原生备用渲染轨尚无独立 RECEIVE 状态，暂使用 alert fallback；Phase 15 统一事件到动画映射时处理。
- KI-11 仍是唯一回归失败；KI-12 不变。

## Phase 8 状态更新

- Pocket UI 的 Open/Explorer 定位依赖 Windows shell；自动化只覆盖调用边界，不在测试中真的启动外部窗口。完整人工验收放到 Phase 17。
- Remove from Pocket 与 Clean Missing 均只删除引用，确认文案明确原文件不受影响。
- KI-11、KI-12 状态不变。

## Phase 9 状态更新

- 标准 file URL + CopyAction 数据路径已自动化；真实拖到不同 Explorer/桌面目标的 Windows shell 行为留 Phase 17 人工验收。
- 当前列表为单选；底层 mime 构建已支持多选，是否开放多选属后续 UX 决策。
- KI-11、KI-12 状态不变。

## Phase 10 状态更新

- Copy/Move 默认自动编号，明确禁止静默覆盖；目录进入自身后代会失败并报告。
- 跨卷 move 由 shutil.move 退化为复制后删除，属于显式 Move To 操作的标准语义；自动测试仅覆盖同卷隔离目录，跨卷人工验收留 Phase 17。
- KI-11、KI-12 状态不变。

## Phase 11 状态更新

- Favorites 只允许添加当时存在的目录；之后失效会保留并标记 missing，避免静默丢失用户配置。
- 收藏移除只改 destinations.json，不删除目录。KI-11、KI-12 状态不变。

## Phase 12 状态更新

- Recents 只记录成功操作；最多 10 条，重复置顶。清空历史不影响 favorites 或磁盘。
- missing 最近目录会展示但禁止执行，等待用户清空或路径恢复。KI-11、KI-12 不变。

## Phase 13 状态更新

- Explorer 查询依赖 Windows Shell COM 可用以及当前前台窗口为普通文件系统 Explorer；搜索、Home 等虚拟位置可能无文件系统 Path，会如实返回不可用。
- 查询使用短生命周期隐藏 PowerShell，非轮询、非常驻；Phase 17 做真实前台窗口人工验收。KI-11、KI-12 不变。

## Phase 14 状态更新

- ReadDirectoryChangesW 只报告目录中发生的事实动作，不能判定由 Explorer、命令行或其他进程触发（KI-08）；实现不作来源推断。
- 当前只监听明确拖入 Pocket 的目录且不递归；文件条目不监听其整个父目录。KI-11、KI-12 不变。

## Phase 15 状态更新

- Windows watcher callback 已经 Qt signal 跨线程，不直接从 worker 修改 UI。
- 原生备用轨尚只消费 coarse state，完整 specific animation 接管列入 Phase 16。KI-11、KI-12 不变。

## Phase 16 状态更新

- KI-11 已修复；KI-12 随 WebEngine 删除关闭。正式套件 0 xfail。
- 仓库不分发 sprite sheet；无自备素材时显示原创中性占位。Phase 1 本机 synthetic sheet 仍只用于机制/性能验证，不提交。
- 帧缓存上限 96，idle 默认停帧；资源实测完整进程树为 1 个进程、avg RSS 78.7MB。

## Phase 17 状态更新

- KI-03 关闭：配置、Pocket、Reminder、Destinations 默认统一写项目/可执行文件旁 `data/`，不再隐式写 C 盘用户主目录。
- KI-04 关闭：三个硬编码 `C:\Users\clara` 的旧启动脚本已删除；原生 sprite 模块也无作者路径。
- KI-08 保持为已接受语义边界：真实 Win32 验收捕获五类文件事件，但仍不推断事件来源程序。
- 真实 Explorer 前台目录查询通过。跨窗口 Pocket 鼠标拖放已于 2026-08-13 使用 `scripts/manual_drag_acceptance.py` 完成人工闭环并 **PASS**：目标副本存在，源文件仍保留，符合 CopyAction 语义。

## Phase 18 状态更新

- Windows x64 one-folder ZIP 已构建并从全新解压副本启动通过；WebEngine/Chromium 文件数为 0。
- PyInstaller 报告的缺失项均为跨平台或可选模块；发行 EXE 黑盒启动与功能边界通过，未新增产品阻塞问题。
- Phase 17 的真实跨窗口鼠标拖放已人工 PASS；至此 Phase 18 发布门槛全部通过。

## V2 状态更新（ux-redesign-v2）

- **KI-01/KI-10 关闭**：不再要求自制 124×93 43 槽位 sprite sheet。新增 Single Image Mode：一张透明 PNG 即时成为桌宠；无图时显示程序绘制的原创默认伙伴（无版权角色）。Sprite Sheet Mode 保留兼容。
- **KI-12 确认消失**：Phase 16 删除 WebEngine 后，offscreen 平台不再 segfault，GUI 测试可安全用 offscreen。
- **KI-11 superseded by V2.2**：原 wheel 默认关闭/float geometry 问题已由原生整数 geometry 路径替代；当前默认 wheel 开启，Ctrl+wheel 强制缩放，回归测试已通过。
- **新增 KI-13（已接受）**：offscreen 平台不渲染 CJK 字体——widget.grab 截图中文空白。真实 GUI 用微软雅黑正常。仅影响离屏截图证据，不影响功能。
- **KI-14 superseded by V2.2**：ShellWatcher 已有真实隐藏窗口消息循环与 `SHChangeNotifyRegister`；仍不推断事件来源，rename 双 PIDL 语义继续保留为已知边界。

## Phase 17/18 历史保留（V2 继续有效）

- 配置/数据统一写 `data/`（D 盘项目旁），不再隐式写 C 盘。
- 旧 `C:\Users\clara` 硬编码启动脚本已删。
- 单进程、WebEngine=0、低资源基线在 V2 继续保持。

## V2.2 状态更新（2026-08-27）

- **KI-15**：源码层 drag enter/move/drop 已统一本地 URL + CopyAction 并加入诊断日志；真实 Explorer → 源码/EXE 的 OLE/UIPI 验收尚未完成，状态 `NOT TESTED`。
- **KI-16**：ShellWatcher 已改为真实 Desktop PIDL + SHCNRF NewDelivery 注册，正确使用 `hChange/dwProcessID` Lock 解包；注册 ID 非零及真实 SHChangeNotify 广播测试通过。普通 Explorer 删除的 release EXE 验收状态 `NOT TESTED`。
- **KI-17**：QuickPanel/PocketWindow 已通过 PetWindow `moveEvent` 实时跟随，live 定位不抢焦点并支持屏幕边界翻转；真人拖动验收状态 `NOT TESTED`。
- **KI-18**：wheel/Ctrl+wheel 与 50%~300% 设置 slider 均实时同步 Character、geometry、hitbox、badge、bubble anchor；Cancel 回滚、OK 持久化及上下限自动化通过；源码/EXE 肉眼缩放验收状态 `NOT TESTED`。

在 `V22_REAL_ACCEPTANCE.md` 的真实 Windows 清单完成前，不宣称 V2.2 四项交互门槛全部 PASS。

## V3 状态更新（2026-08-27）

- **KI-19（代码已修复，真机待验）**：气泡已由 visible alpha bbox 锚定并支持屏幕边缘翻转；独立 BubbleWindow 的真实桌面间距仍需用户手动确认。
- **KI-20（进行中）**：工资服务、工时日历、今日助手和隐私显示已接入；漏打卡一次性提示、修改下班时间和月度详情交互仍需补齐。
- **KI-21（待验）**：ShellWatcher/Explorer 的真实 create/delete/mkdir/rmdir 反馈不能由 offscreen 单测代替，V3 清单当前 `NOT TESTED`。
