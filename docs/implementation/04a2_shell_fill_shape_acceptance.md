# 04A2 球壳填充与形状验收

本轮修正 04A 的两个验收表达问题，并新增与冻结 A01–A13 分离的操作案例 U01–U03。A08 的 fixture、parameters、expected 和几何均未修改；生成的查看说明现在明确其输入是“完整小球＋上半大球壳”，融合后外露的小球下半球面不是封闭空腔内壁。04A 的最终状态门现在把 `volume_error_mm3 <= volume_epsilon_mm3`、单一连通 Solid、有效性和闭合性全部纳入判断，并为失败条件输出结构化 `failures`。

三个新案例都固定 `R=30 mm`、`r=20 mm`、球心原点、上半球 `z>=0`，并显式使用球面角度范围。`benchmarks/shell_fill_04a2/` 中每例保存 `parameters.json`、`expected.json` 与两个独立实体组成的 `inputs.step`。生成命令是：

```text
py -m dmslicer generate-shell-fill-cases benchmarks/shell_fill_04a2
```

正式运行从 tracked STEP 重新导入 Side 1 球壳和 Side 2 内部实心件，再执行实际 common/cut/fuse。实际 operation evidence 写出后才读取 expected，并用独立构造参考体进行双向材料差集、解析体积和表面积、内外采样、边界/空腔状态、有效闭合连通性以及 STEP 往返验证。U01 参考完整 `Ball(R)`；U02 参考 `z>=0` 的 `Ball(R)`；U03 参考完整 `Ball(R)` 减去应保留的下半内腔。

验收输出命令是：

```text
py -m dmslicer run-shell-fill-suite benchmarks/shell_fill_04a2 outputs/shell_fill_04a2
```

本地查看入口为 `outputs/shell_fill_04a2/VIEW_INDEX.md`。每例的 `operation_debug.FCStd` 含 `Originals`、`Partitions`、`Union_Result`；保存并重开后验证默认只显示融合结果。若某 headless FreeCAD 环境不保留显示状态，可在 GUI 控制台运行输出目录的 `view_shell_fill.py`。

最终验收实测如下：

| 案例 | 共同面积 mm² | coverage（壳/内件） | 剩余承载面（壳/内件） | union solid/shell | union 体积 mm³ | 双向参考差集 mm³ |
|---|---:|---:|---:|---:|---:|---:|
| U01 | 5026.548245743667 | 1 / 1 | 0 / 0 | 1 / 1 | 113097.33552923256 | 0 / 0 |
| U02 | 2513.274122871834 | 1 / 1 | 0 / 0 | 1 / 1 | 56548.667764616286 | 0 / 0 |
| U03 | 2513.274122871834 | 0.5 / 1 | 1 / 0 | 1 / 2 | 96342.174710087 | 0 / 0 |

三例均为 valid/closed；共同面均已从融合边界消除，STEP 重导入形状一致，两进程几何复现通过。U03 验证下半内球面面积 `2513.2741228718282 mm²`、赤道圆盘面积 `1256.6370614359173 mm²`，并以内部采样证明下半内腔为空、上半已填充。U01 的同半径错误候选“半球壳＋完整小球”和 U03 的“填满下半内腔”候选都被拒绝。最终完整回归为 83 项测试、0 failures、0 errors、0 skipped。
