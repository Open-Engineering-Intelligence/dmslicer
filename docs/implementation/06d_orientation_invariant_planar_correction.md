# 06D 任意朝向平面接口协变校正

## 范围与设计

06D 只扩展 06C 已验证的两体平面 FaceSet 校正，使整个问题可处于任意 world orientation。`Side_1` 固定，`Side_2` 不旋转、不缩放、不变形，只执行一次 `t=-gap*n` 刚体平移；`n` 是调用者显式提供的 `reference_direction`。本轮不是自动方向发现、姿态配准或 assembly mate solver。

Host 层严格验证并保存 raw direction、original norm 与 normalized direction；缺失、零向量、NaN、inf、bool 或错误长度均 fail closed 为 `UNSUPPORTED_INVALID_REFERENCE_DIRECTION`，零 motion、no Fuse，不回退到 `+Z`，也不自动翻转 `-n`。FreeCAD adapter 只接收重导入 STEP、roles、direction 与 policy；fixture 的 R/q、基础尺寸和 expected 不进入正式几何分析请求。

## world-axis 审计

06C 直接调用链中的 orientation-sensitive 假设为固定 `REFERENCE=(0,0,1)`、`normal.dot(REFERENCE)`、`plane.Position.dot(REFERENCE)`、公开证据的 `[0,0,±1]`、preview/actual `(0,0,-gap)` 与重导入时的同一组假设。06D 将 reference 设为经验证的单位 n：Side_1 要求 outward normal≈+n，Side_2≈-n；support 为 `dot(P,n)`，FaceSet 按有单位线性 epsilon 分组，gap 为 `s2-s1`，平移为 `-gap*n`。`_bounds`、`_center`、`_shape_sort_key` 只稳定单次序列化顺序，不参与跨 orientation identity、correspondence 或 acceptance。

## fixtures 与解析几何

D01 是 P07 语义绕 world Y +45° 后平移 `[17,-23,31]`；D02 是 P10 multipatch，以 proper rotation 将 +Z 映到 `normalize([1,2,3])` 后再绕该方向 roll 37°，平移 `[-41,13,27]`；D03 是 P11 annulus 的 `Rz(17°)Ry(-28°)Rx(31°)` 与 `[29,47,-18]`。生成器使用 FreeCAD `Placement/Rotation`，不使用 `transformGeometry`，并记录变换前后 Plane/Circle 等 surface/boundary curve family。

每个 benchmark bundle 将 `reference_direction` 放在 operation semantics，将 R/q 与构造参数放在 generation manifest，将解析数值放在 expected。正式 runner 在 generator 关闭后重新导入 tracked STEP。R/q 只供最后的独立 covariance validator 使用。

## covariance 与 hash policy

Host 直接比较 gap、common/remaining area、coverage、volume、Fuse 与 topology counts，并验证 `reference'=R*n`、`translation'=R*t`。FreeCAD validator 对 transformed Common、Remaining、Corrected Side_1、Corrected Side_2 与 Fused 施加 inverse rigid Placement，再用实际 B-rep minimum distance、双向 cut、area/volume、valid/closed、surface family 与 topology 建立等价证据。multipatch 使用 bipartite geometry correspondence；不依赖 patch ID、Face ordinal、hash 或 world-AABB order。

文件 SHA-256 只证明 input/artifact exact bytes。`representation_identity` 与 `geometric_equivalence` 分字段报告；representation 不同不导致几何失败，真实 B-rep 位移超过 epsilon 即使记录 hash 未变也必须失败。invalid R、scale、shear 或 det=-1 reflection 均不能通过 proper rotation validator。

## 验证与边界

定向测试覆盖 D01/D02/D03、invalid/reversed direction、translation-only world-origin control、切向或 world-Z 错误平移、面积/拓扑/R 篡改、patch ID 重排、expected mutation、artifact bytes 替换、representation-vs-geometry 分离、STEP round-trip、二进程 repeatability、FCStd visibility 与 06C P10 的 +Z B-rep compatibility。

当前真实支持范围仅是明确 Side_1/Side_2、明确 reference direction、平面、平行、相向、允许单次 pure-normal rigid translation 的两体接口，并且只声称对所测试共同 world proper rotation/translation 的几何协变性。不支持自动方向发现、自动旋转/配准、倾斜或非平行失配、曲面接口、多体 mate solving、field/gradient、slicing 或 G-code。
