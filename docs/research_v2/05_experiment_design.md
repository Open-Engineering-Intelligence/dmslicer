# Interface Detection Benchmark 实验设计

## 证据状态

- **[CODE-CONFIRMED]** legacy baseline 的 AABB/BVH/normal/gap/projected-overlap/pair-patch-component 链与现有 Streamlit/PyVista 人工工作流来自当前旧代码。
- **[DESIGN-DECISION]** 本文冻结 prediction unit、matching、primary/secondary metrics、运行协议和 fail-closed 计分方式。
- **[HYPOTHESIS]** Proposed STEP/B-rep method 是否优于 legacy baseline 由本文实验检验，不预设胜出。

## 1. 实验目标

定量比较三种 interface detection 方法在相同 multi-region fixtures 上的准确性、关系判别、几何误差、拒绝行为和计算代价。截图只用于错误分析，不参与评分。

## 2. 比较方法

### Ground Truth / Reference — Manual annotation

使用现有 Streamlit/PyVista 工作流显示 region 与候选关系，由人工选择 source regions/faces/patch。输出必须转换成统一 `InterfaceResult` DTO，并记录：标注者、开始/结束时间、工具版本、输入 hash、选择/撤销历史和置信度。

合成 fixtures 上解析 truth 仍是最高权威，manual annotation 是被测人工方法、debug/review 工具与 fallback；真实模型没有解析解时，只有双人独立标注加 adjudication 才可作为 reference annotation。人工结果不能覆盖 fixture truth，也不能静默改写自动结果。

### Baseline 1 — Legacy AMF mesh heuristic

固定链路：AABB → BVH → unsigned normal angle → approximate gap → projected overlap → pair/patch/component。输入 AMF 必须由与 STEP 相同的 B-rep fixture 派生，并固定 tessellation profile。

结果适配规则：

- legacy triangle patches 归并成 region-pair connected components；
- projected triangle area 作为 predicted area；
- 无法分类的 edge/point/volume 关系输出 `AMBIGUOUS`，不得从截图补标签；
- 保存 legacy 参数、AMF hash、triangle count 和 conversion diagnostics。

### Proposed Method — STEP/B-rep Interface Engine

按 `03_interface_engine_design.md` 运行 nominal pass；fuzzy sweep 是单独的鲁棒性实验，不与 nominal accuracy 混算。只有 provenance complete 的 2D patch 进入 accepted predictions。

## 3. 数据集分层

### Core deterministic set

CASE 01–10，每个 case 至少一个 canonical STEP/AMF bundle。用于方法正确性、关系覆盖和最小论文表格。

### Tessellation ablation

对能导出 AMF 的二维接触 cases 使用至少三档固定网格：coarse/medium/fine。STEP 输入保持不变，用于测量 legacy 面积误差和检出率随 mesh density 的变化。主结果使用预注册 `medium` profile，其余为消融。

### Tolerance perturbation set

CASE 09 的 δ sweep 与固定 fuzzy sweep。用于状态转换和容差敏感性曲线。

### Real-model extension

后续加入真实 STEP 模型时单独报告，不与十个解析案例混合成一个“总体准确率”。真实集需要 reference annotation 和不可解析真值限制说明。

## 4. 统一 prediction unit

评分单位是 **atomic interface patch**，不是 triangle pair、source object 或截图中的颜色块。每个 prediction 至少包含：

```text
region pair
relation type
patch geometry or boundary representation
area
source faces (if available)
provenance status
confidence/abstention state
```

0D/1D/3D 关系以 relation record 评分，不伪造 2D patch。

## 5. Prediction-to-truth matching

### 5.1 候选边

prediction 与 truth 只有满足以下条件才可匹配：

1. 规范化 region pair 相同；
2. relation 的拓扑维度相同；
3. 对 2D patch，boundary/area spatial overlap 达到预注册门槛；
4. 一对一匹配，不允许一个 prediction 重复解释多个 truth patches。

### 5.2 Assignment

对同一 region pair 建立 cost matrix：

```text
cost = 0.6 × normalized symmetric boundary distance
     + 0.3 × relative area error capped at 1
     + 0.1 × source-face mismatch indicator
```

使用最小代价一对一 assignment。超过 acceptance cost `0.25` 的配对拒绝。该阈值必须在执行主实验前冻结；敏感性分析可以另报 0.15/0.35。

对于解析平面 case，可直接使用 polygon intersection-over-union 辅助 matching；对于曲面 case，距离在 3D 中计算，不先投影到任意平面。

### 5.3 TP/FP/FN

- accepted matched prediction：TP；
- 未匹配 prediction：FP；
- 未匹配 truth patch：FN；
- `AMBIGUOUS`/abstain 不算 FP，但对应 truth 未检出时仍算 FN，并另计 abstention；
- 只输出 curve 而 truth 是 face，relation classification 错且 face 为 FN；curve 作为错误 relation prediction。

## 6. Primary metrics

第一篇论文真正必要的 primary metrics 保持精简：

### 6.1 Patch detection macro F1

