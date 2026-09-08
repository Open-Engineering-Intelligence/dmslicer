# Level A Canonical Case Matrix

## 1. 共同构造约定

Level A 固定为 13 个最小的两体诊断案例。原始几何尺寸均用独立的 raw symbol（如 `a_0,b_0,h_0,r_0`）指定，绝不把 `L` 当作一条原始边长。对每个完整 nominal configuration，先计算两实体**合并包围盒对角线** `L_0`，再以 `λ=100 mm/L_0` 对所有坐标和 raw 尺寸均匀缩放；缩放后才有 `L=100 mm`。下文未加下标的小写尺寸均指相应的归一化量（如 `a=λa_0`）。扰动实例的 `L` 则重新定义为当前 body-pair 合并包围盒对角线，故可不同于 100 mm。除另有说明，实体为独立 `independent_brep`，名义构造使用 `τE = 0.1 mm` 之外的 exact 几何；参数扰动按 [tolerance_protocol.md](tolerance_protocol.md) 执行。

每项都按 [contact_problem_taxonomy.md](contact_problem_taxonomy.md) 的 relation tuple 标注。`patch` 仅用于 2D interface；对 0D/1D/3D 其值为 `not_applicable`，但仍需给出点、线或相交体的真值。

| ID | Canonical geometry | 预期 relation / exact dimension | patch 真值 |
|---|---|---|---|
| A01 | 等尺寸棱柱上下贴合 | `exact`, `2D` planar interface | 1 个 `full_full` 矩形 |
| A02 | 两棱柱平面错位 | `exact`, `2D` planar interface | 1 个 `partial_partial` 矩形 |
| A03 | 小棱柱端面落在大端面内 | `face_in_face`, `2D`，非 solid containment | 1 个 `small_face_contained_in_large_face` 矩形 |
| A04 | 球与平面外切 | `exact`, `0D` touch | 1 点 |
| A05 | 两棱柱仅共边 | `exact`, `1D` touch | 1 条线段 |
| A06 | 两棱柱正体积重叠 | `solid_material_interference`, `3D` | 解析相交体积 |
| A07 | 同半径轴—孔 | `exact`, `2D` cylinder interface | 1 圆柱面 patch |
| A08 | 球体与匹配球窝 | `solid_cavity_wall_touch`, `2D` sphere interface | 1 trimmed 球面 patch |
| A09 | 圆锥台与匹配锥座 | `exact`, `2D` cone interface | 1 锥面 patch |
| A10 | 互补 trimmed NURBS 实体 | `exact`, `2D` freeform interface | 1 个参数域 patch |
| A11 | 桥接实体两支脚接触平板 | `exact`, `2D` plane interface | 2 个不连通 patches |
| A12 | 垫圈接触平板 | `exact`, `2D` plane interface | 1 连通 annular patch、1 孔 |
| A13 | 实体位于密闭腔内有间隙 | `solid_inside_clear`, `none` | 0 patch |

## 2. 案例规范

### A01 — full planar contact

- **因素覆盖**：plane、`full_full`、单 patch、凸实体、独立 B-rep、单 pair、exact `2D`。
- **参数化构造**：两个 raw 尺寸为 `a_0 × b_0 × h_0` 的棱柱（默认比例 `a_0:b_0:h_0=2:2:1`），上体底面与下体顶面共面且 domain 一致；经共同 `λ` 归一化后面积 `A=(λa_0)(λb_0)`，边界为四段线段。
- **预期关系**：`(2D, exact, 2D, none, independent_brep)`；`component_count=1`、`hole_count=0`、`support_surface_family=plane`。
- **ground truth**：`analytic`，矩形域、面积和边界均闭式可得。
- **适合扰动**：法向 gap/penetration、绕界面中心旋转、均匀尺度、sliver 长宽比。
- **不可替代性**：唯一给出 full/full 面积与边界的基本基线；A02 和 A03 不能验证全域重合。

### A02 — partial planar overlap

- **因素覆盖**：plane、`partial_partial`、tangential overlap 临界、single patch。
- **参数化构造**：沿 x 平移 `s` 的同尺寸 A01 棱柱，`0<s<a`；patch 为 `(a-s)×b` 矩形。
- **预期关系**：`(2D, exact, 2D, none, independent_brep)`；一连通分量、零孔。
- **ground truth**：`analytic`：面积 `(a-s)b`、四边界及重叠消失临界 `s=a`。
- **适合扰动**：切向 translation 围绕 `s=a`，法向 offset，角度扰动。
- **不可替代性**：检验部分重叠和面积连续退化，而非 A01 的完整重合。

### A03 — face containment, not solid containment

