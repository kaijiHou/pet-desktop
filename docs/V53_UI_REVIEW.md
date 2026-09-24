# V5.3 UI Review

四张图由 Qt Windows 平台插件直接渲染独立控件生成，顶层窗口没有显示在用户桌面；目录和文件均为 `.tmp/v53-demo/` 合成数据。图像检查用于发现布局问题，不等于真实显示器上的人工验收。

| 截图 | 状态 | 优点 | 问题 | 是否修复 |
|---|---|---|---|---|
| [QuickPanel](screenshots/v53/quick-panel-favorites.png) | Qt 渲染 PASS；真实 DPI NOT TESTED | 280px 面板中 2 列清楚呈现 6 个入口；长名称显示省略号且没有撑宽；“查看全部（8）”明确 | 6 项所在网格仅 3 行，但面板还包含工资、口袋、提醒内容；图像高度是 574px，真实屏幕上的密度仍需手工确认 | 网格按实际可用宽度 elide，保留两列；不缩短工资/口袋/提醒信息 |
| [FavoriteFolders 管理窗](screenshots/v53/favorite-folders.png) | Qt 渲染 PASS；真实 DPI NOT TESTED | 8 项可在 660×760 视图完整查看；完整路径以中段省略呈现；主操作一眼可见 | 之前版本的每行“打开/上移/下移/更多”显得拥挤 | 已移除可见上下移按钮，排序与编辑操作统一放进“更多”菜单 |
| [失效路径修复](screenshots/v53/favorite-folders-missing.png) | Qt 渲染 PASS | 橙色修复提示、蓝色定位边框与“路径失效”标签同时可见 | 打开按钮仍可见，但点击时需要给出修复反馈 | 失效状态禁用“打开”；QuickPanel 左键会打开管理页并提示如何修改路径 |
| [Pocket 目标区](screenshots/v53/pocket-favorite-targets.png) | Qt 渲染 PASS；真实 Explorer NOT TESTED | “常用文件夹”“最近使用”“当前文件夹”作为三个分组，目标和操作容易区分 | 当前文件夹来自测试 stub，不是正在使用的 Explorer | 标注为合成状态，不将其说成真实 Explorer 验收 |

QuickPanel 截图尺寸为 280×574；管理窗分别为 660×760、660×560；Pocket 为 760×580。真实桌面字体、缩放比例、鼠标操作与实际 Explorer 打开均保持 `NOT TESTED`，见 `V53_REAL_ACCEPTANCE.md`。
