# DM-Slicer v2 最小领域模型

## 证据状态

- **[CODE-CONFIRMED]** 旧 `MeshData.count`、`Object.material` 与 include/exclude ID 不满足 v2 的稳定身份、几何权威和 provenance 要求。
- **[DESIGN-DECISION]** 本文类型及不变量是 v2 的规范性合同；它们描述未来实现必须满足的行为，不表示这些类型已经存在于源码中。
- **[OPEN-QUESTION]** 不同 STEP 再导出版本之间的实体 correspondence 不能仅靠 shape digest 自动保证；MVP 将跨文档映射作为显式、可拒绝的外部工件。

## 1. 设计原则

1. 几何身份、材料语义、算法结果和 UI 状态必须分开。
2. 所有持久 ID 都是字符串且确定生成；不得使用 Python 进程计数、list index、内存地址或裸 `TopoDS_Shape::HashCode`。
3. `geometry_ref` 是运行时句柄，持久化记录保存可重建 locator、摘要和 provenance，而不是序列化内核指针。
4. 输入记录不可变；Boolean/split/unify 产生新记录并追加 operation history。
5. candidate、confirmed relation、selected source boundary 是三个不同生命周期。
6. 长度、面积、容差必须带统一单位；MVP 固定内部长度单位为 mm、面积为 mm²。

### 1.1 必需类型的生命周期合同

下表对每个冻结类型统一规定 Purpose、Authority、Inputs、Outputs、Stable identity、Provenance、Dependencies 与明确非职责；后续详细章节不得改变这些边界。

| 类型 | Purpose | Authority | Inputs | Outputs | Stable identity | Provenance | Dependencies | 明确不负责 |
|---|---|---|---|---|---|---|---|---|
| `SolidRegion` | 表示一个有效闭合 STEP 实体区域 | source STEP + validated B-rep | document、product path、solid locator、role/policy | region record + runtime geometry ref | document ID + locator/fingerprint schema digest | import、placement、validation node | STEP importer、shape validator | 界面判定、场求解、UI 状态 |
| `GradientDomain` | 表示闭合 `ΩG` 与边界分区 | validated region geometry | one MVP region、source boundaries、external faces | domain record | ordered region IDs + boundary partition + schema digest | domain-construction node | `SolidRegion`、`InterfaceSourceBoundary` | 把 semantic gradient role 当有效域、生成体网格 |
| `InterfaceCandidate` | 保存高召回 broad-phase pair | candidate generator 证据 | active region pair、bounds、candidate tolerance | pending/evaluated/rejected candidate | sorted region pair + candidate config digest | broad-phase method/reasons/timing | `SolidRegion`、`ParticipationPolicy` | 宣告接触或创建 patch |
| `AtomicInterfacePatch` | 表示最小有效二维 contact fragment | validated B-rep relation/split result | confirmed 2D relation、source faces、operation history | patch geometry/area/wires/source mapping | region pair + source faces + operation/shape digest | complete Boolean/split history | relation classifier、OCCT adapter | 表示 0D/1D/3D 关系、选择场条件 |
| `InterfaceSourceBoundary` | 把 confirmed patches 激活为 grading boundary `Γ` | semantic activation policy | `GradientDomain`、patch set、source regions、condition | boundary record | domain + ordered patches + condition digest | auto/manual selection node | `GradientDomain`、`AtomicInterfacePatch`、policy | 代表整个 Source material region、求解 field |
| `ParticipationPolicy` | 决定 region 是否参与自动关系与语义激活 | versioned semantic annotation | region、mode、eligibility flags | immutable policy record | region ID + policy payload digest | operator/rule/time/input result digest | `SolidRegion` role metadata | 改变几何、用继承表达 material identity |
| `ProvenanceRecord` | 形成 input→operation→output 的可审计 DAG | operation adapter/annotation service | entity IDs、operation、versions、parameters、history | provenance node + completeness | canonical node payload digest | 本身即 provenance；父节点不可变 | importer、backend、run manifest | 用最近几何猜测替代缺失 history |
| `FieldQuery` | 对 `ΩG` 内批量点查询 `φ` 或 fractions | versioned field artifact | points、frame、domain ID | `FieldBatch` | field artifact ID + solver config digest | domain/boundaries/discretization/solver chain | future solver、`GradientDomain` | 界面检测、默认外推、选择 PDE |
| `SliceFieldMap` | 保存一个切片平面的 topology-aware 2D material map | slice geometry + `FieldQuery` output | plane、domain section、samples、policy | contours、holes、samples、field values/masks | plane + domain + field artifact + sampling config digest | section、field、policy nodes | slicer application、`FieldQuery` | toolpath、G-code、删除 source geometry |
| `InternalInterfacePolicy` | 控制制造视图是否发射内部 A/G、G/B 轮廓 | fabrication/application policy | preserved internal interfaces、requested mode | emission decision + audit record | policy schema + payload digest | operator/config/run node | `SliceFieldMap`、interface IDs | 修改 B-rep、patch、source boundary或 field boundary conditions |

