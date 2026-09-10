# 07A 圆柱接口可修复性与位置校正

## 科学边界

07A 对两个明确角色的实体执行固定顺序：从重导入 STEP 的实际 B-rep 提取圆柱面，先完成候选唯一性、轴线、半径、轴向覆盖和当前交集测量，再分类、判断可修复性和检查动作策略。只有 `AXIS_TRANSLATIONAL_MISALIGNMENT` 可提出一次 Side_2 pure translation；半径差、角度差、复合误差和多候选均零动作。

Side_1 是固定 bore，Side_2 是可移动 shaft。`axis_offset_vector_mm` 从 bore target axis 指向 shaft current axis，并通过无限直线的正交投影计算；校正恒为其相反向量。轴向点表示、轴方向反号、world origin、surface minimum distance、AABB、Face ordinal、hash、fixture ID 和 expected 均不参与修正向量。

## 圆柱测量与分类

当前支持完整 `2π` 周期、具有两个圆形端界的 trimmed cylindrical band。每个候选记录实际 surface family、axis point/direction、radius、axial interval、UV/periodic trim、area、shaft/bore role evidence 和 source occurrence。角色来自 oriented face normal 相对 radial direction 的符号，并以实际实体材料侧 probe 复核；不可靠时 fail closed。

半径符号沿用 05A–05C：`radial_clearance_mm = bore_radius - shaft_radius`。正值为 `DIMENSIONAL_RADIAL_CLEARANCE`，负值为 `DIMENSIONAL_RADIAL_INTERFERENCE`。连续判据分别使用 manifest 中声明的 `mm`、`rad`、`mm²`、`mm³` tolerance，不量化后 hash。

C02 的 equal-radius eccentricity 被如实记录为错误 CAD pose：其圆柱表面最短距离为零，轴向重叠区却有正材料交叠体积，另一侧同时 separation。它不是 positive gap，也不表示物理装配路径可行。执行除 `allow_motion` 外还必须明确 `allow_pose_interference_resolution`，并同时通过 `tauE_mm` 与 `max_translation_mm`。

## 场景与历史复用

- C01、C03、C04 逐字节复用 05A 的 nominal、`+0.5τE`、`-0.5τE` A07 STEP；新 manifest 记录源路径与 SHA-256，hash 只证明 byte integrity。
- C02 从 A07 尺寸生成 `0.05 mm` 横向偏心；C05 生成 equal-radius angular mismatch。
- AMBIGUOUS 是非 principal control；同一个 Side_1 实体提供多个 role-valid bore faces，必须在任何遍历顺序下拒绝。
- 03B 的 actual cylindrical common、04B 的 partition/Fuse、05 系列的半径符号和 06 系列的授权、一次动作、失败关闭、逆变换等价与人审约定被复用；历史模块和 frozen research contract 未修改。

## Postcheck 与证据

C02 执行后重新提取 corrected B-rep，验证 residual axis offset、axis angle、radius、axial overlap、actual cylindrical common、material intersection、coverage/remaining、Fuse validity/closedness/volume conservation。Side_2 应用 inverse translation 后，以双向 cut 与 minimum distance 对照 original。Corrected assembly STEP、fused STEP 和 Common BREP 被独立 FreeCADCmd 重读，并用实际 B-rep 双向差、distance、area、volume和 topology 验证；文件 SHA-256 另列为 byte integrity，绝不代替几何等价。

每次运行输出 `operation.json`、`validation.json`、`expected_snapshot.json` 和 `operation_debug.FCStd`。suite 用两次独立 FreeCADCmd 的 tolerance-aware actual projection验证 repeatability，并提供 `VIEW_INDEX.md` 与 `HUMAN_REVIEW/README.md`。关键证据尚未通过 P2 promotion line 建立稳定可恢复副本时，不声称 fully preserved。

## 命令

```powershell
$env:PYTHONPATH='src'
py -m dmslicer generate-cylindrical-interface-repair-07a benchmarks/cylindrical_interface_repair_07a
py -m dmslicer run-cylindrical-interface-repair-case-07a benchmarks/cylindrical_interface_repair_07a/C02 outputs/cylindrical_interface_repair_07a/C02
py -m dmslicer run-cylindrical-interface-repair-suite-07a benchmarks/cylindrical_interface_repair_07a outputs/cylindrical_interface_repair_07a
py -m pytest tests/test_cylindrical_interface_repair_07a.py -q
```

完整 regression 仅在本 Goal 最终实现和限定 reviewer 修复完成后运行一次。
