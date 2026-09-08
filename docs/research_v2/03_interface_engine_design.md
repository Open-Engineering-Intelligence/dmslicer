# STEP/B-rep Interface Engine 技术设计

## 证据状态

- **[CODE-CONFIRMED]** 当前 legacy core 只提供 AMF surface-mesh heuristic；本机有 FreeCADCmd `1.1.1` / OCCT `7.8.1`，项目解释器没有 standalone PythonOCC 或 Gmsh。
- **[EXTERNAL-API-CONFIRMED]** OpenCASCADE 官方接口提供 common、section、split/general-fuse、same-domain 归并、拓扑遍历、fuzzy options 与 operation history 基础能力；FreeCAD `Part::TopoShape` 提供相应高层入口。
- **[DESIGN-DECISION]** Phase I 通过受控 FreeCADCmd adapter 使用现有 CAD kernel，不自行实现 B-rep Boolean kernel。
- **[OPEN-QUESTION]** FreeCAD 1.1.1 Python 层能否对所有 benchmark 提供 face-level complete history 尚未被当前代码证明；CASE 01/03/07 是强制 capability gate。

## 1. 范围

本设计只定义第一阶段 Interface Engine。它不实现 STEP 代码、不调用 Boolean 生成 fixture、不引入 Gmsh、不求解材料场，也不修改 legacy `canonicalize.py`。

主后端优先采用已安装的 FreeCAD Part/OpenCASCADE：本机 FreeCADCmd `1.1.1`，内嵌 OCCT `7.8.1`。项目 Python 中没有 standalone `OCC`、`gmsh` 或 `cadquery` module，因此第一版应通过受控 FreeCADCmd 进程边界运行，而不是假设主 `.venv` 可直接 import FreeCAD。

## 2. 组件边界

```text
Application / Experiment Runner
            │ immutable request/result DTO
            ▼
InterfaceEngine facade
├─ StepDocumentImporter
├─ ShapeValidator
├─ StableIdentityRegistry
├─ CandidateGenerator
├─ OcctOperationAdapter
├─ RelationClassifier
├─ AtomicPatchExtractor
├─ ProvenanceBuilder
└─ InterfaceResultValidator
            │
            ├─ FreeCADCmd + Part/OpenCASCADE  ← geometry truth
            ├─ LegacySurfaceContactBackend    ← comparison only
            └─ DisplayMeshAdapter → PyVista   ← display only
```

`InterfaceEngine` 不认识 Streamlit session state 或 PyVista actors。UI 只能提交 request、读取 result、保存 manual override；不能取得并原地修改 `TopoDS_Shape`。

### 2.1 三层结果不得合并

**[DESIGN-DECISION]** 每个 region pair 必须依次经过三个独立层次，并保存各自记录：

| 层次 | 回答的问题 | 权威来源 | 允许输出 | 禁止推论 |
|---|---|---|---|---|
| broad phase candidate | 是否值得进行昂贵检查？ | 膨胀 AABB/OBB/topology hints | `InterfaceCandidate`、bounds gap、filter reason | candidate 不能等于 contact |
| geometry truth | 实体交集的维度、关系和 fragment 是什么？ | validated B-rep + nominal/fuzzy OCCT operations | relation record、section evidence、`AtomicInterfacePatch`、operation history | geometry result不能自动决定材料/场语义 |
| semantic activation | 哪些 confirmed patches 成为 `Γ`？ | role、`ParticipationPolicy`、manual/auto selection rule | `InterfaceSourceBoundary` | inactive patch 不得从 geometry truth 删除 |

完整数据流固定为：

```text
STEP
→ validated SolidRegion
→ broad-phase InterfaceCandidate
→ exact/fuzzy relation and intersection dimensionality
→ split/fragment
→ AtomicInterfacePatch + provenance
→ semantic activation
→ InterfaceSourceBoundary
```

## 3. 输入输出合同

### 输入 `InterfaceRequest`

- STEP 文件路径和 expected SHA-256；
- import policy：单位、assembly 展开规则、compound/compsolid 规则；
- region roles 与 `ParticipationPolicy`；
- nominal tolerance、candidate tolerance、near-miss band；
- fuzzy sweep（默认空）；
- operation flags：non-destructive、parallel（论文默认 false 以减少非确定性）；
- run ID 与 config digest。

### 输出 `InterfaceResult`