## 2. 通用标识和坐标合同

### 2.1 `SourceDocumentId`

由规范化输入字节 SHA-256 与 importer schema version 构成：

```text
stepdoc:v1:<sha256>
```

文件路径和文件名只作为显示信息，不参与唯一性。相同文件名、不同内容必须得到不同 ID。

### 2.2 `EntityLocator`

定位源实体，至少包含：

| 字段 | 类型 | 含义 |
|---|---|---|
| `document_id` | string | 来源文档 ID |
| `product_path` | list[string] | STEP/XCAF assembly/product label 路径 |
| `entity_kind` | `SOLID` / `FACE` / `EDGE` | 实体维度 |
| `source_ordinal` | int | 在确定性遍历中的序号，仅作 locator 一部分 |
| `persistent_label` | string/null | importer 能取得的 XCAF/STEP label |
| `geometry_digest` | string | 量化后的几何/拓扑 fingerprint |
| `identity_schema` | string | 身份算法版本 |

`source_ordinal` 单独不稳定，因此必须和 document/product/fingerprint 一起使用。重新导出 STEP 后 document ID 会改变；跨文档对应关系需要显式 correspondence，不得假装 ID 不变。

### 2.3 坐标系

所有几何记录引用一个 `frame_id`。进口阶段保存 STEP 原单位、到内部 mm 的 scale 和 assembly placement。算法输入统一在 `model_mm` frame 中；UI 相机坐标、显示缩放和 derived mesh 坐标不得反馈到几何内核。

## 3. `SolidRegion`

### 3.1 目的

表示 STEP 中一个具有稳定来源身份的封闭实体区域。材料相同的多个 solid 仍是多个 `SolidRegion`；是否组合由更高层语义决定。

### 3.2 字段

| 字段 | 类型 | 必需 | 说明 |
|---|---|---:|---|
| `region_id` | string | 是 | `region:v1:<document>:<locator-digest>` |
| `source_document_id` | string | 是 | 输入 STEP 身份 |
| `source_locator` | `EntityLocator` | 是 | original solid provenance |
| `role` | `SOURCE` / `GRADIENT` / `PASSIVE` / `VOID` / `UNKNOWN` | 是 | 语义角色，不改变几何 |
| `material_metadata` | map | 是 | material key、名称、组成及外部 metadata；允许为空 |
| `participation_policy` | `ParticipationPolicy` | 是 | 是否参与候选、source、gradient 等 |
| `geometry_ref` | opaque backend reference | 是（运行时） | 指向原始或派生 `TopoDS_Solid` |
| `frame_id` | string | 是 | 坐标系 |
| `length_unit` | string | 是 | MVP 固定 `mm` |
| `shape_validity` | record | 是 | solid/closed/oriented/BRepCheck 结果 |
| `provenance_id` | string | 是 | 产生本 region 的 provenance node |

### 3.3 不变量

- `geometry_ref` 必须解析为恰好一个 solid；compound/compsolid 需先展开或明确拒绝。
- accepted region 必须是有效封闭实体；open shell 只能以 rejected diagnostic 存在。
- `role=GRADIENT` 不代表它已满足 `GradientDomain` 条件。
- 任何 Boolean 后的 fragment 都得到新 `region_id`；原 region 通过 provenance 与其关联。

