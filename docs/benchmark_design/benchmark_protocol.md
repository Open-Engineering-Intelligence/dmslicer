# DM-Slicer Contact Benchmark Protocol

## 1. 基准目标与实验单元

基准评估的是从 CAD/STEP B-rep 恢复的正交 relation tuple、二维 interface 及多实体 contact graph 是否具有工程意义。所有术语、enum 和注释记录以 [contact_problem_taxonomy.md](contact_problem_taxonomy.md) 为准；Level A 构造以 [canonical_case_matrix.md](canonical_case_matrix.md) 为准；扰动以 [tolerance_protocol.md](tolerance_protocol.md) 为准；外部数据证据界限以 [real_dataset_survey.md](real_dataset_survey.md) 为准。

基本统计单元不是单个 face，而是 canonical case、Level B 扰动实例、Level C assembly 或 Level D 的 joint set/assembly。Joint 内的评价记录键为 `(joint_set_id, joint_index)`，但 bootstrap cluster 为 `joint_set_id`。face-pair 是二维 interface 的评估单元，patch 是 synthetic 2D 真值的评估单元。重复几何的不同 occurrence 永远视为不同图节点。`L` 始终是当前 body-pair 合并包围盒对角线。

## 2. 四层 benchmark

| Level | 固定范围 | 主要问题 | 可评价输出 |
|---|---|---|---|
| A | 13 个两体 canonical diagnostic cases A01–A13 | 单一语义、维数、surface family 或 patch-topology 失败 | relation tuple、2D area/boundary/topology、0D/1D/3D 分类 |
| B | A 周围受控 tolerance/pose/scale/degeneracy sweep | engineering classification 稳定区与临界偏差 | stable-band accuracy、transition-threshold error、first-error location |
| C | 5 个受控多体/复杂拓扑场景，另加 K4 `0D` graph stress | occurrence identity、图恢复、多个 patch 和腔/穿孔 | graph edge P/R/F1、tuple、patch topology |
| D | Autodesk Joint 240 + Assembly 40；NIST 15、ABC 100、Fusion Extended STEP 100 压力样本 | dataset-defined external face-pair/graph validity 与互操作鲁棒性 | Autodesk dataset-defined face-pair/graph 指标，或仅导入/有效性指标 |

### 2.1 Level A：synthetic correctness

逐例运行 A01–A13，不把 13 个不同诊断对象合并成一个二值测试集。每例输出完整 relation tuple、支持曲面、所预测/真值 face-pair、patch component/hole count；有二维 synthetic 真值时再输出面积和 boundary。A01 的 independent-B-rep 与 cellular/compsolid representation control 是同一几何的表达对照，不能增加样本数或提高分数。

### 2.2 Level B：engineering robustness

按 tolerance protocol 对指定 Level A case 做单因素 sweep 和有限的 near-boundary pairwise 组合。以 `τE=0.1 mm` 为主锚点，同时报告 `τE/L`；`τK` 只记录。固定绝对 `τE` 与 co-scaled `τE` 的结果独立呈现。远离阈值的稳定区准确率，不能混入 `|δ|≈τE` 的边界结果。

### 2.3 Level C：受控复合场景

五个场景均由易复核的 Level A primitives 组成，并保留 occurrence-level manifest：

| ID | 构造与目标 | 覆盖的合法关系 |
|---|---|---|
| C01 | 同一几何的多个独立 occurrence 贴合一个底座，形成 one-to-many | occurrence identity、重复 instance、多个独立 `2D` graph edges；几何相同不意味着节点可合并。 |
| C02 | 三到五个实体串联，邻接实体之间为 A01/A07 型界面 | chain、局部 edge 漏检对图连通性的影响；不引入非相邻的伪 contact。 |
| C03 | 中央底座与三至六个辐射部件配合 | branch/star、degree 分层、不同 supporting surface family。 |
| C04 | 同一 body-pair 同时具有 A11 双分离 patch 与 A12 annular patch 的受控组合 | `component_count`、holes、multiple interface face-pairs；所有 patch 仍显式列出。 |
| C05 | 多孔/穿孔板、腔体和 bridge 的受控装配 | perforated/porous-like solid topology、cavity-rich negative clearance、遮蔽的小 patch；包括 `solid_inside_clear` 与 cavity-wall contact 的分离。 |