- `SolidRegion[]` 与 import/validation diagnostics；
- `InterfaceCandidate[]`；
- 每个 pair 的 relation record，包括 0D/1D/2D/3D 证据；
- `AtomicInterfacePatch[]`；
- 可构造的 `InterfaceSourceBoundary[]` 建议，不自动覆盖人工 policy；
- provenance DAG；
- rejected/ambiguous fragments、内核 warnings/errors；
- stage timing、内存、版本、输入/输出 digest。

空 patch 集必须同时携带 `DISJOINT`、`TOUCH_EDGE`、`CROSSING`、`AMBIGUOUS` 或失败状态之一。

## 4. STEP import 与实体映射

### 4.1 推荐 import 路径

1. 在隔离的 FreeCADCmd 文档中使用 FreeCAD `Import` 工作台导入 STEP，以尽可能保留 product labels、颜色和 assembly placement。
2. 遍历导入对象，解析最终 placement 后的 `Part::TopoShape`。
3. compound/compsolid 展开成唯一 solids；一个 accepted `SolidRegion` 对应一个 `TopoDS_Solid`。
4. 保存原始 STEP 文件 SHA-256、原单位、转换到 mm 的 scale、product path、FreeCAD object name/label 和确定性 solid ordinal。
5. 构造 face/edge maps 和几何 fingerprint；不得把 FreeCAD document object name 当全局稳定 ID。

