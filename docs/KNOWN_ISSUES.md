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

## KI-03 🟠 config 默认写 C 盘

`config.py` L11：`CONFIG_DIR = Path.home() / "desktop-pet"`。
**处置**：Phase 2 起由 PathManager 接管，配置写 `D:\pet-desktop\config\`。

## KI-04 🟡 上游脚本硬编码原作者路径

`launch_mochi.bat` / `Mochi.vbs` / `add_to_startup.bat` / `pet_sprite.py __main__` 均含 `C:\Users\clara\...`。
**处置**：三个启动脚本随 Phase 3/4 清理删除；pet_sprite.py 的 `__main__` 块改造或删除。

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

## KI-11 🔴 上游 wheelEvent 滚轮缩放必现 TypeError（Phase 1 实测发现）

`pet_window_web.py` L640：`self.web.setGeometry(10, 10, 124 * self._scale_val, 93 * self._scale_val)` —— `setFixedSize` 处已 `int()`，但 `setGeometry` 的两个尺寸参数是 float。`_scale_val` 步进 0.5，**任何一次滚轮缩放在 scale 为非整数时必然抛**：
```text
TypeError: setGeometry(...): argument 3 has unexpected type 'float'
```
异常发生在 `self._js(f"setScale(...)")` **之前**，因此：① 窗口固定尺寸更新成功、② webview 几何尺寸未更新、③ JS 缩放未下发 —— 每次滚轮后 webview 与窗口尺寸错位一层。smoke 实测 scale 3.5→4.0 时必现（见 docs/baseline/smoke_output.txt）。
**处置**：Phase 1 按任务约束不修（保持原版可测量基线）。Phase 2 已自动化复现：`tests/smoke/test_ki11_wheel_zoom.py`（strict xfail，稳定 XFAIL，89 passed + 1 xfailed 套件的一部分）；修复后将 XPASS 失败强制移除标记。Phase 2 起接管渲染轨时顺带消除；若提前需要人工体验，一行 `int()` 修复即可（待批准后执行）。

## KI-12 🟡 QWebEngine 在 offscreen 平台 segfault（Phase 2 实测发现）

`QWebEngineView.page()` 在 `QT_QPA_PLATFORM=offscreen` 下必现段错误（exit 139）。经 probe_offscreen1~10 逐步二分：崩溃点精确在 `web.page()` 访问本身（与 `setBackgroundColor` 无关）；`AA_ShareOpenGLContexts` + 软件 GL 标志均无效。根因：Chromium 内核需要真实 OpenGL context，offscreen 平台默认不提供。真实 `windows` 平台下构造→page()→正常退出全生命周期 exit 0。
**影响**：GUI 测试无法用 offscreen 隔离，只能在真实平台运行（构造但不 show，teardown 隐藏 tray）。
**处置**：tests/conftest.py 已注释记录该决策；GUI 测试 fixture 按真实平台设计。若未来需要 CI headless 跑 GUI 测试，需另行评估（本阶段不做）。