## 4. `GradientDomain`

### 4.1 目的

表示参与梯度计算的封闭区域 `ΩG`。它是几何域和边界分区，不是旧 `GradientMaterial` 对象。

### 4.2 字段

| 字段 | 类型 | 说明 |
|---|---|---|
| `domain_id` | string | 稳定域身份 |
| `region_ids` | ordered set[string] | 构成 `ΩG` 的一个或多个 solid region；MVP 只允许一个 |
| `geometry_ref` | opaque | 封闭域 B-rep |
| `source_boundary_ids` | ordered set[string] | `Γ` 集合 |
| `external_boundary_face_ids` | ordered set[string] | `∂ΩG` 中非内部材料界面的部分 |
| `boundary_partition_status` | enum | `COMPLETE` / `OVERLAP` / `GAP` / `UNCLASSIFIED` |
| `discretization_ref` | string/null | 第二阶段体网格/体素工件；第一阶段为空 |
| `provenance_id` | string | 域构造来源 |

### 4.3 不变量

- `ΩG` 必须有非零体积、闭合、可定向且通过 shape validation。
- 每个 `InterfaceSourceBoundary` 必须位于 `∂ΩG` 上并引用至少一个 confirmed 2D atomic patch。
- source boundaries 两两 interior-disjoint；允许共享边/点。
- `ΓA`、`ΓB` 不要求覆盖整个 `∂ΩG`；剩余部分由外壁 boundary condition 处理。
- 第一阶段只验证这个合同，不生成 `discretization_ref`。

## 5. `ParticipationPolicy`

旧 `IsolationMaterial(SourceMaterial)` 把材料身份和参与行为混在继承层次中。v2 将其改为正交 policy：

```text
mode: ACTIVE | IGNORE | ISOLATE
external_boundary: bool
source_eligible: bool
gradient_eligible: bool
```

这些字段覆盖用户要求的 `ACTIVE`、`IGNORE`、`ISOLATE`、`EXTERNAL_BOUNDARY`、`SOURCE_ELIGIBLE`、`GRADIENT_ELIGIBLE`，但不强迫互斥概念进入单一 enum。

语义：

- `ACTIVE`：进入候选和关系计算；
- `IGNORE`：不进入自动候选，但保留 provenance 和显示；
- `ISOLATE`：计算其自身几何诊断，但不与其他 region 建立 active grading relation；
- `external_boundary=true`：允许其面成为 fabrication external wall；
- `source_eligible=true`：其 confirmed interface 可被选择为 source boundary；
- `gradient_eligible=true`：可组成 `GradientDomain`。

非法组合应被拒绝，例如 `mode=IGNORE` 且要求自动生成 source boundary；`role=VOID` 且 `source_eligible=true` 也需要显式研究协议才能允许。

## 6. `InterfaceCandidate`

### 6.1 目的

记录两个 `SolidRegion` 可能发生关系的 broad-phase 结果。它不携带“已经接触”的结论。

### 6.2 字段

| 字段 | 类型 | 说明 |
|---|---|---|
| `candidate_id` | string | 对排序后的 region pair、配置和输入版本求摘要 |
| `region_a_id`, `region_b_id` | string | 规范化顺序，`a < b` |
| `face_pair_hints` | list[(face_id, face_id)] | 可选面级候选 |
| `broad_phase_method` | enum | `AABB` / `OBB` / `TOPOLOGY_HINT` / `MANUAL` |
| `bounds_gap_mm` | float | 包围盒下界距离 |
| `candidate_tolerance_mm` | float | 仅用于 broad phase 的膨胀量 |
| `evidence` | map | 过滤原因、计数、耗时 |
| `status` | enum | `PENDING` / `EVALUATED` / `REJECTED` / `FAILED` |
| `config_digest` | string | 候选配置身份 |

候选算法应偏召回；精确分类器可以拒绝候选。AABB 不重叠不得直接证明 `DISJOINT`，除非距离下界大于明确的 near-miss 上限。

## 7. Interface relation taxonomy

