# 旧 DM-Slicer 到 v2 的映射与隔离边界

## 证据状态

- **[CODE-CONFIRMED]** 旧 source/gradient/isolation、pair/patch/component/section、RegionTriangle、PyVista、Streamlit 与 AMF 的职责来自当前代码和 legacy audit。
- **[DESIGN-DECISION]** v2 采用方案 B，通过 anti-corruption adapter 并存 legacy mesh backend 与 STEP/B-rep authority，不在旧核心中添加 STEP 分支。

## 1. 总体策略

采用方案 B：保留旧 UI、实验框架、人工标注、PyVista、pair/patch/component 思想和 AMF contact algorithm；建立独立 STEP/B-rep core 作为新几何真值。迁移通过 DTO/adapter，而不是在旧核心文件中增加 `if step:` 分支。

```text
                    ┌─ LegacySurfaceContactBackend ─ AMF mesh heuristic
Experiment request ─┤
                    └─ StepBRepInterfaceBackend ──── FreeCAD/OCC truth
                              │
                     Unified InterfaceResult
                              │
               Streamlit review / metrics / field boundary
```

## 2. 概念映射

| 旧概念 | v2 概念 | 迁移决策 |
|---|---|---|
| `MeshData` object | `SolidRegion` 的 legacy surface view | 不作为 v2 持久身份 |
| `SourceMaterial` | `MaterialRegion` 语义视图（`SolidRegion.role=SOURCE` + metadata）以及另行生成的 `InterfaceSourceBoundary` | source material region 与 `Γ` 是两个对象；只迁移语义，不迁移继承设计 |
| `GradientMaterial` | `SolidRegion.role=GRADIENT` semantic role + 经验证的 `GradientDomain` | 角色只表示意图；必须另行验证闭合 `ΩG`，且仍不等于 volumetric field |
| `IsolationMaterial` | `ParticipationPolicy` | 替换继承为正交 policy |
| include/exclude neighbor IDs | interface activation / manual override | 转换为显式规则并保存审计记录 |
| object AABB pair | `InterfaceCandidate` / normalized `RegionPair` | 可保留为 legacy/broad phase，不是 confirmed interface |
| BVH triangle pair | candidate evidence | 仅 legacy backend |
| angle/gap/projected overlap | legacy relation evidence | 论文 baseline，不进入 B-rep truth |
| Patch / ACAG | `AtomicInterfacePatch` / interface component | 保留分层思想，重建身份和几何实现 |
| full/other section | legacy evidence classification | 不直接映射打印 slice |
| RegionTriangle | local surface overlay baseline | 不映射体梯度域或 B-rep Boolean |
| `Object.material` | application assignment record | UI 不再原地修改 geometry object |
| material assignment JSON | semantic annotation artifact | 可迁移，需稳定 region correspondence |
| experiment stages | v2 stage orchestration | 复用生命周期/manifest 思想，增加 backend stages |
| PyVista PolyData | `DisplayMesh` | 明确标记 derived、只读 |

## 3. 可以直接复用的能力

### 3.1 实验框架

`src/dmslicer/experiments/` 中 config、stage invalidation、fingerprint、events、metrics 和 stop-after 思想可作为 orchestration 基础。复用条件：stage payload 改为不可变 DTO，不把 `GeometryKernel` 或 FreeCAD shape 放进通用 manifest。

建议的未来 stage 名称：

```text
IMPORT
VALIDATE_REGIONS
CANDIDATE
RELATION
FRAGMENT
PROVENANCE
SOURCE_BOUNDARY
FIELD          # Phase II
SLICE_SAMPLE   # Phase III
SUMMARY
```

Legacy 现有 `PARSE/CONTACT/MATERIAL/SECTION/REGION_TRIANGLE/REPAIR` 保留在 legacy adapter 内，不强迫与新 stage 一一对应。

### 3.2 人工标注和 review

保留 Streamlit 的对象列表、材料选择、include/exclude、检查和 override 心智模型。写入目标改为 `AnnotationCommand`：

```text
target entity ID
old semantic value
new semantic value
operator/time/reason
input result digest
```

application service 验证命令后产生新 annotation artifact；UI 不直接写内核对象。

### 3.3 PyVista visualizer

保留现有 visualizer adapter 和 viewport 交互，用来显示：

- region derived meshes；
- candidate pair；
- confirmed/rejected patches；
- section curves；
- provenance 选中链；
- manual override 前后差异。

显示 mesh 要带 `source_entity_id` 和 `display_mesh_config_digest`。用户在 mesh 上 pick 后只能返回 source ID/hit point，由 geometry service 重新解析 B-rep entity。

### 3.4 Pair / patch / component 思想

旧算法最有价值的是证据分层：对象 pair → triangle pair → patch → component。v2 对应为 region candidate → face evidence → atomic patch → interface component。只复用概念和实验指标，不复用不稳定 list index 或 coverage-sum 逻辑。

## 4. 只作为论文 baseline 保留的代码

| 代码 | baseline 名称 | 使用限制 |
|---|---|---|
| `file_parser/amf_parser.py` | Legacy AMF importer | 保存 parser limitation；不称严格 AMF |
| `geometry_kernel/bvh.py` | Legacy triangle broad phase | 只处理 AMF surface mesh |
| `geometry_kernel/canonicalize.py` | Legacy surface contact | 冻结参数；不加 STEP 分支 |
| `geometry_kernel/patch_level.py` | Legacy patch/component | 输出适配 DTO；不作为 B-rep patch |
| `partial_triangle_resolver.py` | Legacy section inference | 不等于 slice-plane section |
| `regiontriangle/` | Legacy local overlay/repair | 不声称 conformal volume mesh |
| `materials/materials.py` | Legacy role behavior | 已知 bug 不在本轮修复；v2 不依赖其数学语义 |

