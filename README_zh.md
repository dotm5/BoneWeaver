# BoneWeaver

[English](README.md)

BoneWeaver 是一款安全优先的 Blender 工具，用于把 Unreal Engine 骨骼层级整理成
可检查、可回滚、适用于 BoneX 与 Wiggle 的物理骨链。

## 功能亮点

- 点击一次 **全自动转换并重建 L 键骨链**，即可对活动 Armature 执行与 UEFormat
  兼容的骨骼方向转换，并把安全的线性段重建为 Blender 原生 Connected 骨链。
- 在改变选择或静止姿态几何前，检查 Parent、Root、Descendant、Branch 与语义次级链范围。
- 根据 Bone Head 与父子层级构建不可变 Physics Graph，并明确记录末端证据与分叉延续。
- Apply 前预览建议的 Tail、Roll、Connect、警告与 Blocker。
- 提供 BoneX 旋转链、Wiggle 旋转/伸缩链与显式启用的视觉骨链整理 Profile。
- 只有事务、Digest、拓扑、Mutation Ledger 与 Neutral evaluated mesh 验证全部成功后才允许导出。

## 安全合同

Analyze、层级检查与语义发现均为只读。Apply 与全自动转换只允许修改 EditBone 的
`tail`、`roll` 与 `use_connect`，不会重新绑定 Mesh、重算权重、Apply Pose as Rest、
重建 Armature Modifier 或创建生产代理骨骼。

Apply 只接受完全匹配的冻结 Plan，先写入持久化 Snapshot，再验证结果；失败自动回滚。
Restore 检测到后续手工修改时会拒绝覆盖。完整条款见[安全合同](docs/safety.md)。

## 环境要求

- Blender 4.2 或更高版本
- 已导入的 Unreal 风格 Armature，建议保留关联的原始权重 Mesh
- 不需要外部 Python 依赖

BoneX、Wiggle、Auto-Rig Pro 与 UEFormat 只是可选工作流集成，不随插件捆绑。

## 安装

从 [v0.3.0 Release](https://github.com/dotm5/BoneWeaver/releases/tag/v0.3.0)
下载 `boneweaver-0.3.0.zip`。在 Blender 中打开
**编辑 > 偏好设置 > 扩展 > 从磁盘安装**，选择 ZIP 并启用 BoneWeaver。

## 快速开始

1. 导入 UE 模型并保留原始权重。
2. 选择 Armature，打开 **3D 视图 > 侧栏 > BoneWeaver**。
3. 点击面板顶部的 **全自动转换并重建 L 键骨链**。
4. 确认后，BoneWeaver 会自动重定向合格骨骼、用原生 `use_connect` 重建最大线性段、
   验证结果并保存持久化 Snapshot。
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
末端低置信度或 Mesh/Modifier 漂移导致风险时，BoneWeaver 会阻断 Apply。成功 Apply
会记录字段级 Mutation Ledger；导出还会启动第二个 Blender 进程独立重开验证，成功后才报告完成。

## 已验证版本

BoneWeaver v0.3.0 已在 Blender 5.2.0 LTS RC build `710df102694f` 上验证：

- 220 个 Blender 宿主自动化测试全部通过，无 Failure 或 Error。
- 对固定 UEFormat 1.0.0 实现比较了 154 根合格骨骼：最大方向误差 `0.033878°`、
  最大长度误差 `1.164412e-7`，Head、Parent 与 Socket 均未改变。
- 全自动流程在原始 157 骨 `.uemodel` 与现有 `x1.blend` 上通过；手指、头发、飘带、
  脊柱的原生 `L` 键选择均可用，第二次运行无额外修改，精确 Restore 通过，两个源文件哈希不变。
- Release ZIP 通过隔离安装与重复注册/注销验证。
- 安装包：`boneweaver-0.3.0.zip`
- 大小：`185592` bytes
- SHA-256：`4FA71A1F71640047D10F03E023DB03EB89126D6DEF8353BBCB93D9989E2B23C2`

## 已知限制

- 全自动工具会修改静止骨骼的显示方向，但不会改写 UEFormat `post_quat` 动画元数据，
  也不会重定向动画 Basis。
- Blender 4.2 是 Manifest 最低版本；本次本地可执行验证使用上述 Blender 5.2 build。
- BoneX/Wiggle 的实际物理效果仍需按项目进行人工调参。
- Active Action、NLA、Driver、非单位 Pose、相关 Constraint 与不安全的分叉/末端证据会按设计阻断 Apply。

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
