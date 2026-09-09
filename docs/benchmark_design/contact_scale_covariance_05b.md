# 05B co-scaled-τE 多尺度实施说明

范围仅为 `LEVEL_B_SCALE_PILOT`：A01 平面贴合与已修复 A07 轴孔贴合，尺度为 0.01、1、100，且 `tauE(s)=0.1*s mm`。每例使用冻结的 15 个 `q=δ/tauE`，共 90 项；不实施 fixed-absolute-τE、旋转、补缝或其他 Level B 因素。

从 05A 已归一化的 `L=100 mm` 解析尺寸直接同比构造。A01 固定切向覆盖，仅移动一个实体的法向 `δ`；A07 的轴、外半径、轴向范围和两端余量均同比缩放，并只令 `bore_radius=shaft_radius+δ`。每个尺度内这些 A07 控制量固定，且扰动后不再归一化。

1× 的 30 个 STEP 是 05A 已修复、只读的 tracked 输入，manifest 记录原路径与 SHA-256；仅生成 0.01× 与 100× 的 60 个 STEP。分析必须对重导入 B-rep 测量 signed offset、L、面积、体积及 A07 控制量，随后独立构造 expected 进行比较。工程分类、exact geometry 与直接 Fuse 保持独立记录。

固定比较方式为：长度除以 `s`、面积除以 `s²`、体积除以 `s³`，分别与独立的 1× 解析 expected 比较；同时保留原始误差和 05A 的固定绝对验收结论。05A 的算法阈值、FreeCAD/OCCT 设置和 `tauK` 不变；固定阈值造成的尺度效应会记为 `METHOD_MISMATCH` 或 `NUMERICAL_LIMIT`，不会反调阈值。

完整运行生成两个彼此独立的 FreeCADCmd 批次、四个代表性 FCStd（两例在 0.01× 和 100× 的 q=+0.5）、CSV、统计和结论。停止条件是所有 90 项均有必需输入/actual/expected/validation 字段且两批次均运行结束；无效、超时、不支持和方法不匹配均留在分母。
