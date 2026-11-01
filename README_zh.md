# BoneWeaver 0.6.0

主界面并列提供 **全自动整理 / 仅父子重定向 / 仅连接骨链 / 仅清理辅助骨**。零权重辅助子树自底向上筛选；IK、武器槽位、游戏功能节点及有效骨骼的父级保留。

选择模型或骨架，在 N 面板 → BoneWeaver 点击 **全自动整理**。

- 只重定向原来的非根、非末级骨骼；先使用末端位置确定父骨方向，再移除证据充分的无权重辅助子树。
- 检查所有相关网格及骨骼引用；有权重、挂点、约束、驱动等用途的末端骨保留。
- 保留原始骨架备份，可用 **恢复整理前状态** 恢复，包括已清理的末端骨。
- Debug、旧版三种模式及手动流程均位于折叠的 **高级设置**。

请在重新蒙皮、制作动画前使用，优先保留导入时的原始权重。已被自动蒙皮赋权的辅助骨不会强行删除；此功能不修复已有串权。
此新模式不自动重写已有 Action 动画。安装 `dist/boneweaver-0.6.0.zip`，升级后重启 Blender。
详细筛选规则、恢复机制及 UEFormat 上游追踪见 [自动整理算法说明](docs/auto-cleanup.md)。

## 旧版流程说明（高级设置）


[English](README.md)

BoneWeaver 是一款安全优先的 Blender 工具，用于把 Unreal Engine 骨骼层级整理成
可检查、可回滚、适用于 BoneX 与 Wiggle 的物理骨链。

## 功能亮点

- 面板顶部提供三个全自动入口：保留 v0.3.1 行为的原版转换、面向朝向良好骨架的
  “仅重建连接”，以及按骨骼自动选择多特征结果或 UEFormat 回退的实验性混合转换。
- 在改变选择或静止姿态几何前，检查 Parent、Root、Descendant、Branch 与语义次级链范围。
- 根据 Bone Head 与父子层级构建不可变 Physics Graph，并明确记录末端证据与分叉延续。
- Apply 前预览建议的 Tail、Roll、Connect、警告与 Blocker。
- 提供 BoneX 旋转链、Wiggle 旋转/伸缩链与显式启用的视觉骨链整理 Profile。
- 只有事务、Digest、拓扑、Mutation Ledger 与 Neutral evaluated mesh 验证全部成功后才允许导出。

## 安全合同

Analyze、层级检查与语义发现均为只读。Apply 与三个顶部全自动入口只允许修改 EditBone 的
`tail`、`roll` 与 `use_connect`，不会重新绑定 Mesh、重算权重、Apply Pose as Rest、
重建 Armature Modifier 或创建生产代理骨骼。

精细范围 Apply 仍只接受完全匹配的冻结 Plan，并保留严格验证合同。面板顶部的三个功能
使用“强制完成”模式：Action、NLA、Driver、Constraint、Pose、B-Bone、Bone Parent、
Envelope、Modifier 与 Mesh 诊断都只提示、不阻断。操作仍会保存 Snapshot；Blender 编辑
异常时自动回滚，Restore 检测到后续手工修改时会拒绝覆盖。完整条款见[安全合同](docs/safety.md)。

## 环境要求

- Blender 4.2 或更高版本
- 已导入的 Unreal 风格 Armature，建议保留关联的原始权重 Mesh
- 不需要外部 Python 依赖

BoneX、Wiggle、Auto-Rig Pro 与 UEFormat 只是可选工作流集成，不随插件捆绑。

## 安装

安装 `dist/boneweaver-0.4.1.zip`。在 Blender 中打开
**编辑 > 偏好设置 > 扩展 > 从磁盘安装**，选择 ZIP 并启用 BoneWeaver。

## 快速开始

1. 导入 UE 模型并保留原始权重。
2. 选择 Armature，打开 **3D 视图 > 侧栏 > BoneWeaver**。
3. 按模型情况选择一个顶部按钮：
   - **原版**：保留 v0.3.1 的 UEFormat 兼容转换。
   - **仅重建连接**：不运行朝向识别，保留现有朝向并重建原生 Connected 线性骨链。
   - **实验性混合**：逐骨使用可信的多特征结果；无法可靠识别的骨骼自动使用
     UEFormat 兼容回退。
4. 三种模式均立即运行、处理整个合格 Armature、验证结果并保存持久化 Snapshot。
5. 进入编辑模式，将鼠标移到已转换骨链上并按 `L`；同一原生 Connected 段会被快速选择，
   分叉边界按设计保持断开。
6. 不满意时点击 **恢复全自动转换前状态**；若检测到后续手工修改，Restore 会拒绝覆盖。