- **因素覆盖**：plane、`small_face_contained_in_large_face`、face containment、大小不等 face。
- **参数化构造**：小棱柱 `a_s×b_s×h`（`0<a_s<a`、`0<b_s<b`）端面共面置于大棱柱端面内部，四边均留安全 margin。
- **预期关系**：`(2D, exact, 2D, face_in_face, independent_brep)`，一个 patch、零孔；无实体包含推论。
- **ground truth**：`analytic`，patch 是小矩形，面积 `a_sb_s`；face-domain inclusion 可精确判定。
- **适合扰动**：切向移动到 containment 失效边界、gap、rotation、尺度。
- **不可替代性**：把 face-domain containment 从 A02 的部分相交和 A13 的 solid containment 彻底分开。

### A04 — sphere-plane point touch

- **因素覆盖**：sphere/plane、`0D`、曲面 tangency、tiny contact。
- **参数化构造**：半径为 raw `r_0` 的球，与一个有限厚度 `t_0>0` 的平板相切；平板半宽/半长均至少为 `3r_0`，球的切点距所有平板侧边至少 `2r_0`，球心到接触面距离为 `r_0`。共同归一化后真值交集为切点 `(0,0,0)`，不会由无限平面的隐含假设产生边界歧义。
- **预期关系**：`(0D, exact, 0D, none, independent_brep)`，无 area patch。
- **ground truth**：`analytic`，一个点；接触法向和最小距离闭式可得。
- **适合扰动**：沿平面法向 gap/penetration、切向移动、尺度；rotation 对完全球无意义，故不作 sweep。
- **不可替代性**：唯一分离 0D tangency，避免把它错误记为小面积界面。

### A05 — shared-edge geometric touch

- **因素覆盖**：plane、`1D`、edge/curve contact、共边。
- **参数化构造**：两个直棱柱以 raw 长度 `l_0` 的边共线接触，所有非该边的面域不交；共同归一化后线段长度为 `λl_0`。
- **预期关系**：`(1D, exact, 1D, none, independent_brep)`，线段端点和长度 `l` 真值；无 area patch。
- **ground truth**：`analytic`，交集为一条闭线段。
- **适合扰动**：横向小 gap/penetration、平行/非平行 rotation、端点附近切向 translation。
- **不可替代性**：以一维线接触检验维数分类，A04 和 A01 无法替代。

### A06 — volume interference

- **因素覆盖**：`3D`、凸实体 material interference、penetration beyond tolerance。
- **参数化构造**：两 raw `a_0×b_0×h_0` 棱柱相对平移 `(u_0,v_0,w_0)`，取 `0<u_0<a_0`、`0<v_0<b_0`、`0<w_0<h_0`。归一化后定义三个正交 box-overlap thickness：`q_x=λ(a_0-u_0)`、`q_y=λ(b_0-v_0)`、`q_z=λ(h_0-w_0)`；名义 penetration depth 定义为最小 separating translation `d_pen=min(q_x,q_y,q_z)`，并约束 `d_pen>τE`。
- **预期关系**：`(3D, penetration_beyond_tolerance, 3D, solid_material_interference, independent_brep)`。
- **ground truth**：`analytic`，相交体积 `q_xq_yq_z` 与 `d_pen` 均精确可得；无 2D patch 指标。
- **适合扰动**：穿透深度越过 `τE`、尺度、极薄相交层。
- **不可替代性**：验证 3D interference 不能被错误降为 2D contact。

### A07 — cylindrical shaft–bore interface

- **因素覆盖**：cylinder、曲率、concave/convex 配合、2D full angular patch。
- **参数化构造**：同轴轴和孔，半径 `r`、接合长度 `l`；使用互补实体使轴外圆柱面与孔内圆柱面重合，端部留 clearance。
- **预期关系**：`(2D, exact, 2D, none, independent_brep)`；一连通的全周圆柱带，`boundary_component_count=2`、`first_betti_number=hole_count=1`、`annular_or_multiply_connected=true`，面积 `2πrl`。
- **ground truth**：`analytic`，圆柱参数域 `[0,2π)×[0,l]`；参数 seam 不计为边界。
- **适合扰动**：构造型 uniform radial gap/penetration、刚体轴向 translation、以及绕**穿过界面参考中心且垂直于装配轴**的固定轴的 tilt；绕装配对称轴转动仅作 representation control，不是 pose 扰动。另做尺度和高长宽比。
- **不可替代性**：首个非平面 analytic 2D 配合，检验周期参数和曲率。

### A08 — spherical cavity-wall interface

- **因素覆盖**：sphere、internal cavity、`solid_cavity_wall_touch`、trimmed curved patch。
- **参数化构造**：半径 `r` 球置于具有同半径内球面凹腔的壳体；仅由开口角 `α` 限制的球帽接触，其余体积不交。
- **预期关系**：`(2D, exact, 2D, solid_cavity_wall_touch, independent_brep)`；一连通球面 patch、零孔。
- **ground truth**：`analytic`，面积 `2πr²(1-cos α)` 和球面参数边界。
- **适合扰动**：径向 gap/penetration、偏心 translation、rotation（对球本体无意义，仅对非对称修剪参考系记录）、尺度。
- **不可替代性**：在 A07 外引入球面与 cavity-wall 语义，区别 A13。

