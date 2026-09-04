# Character Preview Rendering

状态：PASS（源码、自动化和资源链） / NOT TESTED（真实 Windows 截图）

角色预览、角色库和桌面都从 `CharacterRegistry → CodexPetManifest → SpritesheetAtlas` 读取动态角色。`DynamicPackRenderer.current_frame()` / `current_pixmap()` 是预览层唯一读取入口，预览不访问 `_player` 私有字段。

动态帧和单图都使用 `Qt.KeepAspectRatio` 居中绘制，避免把 192×208 的角色拉伸成正方形。切换角色前会停止播放、断开 signal、解除父对象并安排删除；关闭预览窗口会再次执行清理，AnimationPlayer 和 PetStateMachine idle timer 均停止。

单图统一写入 `data/character_images/`，配置保存 `character_images/<name>.png` 相对路径；仍可读取旧版绝对路径和旧 assets 文件名。Codex home 角色只读展示，必须先导入到 `data/characters/` 才能使用。