统一 relation enum 至少包含：

| 类型 | 拓扑/几何含义 | 是否产生 2D patch |
|---|---|---:|
| `DISJOINT` | nominal tolerance 下闭包无交，且不在 near-miss 带内 | 否 |
| `NEAR_MISS` | 无精确接触，但最小距离在声明的 proximity/fuzzy 带内 | 否 |
| `TOUCH_POINT` | 最大交集维度为 0 | 否 |
| `TOUCH_EDGE` | 最大交集维度为 1，且没有二维同域重叠 | 否 |
| `FACE_CONTACT` | 存在二维接触，但不进一步声明覆盖关系 | 是 |
| `PARTIAL_FACE_OVERLAP` | 二维同域 overlap，且 patch 未覆盖任一相关 source face 的全部 interior，或只完全覆盖一侧的小 face | 是 |
| `FULL_FACE_OVERLAP` | patch 在容差内覆盖相关两侧 source face 的全部 interior | 是 |
| `CONTAINMENT` | 一个 solid 严格包含另一个，边界可接触或不接触；需子类型 | 视边界而定 |
| `CROSSING` | 两 region 边界横截并形成 section curve，通常伴随非法内部穿插 | 否，除非另有同域片 |
| `VOLUME_OVERLAP` | solid common 具有正体积；多区域模型通常应拒绝 | 否，不把 overlap volume 当 interface patch |
| `AMBIGUOUS` | 运算失败、维度证据冲突、容差敏感或无法唯一分类 | 不自动接受 |

`BRepAlgoAPI_Section` 的 edge/vertex 输出只能证明 0D/1D interference；只有 same-domain 验证加二维 common/split 证据才能生成 atomic patch。

## 8. `AtomicInterfacePatch`

### 8.1 目的

表示 B-rep intersection/split/fragment 后得到的最小有效二维接触片。这里的“atomic”相对于本次 operation graph 与 connected-component 分解；并不声称几何面无法进一步细分。

### 8.2 字段

| 字段 | 类型 | 必需 | 说明 |
|---|---|---:|---|
| `patch_id` | string | 是 | region pair、source faces、operation graph、shape digest 的确定性摘要 |
| `region_a_id`, `region_b_id` | string | 是 | 规范化 region pair |
| `source_face_ids_a`, `source_face_ids_b` | ordered set[string] | 是 | 两侧原始 face；不得为空 |
| `generated_shape_ref` | opaque face/shell ref | 是（运行时） | 生成的 2D B-rep shape |
| `generated_shape_digest` | string | 是 | 持久校验摘要 |
| `area_mm2` | float | 是 | B-rep mass properties 面积 |
| `boundary_wire_digests` | list[string] | 是 | outer/inner wire 身份 |
| `component_index` | int | 是 | 同 region pair 的确定性 component 序号 |
| `relation_type` | taxonomy enum | 是 | 必须是能产生 2D patch 的类型 |
| `nominal_tolerance_mm` | float | 是 | 输入实体与运算采用的 nominal tolerance |
| `fuzzy_value_mm` | float | 是 | 0 表示 nominal run |
| `validation` | record | 是 | validity、dimension、area、boundary、same-domain 证据 |
| `provenance_id` | string | 是 | operation history 根节点 |

### 8.3 不变量

- 面积必须有限且大于 `area_epsilon_mm2`；小于阈值的结果记录为 rejected fragment，不静默丢失。
- patch 的 interior 必须同时位于两 region 的边界上；仅位于一个 solid 内部的 Boolean fragment 不是 contact patch。
- `source_face_ids_a/b` 由 operation history 得到；若只能空间猜测，provenance 状态为 incomplete，不能进入主结果。
- 多个 disconnected 结果必须产生多个 patch ID；同一 patch 的 holes 保留为 inner wires，不拆成多个 patch。
- A/B 顺序只用于规范化身份，不改变各自 face orientation；两侧法向关系单独保存。

## 9. `InterfaceSourceBoundary`

### 9.1 目的

把已确认的 geometric patch 提升为场边界条件。`Material Source Object` 与 `Interface Source Boundary` 不是同一对象。

