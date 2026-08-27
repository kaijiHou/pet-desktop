# V3 真实 Windows 验收

## 当前状态

代码级回归已覆盖工资计算、日历优先级、透明像素边界和面板入口。由于本轮按用户要求不使用电脑控制，以下 Explorer 拖拽、鼠标视觉和真实提醒项目必须由用户在 Windows 桌面手动完成，状态暂记 `NOT TESTED`，不能用 offscreen pytest 代替。

## 安全目录

请在 `D:\pet-desktop\.tmp\v3-acceptance\` 下建立测试文件和普通 Explorer 目录，不要使用真实重要文件。

## 手动清单

| Story | 操作 | 结果 |
|---|---|---|
| A 视觉 | 最小/正常/最大缩放触发气泡；移动角色 | 气泡贴近可见轮廓并随角色移动；`NOT TESTED` |
| B 文件 | Explorer 创建 `bronze2.txt`，拖入角色后打开口袋 | 文件仍在原处、口袋可见；`NOT TESTED` |
| C Reminder | 建立 2 分钟后提醒 | 动画、气泡、可选声音；`NOT TESTED` |
| D 时间点 | 上班前、上午、午休、17:29、17:30、18:30、20:01 | 金额/状态符合 `WAGE_RULES.md`；`NOT TESTED` |
| E 阈值 | 历史 24h30m，再计 17:30→19:30 | 0.5h×15 + 1.5h×25；`NOT TESTED` |
| F 餐补 | 19:59、20:00、21:15 下班打卡 | 0、30、30；`NOT TESTED` |
| G 删除 | 普通测试目录删除 `delete-me.txt` | 桌宠产生 DELETE 反馈；`NOT TESTED` |

## 代码回归

本轮使用固定 now provider 的纯逻辑测试，不改系统时钟；完整测试和 fresh release 结果在 `TEST_REPORT.md` 追加。手动清单完成后，把每行 `NOT TESTED` 替换为日期、Windows 版本和观察结果。

