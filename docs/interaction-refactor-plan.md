# BoneWeaver 交互重构计划
## 面向非开发用户的主面板流程，以及性能与算法补充审计

**文档状态：Implementation-ready**
**文档用途：可独立交给 Codex Goal Mode 执行**
**适用项目：BoneWeaver 当前实现**
**本轮范围：Blender UI、会话状态、控制器、可观察性、性能收敛与少量算法稳健性修正**
**不改变的核心安全合同：不解绑、不重绑、不重算权重、不创建生产代理链，只允许修改目标 EditBone 的 `tail`、`roll`、`use_connect`。**

---

# 1. 目标结论

当前插件已经具备较完整的工程能力，但主面板直接暴露了大量算法参数、置信度阈值、权重证据、Proposal、Issue Code 和诊断操作，整体更像测试控制台，而不是面向普通 Blender 用户的生产工具。

本轮重构目标不是删除这些能力，而是把它们重新分层：

```text
主面板
  只呈现：
  选择目标
  选择用途
  检查并预览
  处理必要问题
  应用转换
  完成与恢复

高级副面板
  呈现：
  范围与 Mesh 策略
  末端推断方式
  权重证据
  Roll
  置信度与数值阈值
  验证与恢复选项

开发者诊断
  呈现：
  Plan ID / Graph ID
  Fingerprint
  性能统计
  JSON 导出
  原始 Issue Code
  Schema 与兼容性信息
```

主面板必须做到：

> 用户只需选择一条骨骼链、选择目标物理工具，然后依次点击“检查并预览”和“应用转换”，即可完成正常工作流。

---

# 2. 审计标记

本文使用以下标记区分已确认问题与需实测风险：

- **FACT**：由当前源码审计报告或现有架构文档直接确认。
- **RISK**：从现有分层和算法推导出的高概率风险，需要代码或性能数据进一步验证。
- **TARGET**：本轮必须达到的目标状态。
- **OPTIONAL**：可延期，不阻断主交互重构。

---

# 3. 当前实现的主要交互问题

## 3.1 信息架构过密

**FACT**

当前只有一个主面板，并连续展示：

```text
Context
Scope
Inference
Weight Evidence
Preview & Diagnostics
Chain List
Proposal List
Issue List
Analyze / Preview / Apply / Validate / Restore / Export / Clear
```

这会造成三个问题：

1. 普通用户在开始操作前就必须理解末端推断、权重指数、排他模式和置信度；
2. 主操作与诊断操作没有明显主次；
3. 用户难以判断“现在应该点击哪个按钮”。

## 3.2 工程状态直接泄漏到用户界面

**FACT**

当前界面直接依赖：

```text
PlanState
plan_id
issue_count
proposal list
fingerprint
snapshot name
```

这些数据适合作为内部状态，但不应成为普通用户理解流程的前提。

用户需要看到的不是：

```text
ANALYZED
STALE
RESTORABLE
BONEWEAVER_EXTERNAL_CONNECTED_CHILD
confidence = 0.684
```

而应是：

```text
可以转换
设置已经改变，请重新检查
转换完成，可恢复
有一个未选中的连接子骨会被移动
末端方向需要确认
```

## 3.3 内存 Plan 与持久化状态不一致

**FACT**

`ConversionPlan`、报告和 Preview Cache 存在模块级内存中；WindowManager 却保留状态和 Plan ID。

插件重载、文件切换或会话变化后可能出现：

```text
界面仍显示已分析
但实际 Plan 已丢失
```

主界面必须把这种情况明确呈现为：

```text
分析结果已失效，请重新检查
```

而不是让 Apply、Validate 或 Preview 在执行后才失败。

## 3.4 操作可用性没有统一来源

**FACT**

多个操作器缺少完整 `poll`，或面板始终绘制可点击按钮，失败原因只能在执行后得知。

本轮必须建立统一的：

```text
ActionAvailability
```

所有按钮由同一状态推导函数决定：

```text
是否可用
为什么不可用
下一步应该做什么
```

## 3.5 Preview 生命周期分散

**FACT**

Preview Handler、`preview_enabled` 和 Preview Cache 由多个位置分别维护。

Restore、Clear、插件卸载、Plan Stale、文件加载、Undo/Redo 都必须由统一 PreviewController 处理。

## 3.6 状态枚举与真实流程漂移

**FACT**

现有状态包含部分实际上不会被写入的枚举值；Validate 也不会改变流程状态。

内部状态可以保留兼容，但主 UI 不应直接渲染底层 PlanState，而应映射到更稳定的用户工作流状态。

---

# 4. 新的产品交互原则

## 4.1 一个时刻只突出一个主操作

主面板在不同状态下只显示一个高优先级按钮：

