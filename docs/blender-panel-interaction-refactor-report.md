# UE Chain Prep：Blender 面板与交互逻辑现状报告

> 审计范围：`ue_chain_prep` 当前源码中的注册、RNA 属性、3D View 侧栏面板、UI 列表、操作器与其直接调用的编排/事务模块。
>
> 审计目的：为下一轮 UI 与交互重构建立现状基线；本报告不改变插件行为，也不包含 Blender 运行时验证结论。

## 1. 结论摘要

当前插件只有一个可见面板：`View3D > Sidebar > UE Chain Prep`。它把配置编辑、分析结果浏览、预览、应用、校验、恢复和导出集中在一个纵向面板中。操作流程本质上是：

```text
Scene Settings + Blender Context
        |
        v
  Analyze -> ConversionPlan (进程内) -> UI 列表 / 预览缓存
        |                                  |
        v                                  v
   Apply（指纹校验）                   Viewport Draw Handler
        |
        v
 Snapshot (bpy.data.texts) -> 内置后校验 -> RESTORABLE
        |
        +-> Validate -> Diagnostic Report (进程内) -> Export JSON
        |
        +-> Restore -> Snapshot 冲突校验 -> RESTORED
```

最需要优先处理的不是算法本身，而是 UI 状态边界：`ConversionPlan`、诊断报告和预览缓存都只存在于模块级内存；面板却依赖持久化的 `plan_id`、状态码和快照名来表达流程。这会使重新加载插件、打开新文件、切换窗口或恢复快照后的界面语义不完整，且目前没有明确的失效提示与恢复路径。

## 2. Blender 接入与数据所有权

| 层级 | 现状 | 生命周期 | 重构含义 |
| --- | --- | --- | --- |
| 扩展入口 | `ue_chain_prep/__init__.py` 声明位置为 View3D Sidebar；`registration.py` 统一注册 | 加载/卸载插件 | 保留集中注册入口；后续可将 UI 注册与运行时清理拆成独立生命周期服务。 |
| Scene 设置 | `Scene.uecp_settings`，含范围、终端推断、权重、滚转、预览和校验参数 | 随 `.blend` 持久化 | 适合保存用户意图，但应按“基础/高级/显示”拆组。 |
| WindowManager 运行状态 | `WindowManager.uecp_runtime` 与三个 Collection | 当前 Blender 会话 | 适合 UI 选择与状态，但需定义重开文件、重载插件后的降级语义。 |
| 模块级运行时仓库 | `Plan`、预览缓存、报告、性能指标 | Python 进程内；重载即丢失 | 当前最大边界风险。不要仅保存 `plan_id`，应有可检测的“计划不可用”状态。 |
| Blender Text 快照 | `UECP_SNAPSHOT::<id>` | `.blend` 内持久化 | 是当前唯一跨会话的回滚依据；可发展为可浏览的历史记录。 |
| Viewport Draw Handler | 模块全局 `_HANDLER`、`_CACHE` | 当前 UI 会话 | 应由单一 PreviewController 所有，避免状态码与 handler 实际状态分叉。 |

关键实现位置：

- 注册与卸载：`ue_chain_prep/registration.py:16-43`
- Scene/WindowManager 属性：`ue_chain_prep/properties.py:42-165`
- 内存仓库：`ue_chain_prep/core/runtime_store.py:8-57`
- 预览 handler：`ue_chain_prep/ui/draw.py:8-48`
- 快照事务：`ue_chain_prep/core/apply_transaction.py:62-167`

## 3. 当前面板结构

主面板为 `UECP_PT_main`，位于 `VIEW_3D / UI / UE Chain Prep`。没有子面板、折叠分组或向导页。

