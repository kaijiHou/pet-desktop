# V5.4 真实渲染验收 — 皮肤对比度（2026-09-29）

验收方式：真实 Windows Qt 平台（windows 平台，非 offscreen）构造生产 QuickPanel，
逐套皮肤 `set_skin()` 后 `widget.grab()` 存档，并对 WCAG 相对亮度公式计算的
文字/背景对比度采样。不使用 computer-use。

## 结果：5/5 PASS（门槛 ≥ 3.0，实测 4.5~6.5）

| 皮肤 | 工资卡底色 | 状态文字对比 | 金额对比 | 按钮白字对比 | 判定 |
|---|---|---|---|---|---|
| 樱花粉 sakura | #fef2f6 | 5.8 | 4.8 | 4.9 | PASS |
| 奶油黄 cream | #fef6e9 | 4.9 | 4.7 | 4.5 | PASS |
| 薄荷绿 mint | #ebf8f4 | 5.7 | 4.8 | 4.8 | PASS |
| 天空蓝 sky | #edf4fb | 6.5 | 4.7 | 4.9 | PASS |
| 香芋紫 taro | #f5f2fc | 6.5 | 4.9 | 4.8 | PASS |

截图证据（本目录）：`skin-sakura-panel.png`、`skin-cream-panel.png`、
`skin-mint-panel.png`、`skin-sky-panel.png`、`skin-taro-panel.png`。

## 背景

用户报告工资卡"大块饱和粉、文字看不清"。根因：`ui_skin.palette()` 的
`_tint` 混色比例语义写反（tint_light 实为 88% 主题色）。修正为 12% 主题色
+ 白底后，工资卡回到浅色；次要文字按用户要求加深一级
（`text_soft`、`_darken_for_contrast` 链路）。

## 附带修复（本日）

历史测试的日期/时钟依赖在 2026-09-29 暴露（与皮肤改动无关，HEAD 上同样失败）：

- `test_status_change_recalculates_month_tiers`：朴素"往前找周一~五"撞上
  9/25 中秋（法定休息日）→ 改用服务自身日历找真工作日（最多回溯 60 天）。
- `test_month_worked_value_includes_current_day_partial_income`：真实时钟
  08:48 尚未上班，今日实时收入为 0 → 固定 now_provider 到当日 10:00。
- 三处 emoji 改名后的陈旧精确断言（文件口袋/管理常用文件夹/打开文件口袋）
  → 改为包含式断言。
- `test_dynamic_renderer_loads` 曾读用户真实 config（用户当前选中的是灰衣
  角色属合法状态）→ 改为隔离配置断言全新默认值。

全量：**429 passed**。
