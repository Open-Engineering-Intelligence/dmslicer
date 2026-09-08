# DM-Slicer v2 最小科研 MVP 范围

## 证据状态

- **[DESIGN-DECISION]** Phase I MVP 只交付可复现实验所需的 STEP interface front-end 和 future solver input；field、slicing implementation、toolpath 与 G-code 均排除。
- **[CODE-CONFIRMED]** legacy Streamlit/PyVista、实验 runner 与 AMF contact algorithm 可作为 review/baseline 资产，但当前 Slicer 不构成 MVP 依赖。
- **[OPEN-QUESTION]** FreeCAD Python binding 的 face-level operation history 完整度将在 M1 capability gate 决定；不完整时应设计窄 OCCT bridge，而不是降低 provenance 合同。

## 1. MVP 定义

本 MVP 是“可发表实验链的最小几何前端”，不是完整切片器：

```text
canonical STEP fixture
→ validated SolidRegions
→ candidates
→ classified B-rep relations
→ AtomicInterfacePatches
→ InterfaceSourceBoundaries
→ machine-readable benchmark result
```

MVP 必须能为后续 `FieldQuery` 提供充分输入，但不在第一阶段求解 `φ`。

## 2. In scope

**[DESIGN-DECISION]** 第一版科研 MVP 的产品能力严格限于以下十一项；后续小节中的 schema、fixture、metric 和 UI 内容只是这些能力的验收与科研支撑，不扩大产品范围：

1. STEP multi-solid import；
2. stable provenance；
3. solid validation；
4. interface candidate detection；
5. B-rep relation classification；
6. interface extraction；
7. `AtomicInterfacePatch`；
8. A|G|B 自动识别 `ΓA/ΓB`；
9. manual correction / ground-truth contract；
10. reproducible experiment output；
11. future `FieldQuery` 能直接消费的数据接口。

### 2.1 研究合同

- `02_domain_model.md` 中 Phase I 类型的可序列化 schema；
- relation taxonomy 和闭集错误码；
- run/config/input/provenance digest；
- nominal/fuzzy 结果分离。

### 2.2 STEP/B-rep geometry

- FreeCADCmd/Part 导入一个 multi-solid STEP；
- 单位、assembly/product path、placement 和 stable locator；
- solid/closed/orientation/volume validation；
- region/face/edge 拓扑遍历；
- AABB broad-phase candidate；
- common、section、same-domain、split/general-fuse；
- 0D/1D/2D/3D 关系分类；
- atomic patch count、area、wires/components；
- source-face/operation provenance。

### 2.3 Fixtures 与 benchmark

- 先通过 CASE 01；
- 再发布 CASE 01–10 的 canonical STEP/AMF/truth bundle；
- 三 backend 统一 DTO；
- patch F1、type macro F1、area error、runtime；
- tolerance 和 tessellation ablation；
- machine-readable raw results 与可重建表格。

### 2.4 人工 review

- 现有 Streamlit/PyVista 作为 Manual Annotation reference 与 override 工具；
- 显示 region、source faces、section curves、patch 和 provenance；
- override 不修改 geometry truth，只产生 annotation artifact。

## 3. Explicitly out of scope

- 修复旧 `src/dmslicer/slicer/slicer.py`；
- 重写 Streamlit UI；
- 修改 legacy AMF contact 算法来追求更好结果；
- 工业级 STEP healing 或支持任意坏 CAD；
- 自研 B-rep Boolean kernel；
- tetrahedral/voxel volume discretization；
- normalized distance field 的实现；
- harmonic/Laplace solver；
- 自适应网格、GPU solver；
- toolpath、extrusion control、G-code；
- 打印机、材料或力学性能验证；
- 删除内部 A/G、G/B 几何面。

这些项目需要独立研究阶段和批准。

## 4. Milestone gates

### M0 — Reproducible legacy snapshot

Exit criteria：

- `00_legacy_baseline.md` 的 Git、参数、测试和环境信息可重新采集；
- 当前 dirty 状态被明确标注；
- 论文不会把 dirty HEAD 当不可变版本。

### M1 — CASE 01 contract probe

只实现足以验证技术路径的窄切片：

- 读取 `S0_planar_agb_exact` STEP；
- 返回 A/G/B 三个 valid regions；
- 返回 A/G、G/B 两个 400 mm² full-face patches；
- A/B 为 disjoint；
- `ΓA/ΓB` 自动构造；
- source-face provenance 100%；
- 两次运行 semantic digest 相同；
- 不依赖 Streamlit/PyVista。

M1 失败时停在 adapter/provenance 设计，不开始 field solver。

### M2 — Relation taxonomy benchmark

- CASE 01–10 active；
- point/edge/face/volume dimension 不混淆；
- near-miss nominal 与 fuzzy transition 可追溯；
- curved、partial、contained、disconnected、多 source cases 有机器断言；
- rejected/ambiguous 是合法结果且有原因。

### M3 — Three-baseline experiment

- Manual、legacy AMF、STEP/B-rep 使用同一 truth；
- matching 规则和 metrics 预注册；
- 原始输出、manifests、主表和错误分析可重建；
- 最终论文 run 来自 clean commit/source archive。