| 当前状态 | 主按钮 |
|---|---|
| 未选择有效骨架 | 无按钮，显示选择指导 |
| 已选择但未检查 | `检查并预览` |
| 分析结果过期 | `重新检查` |
| 有阻断问题 | `定位问题` 或 `重新检查` |
| 可以转换 | `应用转换` |
| 转换完成 | `检查另一条骨骼链` |
| Plan 丢失 | `重新检查` |
| 发生错误 | `重置本次会话` |

Preview、详情、恢复、导出等均为次级动作。

## 4.2 主面板不显示数值置信度

主面板仅显示：

```text
可靠
可用，但建议确认
无法确定
```

数值分数、候选方向、第一与第二候选差值、Eigenvalue 等只进入高级或开发者面板。

## 4.3 安全检查使用自然语言

错误码仍作为稳定接口保留，但主面板必须使用可操作的自然语言，例如：

```text
所选骨骼中有一个分叉点。
请从分叉后的子骨开始选择，或在高级设置中指定主路径。
```

而不是只显示：

```text
BONEWEAVER_BRANCH_AMBIGUOUS
```

## 4.4 分析与预览合并为一个用户动作

保留底层两个独立能力：

```text
Analyze
PreviewController.enable
```

但主面板提供组合命令：

```text
检查并预览
```

执行逻辑：

1. 分析；
2. 若得到可预览 Proposal，则自动开启 Preview；
3. 若存在 Blocker，仍显示安全的部分 Preview，但使用警告标记；
4. 若完全没有 Proposal，则不启动 Handler。

高级设置提供：

```text
分析后自动预览
```

默认开启。

## 4.5 Apply 保持独立确认

不得把 Analyze 与 Apply 合并成一键自动写入。

Apply 使用确认对话框：

```text
将调整 6 根骨骼的方向与连接方式。
不会修改网格、权重、骨名或父子层级。
是否继续？
```

## 4.6 转换完成后不要求用户再次 Validate

Apply 已包含强制 Post Validation。

成功后主面板显示：

```text
转换完成，并通过安全验证
```

`重新验证` 移入恢复/诊断区域，不作为标准流程步骤。

---

# 5. 新的面板信息架构

仍保留：

```text
3D Viewport
→ N Panel
→ BoneWeaver
```

但拆为：

```text
BONEWEAVER_PT_main
BONEWEAVER_PT_advanced
BONEWEAVER_PT_details
BONEWEAVER_PT_recovery
BONEWEAVER_PT_developer   # 默认隐藏，由插件偏好开启
```

默认展开：

```text
主面板
```

默认折叠：

```text
高级设置
结果详情
恢复与历史
开发者诊断
```

---

# 6. 主面板设计

## 6.1 顶部上下文卡片

始终显示，但只显示普通用户需要的信息：

```text
骨架：Character_Skeleton
已选择：6 根骨骼
检测用途：BoneX 稳定旋转链
```

若活动对象是 Mesh，但可通过 Armature Modifier 找到骨架：

```text
骨架：Character_Skeleton
来源：当前模型的骨架修改器
```

若没有有效目标：

```text
未找到可用骨架
请选中骨架，或选中带骨架修改器的模型
```

不要显示 Plan ID、指纹或内部状态码。

## 6.2 目标用途

主面板只保留一个用户需要主动选择的配置：

```text
目标用途
```

友好标签：

| 内部 Profile | 主界面标签 |
|---|---|
| `BONEX_ROTATION_CHAIN` | `BoneX · 稳定旋转链` |
| `BONEX_TRANSLATION_ALLOWED` | 不在主面板显示，放高级 |
| `WIGGLE2_ROTATION_CHAIN` | `Wiggle · 稳定旋转链` |
| `WIGGLE2_STRETCH_CHAIN` | `Wiggle · 可伸缩链` |
| `GEOMETRY_ONLY` | `仅整理骨骼链` |

默认：

```text
BoneX · 稳定旋转链
```

主面板不暴露：

```text
Scope Mode
Mesh Scope
Terminal Mode
Roll Mode
Weight Exponent
Confidence Threshold
```

它们使用安全默认值或高级面板中的设置。

## 6.3 IDLE 状态

示例：

```text
┌ BoneWeaver ───────────────┐
│ 骨架：Character_Skeleton     │
│ 已选择：6 根骨骼             │
│                              │
│ 目标用途                     │
│ [ BoneX · 稳定旋转链      ▼ ]│
│                              │
│ [      检查并预览          ] │
│                              │
│ 将检查骨骼链方向、末端位置、 │
│ 权重和安全状态，不会修改模型 │
└──────────────────────────────┘
```

## 6.4 ANALYZED / READY 状态

示例：

```text
┌ 检查结果 ────────────────────┐
│ ✓ 可以转换                   │
│                              │
│ 1 条骨骼链 · 6 根骨骼        │
│ 末端方向已自动识别           │
│ 权重与网格检查正常           │
│                              │
│ [ 显示/隐藏预览 ] [重新检查] │
│                              │
│ [        应用转换          ] │
└──────────────────────────────┘
```

