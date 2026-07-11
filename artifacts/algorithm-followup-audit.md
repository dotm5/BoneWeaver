# Algorithm Follow-up Audit

## 已确认并修复

- Candidate 在计算 Margin 前按 7.5 度聚类；同向 PCA/Imported/Parent 证据不会制造假歧义。
- 多 Mesh 权重证据先分 Mesh，再按拓扑连通分量处理；冲突或相近断开岛不会产生指向空白区域的自动末端。
- 验证容差按 Mesh 的 object-local bbox 单独计算，world-space 仅用于诊断。
- Imported Axis prior 现在检查 `orig_loc`/`orig_quat`/`post_quat` metadata；无可靠 metadata 时先验由 0.5 降为 0.1，且与权重/父链都不一致时增加 penalty。

## 实测后未复现的风险

- Minimal Twist 镜像 fallback 的左右半球一致性回归测试通过，未复现随机相反 Roll。
- 真实 85 骨资产没有未解决分叉；两个分叉均得到稳定主路径。

## 版本

算法版本升级为 `uecp-physics-graph-v3-interaction-hardening`。交付分支已随后端强化把 Schema 从 3.0.0 升级至 `3.1.0`；本节记录的 Imported Axis/交互补丁没有在 3.1.0 之上再次改变 JSON 结构。