### A09 — conical frustum-seat interface

- **因素覆盖**：cone、其他 analytic curved contact、方向性曲率。
- **参数化构造**：半锥角 `β`、内半径 `r_0`、外半径 `r_1` 的互补圆锥台与锥座，共同轴线；端面留 clearance。
- **预期关系**：`(2D, exact, 2D, none, independent_brep)`，一连通全周圆锥台带，`boundary_component_count=2`、`first_betti_number=hole_count=1`、`annular_or_multiply_connected=true`。
- **ground truth**：`analytic`，母线长 `g=(r_1-r_0)/sinβ`，面积 `π(r_0+r_1)g`。
- **适合扰动**：构造型轴向 gap、刚体横向/轴向 translation，以及绕**穿过界面参考中心且垂直于装配轴**的固定轴的 tilt；绕装配对称轴转动只作 representation control，不纳入 pose sweep。
- **不可替代性**：cone 的半径随高度变化，不能由 cylinder 或 sphere 覆盖。

### A10 — complementary trimmed NURBS interface

- **因素覆盖**：`trimmed_bspline_nurbs_freeform`、非解析 B-rep 修剪、freeform 2D。
- **参数化构造**：共享公开、明示控制点/权重/节点向量的双三次 NURBS support；以矩形或曲边闭环 trim 域 `D` 构造两互补实体，界面是同一 `D`。基准发布时将 NURBS 定义与参数域一同冻结。
- **预期关系**：`(2D, exact, 2D, none, independent_brep)`，一连通零孔 patch。
- **ground truth**：`construction_derived`；在参数域给定精确 trim loop，面积由高精度参考积分及收敛容差记录，而非虚称闭式解析。
- **适合扰动**：法向 offset、绕局部 frame rotation、切向 translation、尺度与可控窄 trim strip。
- **不可替代性**：唯一覆盖 NURBS trim/correspondence 的 freeform 问题。

### A11 — two disconnected planar patches

- **因素覆盖**：multiple disconnected patches、single body 对多个界面、component count。
- **参数化构造**：一个 H 形或桥接实体的两个 `a_f×b_f` 支脚落在平板上，支脚中心距 `d>a_f`；桥梁本身离平板有 clearance。
- **预期关系**：`(2D, exact, 2D, none, independent_brep)`，`component_count=2`、`connectedness=disconnected`、零孔。
- **ground truth**：`analytic`，两个互不相交矩形，面积 `2a_fb_f`。
- **适合扰动**：法向 gap、切向移动、rotation、使一支脚首先脱离的阈值。
- **不可替代性**：检验算法不会把分离 interface 合并成一个 patch。

### A12 — annular / multiply connected patch

- **因素覆盖**：annular、hole、multiply connected、perforated solid topology。
- **参数化构造**：外半径 `r_o`、内半径 `r_i` 的平面垫圈底面贴合平板，`0<r_i<r_o`。
- **预期关系**：`(2D, exact, 2D, none, independent_brep)`，`component_count=1`、`hole_count=1`、`annular_or_multiply_connected=true`。
- **ground truth**：`analytic`，面积 `π(r_o²-r_i²)`，内外两个圆边界。
- **适合扰动**：gap、tilt、内孔/外缘附近的 sliver 尺寸与尺度。
- **不可替代性**：与 A11 的两个分量不同，专门揭示连通域内孔的拓扑错误。

### A13 — clear solid containment negative control

- **因素覆盖**：internal cavity、solid containment、无接触负类、concave shell。
- **参数化构造**：封闭腔体内部尺寸各方向均比内实体大 `2g`，取 `g>τE`；内实体居中，外壳材料不交。
- **预期关系**：`(none, positive_gap_beyond_tolerance, none, solid_inside_clear, independent_brep)`，0 patch。
- **ground truth**：`analytic`，最小 clearance `g`；无交集、无面域。
- **适合扰动**：逐渐减小 clearance 至 `τE`，再移至 cavity-wall touch；该连续路径为 A08 的 containment 对照，不把状态混为一例。
- **不可替代性**：证明“在里面”不是 contact，也不是 A03 的 face containment。

## 3. Representation control（不计入 13 例）

以 A01 的**同一几何**提供两种表达：(i) 两独立 solids；(ii) shared-face 的 cellular/compsolid 表达。二者图形相同，但后者存在 `shared_subshape/topologically_adjacent`，前者没有。它仅验证表达依赖性，不增加 Level A 案例数或统计样本数。

## 4. 首版不纳入的因素

torus 需要额外处理周期参数与 self/near-self 交情形，留作后续曲面扩展；极端 sliver 是 Level B 退化变量；多个 identical occurrence 和 dense graph 是 Level C 图问题。这样 13 例仍保持每个案例主要定位一个失败原因，而不是无解释力的组合枚举。