主面板最多显示三条摘要：

```text
链数量与骨骼数量
末端识别情况
安全验证准备情况
```

更多信息进入 Details。

## 6.5 NEEDS_ATTENTION 状态

中等置信度、非阻断建议：

```text
△ 可以转换，但建议先确认
一个末端方向不够明确
已使用父链方向作为安全后备

[在视图中查看]
[打开结果详情]
[应用转换]
```

是否允许 Apply 由现有安全合同决定。

若当前算法将该情况视为 Blocker，则主面板不能提供 Apply。

## 6.6 BLOCKED 状态

示例：

```text
✕ 暂时不能转换

发现 2 个需要处理的问题：
· 所选链包含一个分叉
· 有一个未选中的连接子骨

[定位第一个问题]
[查看全部问题]
[重新检查]
```

主面板最多显示两条问题；其余用：

```text
还有 3 个问题
```

问题列表按：

```text
用户可解决程度
→ 严重性
→ 骨骼顺序
```

排序，而不是只按错误码。

## 6.7 STALE 状态

区分两类：

### 设置变化

```text
设置已经改变
请重新检查后再应用
```

### 选择变化

```text
当前骨骼选择与上次检查不同
上次结果针对 6 根骨骼
```

默认禁用 Apply，要求重新检查，避免用户误以为会处理当前选择。

### Plan 丢失

```text
分析结果已不可用
这通常发生在重新加载插件或切换文件之后
请重新检查
```

## 6.8 APPLIED / RESTORABLE 状态

示例：

```text
✓ 转换完成

6 根骨骼已更新
权重、网格和修改器保持不变
安全验证已通过
恢复快照已保存

[检查另一条骨骼链]
[恢复转换前状态]
```

技术指标移入 Details：

```text
最大中性网格偏移
Snapshot ID
Digest
```

## 6.9 ERROR 状态

示例：

```text
转换未完成

插件已自动尝试恢复修改。
请查看错误详情，确认骨架状态。

[查看详情]
[重置本次会话]
```

若回滚失败，必须明确显示：

```text
自动恢复失败，请立即撤销或关闭文件而不保存
```

---

# 7. 高级副面板设计

面板：

```python
class BONEWEAVER_PT_advanced(Panel):
    bl_parent_id = "BONEWEAVER_PT_main"
    bl_options = {"DEFAULT_CLOSED"}
```

高级面板按折叠组组织，不把全部参数一次展开。

## 7.1 选择范围

```text
骨骼范围
  当前选择
  选择根骨及其后代
  当前骨骼集合

网格来源
  自动选择相关网格
  当前活动网格
  手动勾选相关网格
```

建议新增友好默认值：

```text
AUTO_RELEVANT_MESHES
```

其行为：

- 只纳入由目标 Armature 驱动；
- 且包含目标 Bone 同名顶点组；
- 且具有有效权重成员的 Mesh。

若暂不修改稳定 Schema，可在 UI Controller 中把“自动”映射到现有安全选择逻辑。

## 7.2 末端方向

首先显示预设，而不是数值：

```text
识别策略
  自动稳健（默认）
  优先使用骨骼局部轴
  优先使用权重形状
  沿父骨方向
  手动指定
```

展开“详细参数”后再显示：

```text
Terminal Mode
Imported Forward Axis
Length Source
Minimum Confidence
Candidate Margin
Maximum Auto Bend
Percentile
Minimum / Maximum Length Ratio
```

## 7.3 权重证据

默认折叠：

```text
最小权重
权重指数
顶点面积加权
排他模式
权重分位数
断开区域处理
```

主面板不得显示这些字段。

## 7.4 Roll 与局部轴

显示友好选项：

```text
尽量保留原轴（默认）
平滑整条链
朝参考点外侧
保留原 Roll 数值（实验）
```

对应：

```text
MINIMAL_TWIST
PARALLEL_TRANSPORT
RADIAL_REFERENCE
KEEP_NUMERIC_ROLL
```

只有选中 Radial 时显示参考对象/Bone。

## 7.5 Preview

```text
分析后自动预览
显示原骨骼方向
显示转换后方向
显示局部轴
显示权重质心
显示虚拟末端
显示长段采样提示
预览尺寸
```

所有 Preview-only 设置不得使 Plan Stale。

## 7.6 安全与验证

```text
要求整个骨架处于中性姿态
验证全部相关网格
位置误差阈值
Apply 前显示确认
成功后保留快照
```

不要在普通高级面板显示 Fingerprint 实现细节。

## 7.7 自定义末端覆盖

把现有 `terminal_overrides` 正式接入高级 UI。

每个覆盖项显示：

```text
骨骼
覆盖方式
方向/参考对象
长度
启用
```

提供：

```text
从当前活动骨骼添加
从 3D Cursor 指定
清除覆盖
```