| 面板区域 | 显示内容 | 直接绑定状态 | 条件显示 |
| --- | --- | --- | --- |
| Context | `Plan State`、当前活动对象名 | `runtime.state`、`context.active_object` | 始终显示 |
| Scope | 作用范围、网格范围、物理配置 | `settings.scope_mode`、`mesh_scope`、`physics_profile` | 无 |
| Inference | 终端模式、骨骼轴、末端长度、置信度、Roll | 多个 `settings` 字段 | `ABSOLUTE` 显示绝对长度；不同 Roll 显示对应参考参数 |
| Weight Evidence | 权重阈值、指数、面积权重、排他模式、百分位 | `settings` | 无 |
| Preview & Diagnostics | 采样提示、长骨段阈值、位置 epsilon、问题计数 | `settings`、`runtime.issue_count_*` | 无 |
| Chain List | 根骨到叶骨 | `WindowManager.uecp_chain_items` | 有条目时 |
| Proposal List | 骨骼、角色、置信度 | `WindowManager.uecp_proposal_items` | 有条目时 |
| Issue List | 严重性、代码、消息 | `WindowManager.uecp_issue_items` | 有条目时 |
| Action 区 | Analyze、Preview、Apply、Validate、Restore、Export、Clear | 操作器 | 始终绘制 |

实现：`ue_chain_prep/ui/panel.py:8-77`；三个列表的渲染：`ue_chain_prep/ui/lists.py:6-22`。

## 4. 操作器与交互逻辑

| UI 操作 | 操作器 | 前置条件 | 状态/数据写入 | 副作用与结果 |
| --- | --- | --- | --- | --- |
| Analyze | `uecp.analyze` | 运行时存在且不忙 | 重建三个 UI Collection；写入 plan、性能、预览缓存；更新问题计数、`plan_id`、指纹、状态、generation | 调用分析管线，关闭已有预览，最终为 `ANALYZED`；无活动骨架则取消。 |
| Toggle Preview | `uecp.preview_toggle` | 执行时仅允许 `ANALYZED` / `RESTORABLE` | `runtime.preview_enabled` | 添加/移除 3D 视图绘制 handler；只渲染已缓存线段，不重新分析。 |
| Apply | `uecp.apply` | `ANALYZED`、无 blocker、存在内存计划、源与设置指纹未变 | `state`、`snapshot_id`、`snapshot_text_name`、`last_error` | Edit Mode 原子修改 tail/roll/connect；写入 Text 快照；内置后校验失败则回滚。成功状态为 `RESTORABLE`。 |
| Validate | `uecp.validate` | 执行时要求当前内存计划仍存在 | 写入进程内报告，必要时写 `last_error` | 采集当前中性网格并运行后校验；不改变流程状态。 |
| Restore | `uecp.restore_snapshot` | 无 `poll`；快照名、骨架、权重、修改器和当前骨骼后态必须匹配 | 成功时 `state = RESTORED` | 仅恢复 tail、roll、use_connect，并更新 Text 快照状态。 |
| Export | `uecp.export_report` | 进程内报告存在 | `settings.last_export_directory` | 打开文件选择器后写 JSON。 |
| Clear | `uecp.clear_runtime` | 无 | 清内存计划/报告/预览缓存，部分重置 runtime | 移除绘制 handler，状态回 `IDLE`；不修改场景骨架数据。 |

操作器实现：`ue_chain_prep/operators/*.py`。其中分析编排见 `core/planner.py:94-241`，应用事务见 `core/apply_transaction.py:62-167`，恢复见 `core/restore.py:19-77`，验证见 `core/validation.py:57-133`。

## 5. 状态机与关键失效路径

### 5.1 实际状态迁移

```text
IDLE
  | Analyze
  v
ANALYZED --(源/设置/内存计划不匹配)--> STALE
  | Apply
  v
APPLYING --(事务成功)--> RESTORABLE
  |                     |
  |                     +-- Restore --> RESTORED
  +--(校验失败且已回滚)--> ANALYZED
  +--(回滚失败)---------> ERROR
```

`PlanState` 还定义了 `APPLIED` 与 `VALIDATION_FAILED`，但当前操作器没有写入这两个状态（`ue_chain_prep/contracts.py:119-128`）。`Validate` 也不会改变状态。因此状态枚举表达的产品流程比实际 UI 流程更完整，二者已经开始漂移。

### 5.2 指纹保护

Apply 会比较当前骨架/网格指纹与分析时指纹，并单独比较设置指纹；任一变化都会使计划进入 `STALE`（`ue_chain_prep/operators/apply.py:30-57`）。预览显示相关设置被刻意排除在设置指纹之外（`core/fingerprint.py:52-69`），这是合理方向，但目前这些显示设置没有被完整消费。

### 5.3 预览逻辑