**[DESIGN-DECISION]** **Source Material Region** 是携带材料语义的整个 `SolidRegion`/`MaterialRegion`；**Interface Source Boundary** 是该 region 与 `GradientDomain` 接触后，从 confirmed 2D patches 中激活的 `Γ`。二者是两个对象：前者提供材料来源语义，后者才进入 field solver 的边界条件。

对于 `A | G | B`：

```text
ΓA = confirmed interface(A, G) → boundary value φ=0
ΓB = confirmed interface(G, B) → boundary value φ=1
```

### 9.2 字段

| 字段 | 类型 | 说明 |
|---|---|---|
| `boundary_id` | string | domain、patch set、condition 的摘要 |
| `gradient_domain_id` | string | 所属 `ΩG` |
| `source_region_ids` | ordered set[string] | 提供材料语义的 source regions |
| `patch_ids` | ordered set[string] | 构成 `Γ` 的 confirmed patches |
| `condition_kind` | enum | `DIRICHLET_SCALAR` / `MATERIAL_FRACTIONS` / `DISTANCE_SOURCE` |
| `scalar_value` | float/null | 例如 0 或 1 |
| `fractions` | map[material_key,float]/null | 多材料边界组成 |
| `orientation` | enum | `DOMAIN_OUTWARD` / `DOMAIN_INWARD` / `UNSPECIFIED` |
| `selection` | record | `AUTO` / `MANUAL_OVERRIDE`，规则、操作者和时间 |
| `provenance_id` | string | 选择与几何来源 |

一个 patch 可参与一个 domain 的一个 source boundary。重复或冲突条件必须在 solver 之前报错。

## 10. `ProvenanceRecord`

### 10.1 操作 DAG

每个 provenance node 包含：

| 字段 | 说明 |
|---|---|
| `provenance_id` | node 内容的确定性摘要 |
| `operation` | `IMPORT_STEP`、`VALIDATE`、`COMMON`、`SECTION`、`SPLIT`、`GENERAL_FUSE`、`UNIFY_SAME_DOMAIN`、`SELECT_SOURCE_BOUNDARY` 等 |
| `input_entity_ids` | region/face/patch/provenance IDs |
| `output_entity_ids` | 派生实体 IDs |
| `backend` | `freecad_part` / `occt` / `manual` |
| `backend_version` | FreeCAD 与 OCCT 版本 |
| `parameters` | nominal/fuzzy/linear/angular tolerance、non-destructive 等 |
| `history_links` | 对每个 source shape 的 `UNCHANGED` / `MODIFIED` / `GENERATED` / `DELETED` 映射 |
| `warnings`, `errors` | 内核结构化报告与稳定错误码 |
| `input_digest`, `output_digest` | 几何摘要 |
| `run_id` | 实验运行身份 |

### 10.2 完整度

`provenance_completeness` 是必填枚举：

- `COMPLETE`：每个输出 patch 都能追到两侧 source face；
- `PARTIAL`：能追到 source solid，但至少一侧 face 缺失；
- `MISSING`：只能通过空间匹配推测；
- `NOT_APPLICABLE`：例如 DISJOINT 关系没有输出 patch。

主方法 accepted patch 必须为 `COMPLETE`。空间最近面匹配只能作为 diagnostic fallback，并标记 `PARTIAL/MISSING`。

## 11. `FieldQuery`

本轮只定义接口，不选择 PDE、离散化或求解器。

逻辑签名：

```text
evaluate(
  points: N×3 float array,
  frame_id: string,
  gradient_domain_id: string
) -> FieldBatch
```

`FieldBatch` 至少包含：

- `points`：按原顺序回传或引用；
- `inside_domain[N]`：点是否在 `ΩG` 内/边界上；
- `valid[N]`：能否可靠求值；
- `phi[N]`：双材料标量，可为空；
- `fractions[N,M]` 与 `material_keys[M]`：多材料组成，可为空；
- `diagnostics[N]`：outside、boundary、interpolation failure 等原因；
- `field_artifact_id`、`solver_config_digest`、`provenance_id`。

不变量：