---

# 8. 结果详情面板

默认折叠。

普通模式显示：

```text
骨骼链摘要
需要确认的末端
问题与建议
转换影响范围
```

不再默认显示所有 Proposal。

## 8.1 Chain Summary

每条链一行：

```text
Hair_01 → Hair_06
6 根骨骼
末端：自动识别
状态：可转换
```

## 8.2 Issue Summary

显示自然语言。

点击问题时：

- 激活相关 Armature；
- 选中相关 Bone；
- 将视图聚焦到 Bone；
- Preview 高亮该问题。

原始 Issue Code 仅在 Developer Mode 中显示。

## 8.3 Proposal Details

仅当用户展开具体 Chain 时才生成或填充 UI Collection。

不要在 Analyze 后无条件把所有 BoneProposal 复制到 RNA 列表。

---

# 9. 恢复与历史面板

默认折叠。

显示：

```text
最新快照
创建时间
骨架名称
转换骨骼数量
当前是否可恢复
```

标准动作：

```text
恢复转换前状态
重新验证当前状态
```

Snapshot 历史列表为 OPTIONAL。

`Validate` 的产品定义统一为：

> 重新执行当前骨架与最近快照/当前 Plan 的安全一致性检查。

若 `validation_scope` 暂未实现，应在本轮删除公开入口或真正实现，不能继续暴露空壳参数。

`allow_partial` 同理：

- v1 继续全量恢复：隐藏并删除 UI；
- 未来真正实现部分恢复后再公开。

---

# 10. 开发者诊断面板

通过 Add-on Preferences 开启：

```text
Enable Developer Diagnostics
```

显示：

```text
Plan State
Plan Availability
Plan ID
Graph ID
Source Fingerprint
Settings Fingerprint
Algorithm Version
Snapshot ID
Issue Code
Candidate Score
Candidate Margin
Weight Cloud Statistics
Performance Metrics
Export Diagnostic JSON
Clear Session Runtime
```

普通用户永远不需要打开该面板。

---

# 11. 新的 UI ViewModel

Panel 不再直接读取和组合业务状态。

新增：

```text
ui/view_model.py
```

建议接口：

```python
@dataclass(frozen=True, slots=True)
class ActionView:
    operator_id: str
    label: str
    icon: str
    enabled: bool
    disabled_reason: str
    is_primary: bool = False


@dataclass(frozen=True, slots=True)
class TargetSummaryView:
    armature_name: str | None
    selected_bone_count: int
    chain_count: int | None
    profile_label: str
    source_kind: str


@dataclass(frozen=True, slots=True)
class ResultSummaryView:
    status_kind: str
    title: str
    description: str
    bone_count: int
    chain_count: int
    terminal_reliable_count: int
    terminal_attention_count: int
    blocker_count: int
    warning_count: int


@dataclass(frozen=True, slots=True)
class PanelViewState:
    workflow_stage: str
    target: TargetSummaryView
    result: ResultSummaryView | None
    primary_action: ActionView | None
    secondary_actions: tuple[ActionView, ...]
    notice_lines: tuple[str, ...]
    preview_active: bool
    plan_available: bool
    snapshot_available: bool
```

`PanelViewState` 是主面板唯一输入。

## 11.1 用户工作流阶段

新增 UI 层状态，不必替换底层 PlanState：

```text
NO_CONTEXT
READY_TO_ANALYZE
ANALYZING
READY_TO_APPLY
NEEDS_ATTENTION
BLOCKED
STALE_SETTINGS
STALE_SELECTION
PLAN_LOST
APPLYING
APPLIED
ROLLBACK_FAILED
ERROR
```

映射函数必须是纯函数并可单元测试：

```python
derive_panel_view_state(
    blender_context_summary,
    runtime_summary,
    plan_availability,
    current_selection_signature,
    current_settings_signature,
    snapshot_summary,
)
```

---

# 12. 控制器重构

建议目录：

```text
controllers/
  workflow.py
  preview.py
  session.py
  selection.py
```

## 12.1 WorkflowController

唯一负责：

```text
Analyze
Apply
Validate
Restore
运行时状态迁移
UI 摘要同步
错误报告
```

Operator 只做：

```text
poll
invoke
execute
self.report
```

不得继续在多个 Operator 中分散写：

```text
runtime.state
runtime.plan_id
runtime.last_error
runtime.issue_count
runtime.preview_enabled
```

## 12.2 PreviewController

唯一负责：

```text
Draw Handler
GPU Cache
启用
禁用
重建
重绘
状态同步
文件加载清理
插件卸载清理
```

禁止其他模块直接写：

```text
runtime.preview_enabled
_HANDLER
_CACHE
```

## 12.3 SessionController

负责：

```text
Plan Store availability
Plan lost detection
Load/Unload
Undo/Redo
Clear analysis
Clear full session
UI Collection lazy synchronization
```