分析阶段将 Physics Graph 转成不可变线缓存；预览按钮只切换 handler（`ue_chain_prep/ui/draw.py:28-56`）。因此预览和分析解耦是正确的，但 handler 实际开启状态与 `runtime.preview_enabled` 是两套状态，需要由同一个控制器统一。

## 6. 已发现的交互与重构风险

| 优先级 | 发现 | 证据 | 重构建议 |
| --- | --- | --- | --- |
| P0 | 运行时计划只在内存，`plan_id` 可在 UI 中存在但对应计划已丢失 | `runtime_store.py:8-31` 与 `properties.py:86-101` | 引入 `PlanAvailability`/`SessionStatus`，在面板上明确显示“计划已丢失，需重新分析”；所有依赖计划的按钮共用 guard。 |
| P0 | 恢复后可能保留旧预览 handler | Restore 不调用 `disable_preview`，而预览仅允许分析/可恢复状态 | 在 Restore、Clear、Apply 前后通过 PreviewController 统一关闭或重建预览；不要直接写 `preview_enabled`。 |
| P1 | 多个按钮缺少 `poll`，面板始终给出可点击外观，失败路径没有 UI 解释 | Preview/Validate/Restore/Export/Clear 均未定义针对状态的 `poll` | 将“可执行性”和“失败原因”抽成共享 selector；禁用按钮旁显示下一步提示。 |
| P1 | `Clear Runtime` 名称与实际效果不一致 | 未清除三个 UI Collection、snapshot 字段、active index、generation | 明确拆为“清除分析结果”和“重置会话”；或补齐所有瞬态字段的清理契约。 |
| P1 | UI 列表选择状态混用 | Issue List 把 `runtime.active_chain_index` 作为 active property | 为 issue 增加独立 `active_issue_index`，并把选择变化连接到详情/高亮行为。 |
| P1 | 声明的操作器选项未被兑现 | `validation_scope`、`allow_partial`、`include_plan/include_weight_stats/include_snapshot_summary` 均未在执行逻辑中使用 | 本轮重构前决定“实现、隐藏还是删除”；避免 UI/API 暗示不存在的能力。 |
| P2 | 设置与可见界面不对称 | `terminal_overrides`、`create_role_collections`、多项 preview 开关等有 RNA 字段但没有主面板入口；`preview_show_*` 也未进入线缓存绘制 | 建立 Settings Schema 到面板字段的显式映射；未支持的字段移出公开设置或标记为实验项。 |
| P2 | 信息架构过密 | 单一面板连续呈现基础配置、算法阈值和结果 | 用工作流阶段拆成折叠子面板或分步卡片，将高级阈值放入 Advanced。 |
| P2 | 结果可观察性不足 | 面板未显示 `plan_summary`、`last_error`、性能指标、快照名/时间 | 增加只读状态摘要与“为什么不可 Apply”的诊断区。 |

## 7. 推荐目标结构

建议保留现有算法核心，先把 Blender 适配层拆成五个明确职责：

```text
ui/
  panels/              # 只负责 layout 与绑定 ViewModel
  lists/               # 只负责列表画法
  view_model.py        # 从 runtime/plan/snapshot 推导可见状态与按钮可用性
controllers/
  workflow.py          # Analyze / Apply / Validate / Restore 的状态迁移
  preview.py           # handler、缓存、重绘和清理的唯一所有者
  session.py           # 内存计划可用性、重载后降级、UI collection 同步
operators/
  *.py                 # 薄适配：poll -> controller command -> report
core/                  # 维持纯算法、事务与验证
```

目标原则：

1. Panel 不直接判断业务状态，只渲染 `PanelViewState`。
2. Operator 不直接散写 `runtime` 字段，只调用 Controller 并报告结果。
3. `Plan` 缺失、指纹过期、存在 blocker、正在执行等条件，都由一个可测试的状态推导函数决定。
4. PreviewController 是 draw handler 和 `preview_enabled` 的唯一写入者。
5. Snapshot 是可持久化的领域记录；内存计划是可丢失的会话缓存，UI 必须明确区分两者。

## 8. 建议的面板信息架构

建议仍保留一个 Sidebar 入口，但改成阶段化子面板：

