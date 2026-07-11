# BoneWeaver 本地执行背景

## 当前任务边界

- 项目目标背景：制作 Blender 骨骼转换器，把 UE 导出的骨骼转换为 Blender 期望的骨骼链形式。
- 当前阶段仅做本地背景调查和前置条件验证；不要据此直接开始实现，也不要把尚未验证的骨骼规则当成既定需求。
- 工作目录：`D:\项目复现\BoneWeaver`。
- 本目录在 2026-07-11 调查时不是 Git 仓库（`git status` 返回 `not a git repository`）。

## Blender 操作位置

- 实际 Blender 可执行文件：`E:\SteamLibrary\steamapps\common\Blender\blender.exe`。
- 安装来源：Windows 卸载注册表显示为 Steam 安装，安装目录为 `E:\SteamLibrary\steamapps\common\Blender`。
- 当前实测版本：`Blender 5.2.0 LTS Release Candidate`。
- 构建哈希：`710df102694f`；构建日期为 2026-07-11。
- Blender 刚从 5.2.0 LTS Beta 更新到 RC；后续记录和验证均以可执行文件自报的 RC 版本为准，不再使用 Beta 作为当前环境标签。
- `blender` 当前不在 PATH 中；自动化、测试和复现时必须调用上述绝对路径，不要假定 `blender` 命令可用。
- 可用的只读版本检查：

  ```powershell
  & 'E:\SteamLibrary\steamapps\common\Blender\blender.exe' --version
  ```

- Blender 5.2 用户配置目录：`C:\Users\70560\AppData\Roaming\Blender Foundation\Blender\5.2\config`。
- Blender 5.2 用户脚本目录：`C:\Users\70560\AppData\Roaming\Blender Foundation\Blender\5.2\scripts`。
- Blender 5.2 用户插件目录：`C:\Users\70560\AppData\Roaming\Blender Foundation\Blender\5.2\scripts\addons`。

## UEFormat 导入前置条件

- `.uemodel` 不是 Blender 原生输入；本项目测试必须接入用户已经安装的 UEFormat 扩展。
- Blender 5.2 中已确认的扩展目录：`C:\Users\70560\AppData\Roaming\Blender Foundation\Blender\5.2\extensions\user_default\io_scene_ueformat`。
- 扩展模块名：`bl_ext.user_default.io_scene_ueformat`，当前处于启用状态。
- 扩展清单版本：`1.0.0`；名称为 `UE Format (.uemodel / .ueanim)`；最低 Blender 版本为 4.2.0。
- `.uemodel` 的实际 Blender operator：`bpy.ops.uf.import_uemodel`，RNA id 为 `UF_OT_import_uemodel`。
- operator 已确认提供 `filepath`、`directory`、`files` 和 `filter_glob` 参数，文件过滤器为 `*.uemodel`。
- 正常用户配置下，后台 Blender 已成功注册该 operator。因此 `.uemodel` 加载测试必须明确启用这份 UEFormat 扩展，不能仅用 Blender 原生工厂配置直接导入。

### 隔离测试策略

- 默认可以使用当前用户配置加载 UEFormat，但当前配置同时启用了大量无关插件；后台启动日志已出现第三方插件注册冲突和依赖 GPU 上下文的报错，这些噪声不应混入 BoneWeaver 的基线。
- 需要可重复的干净测试时，复制上述 `io_scene_ueformat` 扩展目录到独立测试环境，再用 Blender 工厂模式加载测试。
- 工厂模式不会自动启用用户安装的 UEFormat。隔离流程必须同时完成“复制扩展、把副本加入测试 Blender 可见的扩展/脚本路径、显式注册或启用扩展”，然后再调用 `bpy.ops.uf.import_uemodel`。
- 插件副本应放在项目独立测试输出/工具目录中，不要修改或覆盖用户现有的 UEFormat 安装，也不要把整个用户 Blender 配置复制进隔离环境。
- 隔离测试应继续调用 `E:\SteamLibrary\steamapps\common\Blender\blender.exe`，并带 `--factory-startup --background`；具体装载脚本在真正开展测试时另行建立和验证。

## 测试文件记忆

- 项目内测试目录：`D:\项目复现\BoneWeaver\test`。
- 2026-07-11 最终复查时共有 10 个 `.uemodel` 文件；项目内暂未发现 `.blend`、`.fbx`、`.psk`、`.pskx`、`.gltf` 或 `.glb` 测试文件。
- 测试资产清单：

  | 文件 | 字节数 | 修改时间 |
  | --- | ---: | --- |
  | `NHT1FuluoluoLifu.uemodel` | 9,041,375 | 2026-04-24 00:47:09 |
  | `NHT1Xiaoxiakong.uemodel` | 3,012,141 | 2026-04-24 00:49:07 |
  | `R2T1AnkeMd10011.uemodel` | 4,288,899 | 2026-04-03 23:30:39 |
  | `R2T1FeiBiMd10011.uemodel` | 6,294,151 | 2026-03-07 00:37:34 |
  | `R2T1JinxiMd10011.uemodel` | 5,818,094 | 2026-03-24 23:23:36 |
  | `R2T1MicaiMd10011.uemodel` | 4,411,134 | 2026-03-06 00:12:42 |
  | `SK_Aika_Lobby_S109.uemodel` | 3,971,106 | 2026-07-08 16:01:52 |
  | `SK_HuiXing_Lobby_S111.uemodel` | 2,771,405 | 2026-02-27 13:59:22 |
  | `SK_Kanami_Lobby_S103.uemodel` | 3,894,367 | 2026-02-26 01:57:19 |
  | `SK_Yvette_Lobby_S114.uemodel` | 3,245,200 | 2026-07-02 01:13:46 |

### 后续验证时的资产定位原则

- 默认从项目内 `test` 目录取样，不依赖 Downloads/Documents 中的外部副本。
- `SK_Aika_Lobby_S109.uemodel` 是当前目录中修改时间最新的样本，适合作为首次环境连通性检查样本。
- `NHT1FuluoluoLifu.uemodel` 是当前最大样本，适合在基础流程已连通后检查较大资产行为。
- `SK_HuiXing_Lobby_S111.uemodel` 是当前最小样本，适合做快速重复检查；这些选择只基于文件元数据，不代表已验证其骨骼结构覆盖面。
- 在首次真实导入前，应先记录源文件哈希；测试过程中不要原地改写 `test` 中的源资产，生成的 `.blend`、日志和快照应放到独立输出目录。

## 已确认与未确认的分界

已确认：

- Blender 的绝对可执行路径和版本可从命令行启动并复现。
- 项目当前测试输入格式为 `.uemodel`，且已有 10 个本地样本。
- Blender 5.2 用户配置已安装并启用 UEFormat 1.0.0，`.uemodel` 导入入口为 `bpy.ops.uf.import_uemodel`。
- 当前工作目录没有现成代码、说明文档或 Git 元数据可供继承。

尚未确认：

- UEFormat 副本在 `--factory-startup` 隔离环境中的最终目录布局和显式注册脚本尚未实际执行验证。
- 每个样本的骨骼数量、根骨、父子拓扑、局部轴、缩放和蒙皮数据是否完整。
- “Blender 期望的骨骼链形式”的精确定义和验收标准。
- 转换前后的基准 `.blend`、截图或结构化骨骼快照。

后续开始任何实现或行为修改前，应先完成 UEFormat 副本的工厂模式隔离加载验证，并保存至少一个样本的导入后骨骼结构快照；本文件中的未确认项不得被当作默认结论。
