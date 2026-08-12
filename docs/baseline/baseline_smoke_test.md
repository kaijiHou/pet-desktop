# Phase 1 Baseline Smoke Test — 2026-08-12

> 素材说明：上游仓库缺少 README 要求的外部 sprite sheet（KI-01），**真实原版角色视觉不可复现**。
> 本测试使用 synthetic baseline asset（合成测试素材）验证窗口、动画切帧、拖动、缩放和菜单**机制**。
> 执行方式：`scripts/smoke_baseline.py`（真实构建 `pet_window_web.PetWindow`，走原事件处理器，非 mock 业务逻辑）。
> 原始输出：`docs/baseline/smoke_output.txt`

## GUI

| 项目 | 结果 | 证据 |
|---|---|---|
| 主程序启动 | PASS | PetWindow visible=True, page+sheet ready in 4.68s |
| 桌宠窗口存在 | PASS | 同上 |
| 背景透明 | PASS | WA_TranslucentBackground 属性为 True |
| 窗口置顶 | PASS | WindowStaysOnTopHint 置位 |
| 角色可见 | PASS (synthetic sprite) | getState()={"anim":"Idle1_1","frame":1,"scale":3.5,"frameCount":43}；sheet 3348x3162 已被页面成功解码 |
| 真实官方角色素材 | BLOCKED | upstream asset missing (KI-01/KI-10) |
| 角色拖动正常 | PASS | 合成鼠标事件 (50,40) 位移 → window.pos delta=(50,40)，config.pet_x/y 同步更新 |
| 滚轮缩放正常 | **FAIL** | scale 3.5→4.0 生效，但上游 wheelEvent 把 float 传给 setGeometry 抛 TypeError（KI-11 上游 bug，首次滚轮必现） |

## Animation

| 项目 | 结果 | 证据 |
|---|---|---|
| idle 动画能切帧 | PASS | Idle1_1 frame 1→43 周期内帧号推进，并观察到原逻辑随机切换 Thinking |
| 至少一个非 idle 动画 | PASS | Wave/Greeting 组触发，current=Greeting |
| 动画结束后状态恢复 | PASS | ALERT 播放完毕自动回 idle |
| sleep 能触发 | PASS | 模拟 60s 无活动 → state=sleep, js anim=IdleSnooze |
| wake / 恢复正常 | PASS | state 回 idle |

## UI

| 项目 | 结果 | 证据 |
|---|---|---|
| 右键菜单可打开 | PASS | 5 个菜单项全部构建（Tanya Clippy/Jadwal/Reset Timer/Settings/Keluar） |
| Settings 可打开 | PASS | OpenAI/Water/Calendar 三组控件构建成功 |
| Chat 入口可打开 | PASS | ChatDialog constructed & shown |
| Calendar/提醒 UI 不崩溃 | PASS | 无凭据下 authenticate()=False 静默返回，主程序不崩 |
| 退出正常 | PASS | _quit_app() → QApplication.quit() 被调用 |

## Reminder

| 项目 | 结果 | 证据 |
|---|---|---|
| Timer 初始化 | PASS | remind=5000ms, idle=60000ms |
| 能触发现有提醒路径 | PASS | tick(31*60) 越过 30min 阈值 → alerted=True（最小测试配置：直接喂累计秒数，未改默认代码逻辑） |
| 提醒 UI / 气泡路径 | PASS | bubble='🚰 Waktunya minum!...' + winsound 音效路径执行 |

## 外部服务（按任务书 §11/§12 不测真实链路）

| 项目 | 结果 |
|---|---|
| AI external-call path | NOT TESTED（no API key；UI 初始化已测，无 Key 时错误可控并给出提示气泡） |
| Google OAuth flow | NOT TESTED（no credentials；模块 import 成功、初始化路径已测） |

## 汇总

**19 PASS / 1 FAIL / 0 BLOCKED-in-test（真实素材 BLOCKED 单列）/ 2 NOT TESTED（外部 API）**

唯一 FAIL = KI-11（上游 wheelEvent float→setGeometry TypeError），属原项目真实缺陷，Phase 1 按约束不修。