| 阶段 | 子面板 | 默认内容 | 主要动作 |
| --- | --- | --- | --- |
| 1 | Setup | Scope、Mesh、Profile；当前活动骨架状态 | Analyze |
| 2 | Inference | Terminal、Axis、Roll；常用阈值 | Re-analyze |
| 3 | Results | 计划摘要、blocker/warning、Chain/Proposal/Issue 列表 | Preview、定位问题 |
| 4 | Apply | 指纹状态、可应用原因、影响范围 | Apply |
| 5 | Verify & Recovery | 验证结果、报告导出、最新快照 | Validate、Export、Restore |
| Advanced | Advanced Settings | 权重与采样细项、实验/隐藏字段 | 无直接流程动作 |

这不是多页面向导：用户仍可快速从一个面板完成工作，但面板优先显示“当前阶段的下一步”和“为何不能继续”。

## 9. 分阶段重构计划

### Phase A：先固化状态契约

1. 为运行时状态定义唯一的 `SessionViewState`，至少包含计划可用性、指纹状态、预览实际状态、最新快照和下一步提示。
2. 给 Issue 增加独立 active index；定义所有 WindowManager 临时字段的 reset 契约。
3. 清理或落实当前未使用的操作器属性与状态枚举。
4. 把 `Clear Runtime` 拆为语义明确的命令，或使其真正清空声明的会话状态。

验收：不重新运行算法也能从任意状态推导出按钮是否可用及其原因。

### Phase B：抽取控制器，保持 UI 外观基本不变

1. 新建 `WorkflowController`，承接 Analyze/Apply/Validate/Restore 的 runtime 写入。
2. 新建 `PreviewController`，承接缓存、handler 开关、状态同步与卸载清理。
3. 让 Operator 仅负责 Blender 的 `poll/execute/report` 薄层。

验收：同一条流程不再在多个 Operator 中手工维护相同状态字段；恢复、清理、卸载都不会留下预览 handler。

### Phase C：重构面板与反馈

1. 按建议的信息架构拆为子面板；默认展开 Setup 和当前阶段。
2. 对每个禁用动作显示短原因，例如“重新分析后设置已变化”。
3. 把摘要、错误、快照、验证结果放入可见的只读状态区。

验收：用户不查看控制台即可理解当前计划是否有效、是否可 Apply、恢复是否可用。

### Phase D：补齐测试与迁移兼容性

1. 用纯 Python 测试覆盖 `SessionViewState` 推导和状态迁移。
2. 用 Blender 集成测试覆盖重载后计划丢失、Restore 后预览关闭、Clear 后列表清空、STALE 后 Apply 禁用。
3. 为已有 `.blend` 中缺少新 WindowManager 属性或 Text 快照字段提供安全默认值。

验收：UI 改动不改变核心 ConversionPlan、快照 JSON、诊断报告的既有 schema，或有明确的版本迁移策略。

## 10. 下一步决策清单

开始编码前建议先确认以下产品选择：

1. `ConversionPlan` 是否需要跨 Blender 会话可恢复？如果需要，应持久化完整计划或可重建输入；如果不需要，UI 必须把“重新分析”作为标准恢复动作。
2. `terminal_overrides`、角色骨骼集合与 preview 细项是正式功能还是预留 API？这决定其进入 Advanced、独立工具页还是被移除。
3. Restore 是否应支持部分恢复？当前 API 暴露 `allow_partial`，但实现是全量冲突即失败。
4. Validate 的产品含义是“Apply 内置校验的再次执行”，还是支持“从快照验证”？当前 `validation_scope` 尚未实现。

## 11. 源码索引

| 主题 | 文件 |
| --- | --- |
| 插件入口与注册 | `ue_chain_prep/__init__.py`、`ue_chain_prep/registration.py` |
| 属性与运行时状态 | `ue_chain_prep/properties.py` |
| 面板、列表、预览绘制 | `ue_chain_prep/ui/panel.py`、`ue_chain_prep/ui/lists.py`、`ue_chain_prep/ui/draw.py` |
| 用户操作 | `ue_chain_prep/operators/analyze.py`、`apply.py`、`preview.py`、`validate.py`、`restore.py`、`export_report.py`、`clear_runtime.py` |
| 分析、指纹、事务、恢复、校验 | `ue_chain_prep/core/planner.py`、`fingerprint.py`、`apply_transaction.py`、`restore.py`、`validation.py` |
| 状态与稳定 ID | `ue_chain_prep/contracts.py` |
