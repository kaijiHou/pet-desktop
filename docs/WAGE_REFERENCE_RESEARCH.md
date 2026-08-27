# V3 工资与日历参考研究

## 研究范围

本阶段只借鉴本地工资计时器的交互和可解释算法，不复制网络服务、逐秒累加或外部账户依赖。运行时工资数据全部留在 `data/`，节假日数据可以更新，但手工日历覆盖永远优先。

## 参考项目

| 项目 | License / 覆盖 | 借鉴 | 不借鉴 |
|---|---|---|---|
| [kouwenhao/salary-timer](https://github.com/kouwenhao/salary-timer) | GitHub 项目页未把许可证作为本阶段运行依赖；Python + PyQt6；Windows 悬浮工资计时器 | 月薪、工作日、工作时间段、悬浮显示、窗口位置和 JSON 配置的产品结构 | PyQt6 迁移、云端报价/更新、开机自启和外部网络请求 |
| [anneheartrecord/salary-timer](https://github.com/anneheartrecord/salary-timer) | MIT；Python 实时工资计时器 | 今天已赚、日/时/分拆分和精确到分的展示方式 | 网页服务、金币雨、逐秒 `money +=`、暂停“摸鱼”作为工资规则 |
| [Silent-Blue/cn-holiday-calendar](https://github.com/Silent-Blue/cn-holiday-calendar) | 以国务院通知为来源的年度 JSON/缓存思路；本阶段不直接 vendoring，仓库页面未确认独立数据许可证 | 节假日与调休上班日的离线数据形态、按年份缓存 | 将远程抓取作为启动依赖；未确认许可证的数据不直接打包 |
| [NateScarlet/holiday-cn](https://github.com/NateScarlet/holiday-cn) | MIT；仓库提供 2023–2027 年 JSON/ICS 数据 | 作为活跃替代数据源候选，支持假日/调休字段 | 不把自动数据覆盖用户手工 override |
| [Lancetwang/china-mainland-calendar](https://github.com/Lancetwang/china-mainland-calendar) | MIT；含 2026 年中国大陆日历/ICS，数据依据国务院安排 | 作为后续更新候选，检查年份覆盖后再生成本地 `holidays.json` | 不在 V3 引入联网刷新或强制第三方包 |

## V3 决策

1. 现有项目保持 Python + PyQt5；工资算法放在 `wage/calculator.py`，服务和 UI 分离。
2. 本地日历解析支持常见 `date -> status`、`holidays` 列表和 `isWorkday/isOffDay` 字段。当前仓库不把未经审核的数据集复制进发布包；没有数据时回退到周一至周五工作、周末休息。
3. 选择顺序固定为：用户手工状态 > 本地节假日数据 > 默认星期规则。工资计算工作日数另有手工覆盖。
4. 工资金额使用 Decimal，按当前时间和记录重新计算，避免休眠、重启或定时器丢失造成累计漂移。

## 验证记录

研究日期：2026-08-27。项目页面与许可证页面已人工核对；发布前如果新增年份数据，必须再次核对上游许可证、来源和年份覆盖，并在本文件追加记录。