面板下方仍保留原有的 Physics Graph 精细流程，用于选择性准备 BoneX/Wiggle 骨链并预览细节。

## 层级检查与语义发现

层级检查用缓存 Overlay 展示 Parent/Root/Descendant，不会自动改变选择。具名 Select
操作只改变临时骨骼选择；只有执行 **用于转换**，结果才会冻结为下一次 Analyze Scope。

语义发现会扫描 Armature 中的头发、飘带、裙摆、尾巴与配饰候选。候选必须人工确认，
不会自动进入 Apply。分叉存在歧义时必须显式选择延续 Child。

## 验证与恢复

当 Action、NLA、Driver、Constraint、Pose 状态、外部 Connected Child、分叉歧义、
末端低置信度或 Mesh/Modifier 漂移导致风险时，精细 Physics Graph 流程会阻断 Apply。成功 Apply
会记录字段级 Mutation Ledger；导出还会启动第二个 Blender 进程独立重开验证，成功后才报告完成。

关闭动画兼容时，面板顶部三个全自动入口保持 v0.4.0 行为。启用“保护现有动画与
UEFormat Basis”后，BoneWeaver 会重基一个安全的 Active Action，并在修改 Rest Basis
前阻断不支持的活动动画栈。混合模式中的识别阻断仍会降级为逐骨 UEFormat 自动回退。

## 已验证版本

BoneWeaver v0.4.1 已在 Blender 5.2.0 LTS build `fbe6228777e7` 上完成本地验证：

- 230 个 Blender 宿主自动化测试全部通过，无 Failure 或 Error。
- 动画验证覆盖父局部 Basis Delta、累计 `post_quat`、Active Action 重基、连接拓扑、
  幂等和 Action/元数据精确 Restore。不支持的活动动画栈会在修改前阻断，空 Action
  使用明确的 Quick 安全回退。
- 对固定 UEFormat 1.0.0 实现比较了 154 根合格骨骼：最大方向误差 `0.033878°`、
  最大长度误差 `1.164412e-7`，Head、Parent 与 Socket 均未改变。
- 三种模式分别在原始 157 骨 `.uemodel` 与现有 `x1.blend` 上通过；手指、头发、飘带、
  脊柱的原生 `L` 键选择均可用，每种模式第二次运行均为零额外修改，精确 Restore 通过，
  两个源文件哈希不变。混合模式采用 94 根可信多特征结果，并对 61 根骨骼自动回退。
- Release ZIP 通过隔离安装与重复注册/注销验证。
- 安装包：`boneweaver-0.4.1.zip`
- 大小：`200097` bytes
- SHA-256：`7D5160229B8FA33D9C29B36D53BC8A8903B88ACD1F3C72434B5D524D94CEB059`

## 已知限制

- 动画兼容仅支持一个本地、未共享且只包含有效 Pose Bone Transform FCurve 的 Active Action。
  活动 NLA Strip、Pose Driver、有效 Pose Constraint、共享 Action 与不支持路径会在修改前阻断。
- 仅连接模式不执行朝向推断；若线性父骨 Tail 与既有子骨 Head 不重合，为建立原生连接，
  会把父骨 Tail 对齐到该子骨 Head，但不会移动子骨 Head。
- 混合模式为实验性功能；多特征结果不满足可信条件时会优先使用 UEFormat 兼容回退。
- Blender 4.2 是 Manifest 最低版本；本次本地可执行验证使用上述 Blender 5.2 build。
- BoneX/Wiggle 的实际物理效果仍需按项目进行人工调参。
- Active Action、NLA、Driver、非单位 Pose、相关 Constraint 与不安全的分叉/末端证据只会阻断
  独立的精细 Physics Graph Apply，不会阻断一键 Quick Reorient。

## 文档

- [用户工作流](docs/user-workflow.md)
- [全自动快速转换](docs/quick-reorient.md)
- [原生 L 键链选择](docs/native-linked-selection.md)
- [架构](docs/architecture.md)
- [算法](docs/algorithms.md)
- [层级选择](docs/hierarchy-selection.md)
- [语义发现](docs/semantic-chain-discovery.md)
- [验证与导出合同](docs/export-contract.md)
- [兼容性](docs/compatibility.md)
- [更新日志](CHANGELOG.md)

## 开发

Blender 宿主测试、打包与隔离安装门槛见 [CONTRIBUTING.md](CONTRIBUTING.md)。
安全问题请按 [SECURITY.md](SECURITY.md) 私密报告。

## 许可证

BoneWeaver 使用 GNU General Public License v3.0 or later，详见 [LICENSE](LICENSE)。
