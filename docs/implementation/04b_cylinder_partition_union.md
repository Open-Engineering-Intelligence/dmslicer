# 04B 圆柱套筒部分贴合与融合

范围限定为三个同轴圆柱操作案例 U04--U06。实现复用 04A2 的受追踪 STEP
输入、实际 B-rep `common`/`cut`/`fuse`、STEP 往返、FCStd 分组和独立参考验收
流程；不会改造 Contact framework。

新增内容是直接以最终尺寸建立闭合套筒与芯轴、按实际半径和轴线聚合内/外圆柱
承载面，以及圆柱轴向分段的独立参考。U04 的全部 40 mm 承载带重合；U05 的芯轴
为 0--20 mm；U06 的芯轴为 -80--20 mm。预期共同面积分别为
1600π、800π、800π mm²，coverage 分别为 [1,1]、[0.5,1]、[0.5,0.2]。

开发定向命令：`py -m pytest tests/test_cylinder_partition_union_04b.py -q`。
正式执行：`py -m dmslicer generate-cylinder-fit-cases benchmarks/cylinder_fit_04b`，
然后 `py -m dmslicer run-cylinder-fit-suite benchmarks/cylinder_fit_04b
outputs/cylinder_fit_04b`。最终只执行一次相关完整回归。