## 12.4 SelectionController

负责：

```text
选择签名
Plan Target Bone Set
选择变化检测
定位问题 Bone
视图聚焦
```

---

# 13. 会话生命周期修正

## 13.1 插件重载与文件加载

注册：

```text
load_pre
load_post
```

行为：

```text
关闭 Preview
清除内存 Plan/Report/Cache
重置 transient UI lists
保留 Blender Text Snapshot
将 UI 映射为 PLAN_LOST 或 READY_TO_ANALYZE
```

## 13.2 Undo / Redo

**RISK，优先验证**

Apply 支持 Undo，但当前 Runtime 可能仍显示转换完成。

注册：

```text
undo_post
redo_post
```

保守行为：

```text
关闭 Preview
清除当前 Plan
重新评估最近 Snapshot 状态
UI 显示“场景已撤销或重做，请重新检查”
```

不要尝试从 Undo Stack 猜测 Plan 仍然有效。

## 13.3 设置变化

算法设置 Property Update Callback：

```text
标记当前 Plan Stale
关闭 Preview
保留 Plan 摘要用于提示
```

Preview-only 设置：

```text
不标记 Stale
只重建 Preview Cache
```

## 13.4 选择变化

记录：

```text
selection_signature
```

Analyze 后若当前选择不同：

```text
STALE_SELECTION
禁用 Apply
提示重新检查
```

这虽然比底层 Fingerprint 更严格，但更符合非开发用户对“处理当前选择”的理解。

## 13.5 Restore

Restore 前后必须：

```text
关闭 Preview
清除 Plan
清空 Proposal/Issue/Chain 临时列表
重新评估 Snapshot
切换到 APPLIED 前或 READY_TO_ANALYZE 的可解释状态
```

## 13.6 Clear

拆分为两个内部命令：

```text
Clear Analysis
Reset Session
```

主界面只提供：

```text
清除本次检查
```

开发者面板提供：

```text
重置完整会话
```

两者都不得删除 Snapshot。

---

# 14. 操作器调整

## 14.1 新增组合操作器

```python
boneweaver.check_and_preview
```

行为：

```text
调用 Analyze
同步 ViewModel
若有可用 Preview Cache，则启用 Preview
```

底层 `boneweaver.analyze` 可继续保留供测试和开发者使用。

## 14.2 Apply

增加：

```text
invoke_confirm
```

确认框显示自然语言影响摘要。

## 14.3 Locate Issue

新增：

```python
boneweaver.locate_issue
```

参数：

```text
issue_index
bone_name
```

行为：

```text
激活 Armature
进入合适 Mode
选中 Bone
视图聚焦
Preview 高亮
```

## 14.4 Recheck

主面板使用同一个：

```text
check_and_preview
```

不单独维护 Recheck Operator。

## 14.5 Validate / Export / Clear

移出主动作区。

---

# 15. 性能审计与改进

以下问题中，FACT 为已知 UI/生命周期问题；RISK 需要在代码中通过 Metrics 验证。

## 15.1 重复 Mesh 扫描

**RISK：高优先级**

当前算法文档保证权重证据扫描一次，但以下模块可能各自再次遍历：

```text
Weight Evidence
Vertex Group Digest
Base Mesh Digest
Area Weight
Associated Mesh Summary
Source Fingerprint
```

目标设计：

```text
MeshScanCache
```

一次扫描产生：

```text
Base Mesh Digest
Vertex Group Digest
Area per Vertex
Target Group Evidence
Vertex/Polygon Count
Membership Count
Per-Mesh Weight Summary
```

接口示例：

```python
@dataclass(slots=True)
class MeshScanCache:
    mesh_state: MeshBindingState
    area_weights: array
    target_samples: dict[str, CompactWeightSamples]
    vertex_group_digest: str
    base_mesh_digest: str
    metrics: MeshScanMetrics
```

Apply 前的重新 Fingerprint 仍需重新扫描当前数据，但同一次校验中不能重复扫描。

## 15.2 Python 对象内存膨胀

**RISK：高优先级**

若 evaluated vertex、权重点或 Preview 数据使用：

```text
list[tuple[float, float, float]]
```

百万顶点模型会产生远高于原始 Float 数据的 Python 对象开销。

要求：

- 使用标准库 `array("f")` 或 `array("d")` 存储连续坐标；
- Digest 使用流式 `hashlib.update`；
- Weight Cloud 统计完成后释放原始点；
- Immutable Plan 只保存统计，不保存全部顶点样本；
- `evaluated_mesh.to_mesh_clear()` 必须在 `finally` 调用；
- Preview Cache 只保存线段与少量标记。

为 Analyze 增加：

```text
tracemalloc peak
sample count
temporary float count
```

开发者报告中记录。

## 15.3 UI Collection 无条件复制

**FACT / RISK**