另设一个合法的 dense-graph stress：四个等半径球以四面体顶点位置布置，使四个球**两两外切**，得到 K4 的六条 `0D` touch edges。它不计作第六个复杂场景，也不伪称存在 `2D` interface。Level C 的几何应避免相互 material interference，除非该场景明示用 A06 作为 `3D` 负/干涉类别。

### 2.4 Level D：external validity 与压力测试

Autodesk Assembly Joint 的 240 joint sets 是真实**dataset-defined** contact face-pair 主验证集；完整 Assembly 的 40 个小样本是 contact graph 辅助验证集。它们的 `0.1 mm` labels 不构成 exact `2D` dimension 或完整 relation tuple ground truth。采样、许可、surface quota、cluster bootstrap、每个 `(joint_set_id,joint_index)` 的 assembled transform/contact pose 保存，以及 SMT/OBJ/STEP correspondence audit 必须遵守 [real_dataset_survey.md](real_dataset_survey.md)。face mapping 覆盖率低于 95% 时，禁止声称 STEP face-pair 指标有效。

NIST 15、ABC 100、Fusion Extended STEP 100 仅作 STEP/geometry stress。Fusion Reconstruction 和 Fusion Segmentation 只保留为 evidence-map 中的候选单体几何来源，不纳入本版执行或第一篇论文样本计数。压力样本不拥有 contact ground truth，因此只报告读入、有效性和无崩溃等指标；不得借由它们扩展 relation、patch 或 graph 性能结论。

## 3. 真值和评价前置条件

synthetic cases 的 relation、面积、boundary 和 topology 使用 `analytic` 或 `construction_derived` 真值。A10 的参数域真值与参考积分误差必须随版本冻结。外部 Autodesk 标签是 `dataset_face_pair`，不转写为 patch polygon/area。若某样本被人工确认，其 `manual_adjudication` provenance、复核流程与 `label_confidence` 必须单独公开。

任何算法输出先归一为 taxonomy tuple，再按下列规则评价：

1. **face-pair 集合不按预测维数 gate。**对每个 eligible occurrence-pair，`U` 是所有已映射的跨-body B-rep face-pair（synthetic 使用完整已知宇集，Autodesk 使用 audit 后可比较的 face-pair 宇集）；在 `U` 上比较 truth set 与 prediction set。真值 `2D` pair 被预测为 `0D/1D/none` 时其 interface pair 缺失，记为 FN；无真值 interface 的 pair 被预测成 `2D` interface 时，记为 FP。unmapped faces 从 `U` 排除但必须报告比例。
2. patch geometry 指标只在 synthetic `2D` truth 与同一 face-pair 的预测 patch 成功匹配后计算；matching 采用一对一最大匹配。未匹配真值 patch 保持为 patch-recall failure，未匹配预测 patch 保持为 patch-precision failure，不能因 geometry gate 从失败中消失。
3. Autodesk `dataset_face_pair` 可用于该数据集定义下的 face-pair 指标；没有 `manual_adjudication` 时，不能用于 exact dimension、relation tuple、patch area/boundary/topology 指标。
4. 只有参考图完整或其 coverage 明示时评价 graph edge recall；只有 occurrence mapping 已验证时评价相应外部 face-pair。
5. 无法映射、超时、invalid result 不可静默丢弃，须作为单独结果和分母说明。

## 4. Primary metrics

| Metric | 定义与适用范围 |
|---|---|
| `relation_tuple_macro_F1` | 仅在有 analytic/construction-derived 或 `manual_adjudication` tuple 真值的 synthetic Level A/B/C 上，对 `(exact_intersection_dimension, engineering_state, intended_relation_dimension, containment_state, topological_relation)` 做分层宏 F1；显式包含 `0D`、`1D`、`2D`、`3D` 与 containment，不能退化为 `CONTACT`。同时给出每个字段的 F1。 |
| `interface_face_pair_precision/recall/F1` | 在全部 eligible `U` 上比较 truth/predicted 2D-interface face-pair 集合的 micro 和 macro P/R/F1；维数误分类按 FP/FN 计入。synthetic 与 audited Autodesk dataset-defined labels 分开报告。 |
| `surface_area_IoU` | synthetic `2D` patch 的交并面积比；multi-patch 先一对一最大匹配，再报告 matched-patch IoU，并以未匹配真值/预测 patch 的 P/R 保留失败。 |
| `relative_area_error` | `|A_pred-A_gt| / max(A_gt, ε_A)`；只对有正面积的 synthetic 2D patch，用声明的数值 `ε_A` 防止除零。 |
| `transition_threshold_error` | Level B 中 analytic/construction-derived 精确理论临界值 `t*` 与预测 transition bracket 的 midpoint estimate 的归一化偏差；同时报告 bracket 与 discretization half-width。若预测在范围内无 transition，报告 `no_transition_within_range`，见 tolerance protocol。 |
| `stable_band_accuracy` | 远离边界的 Level B tuple 准确率；near-threshold strata 分开。 |
| `contact_graph_edge_precision/recall/F1` | occurrence-level 无向 graph edge 集合的 P/R/F1；C 和具备完整标签覆盖的 Autodesk Assembly 使用。 |
| `read_success_rate`、`valid_solid_retention_rate`、`no_crash_rate` | 外部 STEP stress 的读入、有效 solid 保持、无异常终止比例；无 contact truth 也可使用。 |

