# 角色预览一致性（V4.7）

角色 ID 是唯一选择键：`CharacterRegistry.resolve(id)` 得到 pack 根目录，`CodexPetManifest` 校验清单，`SpritesheetAtlas` 提取 idle 帧。桌面渲染器、设置预览和角色管理共用这条链；设置重置固定回到 `default_dynamic_ghost`。

默认小幽灵图集由 `character_v4/default_pet.py` 生成，原语先按 4× supersampling 绘制再缩回 192×208 单元，idle、挥手、失败、review 等语义帧具有独立像素内容。`DynamicPackRenderer.stop()` 同时停止播放计时器和状态机随机 idle 计时器，预览切换不会留下后台动画。