Analyze 后把所有 Chain、Proposal、Issue 复制到 WindowManager RNA Collection，数量大时增加：

- RNA 创建成本；
- UIList 绘制成本；
- 状态同步复杂度。

目标：

```text
主面板只保存摘要
Details 打开时按需生成列表
关闭或 Plan 失效时立即清理
```

可设置普通详情最大显示：

```text
前 200 条
```

完整结果仍保留在不可变 Plan 和 JSON 报告中。

## 15.4 Preview 每帧重建

**RISK**

确认 Draw Callback 是否每帧重新：

```text
构造 Vertex List
创建 GPU Batch
计算颜色/轴
```

目标：

- Plan 或 Preview 设置变化时构建一次 GPU Batch；
- Draw Callback 只 bind/draw；
- Plan Stale 后释放 Batch；
- 大骨架 Preview 可按 Chain 或选中项过滤。

## 15.5 全量 evaluated mesh 基线

**RISK：内存重点**

Post Validation 需要完整比较，这是正确的安全设计。

优化方式不是降级为抽样，而是使用紧凑连续缓存：

```text
array("f") world positions
```

指标在单次比较中流式计算：

```text
max
mean
RMS
```

禁止使用百万个 Python Vector 或 tuple 长期存储。

## 15.6 进度反馈

**TARGET**

Analyze 可能包含：

```text
Mesh 扫描
图构建
权重统计
末端候选
Fingerprint
Preview Cache
```

使用：

```python
WindowManager.progress_begin()
progress_update()
progress_end()
```

同时在 Status Bar 显示阶段。

若实测 1M 顶点仍产生长时间无响应，再评估 Modal 分块；MVP 不应贸然把 Blender 数据读取放入线程。

## 15.7 性能基准

新增程序化基准：

| Fixture | 目标 |
|---|---|
| 100 Bones / 100k Vertices | 交互级 |
| 300 Bones / 500k Vertices | 无重复全量扫描 |
| 500 Bones / 1M Vertices | 内存可控，无 Python 对象爆炸 |

报告：

```text
vertex_pass_count
membership_pass_count
analysis_time
fingerprint_time
preview_build_time
peak_memory
plan_size
ui_item_count
```

不以单台机器的固定秒数作为唯一 Gate，重点检查算法复杂度和扫描次数。

---

# 16. 算法补充审计

## 16.1 候选方向去重

**RISK：高优先级正确性问题**

候选可能包含方向近似相同的：

```text
Imported +X
PCA
Centroid
Parent Tangent
Original Display Axis
```

若直接按候选条目计算第一名与第二名 Margin，两个几乎相同方向可能造成：

```text
最佳方向其实非常稳定
但第一、第二候选分差很小
被误判为歧义
```

修正：

1. 先按角度容差聚类；
2. 同一方向簇合并 Evidence；
3. 再在不同方向簇之间计算 Margin。

建议：

```text
direction_merge_angle = 5°～10°
```

该值进入高级设置或算法常量，不进入主面板。

新增测试：

```text
PCA 与 Imported Axis 同向时不得触发假歧义
```

## 16.2 多 Mesh 与断开权重岛

**RISK：高优先级正确性问题**

直接把多个远离的权重区域聚合，质心和 PCA 可能指向两者中间的空白区域。

建议分两级：

### 第一级：按 Mesh 分组

为每个 Bone 先计算：

```text
per-mesh cloud stats
```

只有当多个 Mesh 的方向证据一致时才合并。

### 第二级：按连通区域

对超过阈值的权重顶点做 Mesh 拓扑连通分量。

默认策略：

```text
DOMINANT_COMPONENT
```

只有当最大分量的统计权重占比达到安全阈值时自动采用。

否则：

```text
BONEWEAVER_DISCONNECTED_WEIGHT_ISLANDS
需要确认或限定 Mesh Scope
```

不要只做 Confidence Penalty 后继续使用聚合方向。

性能要求：

```text
BFS/DFS O(V+E)
只对目标权重顶点子图执行
```

## 16.3 Imported Axis Prior

**RISK**

导入骨骼的 Rest Axis 可能包含：

- UE 原始局部轴；
- FBX Axis Conversion；
- 导入器 Post Rotation；
- 仅用于 Blender 显示的固定 Tail 方向。

因此 Imported Axis 不能无条件获得高先验。

策略：

```text
存在可靠 importer metadata:
    正常先验

无 metadata:
    降低 imported-axis prior
    必须与 parent tangent 或 weight evidence 一致
```

Diagnostic Report 记录证据来源。

## 16.4 全局尺度导致验证阈值过宽

**RISK**

若使用所有关联 Mesh 中最大的包围盒确定统一 epsilon：

```text
一个巨大隐藏物体或异常 LOD
可能让小型头发链的验证阈值过宽
```

修正：