先按 case 计算 precision/recall/F1，再对 cases 做 macro average，避免 patch 多的 case 支配结果。同时报告 micro counts 作为透明度信息。

```text
precision = TP / (TP + FP)
recall    = TP / (TP + FN)
F1        = 2PR / (P + R)
```

分母为 0 时不武断设为 1：按预注册规则记 `not_applicable`，并报告负样本 false positives。

### 6.2 Contact-type macro accuracy / macro F1

在所有 declared region pairs 上评价 taxonomy。类别不均衡时 macro F1 是主值，overall accuracy 同时报出。特别单列 1D section 与 2D same-domain 的混淆矩阵。

### 6.3 Interface area error

只对 matched 2D patches：

```text
absolute error = |A_pred - A_truth| mm²
relative error = |A_pred - A_truth| / A_truth
```

主报告使用每 case 总 interface area 的 median relative error，并同时给 patch-level absolute error。零面积关系不计算 relative area error。

### 6.4 Runtime

报告冷启动 end-to-end runtime 和 warm operation runtime 的 median/IQR。准确性提升必须同时说明计算代价，因此 runtime 是主 trade-off metric，但不是几何正确性的替代指标。

## 7. Secondary metrics

| 指标 | 用途 | 为什么不是首要 headline |
|---|---|---|
| boundary Hausdorff distance | 衡量整个边界最坏双向距离 | 对离散 legacy mesh 很敏感，需明确采样/解析算法 |
| maximum boundary deviation | 定位局部最坏误差 | 易受单个 sliver/outlier 支配 |
| false-positive interface count | 解释 precision | 已包含于 F1，但保留原始计数 |
| false-negative interface count | 解释 recall | 已包含于 F1，但保留原始计数 |
| ambiguous/rejected rate | 评价 fail-closed 行为 | 高 abstention 可能换取高 precision，需与 coverage 联读 |
| memory peak | 可扩展性 | 十个小 fixture 上差异可能不稳定 |
| provenance completeness | 科研可审计性 | 是准入门槛与质量指标，不应与几何 accuracy 混成单一分数 |
| tolerance sensitivity | 鲁棒性 | 作为 CASE 09 独立曲线，避免稀释主 nominal 指标 |
| manual correction count/time | 实用负担 | 只对 manual/override workflow 有意义 |

Boundary Hausdorff 使用 patch boundary 的 3D symmetric Hausdorff；对解析 line/arc 尽量使用 curve distance，若离散采样必须记录 chord tolerance 和 sample density。最大 boundary deviation 与 Hausdorff 在同一算法上计算。

## 8. Provenance score

不使用含糊的“有/无 metadata”。对每个 accepted patch 检查六个字段：

1. source document；
2. region A/B；
3. source faces A/B；
4. operation kind/parameters；
5. backend/version；
6. output shape digest。

```text
provenance completeness = present required fields / 6
```

B-rep 主方法进入 accuracy 主表的 patch 必须为 6/6。Legacy 和 manual 可以低于 6/6，但必须原样报告，不能用空间推断填满。

## 9. Tolerance sensitivity protocol

对 CASE 08/09：

- nominal run 固定 fuzzy=0；
- fuzzy values 固定为 `[1e-6,1e-5,1e-4,1e-3,1e-2,5e-2]` mm；
- 记录首次改变 relation 的 threshold、patch area、fragment count 和 provenance；
- 报告 classification stability interval；
- 将结果画成 `δ × fuzzy → relation` 网格，不选择最好看的单个参数。

Legacy backend 的 gap factors 也必须作为独立预注册 sweep；不能把 B-rep 的 mm tolerance 与 legacy 的局部尺度 factor 直接写成同一数值。

## 10. Runtime 与 memory protocol

1. 保存 CPU、RAM、OS、Python、FreeCAD/OCCT 和 backend versions；
2. 每个 case/backend 先做 1 次 warm-up，再做 10 次计时；
3. cold import 与 warm geometry operation 分别报告；
4. legacy cache 默认关闭用于 cold fairness，另报 cache-on 结果；
5. B-rep parallel 默认关闭；若启用作为单独 ablation；
6. 记录 median、IQR、min/max，不对十个 deterministic cases 强行做正态假设；
7. memory 使用同一采样方法并说明它是 process RSS peak 还是 Python allocation。

## 11. Manual baseline protocol

- 随机化 case 显示顺序；隐藏 truth 面积和关系标签；
- 每个 annotator 先完成同一训练 case，训练 case 不进入评估；
- 至少两名 annotator；保存各自结果，不只保存 adjudicated 结果；
- 报告 inter-annotator agreement、每 case 时间和 correction count；
- PyVista mesh 只用于观察，人工可以查询 B-rep face metadata，但不能看到新 backend prediction；
- UI 无法表达 point/edge/curve relation 时必须记录 `tool_not_expressible`，不能视为错误点击。

## 12. Legacy AMF fairness

