# Level B Tolerance and Perturbation Protocol

## 1. 变量、尺度与判定

工程容差记为 `τE`，并与 STEP 文件或几何内核固有的拓扑容差 `τK` 完全分离。主锚点为 `τE = 0.1 mm`，与 Autodesk Assembly 标签的公开 engineering-contact 定义对齐；它不是对 Autodesk 未公开 face-distance 聚合实现的假设。`L` 一律为**当前 body-pair 合并包围盒对角线**，每个样本记录 `τE`、输入的 `τK`、单位、当前 `L` 与 `τE/L`。

法向 signed offset 为 `δ`：`δ>0` 是正间隙，`δ<0` 是 penetration。工程状态采用 inclusive boundary：

| 条件 | `engineering_state` |
|---|---|
| `δ=0` | `exact` |
| `0<δ≤τE` | `positive_gap_within_tolerance` |
| `δ>τE` | `positive_gap_beyond_tolerance` |
| `-τE≤δ<0` | `penetration_within_tolerance` |
| `δ<-τE` | `penetration_beyond_tolerance` |

边界 `|δ|=τE` 必须作为单独 strata 报告；不得并入远离阈值的稳定区。`intended_relation_dimension` 固定为名义 Level A 的工程意图（A13 为 `none`，A06 为 `3D`），但 `exact_intersection_dimension` 必须为**当前 post-perturbation 几何**重新标注；它可以从名义 `2D` 变为 `none` 或 `3D`，不能因工程意图被保留为名义值。

## 2. 单因素 sweep

### 2.1 刚体 pose：法向 gap / penetration 与 translation

对具有明确刚体局部法向的 case，保持实体形状不变、仅沿局部法向平移一个 occurrence，取：

`δ/τE ∈ {-4, -2, -1.1, -1, -0.9, -0.5, -0.1, 0, 0.1, 0.5, 0.9, 1, 1.1, 2, 4}`。

该非均匀网格把预算集中在两侧 boundary value。它直接适用于平面、edge、球—板等刚体 pose；对于 A04、A05，结果仍依据当前 exact/engineering tuple 报告，绝不由小距离升级成 2D patch。A06 的 sweep 用于识别从 `3D` interference 到边界/脱离的分类过渡；A13 的 inward motion 要保持 `solid_inside_clear` 直到 cavity wall 的真实首次接触。

### 2.2 构造/尺寸 variants：曲面 uniform gap、penetration 与 freeform offset

曲面配合不能把“全域 uniform radial gap”误写成刚体平移。下列样本另标 `perturbation_kind=construction_variant`，与刚体 pose 结果分开汇总，且每一个由精确方程和当前几何重新生成真值：

- **A07 cylinder**：固定 shaft 半径 `r`，将 bore 内半径改为 `r+δ`（positive gap）或 `r-|δ|`（material penetration），并保持共同轴线和接合长度；正 gap 的当前 exact 交为 `none`，penetration 的当前 intersection/solid 状态由两实体的解析实体交重新标注。
- **A08 sphere cavity**：固定球半径 `r`，将腔壁半径改为 `r+δ` 或 `r-|δ|`，trim 开口角不变；同样逐实例给出解析 min clearance、current exact dimension、面积/相交体真值。
- **A10 freeform**：以冻结 support 的 regular normal offset `S_δ(u,v)=S(u,v)+δn(u,v)` 构造互补侧，限制 `δ` 在 offset 无 self-intersection 的已验证范围，并冻结对应 trim。positive offset、exact coincidence、material penetration 分别由 construction-derived reference 重新标注；不把它们称为 rigid motion。

这些 variants 的 `intended_relation_dimension` 仍是名义值，但 `exact_intersection_dimension`、`engineering_state`、面积/patch 真值均是**该 variant 的当前真值**。如果某 variant 因 trim 或 offset 正则性不再有唯一解析 reference，则不纳入 sweep，而不是推测标签。

### 2.3 刚体 Rotation

不以固定角度跨尺度比较。取候选界面最远点到旋转轴的有效半径 `R_eff`，按

`qθ = R_eff · tan(θ) / τE`

使用与法向 offset 相同的有符号绝对序列 `{0, 0.1, 0.5, 0.9, 1, 1.1, 2, 4}`，并分别测试正负旋转。旋转轴和 pivot 必须记录：平面例绕 interface centroid；A07/A09 必须绕**穿过界面参考中心、且垂直于装配轴**的固定轴；freeform 绕预定义局部 frame。A07/A09 绕装配对称轴的 rotation 仅为 representation control，不纳入 pose sweep。完美球 A04/A08 的自身 rotation 对几何没有信息量，因此不做 body rotation sweep；若旋转外壳 trim，只能明确说明其改变了 trimming，而非球面本身。