- 双材料模式下 `φ∈[0,1]`，允许的数值超界 epsilon 必须声明；
- fraction 模式下每项非负且每行和为 1（在声明 epsilon 内）；
- `ΓA` 上 `φ=0`、`ΓB` 上 `φ=1` 的误差由 solver validation 报告；
- outside point 不做未经声明的 extrapolation；
- scalar 与 fraction 表示不能互相矛盾，双材料时约定 `f_A=1-φ`、`f_B=φ`。

## 12. `SliceFieldMap`

### 12.1 目的与权威

`SliceFieldMap` 是未来 `z=zk` 截面的机器可读材料图。其轮廓权威来自 `GradientDomain` 与切片平面的 topology-aware intersection；材料值权威来自指定 `FieldQuery` artifact。显示网格或截图不得成为其数据来源。

### 12.2 输入、输出与身份

输入为 `SlicePlane`、`GradientDomain`、`FieldQuery`、sampling config 和 `InternalInterfacePolicy`。输出至少包含：

- `slice_map_id`；
- `slice_plane` 与 `frame_id`；
- `domain_contours_2d`、holes 和 topology status；
- `sample_points_2d` 与对应 3D points；
- `phi` 或 fractions、valid/inside mask 和 diagnostics；
- sampling resolution、误差估计；
- `field_artifact_id`、`domain_id`、interface IDs、policy ID 和 `provenance_id`。

稳定身份由 canonical plane、domain ID、field artifact ID、sampling config 和 policy digest 共同生成。它依赖 `GradientDomain`、`FieldQuery` 和已验证截面，但不负责生成 toolpath/G-code，也不把内部材料界面从上游几何中删除。

## 13. `InternalInterfacePolicy`

### 13.1 目的

在保留 A/G、G/B 几何和场边界的前提下，决定制造视图是否发射内部界面轮廓。MVP 冻结两个值：

```text
KEEP_INTERNAL_INTERFACE
SUPPRESS_INTERNAL_INTERFACE
```

### 13.2 合同

- 输入：`SliceFieldMap` 中的 interface-tagged contours、请求 mode、operator/config identity；
- 输出：每条 contour 的 `EMIT` / `SUPPRESS_FOR_FABRICATION` 决策及理由；
- 稳定身份：policy schema version + canonical payload digest；
- provenance：创建者、时间、run/config、输入 interface IDs；
- 依赖：上游 immutable interface/field/slice records；
- 明确非职责：不得删除/改写 `AtomicInterfacePatch`、`InterfaceSourceBoundary`、B-rep faces 或 `φ` 边界条件。

**[DESIGN-DECISION]** `SUPPRESS_INTERNAL_INTERFACE` 只影响 fabrication contour emission；geometry/topology 和 field 两层始终保留 `ΓA/ΓB`。

## 14. 切片和 fabrication policy 接口

未来切片输入：

```text
SlicePlane(frame_id, origin_mm, normal, slice_id)
GradientDomain
FieldQuery
FabricationPolicy
```

输出 `SliceFieldMap`：

- `domain_contours_2d`：`ΩG` 与平面的拓扑截面；
- `sample_points_2d/3d`；
- `phi` 或 fractions；
- contour 与 field provenance；
- sampling resolution、误差估计和无效点掩码。

`FabricationPolicy` 引用一个 `InternalInterfacePolicy`；`SUPPRESS_INTERNAL_INTERFACE` 的含义仅是下游不把 A/G、G/B 内部边界输出为打印外轮廓。它不得从 B-rep、patch、source boundary 或 provenance 中删除对应几何。

## 15. 结果与失败合同

每个 stage 返回 `result + diagnostics`，不能用空列表同时表达“没有接触”和“算法失败”。最小状态集：

```text
SUCCEEDED
SUCCEEDED_WITH_WARNINGS
REJECTED_BY_POLICY
AMBIGUOUS
FAILED_IMPORT
FAILED_VALIDATION
FAILED_BOOLEAN
FAILED_PROVENANCE
```

所有结果记录 config digest、输入 digest、backend 版本、耗时和峰值内存采样。错误码是闭集；新增错误码需要更新 schema 和实验解析器。
