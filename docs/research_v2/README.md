# DM-Slicer Research v2 设计文档

## 文档状态

**DESIGN FREEZE**：本目录定义 DM-Slicer 从旧 AMF 表面网格原型迁移到 STEP/B-rep 研究链的规范性 Research Contract。它是研究设计，不是 implementation complete，也不表示 STEP Interface Engine、梯度场求解器、切片器或 G-code 已经完成。

### 证据标签

- **CODE-CONFIRMED**：来自当前 DM-Slicer 代码、只读仓库检查、已运行测试或 legacy audit；
- **EXTERNAL-API-CONFIRMED**：来自 OpenCASCADE、FreeCAD 或 Gmsh 官方资料；
- **DESIGN-DECISION**：v2 新合同的规范性决定，不表示已有实现；
- **HYPOTHESIS**：必须由后续实验检验的可证伪科研主张；
- **OPEN-QUESTION**：当前不足以可靠冻结，但已有 fail-closed 边界和后续决策 gate 的问题。

本轮边界：

- 旧 DM-Slicer 保持为只读 legacy baseline；
- 新几何真值来自 STEP/B-rep 与 FreeCAD/OpenCASCADE；
- PyVista 只用于显示，Streamlit 只用于工作流与人工复核；
- 场求解和切片仅定义输入输出接口；
- 本目录不包含生成的 STEP、FCStd、AMF、网格或实验结果。

## 文档关系

```text
00_legacy_baseline.md
  冻结旧方法、版本、参数、环境和已知测试状态
            │
            ▼
01_research_problem.md
  定义研究问题、可证伪假设、真值层级与阶段边界
            │
            ▼
02_domain_model.md
  定义 SolidRegion / GradientDomain / Interface / Provenance / FieldQuery
            │
            ├───────────────┐
            ▼               ▼
03_interface_engine_design.md   04_fixture_and_ground_truth_spec.md
  STEP/B-rep 算法合同            CASE 01 真值与 CASE 01–10 benchmark
            │               │
            └───────┬───────┘
                    ▼
05_experiment_design.md
  三种 baseline、匹配规则、指标、运行协议与报告格式
                    │
            ┌───────┴────────┐
            ▼                ▼
06_old_to_v2_mapping.md   07_mvp_scope.md
  复用/隔离/替换边界        第一阶段准入、退出条件与后续接口
```

建议阅读顺序即编号顺序。实现者必须先读 `01`、`02`、`03`、`04` 和 `07`；实验执行者还必须读 `00` 与 `05`；迁移旧功能时必须读 `06`。

推荐执行顺序固定为：

```text
Legacy Baseline
→ Research Problem
→ Typed Domain Contract
→ Interface Engine
→ Fixtures / Ground Truth
→ Experiment Design
→ Old-to-v2 Mapping
→ MVP Scope
→ future implementation（不属于本轮）
```

## 权威性顺序

出现冲突时采用以下顺序：

1. 经审核的 fixture 声明与解析几何真值；
2. 本目录的领域和接口合同；
3. 实验 manifest 中冻结的运行参数；
4. legacy 代码当前行为；
5. Wiki、截图、人工记忆和历史说明。

人工标注在合成案例上是比较方法，不覆盖解析 ground truth；在没有解析真值的真实模型上，它可以作为经双人复核的 reference annotation。

## 统一术语

- **SolidRegion / region**：一个有稳定来源身份的封闭实体区域；材料语义不改变其 geometry truth。
- **Source Material Region**：`role=SOURCE` 的 material region；旧 `SourceMaterial` 是对象级角色实现，二者都不是 `InterfaceSourceBoundary`。
- **InterfaceSourceBoundary / source boundary**：从已确认二维 patch 选择出来、位于 `∂ΩG` 且带边界值或材料条件的 `Γ`。
- **Gradient semantic role**：region 参与梯度流程的意图；旧 `GradientMaterial` 只是对象角色和邻居集合。
- **GradientDomain**：通过闭合性与 boundary partition 验证的几何域 `ΩG`；它不是 semantic role，也不是已求解的 volumetric field。
- **volumetric material field**：future solver 在 `ΩG` 上产生、可由 `FieldQuery` 查询的 `φ` 或 material fractions。
- **candidate**：值得精确检查的区域或面配对，不等于界面。
- **interface**：两个区域之间经 B-rep 几何运算确认的关系；0D/1D/2D/3D 必须区分。
- **legacy patch**：triangle-pair heuristic evidence 的集合；不能直接作为 v2 geometry truth。
- **AtomicInterfacePatch / atomic patch**：split/fragment 后不可再按当前 operation/topology evidence 拆分的二维 contact face。
- **legacy section**：旧 Gradient–Source surface triangles 的 full/other 分类与边界 loop；不是打印切片。
- **B-rep section**：`BRepAlgoAPI_Section` 产生的 vertex/edge 一维证据；不是二维 overlap patch。
- **slice / SliceFieldMap**：`ΩG` 与制造平面的拓扑截面及其 field samples；不是 legacy section，也不自动等于 toolpath。
- **derived mesh**：从 B-rep 生成的显示或离散网格，永远不是 STEP 主线的几何真值。

## 阶段门禁

```text
Gate 0  Legacy snapshot 可引用且 dirty 状态已说明
Gate 1  CASE 01 的 STEP 导入、关系分类、两片界面和 provenance 全部通过
Gate 2  CASE 01–10 benchmark 通过并完成三种 baseline 对比
Gate 3  FieldQuery 后端接入，先距离场、后 harmonic field
Gate 4  平面截面与 2D material map 接入
Gate 5  toolpath / G-code（不属于当前 MVP）
```

任何阶段都不得用截图替代机器可读断言，也不得把模糊容差得到的 near-miss 悄悄升级为精确接触。

## OPEN-QUESTION register

这些问题不阻止本次 DESIGN FREEZE，因为合同已经规定保留证据、fail closed 或延迟到相应 gate 决策：

1. **[OPEN-QUESTION] FreeCAD face history**：FreeCAD 1.1.1 的 Python binding 能否对 common/section/generalFuse 后的每个 patch 提供完整 source-face history？M1 在 CASE 01/03/07 验证；失败则设计窄 OCCT bridge，不降低 `COMPLETE` 准入标准。
2. **[OPEN-QUESTION] Cross-export identity**：STEP 文件重新导出后，实体 correspondence 无法仅凭 document hash/ordinal 保证。MVP 要求显式 correspondence artifact，无法证明时拒绝自动迁移 annotation。
3. **[OPEN-QUESTION] Phase II outer boundary condition**：`∂ΩG \ (ΓA∪ΓB)` 使用 Neumann、mixed 或制造语义分区需后续消融；Phase I 只完整保存 boundary partition。
4. **[OPEN-QUESTION] Extended taxonomy coverage**：`TOUCH_POINT`、严格 `CONTAINMENT`、明确 interior `CROSSING` 与坏 B-rep `AMBIGUOUS` 已定义但不在首批十例；作为扩展 suite，不修改 CASE 01–10 truth。

## 冻结后的下一阶段

下一 Goal 原则上是 **STEP Interface Engine MVP 实现**，从 M1 CASE 01 capability probe 开始。启动前必须由用户处理或明确封存当前 dirty baseline，并建立隔离实现环境；本次 Goal 不创建 implementation code、fixture geometry、solver 或新 Git branch。
