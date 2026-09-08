# 04A 接触面分割与实体融合

范围仅为冻结 STEP 案例 A02（平面局部贴合）和 A08（球体与球形空腔内壁上半球贴合）。每次操作都重新导入 tracked STEP，使用直接 B-rep face common 取得共同二维面片；`expected.json` 不参与面片选择、裁剪或融合。

对每个实际参与面 `F`，输出共同部分 `C_F`，并通过 `F.cut(C_F)` 输出剩余部分 `R_F`。验收为 `area(F) ~= area(C_F)+area(R_F)`，共同/剩余正面积交叠为零，且其并集不离开原面。空剩余记录为空，不伪造零面积 Face。非空面片分别导出 BREP 和 STEP。

原始两个 solids 保留；融合使用其副本的 OCC `fuse(...).removeSplitter()`，得到新的 `U`，不以 compound 或删除整张面代替。验收记录一个连通 solid、每个实际 shell 闭合、有效性、体积守恒、输入材料包含、无额外材料、共同面不在 U（及其 STEP 重导入）边界上。A08 额外从 B-rep 确认两个封闭有效 solid、球形内壁共同面和无实质体积穿透；它允许 U 有多个 shell，以保留空腔边界。

每例输出 `operation.json`、`validation.json`、面片导出、`fused.step` 和含 Originals / Partitions / Union_Result 三个可切换组的 `operation_debug.FCStd`。重复性调用两个独立 FreeCADCmd 进程，并比较共同面、分割、融合和验证证据。
