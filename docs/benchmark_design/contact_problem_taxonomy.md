# DM-Slicer Contact Benchmark：问题分类与标注约定

## 1. 目的与边界

本规范把研究对象定义为：**从具有数值容差的 CAD/STEP B-rep 数据中，恢复具有工程意义的实体间 `contact/interface relationship`**。它是 benchmark 的共同语言，不是某一求解器的输出格式，也不把不同几何关系合并成单一 `CONTACT` 标签。

本设计仅规定 benchmark 的问题空间、标签、案例与评价协议；不改变任何现有系统，也不生成几何样本或实现求解方法。

每条标注记录的对象是一个有序规范化的 `(occurrence_i, occurrence_j)` body-pair；需要 face 级评价时，在该记录下附加候选 `face_pair`。排序只为去重，不表示物理方向。

## 2. 统一注释记录

下列字段必须正交存储。枚举值以英文 token 写入 manifest，中文解释仅用于本设计文档。

| 字段 | 必填内容与合法值 |
|---|---|
| `entity_identity` | `component_id`、`occurrence_id`、`body_id`、`instance_index`；几何相同的实例仍用不同 `occurrence_id`。 |
| `topological_relation` | `independent_brep`（两个独立 B-rep）、`shared_subshape`（共享 topological subshape）、`topologically_adjacent`（同一 cellular/compsolid 表达中的拓扑邻接）。可多值但须注明表达模型。 |
| `exact_intersection_dimension` | `none`、`0D`、`1D`、`2D`、`3D`，指**当前记录的 post-perturbation 几何**集合交的最大维数；不是名义构造的固定属性。 |
| `engineering_state` | `exact`、`positive_gap_within_tolerance`、`positive_gap_beyond_tolerance`、`penetration_within_tolerance`、`penetration_beyond_tolerance`。阈值由 `τE` 定义。 |
| `intended_relation_dimension` | `none`、`0D`、`1D`、`2D`、`3D`；在工程容差下拟恢复的关系维数。它不覆盖或改写 exact 维数。 |
| `containment_state` | `none`、`face_in_face`、`solid_inside_clear`、`solid_cavity_wall_touch`、`solid_material_interference`。 |
| `support_surface_family` | 对每个界面 face-pair 给出 `plane`、`cylinder`、`cone`、`sphere`、`torus`、`trimmed_bspline_nurbs_freeform` 中一项；异类配对记为两个 token。 |
| `overlap_extent` | 适用于 `2D` interface：`full_full`、`partial_partial`、`small_face_contained_in_large_face`；否则为 `not_applicable`。 |
| `patch_topology` | `component_count`、`connectedness`（`connected`/`disconnected`/`not_applicable`）、`boundary_component_count`、`first_betti_number`、`hole_count`、`annular_or_multiply_connected`（布尔）。这些量定义在几何 patch 域上，不依赖 B-rep seam。 |
| `ground_truth_mode` | `analytic`、`construction_derived`、`dataset_face_pair`、`manual_adjudication`；允许并列，需说明各自对应的标签。 |
| `provenance` | case ID 或外部数据集版本、样本 ID、导入格式、变换、标注者/脚本版本（如有）。 |
| `label_confidence` | `high`（解析/可构造复核）、`medium`（可重复映射或双人复核）、`low`（不确定人工裁定）。 |

推荐的最小关系 tuple 是：

`(exact_intersection_dimension, engineering_state, intended_relation_dimension, containment_state, topological_relation)`。

`engineering_contact` 若被产品或报告需要，只能是该 tuple 的**派生视图**：它应显式给出 `τE`、纳入的维数以及是否接受小 penetration；不得作为原始真值字段或与 2D area interface 混用。

## 3. 必须分开的概念

### 3.1 几何、工程与拓扑

- `geometric exact contact`：当前几何恰好相交；其维数由 `exact_intersection_dimension` 报告。扰动后它可以与名义维数不同。
- `tolerance-aware engineering contact`：存在小正间隙或小 penetration，但其绝对值不超过 `τE`，并且 `intended_relation_dimension` 指明工程意图。
- `topological adjacency`：B-rep 表达中的邻接关系；它可存在而没有两个独立实体之间的几何接触，也可缺失而两个独立 B-rep 几何重合。因此不能替代前两者。
- `0D` point touch、`1D` edge/curve touch、`2D` area interface、`3D` volume interference 是互相独立的报告类别。仅 `2D` 才有 surface-area、patch boundary 与 hole 的 area-interface 指标。

### 3.2 Face containment 与 solid containment

`face_in_face` 只表示两个二维 trimmed domain 位于同一 supporting surface，且小 face 的 domain 被大 face 的 domain 包含。它不推断一个实体位于另一个实体内部。

实体包含必须使用下列互斥状态：`solid_inside_clear`（封闭腔中有正间隙、零 patch）、`solid_cavity_wall_touch`（内壁形成 surface contact）和 `solid_material_interference`（实体材料具有正体积交）。最后一项与普通相邻两实体验证的 `3D` interference 同样报告，但可额外保留 cavity provenance。

## 4. 因素覆盖与合法组合

benchmark 按正交因素覆盖，而非对所有因素做 Cartesian product：body/occurrence multiplicity、维数、surface family、overlap、patch topology、solid topology、tolerance、scale/degeneracy、occurrence identity、contact graph。每个实验须在 manifest 中声明覆盖的因素和值。

并非任意组合都合法。例如：`annular_or_multiply_connected=true` 只适用于 `2D`；`surface_area_IoU` 不适用于 `0D/1D/3D`；`full_full` 不适用于异类曲面；物理实体 body-pair 的 dense graph 不能随意由同一空间位置的重叠面伪造。Level C 的 K4 由四个等半径球两两外切的合法 `0D` touch 构造。torus、极端 sliver、重复 occurrence、dense graph 不进入最小 Level A，分别留给后续曲面扩展、Level B 与 Level C。

## 5. 标注与报告规则

1. 单位统一为 mm。`L` 一律是**当前 body-pair 合并包围盒的对角线**（包含当前 pose/perturbation）；每一完整 nominal configuration 经均匀归一化后满足 `L=100 mm`。所有 `τE`、`τK`、`L` 和变换必须保存；`τK` 是 STEP/内核已有拓扑容差，绝不当作工程判定阈值。
2. 同一 body-pair 有多个二维 patch 时，保留全部 patch；不得用单一面积或单一 face-pair吞没其连通性。
3. face-pair 标签是 B-rep/格式相关标签。跨格式评价先完成 correspondence audit，并将 `unmapped-face rate` 单列。
4. 报告必须同时列 exact tuple、tolerance tuple 和拓扑状态；不能以一个二值结论取代它们。
5. synthetic label 要指出解析公式或 construction-derived 来源；外部数据的无 patch 真值要明确限制可评指标。

## 6. 本版冻结的术语

本文的 `patch` 是二维 interface 在 supporting surface 上的 trimmed 参数域/几何域；`component_count` 指其连通分量数。`boundary_component_count` 是该域的几何边界连通分量数，`first_betti_number=β1`，`hole_count=β1`；对紧致、可定向平面/曲面域，单连通盘为 `β1=0`，annulus 和全周圆柱/圆锥台带为 `β1=1`。参数化 seam 或 B-rep seam 不是 patch boundary，不能改变这些值。`interface face-pair` 是承载该 patch 的 B-rep face 对，而不是保证 patch 等同于完整 face。所有后续文档使用本表的 enum 与 metric 名称。
