# UE Chain Prep

UE Chain Prep 是 Blender 4.2+ 扩展。它把 UE 导入骨架的 Bone Head 与父子层级解释为不可变 Physics Graph，再把无歧义的 Graph Edge 投影到原 deform bones，供 BoneX、Wiggle 2 等工具使用连续骨链。

## 安装

在 Blender“偏好设置 → 扩展 → 从磁盘安装”中选择 `dist/ue_chain_prep-0.2.0.zip`。插件不依赖 NumPy、pytest 或其他外部 Python 包。

标准交互已简化为：选择骨骼链和目标用途 → “检查并预览” → “应用转换”。算法阈值位于高级设置，结果/恢复单独分层，Plan ID、Fingerprint 和原始 Issue Code 默认隐藏。完整说明见 [用户工作流](docs/user-workflow.md)。

## 推荐顺序

1. 导入 UE 模型与原始权重；
2. 在 ARP、BoneX、Wiggle 建立控制关系前选择头发、裙摆、尾巴或飘带骨链；
3. 打开“3D 视图 → 侧栏 → UE Chain Prep”；
4. 设置 Scope、Physics Profile、Terminal Inference 与 Roll；
5. Analyze 后检查 Physics Graph、Virtual Tip、Imported Forward Axis、候选排名、Confidence、Score Margin 和 Blocker；
6. 仅对当前且无 Blocker 的 Plan 执行 Apply；
7. Validate 后再配置第三方物理工具，确认结果前保留 Snapshot。

## 核心语义

- Interior Segment 的真值是 `parent.head → child.head`，不是 imported tail。
- Leaf 先生成只存在于 Plan 中的 Virtual Tip，再把该位置投影为真实 leaf tail。
- AUTO 会比较 Imported `±X/±Y/±Z`、PCA、Centroid、Planar Blend、Parent Tangent 与原显示轴；分数接近或置信度低时阻断，不静默猜测。
- 默认 Roll 是 `MINIMAL_TWIST`，尽量保存旧局部 Z/Twist；`PARALLEL_TRANSPORT` 只在显式选择时使用。
- Profile 区分几何连续与 Blender `use_connect`：Rotation Chain 连接，Stretch/Translation Profile 保持几何连续但断开连接。

## 安全与恢复

MVP 只允许修改目标 Bone 的 `tail`、`roll`、`use_connect`。不解绑、不重绑、不 Apply Pose as Rest、不重算权重、不创建生产代理链。Apply 前创建持久化 Snapshot，验证权重、Base Mesh、Modifier、Graph Projection 与 Neutral evaluated mesh；失败自动回滚。Restore 检测到用户手工修改时返回 `UECP_RESTORE_CONFLICT`，不会覆盖新数据。

## 常见 Blocker

Active Action/NLA/Driver、非单位 Pose、相关 Constraint、Bone-parented object、Envelope、B-Bone、多 Armature Modifier、拓扑修改器位于 Armature 前、外部 Connected Child、Coincident Helper、分叉方向歧义、候选 tie/低置信度。

## 动画警告

v0.2.0 是 Physics Preparation 工具，不是 UE 动画 Basis 重定向工具。转换后继续直接导入 UE 动画可能需要 Basis Rebase。

## Blender 5.2 下的 BoneX 1.2.6

BoneX 1.2.6 的 Soft Connection 面板可能在 `draw()` 中初始化 `Object["bonex_data"]`，Blender 5.2 会拒绝这种 UI 绘制期写入。该问题不加载 UE Chain Prep 也能独立复现。项目提供了带版本校验、备份和恢复能力的本地修复工具，详见 [BoneX 1.2.6 draw-context 修复说明](docs/bonex-1.2.6-draw-context-hotfix.md)。应用或恢复后需重启 Blender。

详见 [架构](docs/architecture.md)、[算法](docs/algorithms.md)、[安全合同](docs/safety.md) 与 [BoneX/Wiggle 手工验收表](docs/manual-test-bonex-wiggle.md)。

## 后端稳健性

生产默认现已使用逐 Mesh 的 evaluated object-local 中性验证、父链安全 Leaf 回退、候选方向聚类、分叉主延续评分、权重岛保护、带 Armature 指纹的幂等 Override、字段级 Mutation/Topology 账本、导出硬 Gate 与独立 Blender 重开验证。详见 [容差合同](docs/validation-tolerance.md)、[分叉解析](docs/branch-resolution.md) 与 [导出合同](docs/export-contract.md)。

## 层级与语义选择（开发中）

当前开发分支新增五种层级检查模式、缓存式 Parent/Root/Descendant
Overlay、显式分叉延续选择，以及必须确认后才能使用的语义次级链发现。
Inspection 与 Discovery 本身只读；只有具名的 Select 操作会改变选择，且
必须再次执行 Use 才会冻结为 Analyze Scope。`VISUAL_CHAIN_CLEANUP` 也是
显式选择项，不会自动替换生产默认 Profile。详见 [层级选择](docs/hierarchy-selection.md)、
[语义发现](docs/semantic-chain-discovery.md) 与 [视觉整理](docs/visual-chain-cleanup.md)。
