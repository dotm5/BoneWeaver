# UI Integration Test Report

## 自动化结果

- Blender：5.2.0 LTS RC `710df102694f`
- 命令：`blender.exe --background --factory-startup --python tests/run_blender_tests.py -- --verbose`
- 结果：160 run，0 failures，0 errors，0 skipped。

覆盖包含 ViewModel 全状态映射、唯一主动作、Plan Lost、Settings/Selection Stale、Preview Controller、Load/Undo/Redo handlers、Clear/Restore 清理、算法设置与 Preview-only 设置差异、Operator 薄适配、主面板结构、Developer 默认隐藏、RNA 列表 lazy、Apply/transaction/rollback、ZIP 注册循环以及算法/性能回归。

## 真实模型

`C:\Users\70560\Documents\Blender项目\x1.blend` 在 `--factory-startup` 下完成 85 Bone Analyze → Apply → Export → 独立 Blender 重开验证：0 blocker、82 warning、85 proposal、85 mutation，状态 `RESTORABLE`，源文件 SHA-256 与时间戳不变。

首次使用用户配置的后台运行在进入算法前被已安装旧版 UECP 和后台不兼容第三方插件阻断；隔离运行通过，证明该失败属于用户配置污染而不是本轮代码回归。

## 仍需人工验证

- BoneX 1.2.6 物理生成、播放与 bake。
- Wiggle 2 RTX 2.2.5 的旋转链/伸缩链实际动态行为。
- Issue 定位后的交互式 viewport framing 观感与 Apply 对话框排版。

## 发布包

Blender extension build 与隔离安装/三次注册循环通过。`dist/ue_chain_prep-0.1.0.zip` 为 95,147 bytes，SHA-256 `0F4C47E9A427B1AFE6754A75FB9814BB0CF3AA47B98E8A103312C8B6A17E5CEA`。
