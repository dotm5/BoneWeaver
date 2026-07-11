# UI State Contract

`PanelViewState` 是主面板的业务状态输入。纯函数 `derive_panel_view_state()` 接收 Blender 上下文摘要、运行时摘要、Plan 可用性、当前选择/设置签名和快照摘要，返回唯一的 `WorkflowStage`、一个主动作、次级动作和自然语言说明。

| Stage | 条件摘要 | 主动作 |
|---|---|---|
| `NO_CONTEXT` | 无可用 Armature | 无 |
| `READY_TO_ANALYZE` | 有目标、无有效 Plan | 检查并预览 |
| `ANALYZING` | Analyze 进行中 | 禁用的进度动作 |
| `READY_TO_APPLY` | Plan 可用、无警告/阻断、签名一致 | 应用转换 |
| `NEEDS_ATTENTION` | 无阻断、有警告 | 应用转换 |
| `BLOCKED` | 有 Blocker | 重新检查/处理问题 |
| `STALE_SETTINGS` | 设置签名变化 | 重新检查 |
| `STALE_SELECTION` | 选择签名变化 | 重新检查 |
| `PLAN_LOST` | UI 有 Plan ID、内存 Store 无 Plan | 重新检查 |
| `APPLYING` | Apply 进行中 | 禁用的进度动作 |
| `APPLIED` | Apply/验证成功 | 检查另一条骨骼链 |
| `ROLLBACK_FAILED` | `UECP_ROLLBACK_FAILED` | 重置本次会话 |
| `ERROR` | 其他不可恢复错误 | 重置本次会话 |

主面板不得显示原始 Issue Code、数值 Confidence、Plan ID 或 Fingerprint。算法设置回调使当前 Analyze Plan Stale 并关闭 Preview；Preview-only 设置只重绘，不改变 Plan 指纹。
