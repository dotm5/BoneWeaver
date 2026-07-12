# Interaction Refactor Final Report

## 已确认并修复的问题

- 主面板过密、工程状态泄漏、动作可用性分散：以纯 ViewModel 和分层面板替代。
- Plan Store 丢失、设置/选择过期语义不清：分别映射 `PLAN_LOST`、`STALE_SETTINGS`、`STALE_SELECTION`。
- Preview handler/runtime/cache 多点写入及 Restore/Clear/Load/Undo/Redo 残留：统一归 `PreviewController` 与 `SessionController`。
- Operator 散写运行时、Apply 无影响摘要、未实现公开属性：统一控制器编排，增加确认，隐藏 `validation_scope`/`allow_partial` 等空壳接口。
- Analyze 无条件复制 RNA 列表、Draw 每帧重建 batch、中性网格 tuple 膨胀：改为 lazy 列表、GPU cache 与连续数组/流式统计。
- Imported Axis 无条件先验：根据 importer metadata 降级并在证据冲突时惩罚。

## 实测后未复现的风险

- 168 项自动测试未复现 Preview 清理、注册泄漏、镜像 Roll fallback、方向聚类 Margin、断开权重岛、逐 Mesh tolerance 或事务安全回归。
- 85 Bone 真实模型中两个分叉均稳定解析，0 blocker；Apply、导出和独立重开验证通过。

## 仍需真实 BoneX/Wiggle 验证

- BoneX 1.2.6 的物理生成、播放、bake 与主面板真实交互观感。
- Wiggle 2 RTX 2.2.5 的稳定旋转链和可伸缩链动态行为。
- 这些项目不影响 BONEWEAVER 的 transaction/digest/neutral-mesh 自动安全验证，但不能由 headless 测试替代。

## 版本声明

- `algorithm_version`：已修改，升级到 `boneweaver-physics-graph-v3-interaction-hardening`。
- JSON `schema_version`：本交付分支相对父提交从 `3.0.0` 升级到 `3.1.0`，用于已纳入本分支的 branch、tolerance、mutation、topology 与 export 持久化字段；交互 ViewModel/RNA 状态本身未再增加持久化 JSON 字段。
- BoneX 1.2.6 hotfix 仍是独立支持工具；BONEWEAVER Runtime 未导入、修改或初始化 BoneX 状态。
