# Modern UI System（V4.7）

共享组件位于 `ui/modern/`：

- `ModernDialog`：无原生标题栏、圆角卡片、可拖动标题区
- `PrimaryButton` / `SecondaryButton` / `DangerButton`：统一操作层级
- `Card` / `StatCard` / `SectionTitle`：统计和分区骨架
- `ModernLineEdit` / `ModernComboBox` / `ModernTimeField`：统一输入样式
- `InlineBanner` / `Toast`：非阻塞提示，避免启动流程被 QMessageBox 打断

工作日历、工资设置、桌宠设置和角色管理均使用该系统。文件选择器保留系统原生对话框，便于 Windows 路径和权限交互。
