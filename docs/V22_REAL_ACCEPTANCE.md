# V2.2 Real Windows Acceptance

基线：`8648f96ce5bc506969fc850d49b9d0430b818bcc`  
分支：`v2.2-interaction-fix`  
目标仓库：`https://github.com/kaijiHou/pet-desktop`

状态只使用 `PASS` / `FAIL` / `NOT TESTED` / `BLOCKED`。自动化测试结果不能替代真实 Windows 鼠标验收。

## Fresh release

- 构建来源：`release/DesktopPet/DesktopPet.exe`
- 构建方式：`scripts/build_release.ps1` clean build
- ZIP SHA-256：待 fresh build 后填写

## Acceptance checklist

| 场景 | 状态 | 证据/备注 |
|---|---|---|
| 源码版 slider 缩放 | NOT TESTED | 需真实窗口拖动 slider，确认肉眼尺寸变化 |
| 源码版滚轮缩放 | NOT TESTED | 需真实窗口滚轮上/下 |
| EXE slider 缩放 | NOT TESTED | 需 release EXE |
| EXE 滚轮缩放 | NOT TESTED | 需 release EXE |
| Explorer → 源码版拖文件 | NOT TESTED | 需真实 OLE drag，确认非禁止图标 |
| Explorer → EXE 拖文件 | NOT TESTED | 需 `drag-test.txt`，确认源文件保留 |
| Explorer → EXE 拖文件夹 | NOT TESTED | 需目录引用进入 Pocket |
| Explorer → EXE 多文件 | NOT TESTED | 需多选拖入 |
| 普通 Explorer Delete → watcher 收到 | NOT TESTED | 需普通 Explorer 文件夹，不加入 Pocket watch |
| Delete → DELETE_FILE | NOT TESTED | 需观察动画语义 |
| Delete → bubble | NOT TESTED | 需观察气泡并约 2 秒回 idle |
| watcher registration id != 0 | NOT TESTED | 启动日志应记录 `id=<非零>` |
| QuickPanel X 关闭 | NOT TESTED | 自动化已覆盖，仍需真人窗口确认 |
| QuickPanel 二次点击关闭 | NOT TESTED | 自动化已覆盖，仍需真人窗口确认 |
| QuickPanel 跟随桌宠 | NOT TESTED | 左/右边界均需确认 |
| PocketWindow X 关闭 | NOT TESTED | 自动化已覆盖，仍需真人窗口确认 |
| PocketWindow 跟随桌宠 | NOT TESTED | 左/右边界均需确认 |

## Test workspace

真实验收文件统一放在：`D:\pet-desktop\.tmp\v22-drag\` 和 `D:\pet-desktop\.tmp\v22-shell\`。不要使用用户真实文件作为测试对象。
