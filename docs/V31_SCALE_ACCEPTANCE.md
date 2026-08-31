# V3.1 缩放专项验收

## 复现方法（PET_SCALE_DEBUG=1 + .tmp/v31-probe/realapp_soak.py）

真实 Windows 平台、完整 PetWindow 栈（shell watcher/tray/wage）、固定沙盒配置（复制用户真实 config.json，不污染）。每个操作前后记录：
`config.pet_scale / character.scale / character.base_size() / PetWindow.size() / visible_pet_rect / visible_pet_global_rect`。

## 2026-08-31 实测记录（修复后）

| 步骤 | cfg | char.scale | base_size | 窗口 | visible_rect | 判定 |
|---|---|---|---|---|---|---|
| 初始 | 3.0 | 3.0 | 576×576 | 616×636 | 387×387 | — |
| A1 普通滚轮（存量 false 配置，迁移后） | 3.0→3.2 | 3.2 | 614×614 | 654×674 | 413×413 | PASS（每格 +0.2 肉眼明显） |
| A2 再滚一格 | 3.4 | 3.4 | 652×652 | 692×712 | 438×438 | PASS |
| B Ctrl+滚轮 | 3.5 | 3.5 | 672×672 | 712×732 | 452×452 | PASS（细步 0.1） |
| C0 打开 Settings | 3.5 | 3.5 | — | — | — | — |
| C1 slider 拉到 300% | 3.5（未保存） | 6.0 | 1152×1152 | 1192×1212 | 774×774 | PASS（即时预览） |
| C2 Cancel | 3.5 | 3.5 | 672×672 | 712×732 | 452×452 | PASS（完整回滚） |

修复前对照（同一探针，迁移前）：
| A1 存量 `wheel_zoom_enabled=false` | 3.0 | 3.0 | 576×576 | 616×636 | 387×387 | **FAIL → 根因确认为遗留配置禁用 plain wheel** |

## 根因与修复（摘要）

1. V2 时代设置对话框把 `wheel_zoom_enabled=false` 写进了存量 config；V2.2 只改了默认值不做迁移 → `config.py` 增加 `v31_wheel_migration_done` 一次性迁移（之后完全尊重设置复选框）。
2. 滚轮步长 0.1→0.2（普通）/0.1（Ctrl）确保每格可见。
3. 气泡窗口改为输入穿透（WindowTransparentForInput + WA_TransparentForMouseEvents），排除"气泡盖住角色吃滚轮"的 Case 1。
4. 气泡渲染改为纯 QLabel + QImage 预渲染（无 Python paintEvent），修复 IME 重入 fail-fast（详见 KI-22/KI-26）。

## Case 1~5 排查结论

- Case 1（wheelEvent 未收到）：气泡窗口确实可能覆盖角色上方透明区并接收滚轮 → 已通过输入穿透修复；普通滚轮主因仍是 Case 5 变体"存量配置不同"。
- Case 2/3/4（调用链断裂/base_size 不变/只变透明框）：探针证明全链路同步，不存在。
- Case 5（EXE 失败）：EXE 与源码同代码；EXE 上三路径行为与源码一致（黑盒启动/响应 PASS），肉眼截图项待用户按 `V31_REAL_ACCEPTANCE.md` 清单复核。