- 每个 Mesh 使用自己的 bbox diagonal；
- Bone Head/Tail 使用 Armature/Chain 尺度；
- 最终失败依据为 per-object tolerance；
- 报告记录每个 Mesh 的 tolerance。

## 16.5 Selection 与 Plan 目标错位

**FACT / 产品正确性**

底层 Plan 可以安全应用上次选择，但普通用户通常认为 Apply 会处理当前选择。

因此 UI 层把选择变化视为 Stale，是必要的交互正确性修正。

## 16.6 Branch Boundary 的用户指导

**FACT**

算法正确地不为分叉 Parent 自动生成 Tail Proposal。

主面板必须明确建议：

```text
从分叉后的某个子骨开始选择
```

而不是只显示“Branch Ambiguous”。

未来可增加：

```text
主路径覆盖
```

但不属于本轮必做。

## 16.7 Roll 退化与镜像一致性

**RISK**

Minimal Twist 在旧 Z 与新 Y 接近平行时会走 fallback。

新增测试：

- 左右镜像链；
- 近垂直链；
- 180° 弯折；
- 旧 Z 投影接近零；
- Parent Transport 与 Old X fallback。

目标：

```text
左右链不产生随机相反 Roll
```

## 16.8 Confidence 校准

**RISK / OPTIONAL**

当前 Confidence 由多个证据组合，阈值很难仅靠合成 Fixture 校准。

建议在高级面板增加：

```text
识别严格度
  稳健
  平衡
  自定义
```

Preset 只映射现有参数，不改变稳定 Schema。

收集真实资产的：

```text
候选分数
最终人工选择
是否需要覆盖
```

作为后续校准数据。

本轮不做自动学习或在线遥测。

---

# 17. 需要修正的现有接口漂移

以下内容在交互重构时必须一起处理：

## 17.1 `active_issue_index`

Issue List 不得继续复用：

```text
active_chain_index
```

新增独立字段。

## 17.2 未兑现的 Operator 属性

逐一决定：

```text
validation_scope
allow_partial
include_plan
include_weight_stats
include_snapshot_summary
```

规则：

- 已实现：保留并补测试；
- 未实现：从公开 UI 隐藏；
- 不得继续暗示不存在的能力。

## 17.3 未消费的 Preview 设置

如果：

```text
preview_show_old_axes
preview_show_new_axes
preview_show_weight_centroid
```

未真正进入 Draw Cache，则：

- 本轮实现；
- 或暂时移出公开高级面板。

## 17.4 `create_role_collections`

放入高级面板，并明确：

```text
默认关闭
只创建 Bone Collection
不影响 Deform
```

## 17.5 PlanState

内部兼容可保留，但删除未使用状态或补齐真实迁移。

主面板只使用 WorkflowViewState。

---

# 18. 分阶段实施计划

## UI-R01：ViewModel 与状态契约

实现：

```text
PanelViewState
ActionView
TargetSummaryView
ResultSummaryView
WorkflowStage
ActionAvailability
```

完成：

- Plan Lost；
- Stale Settings；
- Stale Selection；
- Snapshot Availability；
- Primary Action 推导。

测试：

```text
每个底层状态都得到唯一、可解释的用户状态
```

## UI-R02：Session / Preview Controller

实现：

```text
SessionController
PreviewController
load/undo/redo/unregister cleanup
```

修复：

- Restore 后 Preview 残留；
- Runtime 与 Handler 分叉；
- Plan Store 丢失；
- Clear 不完整。

## UI-R03：简洁主面板

实现新的 `BONEWEAVER_PT_main`：

```text
上下文摘要
目标用途
一个主按钮
结果摘要
Preview 次级按钮
Apply
完成/恢复
```

主面板不得显示数值算法参数。

## UI-R04：高级副面板

迁移：

```text
Scope
Mesh Scope
Terminal
Weight Evidence
Roll
Confidence
Preview
Validation
Overrides
```

实现字段依赖显示。

## UI-R05：Details / Recovery / Developer

实现：

```text
自然语言问题详情
定位 Bone
按需 Proposal List
恢复状态
Developer Diagnostics
```

## UI-R06：性能收敛

审计并实现：

```text
MeshScanCache
Compact Numeric Buffers
Lazy RNA Lists
GPU Batch Cache
Progress Feedback
Metrics
```

## UI-R07：算法稳健性修正

优先：

```text
Candidate Direction Dedup
Per-Mesh Weight Evidence
Disconnected Component Guard
Per-Mesh Validation Tolerance
Imported Axis Prior Audit
```

这些修改必须升级：

```text
algorithm_version
```

若改变 Plan Schema，再升级 Schema Minor/Major。

## UI-R08：测试、真实模型与文档

更新：

```text
README_zh
Interaction Guide
Safety
Manual Test
Compatibility
Test Report
```

在真实 UE 导入模型上验证非开发用户流程。

---

# 19. 自动化测试

## 19.1 ViewModel 纯测试