论文调用名固定为 `LegacySurfaceContactBackend`。adapter 可以读取旧结果，但不得让旧对象成为 v2 `SolidRegion.geometry_ref`。

这里的 `MaterialRegion` 不是新增 geometry authority，而是 `SolidRegion` 加材料元数据与 semantic role 的领域视图；它不得包含或替代 `InterfaceSourceBoundary`。同理，`InterfaceComponent` 是同一 region pair 下 atomic patches 的连通/语义分组，不获得新的 B-rep truth。

## 5. 必须重建的能力

- namespace/assembly/unit-aware STEP import；
- stable document/region/face identity；
- solid validity 与闭合性；
- topology dimension classification；
- same-domain face overlap；
- common/section/split/general-fuse；
- Boolean history 与 source-face provenance；
- `GradientDomain` 和 `InterfaceSourceBoundary`；
- volume discretization 与 `FieldQuery`；
- B-rep/slice-plane intersection 与 field sampling。

旧代码中不存在这些完整合同，不能通过重命名旧 class 获得。

## 6. Anti-corruption layer

新旧 backend 只通过统一 DTO 比较：

```text
Legacy input adapter:
  canonical fixture manifest + AMF
  → old Model/GeometryKernel
  → LegacyEvidence
  → InterfaceResult-compatible predictions

STEP input adapter:
  canonical fixture manifest + STEP
  → SolidRegion/B-rep
  → InterfaceResult
```

转换约束：

- legacy object ID 必须通过 manifest 映射到 region ID；
- legacy triangle/patch IDs 保留在 `backend_evidence`，不伪造成 source STEP face IDs；
- legacy provenance completeness 通常低于 B-rep，原样评分；
- DTO serialization 不依赖 pickle；
- 两 backend 使用同一 relation taxonomy，但允许 `AMBIGUOUS/unsupported`。

## 7. PyVista 边界

### 允许

- visualization；
- inspection；
- debug；
- manual override display；
- 将 pick 映射回稳定 entity ID。

### 禁止

- 用 `PolyData` 判定 STEP same-domain；
- 用显示 tessellation area 作为 B-rep area；
- 从 viewport actor adjacency 推导 interface；
- 把 camera/float32/decimation 结果反馈给 geometry truth；
- 使用 screenshot 作为 regression oracle。

## 8. Streamlit 边界

### 负责

- workflow；
- manual annotation；
- result review；
- explicit override；
- experiment/backend comparison；
- diagnostics 和 provenance 展示。

### 不负责

- 直接执行或拼接 Boolean 操作；
- 原地修改 FreeCAD/OCCT shape；
- 生成稳定 ID；
- 决定 tolerance truth；
- 把 widget state 当持久科学结果。

UI 调用 application service；application service 再调用 backend。任何 override 都生成新 artifact 和 provenance，不覆盖原自动结果。

## 9. 旧 AMF 核心的保护区

以下文件视为 legacy protected zone：

```text
src/dmslicer/file_parser/amf_parser.py
src/dmslicer/geometry_kernel/canonicalize.py
src/dmslicer/geometry_kernel/bvh.py
src/dmslicer/geometry_kernel/patch_level.py
src/dmslicer/geometry_kernel/partial_triangle_resolver.py
src/dmslicer/geometry_kernel/regiontriangle/
src/dmslicer/materials/
```

Phase I 默认不修改这些文件。唯一允许的未来改动是窄 adapter 所必需、并有 legacy regression coverage 的公开只读接口；任何算法行为修复必须单独立项并产生新的 baseline version。

## 10. 依赖方向

```text
domain contracts        ← 不依赖 FreeCAD、PyVista、Streamlit、legacy
STEP backend            → domain contracts + FreeCAD/OCC adapter
legacy backend adapter  → domain contracts + old DM-Slicer
field backend           → domain contracts，不依赖 UI/legacy
slicing application     → domain contracts + FieldQuery
visualization adapter   → serialized DTO/display mesh
Streamlit               → application services
experiment runner       → backend facade + serialized metrics
```

禁止反向依赖：domain 不 import FreeCAD；geometry backend 不 import Streamlit；legacy code 不 import v2 STEP backend；FieldQuery 不 import PyVista。

## 11. 数据迁移规则

旧 material assignment 只有在满足下列条件时才能映射：

1. AMF 与 STEP 来自同一 canonical fixture bundle；
2. manifest 提供 AMF object ↔ STEP region correspondence；
3. correspondence 有 hash 和生成 provenance；
4. object 计数、bounds、volume/surface checks 通过；
5. 不使用 filename stem 或进程级 counter 自动猜测。

无法证明对应关系时，保留为 `unresolved_legacy_annotation`，由 UI 复核，不自动应用。

## 12. 版本和结果命名

- `backend=legacy_surface_contact`：旧 AMF 方法；
- `backend=step_brep_interface`：新 B-rep 方法；
- `backend=manual_annotation`：人工方法；
- 每个结果包含 `contract_schema_version`；
- 改 relation taxonomy、匹配规则或 identity schema 时提升相应版本；
- 旧结果永不被新 schema 静默重写。

## 13. 迁移停止线

第一阶段完成时旧 DM-Slicer 仍可独立运行；新 core 也可在无 UI 情况下运行。二者只在 experiment/application 层汇合。若实现需要把 STEP `TopoDS_Face` 塞进旧 `Object.triangles` 或让 `canonicalize.py` 同时处理两种表示，说明边界已经失守，应停止并重新设计 adapter。
