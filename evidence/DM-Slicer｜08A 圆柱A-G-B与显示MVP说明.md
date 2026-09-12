# DM-Slicer｜08A 圆柱A-G-B与显示MVP说明

## 当前显示 MVP

`CASE01-GEOMETRY-DISPLAY-01/case01-brep-display-20260912-006/` 是当前可检视
的 A–G–B 平面演示。它从 STEP 重导入的 FreeCAD/OCCT B-rep 生成三 Region 与两个
确认公共面 Patch；网格仅用于显示，不能成为 Geometry 真相。

检视器是有意很小的数据驱动工具：Regions、Interfaces、Patches 可折叠，支持文本
过滤和每组 All/None。显示开关只改变 display mesh 的可见性；它不执行 Union，也不
表示路径可以跨越接口。选择信息保留稳定 `entity_ref`。

## 圆柱证据审计

仓库没有已验证的三个圆柱 A–G–B fixture。现有圆柱几何证据是两个实体的 sleeve/core
情形：

- `benchmarks/cylinder_fit_04b/U04_cylinder_full_fill`、`U05_cylinder_short_core`、
  `U06_cylinder_unequal_overlap`；执行器在
  `src/dmslicer/cylinder_partition_union_04b.py`。
- 04B 从重导入 STEP 测量正面积圆柱 common、partition remaining 与 fuse 后结果；
  其测试检查 U04–U06 的面积、coverage、remaining patch count、体积以及最多
  `1e-6 mm3` 的 reference 差异。它不是三个 Region A–G–B 接触链，也不能仅由文件
  SHA-256 推导几何等价。
- 07A 位于 `benchmarks/cylindrical_interface_repair_07a/`，执行器是
  `src/dmslicer/cylindrical_interface_repair_07a.py`。它仅覆盖圆柱接口：C01 exact
  contact、C02–C04 可支持的平移/间隙状态、C05 angular misalignment 拒绝、以及
  ambiguous control。其显式阈值为 linear/radius `1e-7 mm`、area `1e-8 mm2`、
  volume `1e-6 mm3`、angular `1e-7 rad`。

07A **不能**用于任何球面结论；球面尚未完成几何验证。

## 三圆柱 A–G–B 的最小后续构造

可复用 04B 的 FreeCAD sleeve/core construction 和实际 common/partition 验证，但不应
重写其算法。最小新 case 需要一个明确 Geometry 决定：G 是一个与 A、B 分别共享圆柱
载体的单一 shell/solid，还是两个各自独立的圆柱接口面。决定后，应新增独立 fixture，
以两个已确认公共圆柱面、明确 mm 容差、每对候选/确认状态、STEP 重导入测量和失败
fixture 为验收；不以现有二体 case 或 hash 代替验证。