Gmsh 官方教程表明其 OpenCASCADE kernel 可以 `ShapeFromFile` 导入 STEP 并显式设置目标单位；该能力留给第二阶段体网格化备选，不是 Phase I import authority。[Gmsh STEP import and OpenCASCADE tutorial](https://gmsh.info/doc/texinfo/gmsh.html#t20)

### 4.2 TopoDS 类型映射

| OCCT 类型 | v2 概念 | 用途 |
|---|---|---|
| `TopoDS_Solid` | `SolidRegion.geometry_ref` | 封闭实体真值 |
| `TopoDS_Shell` | validation evidence | solid 闭合与方向检查 |
| `TopoDS_Face` | source face / generated patch | 二维界面及其来源 |
| `TopoDS_Wire` | patch boundary | outer/inner loop |
| `TopoDS_Edge` | section curve / adjacency | 一维相交与 patch 边界 |
| `TopoDS_Vertex` | point touch | 零维相交 |

`TopoDS_TShape`、Location 和 Orientation 共同影响 shape 身份；内存期的 partner/same 判断可辅助映射，但不能替代持久 locator。

### 4.3 外部 API 到 v2 职责映射

| 外部 API / 概念 | 官方能力边界 | v2 用途 |
|---|---|---|
| STEP import / FreeCAD `Part::TopoShape` | 导入 CAD shape 并暴露 solids/faces/edges 与 placement | 构造 `SolidRegion` 和 source locators；不把 FreeCAD object name 当稳定 ID |
| `TopoDS_Solid` / `Face` / `Edge` | 分别表示 3D、2D、1D B-rep 拓扑实体 | region truth、patch/source face、section/boundary evidence |
| `TopExp_Explorer` / ancestor maps | 遍历 subshapes 并建立反向祖先关系 | face/edge/solid adjacency 与确定性 locator evidence |
| `BRepAlgoAPI_Common` | 计算 Boolean common | 判定正体积 overlap，并为低维关系提供几何证据 |
| `BRepAlgoAPI_Section` | 结果由 vertices/edges 构成 | 0D/1D section evidence；不能直接生成二维 patch |
| `BOPAlgo_Splitter` / General Fuse | 以 tools 分割 objects 或共同 fragment，并支持 fuzzy/non-destructive/history options | 生成 atomic fragments 与 ancestry evidence |
| same-domain + `ShapeUpgrade_UnifySameDomain` | 识别/归并位于同一几何 domain 的 face/edge | 在保存 source history 后规范化二维 coincident overlap |
| builder operation history | `Modified` / `Generated` / `IsDeleted` 等 source→result 关系 | 构建 `ProvenanceRecord`；binding 暴露不足时 fail closed |
| native/fuzzy tolerance | shape tolerance 与额外 fuzzy value 会影响 Boolean 结果 | nominal/fuzzy 分开运行和报告，不把 fuzzy 升格为 exact truth |

**[EXTERNAL-API-CONFIRMED]** 上表能力由 OpenCASCADE 的 [BRepAlgoAPI package](https://dev.opencascade.org/doc/refman/html/package_brepalgoapi.html)、[Splitter](https://dev.opencascade.org/doc/occt-7.7.0/refman/html/class_b_rep_algo_a_p_i___splitter.html)、[TopExp](https://dev.opencascade.org/doc/refman/html/class_top_exp.html) 及 FreeCAD [Part::TopoShape](https://freecad.github.io/SourceDoc/d8/ded/classPart_1_1TopoShape.html) 官方资料支持。具体 Python binding 返回值仍以 Phase I capability tests 为准。

## 5. Topology exploration 与 adjacency

**[EXTERNAL-API-CONFIRMED]** OCCT 的 `TopExp_Explorer` 用于向下遍历拓扑；`TopExp::MapShapesAndUniqueAncestors` 可建立 edge→faces、face→solids 等反向关系，并可选择是否区分 orientation。[OCCT TopExp reference](https://dev.opencascade.org/doc/occt-7.9.0/refman/html/class_top_exp.html)

本机 FreeCAD `Part::TopoShape` 已确认公开：

- `ancestorsOfType(subshape, shape_type)`；
- `isSame` / `isPartner`；
- `Faces` / `Edges` / `Solids` 等子实体访问。

第一版 adapter 可用 FreeCAD 的 `ancestorsOfType` 建图，但必须以确定性 map 去重并保留 orientation。若高层 API 无法返回足够的 source mapping，应在 adapter 内引入受控低层 OCCT bridge；不得在应用层用面序号猜祖先。

## 6. Candidate generation

候选阶段只做高召回过滤：

1. 对 active region 的 B-rep bounds 使用 `candidate_tolerance_mm` 膨胀；
2. 生成规范化 region pair；
3. 可选生成膨胀 face-box pair hints；
4. 记录所有被过滤 pair 的 bounds distance 和理由；
5. `IGNORE/ISOLATE` policy 在这里生效，但不删除 region。

与 legacy 的 exact AABB hard gate 不同，v2 候选膨胀量必须大于等于 planned near-miss 上限，否则 CASE 08 无法进入精确诊断。候选数量与精确判定数量分别计时。

## 7. 精确关系判定流水线

对每个 candidate 执行以下固定顺序：

### 7.1 Nominal solid-level check

- 检查每个 solid 的 validity、体积和 boundary；
- 计算 solid common 的最高维度；
- common 有正体积时报告 `VOLUME_OVERLAP`，不得提取为 interface；
- 用 point-in-solid/containment 检查区分严格包含与重叠。

**[EXTERNAL-API-CONFIRMED]** `BRepAlgoAPI_Common` 是 OCCT 的 Boolean intersection 运算。[OCCT BRepAlgoAPI_Common](https://dev.opencascade.org/doc/occt-7.7.0/refman/html/class_b_rep_algo_a_p_i___common.html) 本机 FreeCAD 的 `TopoShape.common` 已确认支持单/多 tool 和可选 fuzzy tolerance。

### 7.2 Section dimension evidence

运行 nominal section，统计 vertices 和 edges，并追踪产生这些 section edges 的两侧 faces。**[EXTERNAL-API-CONFIRMED]** OCCT 明确说明 `BRepAlgoAPI_Section` 的结果由 vertices 和 edges 组成，而不是二维 faces；因此 section edge 不能直接当 interface patch。[OCCT BRepAlgoAPI_Section](https://dev.opencascade.org/doc/refman/html/class_b_rep_algo_a_p_i___section.html)

判定：

- 仅 vertex → `TOUCH_POINT`；
- edge/curve 且没有 2D evidence → `TOUCH_EDGE` 或 `CROSSING`；
- crossing 与 touch 的区分依赖 local side/classifier：边界是否穿越对方 solid interior、是否有正体积 overlap。

### 7.3 Same-domain 与二维 overlap

对 face pair hints 和 section ancestors：

1. 判断 underlying surfaces 在声明 linear/angular tolerance 下是否 same-domain；
2. 对 same-domain trimmed faces 计算二维 common/fragment；
3. 验证结果位于两侧 region boundary；
4. 计算 B-rep area、source-face coverage 和 boundary wires；
5. 依据双侧覆盖率分类 `FULL_FACE_OVERLAP` 或 `PARTIAL_FACE_OVERLAP`。

same-domain 意味着相邻 face/edge 落在重合 surface/curve 上，而不仅是法线近似平行。**[EXTERNAL-API-CONFIRMED]** `ShapeUpgrade_UnifySameDomain` 可合并这种 face/edge，并支持 linear/angular tolerance。[OCCT ShapeUpgrade_UnifySameDomain](https://dev.opencascade.org/doc/occt-7.7.0/refman/html/class_shape_upgrade___unify_same_domain.html)

`UnifySameDomain` 只允许作为结果规范化步骤：先保存 source faces 和 split history，再 unify。若先 refine 输入，会破坏原 face provenance。

### 7.4 Split / General Fuse / atomic fragments

- 对需要分片的二维重叠，优先使用 non-destructive split/general-fuse；
- 将输出按拓扑 connected components 分解；
- 一片带 hole 的 face 保留为一个 patch，多片 disconnected faces 生成多个 patch；
- 面积小于阈值的 sliver 作为 rejected fragment 记录。

**[EXTERNAL-API-CONFIRMED]** OCCT `BOPAlgo_Splitter` 把 Objects 按 Tools 分割，结果只保留 Objects 的 split parts。[OCCT BOPAlgo_Splitter](https://dev.opencascade.org/doc/refman/html/class_b_o_p_algo___splitter.html) 本机 FreeCAD `TopoShape.generalFuse` 已确认返回 `(result, map)`：map 给出每个 argument 对应的 result children。这个 map 是 Phase I 的首选 ancestry 入口，但能否提供完整的 face-level history 必须由 CASE 01/03/07 的 adapter probe 验证。

## 8. Boolean operation history

**[EXTERNAL-API-CONFIRMED]** OCCT builder API 提供 `Modified`、`Generated`、`IsDeleted`、`SetToFillHistory` 和 `History()`；还可以收集 warnings/errors 与 fuzzy value。[OCCT BRepAlgoAPI_BuilderAlgo](https://dev.opencascade.org/doc/refman/html/class_b_rep_algo_a_p_i___builder_algo.html)

每次 operation 必须保存：

```text
input source entities
operation kind + ordered arguments/tools
nominal and fuzzy tolerance
non-destructive / parallel / glue flags
Modified(source) outputs
Generated(source) outputs
IsDeleted(source)
kernel report
result shape digest
```

高层 FreeCAD `generalFuse` 的 argument→pieces map 不等于完整 OCCT history。设计采用 capability gate：

- 若可从 map 和 `isSame` 完整建立 source-face→patch 映射，记录 `COMPLETE`；
- 若只能到 source solid，记录 `PARTIAL`，结果不进入主指标；
- 不允许用“最近面”把 `PARTIAL` 伪装成 `COMPLETE`；
- 若 FreeCAD Python binding 暴露不足，后续单独设计窄 OCCT bridge，而不是重写 Boolean kernel。

## 9. Tolerance 与 fuzzy 策略

### 9.1 三类阈值分离

| 阈值 | 用途 | 能否改变最终分类 |
|---|---|---:|
| entity/native tolerance | STEP/B-rep 自带精度 | 是，必须记录 |
| candidate tolerance | broad phase 膨胀 | 否，只决定是否计算 |
| fuzzy value | Boolean 附加容差 | 是，但结果必须标为 fuzzy |
| near-miss band | proximity 分类 | 只产生 `NEAR_MISS` |
| area epsilon | 拒绝数值 sliver | 是，记录 rejected fragment |

### 9.2 两遍运行

1. **nominal pass**：`fuzzy=0`，得到论文主分类；
2. **diagnostic fuzzy sweep**：只对 `DISJOINT/AMBIGUOUS` 和 CASE 09 运行预注册的 fuzzy values。

**[EXTERNAL-API-CONFIRMED]** Fuzzy Boolean 使用额外 tolerance 处理轻微 gap/embedding，但选择值应基于被测 gap，且会改变拓扑。[OCCT fuzzy Boolean description](https://dev.opencascade.org/sites/default/files/pdf/OCCT_release_notes_6.9.0.pdf) 因此 fuzzy pass 不能覆盖 nominal 结果：例如 nominal `NEAR_MISS`、fuzzy `FACE_CONTACT@0.02mm` 必须同时保留。

### 9.3 推荐初始研究参数

以下是待 benchmark 验证的研究默认值，不是制造容差：

```text
internal unit             = mm
candidate_tolerance       = 0.05 mm
near_miss_max_gap         = 0.05 mm
nominal_fuzzy_value       = 0.0 mm
diagnostic fuzzy sweep    = [1e-6, 1e-5, 1e-4, 1e-3, 1e-2, 5e-2] mm
angular_same_domain_tol   = 1e-6 rad
area_epsilon              = 1e-8 mm²
```

这些值必须在 CASE 09 前注册，并同时按模型 characteristic length 报告无量纲比例；不得看完结果后逐 case 调参。

## 10. Relation classifier 决策表

| solid common | section | 2D same-domain patch | proximity | 输出 |
|---|---|---|---|---|
| positive volume | 任意 | 任意 | 任意 | `VOLUME_OVERLAP` 或 containment subtype |
| none | none | none | gap > band | `DISJOINT` |
| none | none | none | 0 < gap ≤ band | `NEAR_MISS` |
| zero volume | vertices only | none | 0 | `TOUCH_POINT` |
| zero volume | edges | none | 0 | `TOUCH_EDGE`；若横截语义成立则 `CROSSING` |
| zero volume | optional edges | positive area | 0 | `FULL_FACE_OVERLAP` / `PARTIAL_FACE_OVERLAP` |
| conflicting/failed | 任意 | 不确定 | 任意 | `AMBIGUOUS` |

`FACE_CONTACT` 只用于确认二维接触但覆盖子类无法可靠计算的情况；主 benchmark 应尽量输出 full/partial 的更具体分类。

## 11. Source boundary 自动构造

对每个合法 `GradientDomain G`：

1. 选择 `region_id=G` 的 confirmed 2D patches；
2. 邻区必须为 `source_eligible=true`；
3. 按 source material key 与 boundary value 分组；
4. 生成 `InterfaceSourceBoundary`，保留 patch IDs；
5. 检查 boundary interiors 不重叠且均属于 `∂G`；
6. 对 A/G 设 `ΓA`、对 G/B 设 `ΓB`；
7. 多 source 情况只生成边界集合，不在 Phase I 推断 PDE 解法。

自动建议可以被 Streamlit 人工 override，但 override 生成新的 selection provenance，不能修改 underlying patch。

## 12. 进程与工件协议

由于 FreeCAD 与项目 Python 环境分离，推荐 future runner 采用 JSON request/response + staging directory：

- 主进程验证 input hash 和 request schema；
- FreeCADCmd 只读输入 STEP，写入本次 run 的 staging；
- 输出 JSON 只含 DTO、诊断和 artifact hashes；B-rep 工件用独立文件引用；
- subprocess 使用参数数组、`shell=false`、timeout 和 stdout/stderr 捕获；
- 主进程校验响应、hash、文件集合后才发布 run artifact；
- 用户 FreeCAD 配置中的 Robust MCP Bridge 初始化异常必须进入 environment diagnostics。

该协议与旧 `GeometryKernel` 对象完全隔离。

## 13. Gmsh 的后续位置

Gmsh 是 Phase II 的候选 volume discretization backend：可通过 OpenCASCADE import/fragment 后生成共享拓扑的 tetrahedral mesh。当前本机项目环境未发现 Gmsh，因此不能把它写成已满足依赖。Phase I 不依赖 Gmsh；待 Interface Engine 稳定后再比较 Gmsh、FreeCAD FEM 或其他离散化路径。

## 14. 明确禁止的耦合

- 不在 `canonicalize.py`、`patch_level.py` 或旧 AMF parser 中增加 STEP 分支；
- 不把 PyVista `PolyData` 传回 relation classifier；
- 不让 Streamlit 直接写 `TopoDS_Shape` 或修改 operation history；
- 不把 `removeSplitter()`/unify 后的简化形状当作无历史的原始 face；
- 不把 fuzzy contact 报成 nominal exact contact；
- 不为解决 binding 不足而自研 B-rep Boolean kernel。

## 15. 第一实现切片的技术门禁

后续实现开始前必须先证明：

1. FreeCADCmd headless import 在受控配置下可重复；
2. CASE 01 的三 solids 可通过 product path 稳定定位；
3. `common/section/generalFuse/ancestorsOfType` 的实际返回结构可序列化；
4. 两片 400 mm² patch 能追踪到四个 source faces；
5. 重新运行得到相同 semantic digest；
6. 任一 provenance 缺失时能 fail closed。

这些是 adapter feasibility gate，不是对完整 Interface Engine 的实现授权。