M3 即 Phase I research MVP 完成。之后才允许进入 field implementation 设计审查。

## 5. Phase II 数据兼容门禁（只设计）

Interface Engine 的输出必须允许下游在不重做几何识别的情况下构造：

```text
GradientDomain ΩG
├─ geometry_ref / volume mesh target
├─ ΓA: patch IDs + φ=0
├─ ΓB: patch IDs + φ=1
└─ remaining external boundary faces
```

### Method 1：normalized source-distance field

未来可定义：

```text
dA(x) = distance(x, ΓA)
dB(x) = distance(x, ΓB)
φ(x)  = dA(x) / (dA(x) + dB(x))
```

该公式只是 baseline 定义。必须处理分母接近 0、多 source boundary、domain 外点和 curved surface distance；本阶段不实现。

### Method 2：harmonic/Laplace field

未来在 `ΩG` 上求：

```text
∇²φ = 0
φ = 0 on ΓA
φ = 1 on ΓB
```

`∂ΩG \ (ΓA∪ΓB)` 的边界条件必须在 Phase II 明确选择并做消融，例如 homogeneous Neumann。该选择不是 Interface Engine 的职责。

**[OPEN-QUESTION]** 剩余外壁采用 homogeneous Neumann、mixed condition 或按制造语义分区，当前证据不足以冻结为唯一选择。Phase I 通过 `external_boundary_face_ids` 保留完整边界分区，使 Phase II 可以比较这些条件而无需重定义 interface types。

### Field acceptance（未来）

- `φ` range、source boundary error、partition-of-unity；
- discretization convergence；
- distance 与 harmonic field 的同 fixture 对照；
- volume mesh 的 region/boundary tag 与 patch provenance 对齐。

## 6. Phase III slicing 接口（只设计）

未来调用：

```text
slice_plane(z = zk)
→ GradientDomain cross-section
→ FieldQuery.evaluate(x, y, zk)
→ SliceFieldMap
```

最小输出包含闭合 2D contours、holes、sample coordinates、`φ`/fractions、invalid mask、resolution 和 provenance。平面与 B-rep/validated volume mesh 的交必须形成 topology-aware contours，不能用 screenshot 或 display mesh 像素代替。

`InternalInterfacePolicy.SUPPRESS_INTERNAL_INTERFACE` 的作用阶段：

```text
geometry/topology: KEEP A/G and G/B
field:             KEEP ΓA and ΓB boundary conditions
fabrication view:  MAY suppress internal contour emission
```

它永远不删除 source surfaces 或其 provenance。

## 7. 质量属性

### Determinism

相同 input/config/backend version 重复运行产生相同 semantic digest。并行 Boolean 默认关闭，输出集合排序后序列化。

### Fail closed

Boolean error、invalid solid、缺失 source face、维度证据冲突均返回结构化失败/ambiguity；不得退化成“无接触”。

### Auditability

每个 accepted patch 从 result 可追到 STEP hash、region、source face、operation 和 backend version。

### Isolation

FreeCAD 在子进程运行；PyVista/Streamlit 不在 geometry dependency graph；legacy backend 不 import 新 STEP core。

### Reproducibility

fixture、truth、parameters、code revision、environment 和 raw results 都可打包。最终论文运行不使用未记录的 dirty state。

## 8. MVP 验收清单

- [ ] CASE 01 三 region 身份稳定；
- [ ] 两个 400 mm² patch 数量、area、faces 和 topology 匹配；
- [ ] A/B disjoint；
- [ ] CASE 05 不产生 2D patch；
- [ ] CASE 07 产生两个 disconnected patches；
- [ ] CASE 08/09 nominal/fuzzy 不混写；
- [ ] CASE 10 产生三个 source boundaries；
- [ ] provenance completeness 6/6；
- [ ] 三 baseline 统一评分；
- [ ] primary metrics 可从 raw result 重建；
- [ ] 无 UI/headless 运行路径；
- [ ] legacy protected zone 行为未改变。

该清单描述 future implementation 的 exit criteria；本轮文档创建不勾选任何实现项。

## 9. 当前推荐的下一步

下一轮仍不应直接实现完整 Interface Engine。推荐顺序：

1. 由用户决定如何保存当前 5 个 tracked 修改和关键 untracked dependency；在此之前不要把当前工作树称为冻结 commit。
2. 在隔离 worktree/branch 中只做 **M1 CASE 01 contract probe**，先创建 schema tests 和解析 truth，再建立受控 FreeCADCmd adapter。
3. 只验证 `Import → regions → common/section/generalFuse → two patches → provenance`；不接 UI、不接 Gmsh、不接 field。
4. M1 通过并审核 operation history 能力后，再为 CASE 02–10 写分 case implementation plan。

这一步的关键决策不是 Boolean 能否算出两个矩形，而是 FreeCAD 1.1.1 的 Python 暴露是否足以提供完整、确定的 source-face provenance。若不能，应先设计窄 OCCT bridge，再继续扩展 benchmark。

## 10. “完成”定义

Phase I 只有在 M0–M3 全部满足时才可称为 research MVP。单个截图、一次成功的 `common()`、一个 STEP 文件、UI 中看到两片接触面或测试数量增加，都不构成完成。
