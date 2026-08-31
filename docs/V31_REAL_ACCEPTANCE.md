# V3.1 真实 Windows 验收

状态只允许 PASS / FAIL / NOT TESTED / BLOCKED。真机 FAIL = 产品 FAIL。
测试时钟一律用固定 now_provider，不改系统时钟。

## 【Scale】
| 项目 | 状态 | 证据 |
|---|---|---|
| 普通滚轮（源码，存量配置迁移后） | PASS | 探针 A1: 3.0→3.2，visible 387→413（V31_SCALE_ACCEPTANCE.md） |
| Ctrl+滚轮（源码） | PASS | 探针 B: 3.4→3.5 全链路同步 |
| Settings slider + Cancel（源码） | PASS | 探针 C1/C2 + test_settings_slider_preview_updates_visible_pixels |
| OK 持久化 | PASS | V2.2 test_scale_ok_persists |
| fresh EXE 启动/响应/单进程/无 WebEngine | PASS | verify_release.ps1 (2026-08-31, SHA 20afe707…) |
| fresh EXE 节假日数据打包 | PASS | dist/DesktopPet/_internal/assets/holiday_cn/{2025,2026}.json |
| fresh EXE 肉眼缩放 50/100/300 截图 | NOT TESTED | 计算机控制权限本轮被收回；见下方"用户 5 分钟清单" |

## 【Bubble】
| 项目 | 状态 | 证据 |
|---|---|---|
| 间距 4~10px（可见像素边界） | PASS（源码） | test_bubble_gap_target_near_visible_pet |
| 缩放/移动跟随 | PASS（源码） | test_bubble_reanchors_after_scale / _after_move |
| 屏幕边缘翻转 + clamp | PASS（源码） | test_anchor_flips_left… / test_anchor_stays_inside_available_geometry |
| 三个尺度触发文案（已在口袋中/提醒已保存/今天已赚） | PASS（源码级文案与锚点）；EXE 截图 NOT TESTED | 同上 |
| 输入穿透（不再吃滚轮） | PASS | test_bubble_window_is_input_transparent |
| IME 崩溃加固 | PASS（缓解） | 真机 46s/37 气泡 soak（KI-22/KI-26） |

## 【File】
| 项目 | 状态 |
|---|---|
| Explorer 拖入 → Pocket（源文件保留） | PASS（V2.2 人工闭环 + 用户 V3 验收确认） |
| Pocket drag out / copy / move | NOT TESTED（本轮无计算机控制） |
| current Explorer 查询 | PASS（Phase 17 人工验收保留） |

## 【Reminder】
| 项目 | 状态 |
|---|---|
| 2 分钟真实提醒（动画+气泡+声音） | NOT TESTED（本轮无计算机控制；服务层 check_due/动画触发有自动化） |

## 【Shell】（普通目录，非 Pocket watch）
| 项目 | 状态 |
|---|---|
| delete / create / mkdir / rmdir 真机反馈 | NOT TESTED（本轮无计算机控制；KI-21 的 EXE 级验收仍未完成） |

## 【Wage】（固定时钟 + 真实窗口，全部自动化 PASS）
| 时间点 | 状态 |
|---|---|
| 08:00 上班前 = 0 | PASS |
| 10:00 = 133.33 | PASS |
| 12:30 午休停累计 | PASS |
| 17:29 正常段尾 | PASS |
| 17:30 base 恰=日薪、加班 0 | PASS |
| 18:30 = +15.00 | PASS |
| 20:00/20:01 餐补预计 | PASS |
| 20:00 打卡确认 +30 | PASS |

## 【Overtime / Meal / Missing / Calendar / Privacy】
全部 PASS（见 TEST_REPORT 2026-08-31 表：299 passed）。

## 用户 5 分钟清单（EXE 肉眼项，完成后回填 PASS）

1. 双击 `dist/DesktopPet/DesktopPet.exe`；
2. 滚轮悬停角色缩放：50%（约 scale 1）→ 100%（scale 3）→ 300%（scale 6），每格肉眼变化明显；
3. 右键角色 → 新建提醒 → 保存 → 出现"提醒已保存"气泡：三个尺度下各截一张图，气泡均贴角色 4~10px；
4. 单击角色开面板 → 拖动角色 → 面板跟随；点面板外空白 → 面板关闭；
5. 打开普通 Explorer 目录（如 `.tmp/v3-acceptance/explorer-dir`）：新建文件/新建文件夹/删除/重命名各一次，桌宠应有动画+气泡反馈；
6. 建 2 分钟后提醒，等待触发（动画+气泡）；
7. 右键 → 今日收入 → 配置工资与上班时间 → 面板出现今日收入（隐私模式可开关）。
