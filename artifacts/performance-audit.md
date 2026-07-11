# Interaction Refactor Performance Audit

## 已确认并修复

- Analyze 使用 `MeshScanCache`，真实 85 骨模型记录 `vertex_pass_count=1`、`membership_pass_count=1`。
- 中性网格基线从嵌套 Python tuple 改为连续 `array('d')`，比较过程流式计算 max/mean/RMS/outlier，不再创建百万个 delta 对象。
- Draw callback 改为缓存 GPU batch；同一 Preview 生命周期不再每帧调用 `batch_for_shader`。
- Analyze 后 RNA Chain/Proposal/Issue 列表保持为空；Details 显式按需生成，单类最多 200 条。
- Analyze 记录 `tracemalloc_peak`、`preview_build_time` 和 `ui_item_count`，并使用 Blender progress API。

## 实测

Blender 5.2 RC、`x1.blend`、85 个目标 Bone：Analyze 43.087 s，tracemalloc peak 10,155,672 bytes，Preview cache 构建 0.000194 s，UI item count 0。Apply、导出和独立重开验证均通过；源文件前后签名一致。

程序化规模契约覆盖 100 Bones/100k Vertices、300/500k 与 500/1M，紧凑权重点缓冲按每个选中顶点 36 bytes 线性增长。固定秒数不作为跨机器 Gate。
