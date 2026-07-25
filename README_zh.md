# BoneWeaver

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

安装 `dist/boneweaver-0.4.0.zip`。在 Blender 中打开
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

这些阻断不适用于 v0.4.0 面板顶部的三个全自动入口。混合模式中的识别阻断会降级为
提示并触发逐骨 UEFormat 回退，不会终止全局流程。

## 已验证版本

BoneWeaver v0.4.0 已在 Blender 5.2.0 LTS build `fbe6228777e7` 上完成本地验证：

- 230 个 Blender 宿主自动化测试全部通过，无 Failure 或 Error。
- 同一强制完成 Fixture 同时包含 Action、NLA、Driver、非单位 Pose、骨骼/对象 Constraint、
  B-Bone、Bone Parent、Envelope、重复 Armature Modifier 与共享 Armature Data，仍一键完成、
  `BLOCKER=0` 且精确 Restore 通过。
- 对固定 UEFormat 1.0.0 实现比较了 154 根合格骨骼：最大方向误差 `0.033878°`、
  最大长度误差 `1.164412e-7`，Head、Parent 与 Socket 均未改变。
- 三种模式分别在原始 157 骨 `.uemodel` 与现有 `x1.blend` 上通过；手指、头发、飘带、
  脊柱的原生 `L` 键选择均可用，每种模式第二次运行均为零额外修改，精确 Restore 通过，
  两个源文件哈希不变。混合模式采用 94 根可信多特征结果，并对 61 根骨骼自动回退。
- Release ZIP 通过隔离安装与重复注册/注销验证。
- 安装包：`boneweaver-0.4.0.zip`
- 大小：`190353` bytes
- SHA-256：`A68C65050DAFE9DC91A53C0F9DA91C4610EBC343F153D0F21DC540C0A1E4E709`

## 已知限制

- 原版与混合模式会修改静止骨骼的显示方向，但不会改写 UEFormat `post_quat` 动画元数据，
  也不会重定向动画 Basis。
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
