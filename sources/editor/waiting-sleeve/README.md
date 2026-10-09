# waiting 袖子：实际 GIMP 工程

`kaguya-waiting-sleeve.xcf` 是 GIMP 3.2.6 官方 batch API 真正保存、重开后导出的工程。不是桌面画笔绘制或仅更名 PNG。

- 锁定基底是 waiting-art-v1 的实际托腮姿势，脸、原手、肩披与主体保留。
- 可编辑材料来自 waiting-sleeve-v1 的固定方画布投影；只采用衣料与轮廓旁有界遮挡底图，不能当作干净语义分层。
- 两个真实 mask 分别为衣料权重和底层浮点补偿。普通 normal-over 会重复叠加素材 alpha；改动上层权重后必须重算底层 `(1-w)/(1-alpha*w)`，不能把权重随意改完就宣称精确。
- 原母版与保护区指引是隐藏、锁定的参考图层，不参与可见输出。

两次真实导出逐字节一致，可见 RGBA 与当前候选一致；859 个完全透明像素的隐藏 RGB 被 GIMP 归零。项目 SHA256 记录于 editor-check.json，测试检查归档与导出证据，不宣称 CI 运行 GIMP。

重建入口为 tools/gimp_waiting_sleeve_project.py；它拒绝覆盖现有 XCF。另存新工程再改，不覆盖这份验证过的版本。源脸与手位不可变；阴影、衣料边界、手袖体积与完整自然度仍待视觉确认。该工程不构成安装批准。