- STEP 与 AMF 来自同一 canonical FCStd/B-rep build；
- 固定 AMF tessellation linear/angular deflection、relative flag 和单位；
- 保存 triangles per region 和文件 hash；
- object/material mapping 通过 case manifest，不依赖进程级 `MeshData.count`；
- 使用 `00_legacy_baseline.md` 的代码身份和参数；
- legacy 无法表示的 relation 类型仍进入混淆矩阵，不从数据集删除。

## 13. 实验 manifest

每个 run 必须保存：

```json
{
  "run_id": "...",
  "case_id": "...",
  "backend": "manual_annotation|legacy_surface_contact|step_brep_interface",
  "code": {"repository": "...", "head": "...", "dirty": true, "diff_sha256": "..."},
  "inputs": {"step_sha256": "...", "amf_sha256": "...", "truth_sha256": "..."},
  "environment": {"python": "...", "freecad": "...", "occt": "..."},
  "config": {},
  "stage_timings_ms": {},
  "memory": {},
  "result_artifact": "...",
  "diagnostics_artifact": "..."
}
```

Dirty run 可以用于开发，不进入最终论文主表。最终论文 run 必须来自明确 commit 或可验证 source archive。

## 14. Failure-case analysis 与 ablation

### 14.1 Failure taxonomy

每个非完全正确结果必须恰好进入一个主要失败类别，并可附次要标签：

| 类别 | 判定 | 必存证据 |
|---|---|---|
| candidate miss | truth pair 未进入 exact stage | bounds、candidate tolerance、filter reason |
| dimension confusion | 0D/1D/2D/3D 最大维度分类错误 | common/section/same-domain evidence |
| fragmentation error | patch 被错误合并、拆分或产生 sliver | component graph、areas、wires |
| geometry deviation | 匹配成功但 area/boundary 超限 | area error、Hausdorff/max deviation |
| provenance failure | geometry plausible 但 source face/history 不完整 | completeness fields、operation report |
| tolerance instability | nominal 或相邻 fuzzy 值产生未解释跳变 | complete sweep、native tolerances |
| backend failure | import/validation/Boolean/serialization 失败 | stable error code、stdout/stderr、versions |
| semantic activation error | confirmed patch 到 `Γ` 的 role/policy 映射错误 | patch IDs、policy、override audit |

报告必须同时保留 raw prediction；不能只保存人工解释后的错误类别。对每个 backend 至少展示一个最具代表性的失败，若某类未发生则明确为 0，而不是省略。

### 14.2 预注册 ablation

1. **Legacy tessellation**：coarse/medium/fine，STEP truth 不变；检验 mesh density 对 F1、area 和 runtime 的影响。
2. **Legacy contact stages**：AABB only；AABB+BVH；再加 angle/gap；再加 projected overlap；再加 patch/component promotion。每级都输出独立 prediction，避免把多个启发式贡献混在一起。
3. **B-rep relation evidence**：common+section；再加 same-domain；再加 split/general-fuse；再加 complete history gate。任何简化版本仍须 fail closed。
4. **Tolerance**：nominal 与预注册 fuzzy sweep 分开；比较 classification stability、fragment count 和 provenance，不以最佳 fuzzy 值替代 nominal 主结果。
5. **Matching sensitivity**：主 acceptance cost 0.25，仅补充报告 0.15/0.35；不得据此选择对 proposed method 最有利的阈值。

**[HYPOTHESIS]** same-domain + split/history 可能提高二维 overlap 分类和 provenance，但增加 runtime；legacy mesh refinement 可能降低面积误差，却不能恢复 AMF 中已丢失的 STEP source-face truth。两点均须由消融数据验证。

## 15. 报告表

### 主表

| backend | patch macro P | patch macro R | patch macro F1 | type macro F1 | median area rel. error | cold runtime median |
|---|---:|---:|---:|---:|---:|---:|

### 错误分析表

按 case 列出 truth/predicted relation、TP/FP/FN、area error、abstain、provenance completeness、warning/error code。

### 鲁棒性图

- CASE 09 relation transition heatmap；
- legacy tessellation density vs F1/area error；
- accuracy vs runtime scatter。

截图只放在 failure taxonomy 示例中，并链接机器结果 ID。

## 16. 统计和结论规则

- Core set 是诊断套件，重点报告 per-case 完整结果，不用小样本 p-value 包装确定性差异；
- runtime 重复用于描述系统噪声，不把 10 次同一 case 当 10 个独立几何样本；
- 后续扩大到参数化随机 case family 后，再预注册统计模型和置信区间；
- 若某 backend abstain，必须同时报告 coverage；不能只在它选择回答的子集上报告 precision；
- 不把 provenance score 与 accuracy 加权成一个不可解释总分。

## 17. 最小论文证据包

1. CASE 01–10 声明、truth、STEP、AMF 和 validation hashes；
2. 三 backend 的原始 machine-readable outputs；
3. frozen code/environment/config manifests；
4. matching 与 metric 脚本版本；
5. 主表、混淆矩阵、area error、runtime 和 tolerance plot；
6. 所有 rejected/ambiguous case 的错误码；
7. 不超过必要数量的解释性截图。
