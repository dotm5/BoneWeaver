# BoneWeaver 用户工作流

## 全自动转换与原生 L 键选择

需要一次完成整个 UE 骨架的方向转换与层级整理时，选中 Armature，打开
`N 面板 > BoneWeaver`，点击顶部的“全自动转换并重建 L 键骨链”。按钮会立即执行，
无需二次确认；Action、NLA、Driver、Constraint、Pose、B-Bone、Bone Parent、
Envelope、Modifier 与 Mesh 诊断都只提示、不阻断。
BoneWeaver 会自动捕获全骨架、生成不可变 Plan、排除 Socket/控制/零长度骨、
修改合格骨骼、重建最大线性 Connected 分量、验证结果并保存恢复快照。

完成后进入 Armature 编辑模式，把鼠标放到手指、头发、飘带、脊柱等已转换
线性段上并按 `L`，Blender 会使用原生连接关系选中该段。分叉边界会保持断开，
不会把多个兄弟分支合成一个 L 键分量。再次运行不会产生额外几何修改；不满意时
可点击“恢复全自动转换前状态”，若转换后已有手工修改则恢复会安全拒绝。

这条全自动路径处理整个合格 Armature。只想处理指定次级链、查看详细 Physics
Graph 或选择 BoneX/Wiggle Profile 时，继续使用下方标准流程。

## 标准流程

1. 在 3D 视图中选中 Armature，或选中带 Armature Modifier 的 Mesh。
2. 选择要处理的骨骼链。
3. 在 `N 面板 > BoneWeaver` 选择目标用途：BoneX 稳定旋转链、Wiggle 稳定旋转链、Wiggle 可伸缩链或仅整理骨骼链。
4. 点击“检查并预览”。该操作只分析并显示预览，不修改骨架或网格。
5. 根据结果处理阻断问题；设置、选择或文件发生变化后应重新检查。
6. 点击“应用转换”并确认影响摘要。Apply 内置安全验证，成功后无需再执行一次 Validate。

## 状态解释

- “可以转换”：当前 Plan、选择和设置一致，且没有阻断问题。
- “可以转换，但建议先确认”：可应用，但存在安全后备或警告。
- “暂时不能转换”：Details 中列出的阻断问题必须先处理。
- “设置已经改变”与“当前选择已经改变”：上次结果已失效，重新检查即可。
- “分析结果已不可用”：插件重载、文件切换或 Undo/Redo 后内存 Plan 已丢失，快照不受影响。
- “转换完成”：Apply 已通过内置中性网格、Digest、拓扑与事务验证。

## 可选：层级检查与语义次级链发现

尚未 Connected 的 UE 骨架可以先使用“层级检查”：选择活动 Bone 与检查
模式，生成 Parent/Root/Descendant Overlay；检查本身不改变选择。只有点击
具名的“选择检查范围”后才改变 Bone Selection，再点击“用于转换”才把当前
结果冻结为下一次 Analyze 的 Scope。遇到分叉时可显式指定延续 Child。

头发、飘带、裙摆或饰品可先运行“发现次级链”。发现阶段读取全骨架但不
改变选择；候选必须由用户确认并选择，再显式用于转换。缺失可复用权重证据
时不会自动接纳候选。层级 Scope 与语义 Scope 互斥，切换文件、骨架变化、
Undo/Redo 或相关 depsgraph 更新会使临时结果失效。

“仅整理骨骼链”对应显式的 `VISUAL_CHAIN_CLEANUP` Profile。它不会自动
启用，也不会绕过分叉歧义或 Existing Tip Helper 的安全限制。

## 详情、恢复与开发者诊断

结果详情默认折叠。点击“加载结果详情”时最多生成 200 条 RNA 列表项，完整结果仍保留在不可变 Plan/JSON 报告中。Issue 使用自然语言显示，可定位相关 Bone。

恢复面板显示最近快照并提供“恢复转换前状态”和“重新验证当前状态”。清除分析或重置会话不会删除 Blender Text 快照。

数值阈值、权重证据、Roll、验证策略和覆盖项位于高级面板。Plan ID、Fingerprint、原始 Issue Code、Schema、算法版本与报告导出仅在 Add-on Preferences 中启用 Developer Diagnostics 后显示。