### 2.4 刚体 Tangential translation

不做任意网格。围绕每例的可解析几何事件取 `0.9、0.99、1、1.01、1.1` 倍临界位移：A02 是 overlap 出现/消失；A03 是 face containment 首次失效；A11 是一支脚先脱离；A12 是内孔/外缘边界接近；A07/A09 是端部覆盖改变。每条 sweep 同时保存临界值的推导及平移方向，防止将不同几何事件混作同一阈值。

## 3. 适用案例与组合预算

完整单因素 sweep 适用于 `A01, A03, A04, A05, A07, A08, A10, A11, A12`。A02、A06、A09、A13 仍有其在上节定义的专门 transition 扫描，但不参加全部因素矩阵，以免用无意义的旋转或翻译消耗预算。

仅增加两类**边界 pairwise**组合：

1. `gap × rotation`：各自取 `{0.9, 1, 1.1}τE` 的正间隙与等效旋转位移；
2. `translation × rotation`：各自取临界值的 `{0.99, 1, 1.01}` 倍。

它们只在 A01、A03、A07、A10、A11、A12 的局部临界区域运行。不得做 gap、penetration、translation、rotation、scale、degeneracy 的 Cartesian product；每个附加样本必须标出其假设的失效交互。

## 4. Scale 与 degeneracy

每个已选 sweep 至少采用尺度倍率 `0.01×、1×、100×`。设置两个互不混合的报告模式：

- **fixed-absolute-τE**：始终 `τE=0.1 mm`，检验绝对工程要求在小/大件上的表现；
- **co-scaled-τE**：几何与 `τE` 同比例缩放，保持 `τE/L` 不变，检验尺度协变性。

可控退化变体包括：窄条/小 patch（面积缩至但不低于可构造阈值）、sliver face（小宽度）、high-aspect-ratio 平面或圆柱 patch。它们建立在 A01、A02、A07、A10、A12 的明确参数上，记录最小边长、aspect ratio、面积和 `τK`；不会被伪装成新的 canonical case。

## 5. 真值生成与测量

名义构造先给出 relation tuple；每个样本再按指定的 `perturbation_kind`（`rigid_pose` 或 `construction_variant`）生成**当前**参数真值。记录 case ID、变换矩阵或构造方程、`δ/τE`、`qθ`、切向临界比、scale mode、degeneracy 参数、`τE`、`τK`、当前 `L`、current tuple 与 nominal intended dimension。对 freeform A10，boundary/area 由冻结参数域和高精度参考计算，报告积分误差上界。

## 6. 主输出与指标口径

- **stable classification interval**：以离散 sweep 的相邻采样点为闭区间端点；只有端点及区间内全部实际采样点均为正确 current tuple，才计入稳定区。理论 transition 若正好落在采样点，归入 near-threshold，不算 stable。
- **first-error location**：自 nominal 向各扰动方向按采样顺序移动时，第一条错误 current-tuple 样本的无量纲位置；若 nominal 已错为 `0`。若在 sweep 范围内没有错误，记为 `no_error_within_range`，不得外推。
- **transition-threshold error**：`t*` 必须是 analytic 或 construction-derived reference 给出的**精确理论 transition**，而不是离散真值标签首次改变的中点。预测标签首次改变时，报告相邻采样值构成的 bracket `[t_k,t_{k+1}]`、可选 midpoint estimate `\hat t=(t_k+t_{k+1})/2`，以及 discretization half-width `(t_{k+1}-t_k)/2`（或等价 interval uncertainty）；数值误差为 `|\hat t-t*|`，按 `τE`（translation/gap）或 `qθ`（rotation）归一化。若预测在 sweep 范围内无 transition，报告 `no_transition_within_range`，不产生数值 error，也不当作零。
- **stable-band accuracy**：仅对与任何真值 transition 的距离**大于或等于** `0.1τE`（rotation 为 `qθ≥0.1`）的采样点计算；包含恰好等于 band 边缘的点。near-threshold strata 单独列示。

同时报告 `runtime`、`timeout_rate`、`invalid_result_rate`、`unmapped_face_rate`。任何二维 patch 指标（`surface_area_IoU`、`relative_area_error`、`normalized_95pct_symmetric_boundary_Hausdorff`）仅在 synthetic 2D 真值存在时计算。不得把阈值附近的正常语义不确定性与稳定区错误合并为一个准确率。
