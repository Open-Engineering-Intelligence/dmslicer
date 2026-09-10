# 05B co-scaled-τE 多尺度实施说明

范围仅为 `LEVEL_B_SCALE_PILOT`：A01 平面贴合与已修复 A07 轴孔贴合，尺度为 0.01、1、100，且 `tauE(s)=0.1*s mm`。每例使用冻结的 15 个 `q=δ/tauE`，共 90 项；不实施 fixed-absolute-τE、旋转、补缝或其他 Level B 因素。

从 05A 已归一化的 `L=100 mm` 解析尺寸直接同比构造。A01 固定切向覆盖，仅移动一个实体的法向 `δ`；A07 的轴、外半径、轴向范围和两端余量均同比缩放，并只令 `bore_radius=shaft_radius+δ`。每个尺度内这些 A07 控制量固定，且扰动后不再归一化。

1× 的 30 个 STEP 是 05A 已修复、只读的 tracked 输入，manifest 记录原路径与 SHA-256；仅生成 0.01× 与 100× 的 60 个 STEP。分析必须对重导入 B-rep 测量 signed offset、L、面积、体积及 A07 控制量，随后独立构造 expected 进行比较。工程分类、exact geometry 与直接 Fuse 保持独立记录。

固定比较方式为：长度除以 `s`、面积除以 `s²`、体积除以 `s³`，分别与独立的 1× 解析 expected 比较；同时保留原始误差和 05A 的固定绝对验收结论。05A 的算法阈值、FreeCAD/OCCT 设置和 `tauK` 不变；固定阈值造成的尺度效应会记为 `METHOD_MISMATCH` 或 `NUMERICAL_LIMIT`，不会反调阈值。

完整运行生成两个彼此独立的 FreeCADCmd 批次、四个代表性 FCStd（两例在 0.01× 和 100× 的 q=+0.5）、CSV、统计和结论。停止条件是所有 90 项均有必需输入/actual/expected/validation 字段且两批次均运行结束；无效、超时、不支持和方法不匹配均留在分母。

## 验收口径补齐（revalidation v2）

原始实验的 `native_validation` 只覆盖分类、exact dimension 与 signed offset；它没有以固定绝对误差限逐项比较同尺度的实际共同面积或共同体积。因此其 PASS 不能解释为 native absolute 量纲验收通过。原始 `actual.json`、输入、expected、阈值和几何构造均保持不变；补齐工作只读取两轮已保存的 actual 记录。

重验收输出两套独立结论：`native_absolute_validation` 将实际长度、面积、体积同**同尺度独立 expected** 比较，使用 05A 的固定绝对限（不乘 scale）；`scale_normalized_validation` 分别以 `s`、`s²`、`s³` 归一化后同独立 1× expected 比较，复用既有基准限。面积/体积不适用时明确记为 `NOT_APPLICABLE`；正间隙仍检查零交集。分类、A07 construction、direct Fuse 与输入证据另列，不混入两类量纲误差。

主实验判据没有改为“双口径均须 PASS”：仍是原先的尺度协变主判据，即分类与 construction 正确、且 `scale_normalized_validation` 通过。`method_mismatch_count` 为保持兼容仅表示这一主判据的归一化超差数；native fixed-absolute 结果单列。

从保存的 90 对独立测量记录重验收得到：native absolute 超差 16 项、scale normalized 超差 1 项、classification/construction/evidence 超差均为 0。保留的 A07、s=0.01、q=0 面积项原始误差为 `-1.3045675650857902e-12 mm²`，归一化误差为 `-1.3046701496932656e-8 mm²`；前者在固定面积限内、后者超过 `1e-8 mm²`，因此仍是 `METHOD_MISMATCH`。此次重验收未调用 FreeCAD，也没有新增几何测量。