`relation_tuple_macro_F1` 的宏平均按声明 strata 计算，且 Level A、B、C、D 不混合。每个宏平均都同时给每类分母，避免 class imbalance 或稀有维度消失。

## 5. Secondary metrics 与分层报告

- `intersection_dimension_confusion_matrix`：`none/0D/1D/2D/3D` 完整混淆矩阵。
- `patch_component_hole_exact_match`：synthetic 2D 中 component count、boundary component count 与 `first_betti_number/hole_count` 同时正确的比例，并分别报告；B-rep/parameter seam 不得造成拓扑差异。
- `normalized_95pct_symmetric_boundary_Hausdorff`：二维 synthetic boundary 的双向 95th percentile Hausdorff distance，除以 `L`；boundary 不存在时 `not_applicable`。
- `surface_family_stratified_accuracy`、`scale_stratified_accuracy`、`complexity_stratified_accuracy`：按 taxonomy family、`0.01×/1×/100×` 和 face-count/graph-degree bin 列示。
- `runtime`、`timeout_rate`、`invalid_result_rate`、`unmapped_face_rate`：按 case 和数据源列示分布（median、p95），而非只报均值。

外部 Joint 指标的 95% CI 使用 1,000 次以 `joint_set_id` 为 cluster 的 bootstrap（即使评价记录为 `(joint_set_id,joint_index)`）；Assembly 以 assembly 为 cluster。synthetic 结果可报告确定性值；如引入随机采样，固定 seed 并给重复次数。

## 6. 结果表与失败分析最低要求

论文应至少提供：(i) Level A 13 行 case matrix；(ii) Level B transition plots/表格，标出 `±τE`；(iii) Level C occurrence graph error；(iv) Autodesk 的 audited subset、coverage、CI；(v) 外部 STEP stress 的格式/有效性结果。每个失败样本保存 provenance、input format、`τE/τK`、变换、原始/映射 face ID、输出 tuple 与失败类别。应展示代表性的 false 0D/1D/2D/3D、containment 混淆、patch merge/split 和 mapping failure，而不是只筛选成功例。

## 7. 第一篇论文范围

第一篇论文完成以下可验证交付：冻结本 taxonomy；发布 13 个 Level A 定义、Level B boundary sweep、5 个 Level C 场景与 K4 stress；对 synthetic cases 提供 relation、area、boundary、topology 的 analytic/construction-derived 真值；完成 Autodesk Joint/Assembly 小样本和 correspondence audit；以 NIST/ABC/Fusion STEP 展示互操作/几何鲁棒性；披露数据局限、失败案例和置信区间。

它不要求提出新的 contact algorithm，也不因外部数据缺少真值而声称 patch accuracy。任何方法的算法细节应作为独立工作，不是本 benchmark design 的交付。

## 8. 后续论文范围与实施顺序

后续扩展可纳入 torus 与更多混合 analytic/freeform interfaces、大型 porous/lattice、数百 patch、non-manifold 输入、真实 patch polygon/area 人工标注、全量 Autodesk/ABC 运行、学习式方法和跨 CAD-kernel 排名。这些不应倒灌改变首版的样本量或语义。仍明确排除 gradient、field、source boundary、slicing、任何新的 contact algorithm，以及对现有 Interface Engine 或 DESIGN FREEZE 的修改。

下一实现阶段按诊断依赖顺序执行：**A01–A03 平面面积语义 → A04–A06 维数分类 → A07–A09 曲面配合 → A11–A12 patch topology → A10 freeform → A13 containment negative control**。每步先验证其对应 relation tuple，后再进入下一组；完成研究设计后在此停止。