覆盖：

```text
无骨架
未分析
Ready
Blocker
Warning
Settings Stale
Selection Stale
Plan Lost
Applied
Snapshot Available
Rollback Failed
```

每个状态验证：

```text
主标题
说明
主按钮
按钮可用性
不可用原因
```

## 19.2 Blender UI 集成测试

至少覆盖：

1. Analyze 后自动 Preview；
2. Restore 自动关闭 Preview；
3. Clear 清空所有临时列表；
4. 插件 Unregister 无 Handler；
5. Load 新文件后 Plan Lost；
6. Undo Apply 后状态失效；
7. 改算法设置后 Stale；
8. 改 Preview 设置不 Stale；
9. 改选择后 Stale Selection；
10. 点击 Issue 可选中并聚焦 Bone；
11. Apply 确认框；
12. Developer Mode 默认隐藏。

## 19.3 性能回归

加入计数断言：

```text
同一次 Analyze 中每个 Mesh 全量 vertex pass 不超过设计次数
同一次 Fingerprint 中 membership 不重复扫描
Plan 不保存完整 Vertex Sample
RNA Proposal Items 为 lazy
```

## 19.4 算法回归

新增：

```text
近同向 Candidate Dedup
多个候选同簇不降低 Margin
多 Mesh 同向证据可合并
多 Mesh 冲突证据被阻断
Dominant Component
Disconnected Equal Components
Per-Mesh Epsilon
Mirrored Roll Fallback
```

---

# 20. 人工可用性验收

邀请一个不了解实现细节的 Blender 用户，仅提供以下说明：

```text
1. 选中要处理的骨骼链
2. 选择 BoneX 或 Wiggle
3. 点击“检查并预览”
4. 确认预览
5. 点击“应用转换”
```

通过标准：

- 不需要解释 Confidence、PCA、Fingerprint；
- 不查看控制台；
- 能理解为什么按钮不可用；
- 能找到有问题的 Bone；
- 能恢复转换；
- 不会误以为 Clear 会删除 Snapshot；
- 不会误以为 Apply 处理的是已经变化后的新选择。

---

# 21. 最终验收标准

交互重构只有在以下条件全部满足时才可完成：

1. 主面板默认不显示工程参数；
2. 标准流程不超过两个主动作：
   - 检查并预览；
   - 应用转换；
3. 任一状态只有一个主按钮；
4. 禁用按钮有自然语言原因；
5. Plan Lost 可被明确识别；
6. Settings/Selection Stale 可区分；
7. Restore、Clear、Unload、Undo/Redo 不残留 Preview；
8. 主面板不显示原始 Issue Code；
9. Confidence 数值只在高级/开发者面板；
10. Proposal List 按需加载；
11. Apply 后直接显示验证成功；
12. 快照恢复对普通用户可见；
13. 未实现 Operator 选项不再公开；
14. 性能报告证明无明显重复 Mesh 扫描；
15. 大 Mesh 数据使用紧凑缓冲；
16. Candidate 去重测试通过；
17. 断开权重岛不会生成指向空白区域的自动末端；
18. 每个 Mesh 使用独立验证阈值；
19. 核心 Safety Contract 不变；
20. BoneX 1.2.6 Hotfix 仍保持独立支持工具，BONEWEAVER Runtime 不导入或修改 BoneX 状态。

---

# 22. Codex 执行约束

将本文件交给 Codex Goal Mode 时，附加以下执行要求：

```text
先读取：
- architecture.md
- algorithms.md
- safety.md
- compatibility.md
- blender-panel-interaction-refactor-report.md
- bonex-1.2.6-draw-context-hotfix.md
- manual-test-bonex-wiggle.md

本轮不得重写核心转换算法，除非对应 UI-R07 中明确列出的稳健性修正。

先完成 UI-R01 和 UI-R02，再改 Panel。
不得先画新面板，再继续沿用分散的 runtime 状态写入。

所有 Operator 必须成为 Controller 的薄适配。
所有 Panel 必须只消费 ViewModel。
Preview Handler 只能由 PreviewController 管理。
所有新增稳定枚举必须集中定义。
所有算法行为变化必须升级 algorithm_version。
所有 Schema 行为变化必须升级 schema_version。
不得通过降低安全校验换取更顺畅的 UI。
不得删除现有 transaction / rollback / digest / neutral mesh 验证。
```

---

# 23. 最终交付物

```text
docs/interaction-refactor-plan.md
docs/user-workflow.md
artifacts/ui-state-contract.md
artifacts/performance-audit.md
artifacts/algorithm-followup-audit.md
artifacts/ui-integration-test-report.md
```

最终报告必须分别声明：

```text
已确认并修复的问题
实测后未复现的风险
仍需真实 BoneX/Wiggle 验证的项目
本轮是否修改 algorithm_version
本轮是否修改 JSON schema_version
```
