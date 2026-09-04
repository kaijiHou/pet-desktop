# Modern UI System（V4.8）

共享组件位于 `ui/modern/`：

- `ModernDialog`：无原生标题栏、圆角卡片、可拖动标题区；按需支持 7px 边缘/角落 resize、最大化/还原和标题栏双击
- `PrimaryButton` / `SecondaryButton` / `DangerButton`：统一操作层级
- `Card` / `StatCard` / `SectionTitle`：统计和分区骨架
- `ModernLineEdit` / `ModernComboBox` / `ModernTimeField` / `ModernMoneyField`：统一输入样式，时间/金额控件隐藏原生箭头
- `SettingsRow` / `ToggleRow`：设置页的标签、说明和开关行，避免 QGroupBox 套盒
- `InlineBanner` / `Toast`：非阻塞提示，避免启动流程被 QMessageBox 打断

工作日历、工资设置、桌宠设置和角色管理均使用该系统。文件选择器保留系统原生对话框，便于 Windows 路径和权限交互。

V4.8 约束：页面动作统一使用中文 Primary/Secondary/Danger 按钮和 InlineBanner/Toast；删除动作使用 ModernConfirmDialog。日历月度覆盖通过右上角“⋯”进入，覆盖只影响当前月份，恢复“自动”即可回到逐日统计。
