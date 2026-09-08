# 真实数据集与外部证据边界

**访问日期：2026-09-08。**本调查只引用官方数据集仓库、官方机构页面、官方项目页面或原始论文。数量、格式和许可证应在实际取得数据前再次以对应版本的 release manifest 核验；本设计阶段不下载任何数据。

## 1. Evidence map

| 来源 | 官方规模与主要格式 | 能支持的声明 | 不能支持的声明 / 风险 |
|---|---|---|---|
| [Autodesk Fusion 360 Gallery Assembly](https://github.com/AutodeskAILab/Fusion360GalleryDataset/blob/master/docs/assembly.md) | 8,251 assemblies、154,468 parts；SMT native B-rep，另有 STEP 替代格式、OBJ 与 occurrence/assembly graph；原始几何/JSON 长度单位为 cm、角度为 rad。 | assembled state 的 face-pair contact、surface-type 分层、occurrence 图和多体 contact graph 的外部验证。官方定义为 B-rep faces coincident 或在 `0.1 mm` 内。 | 不提供 exact interface patch polygon、area 或 boundary 真值；不能计算真实数据 `surface_area_IoU`、`relative_area_error`、`normalized_95pct_symmetric_boundary_Hausdorff`。SMT face index 不能假定在 STEP import 后保序。 |
| [Autodesk Fusion 360 Gallery Assembly Joint](https://github.com/AutodeskAILab/Fusion360GalleryDataset/blob/master/docs/assembly_joint.md)；[JoinABLe, CVPR 2022](https://openaccess.thecvf.com/content/CVPR2022/html/Willis_JoinABLe_Learning_Bottom-Up_Assembly_of_Parametric_CAD_Joints_CVPR_2022_paper.html) | 19,156 joint sets、32,148 joints、23,029 parts；官方打包约 2.8 GB；每个 joint set 是一对 parts 与一个或多个 joints。 | 官方定义下 assembled pose 的 dataset-defined contact face-pair precision/recall/F1、surface-label bucket 分层与 joint/pose provenance；是 Level D 的主要真实 face-pair 验证集。 | `0.1 mm` face-pair 标签不建立 exact `2D` interface dimension，也没有 exact patch polygon/area/boundary；不能用它算 dimension tuple F1、patch IoU/area/boundary，除非另有 `manual_adjudication`。STEP face ID correspondence 未审计前不构成 STEP face-pair 真值。 |
| [Autodesk 许可证](https://github.com/AutodeskAILab/Fusion360GalleryDataset/blob/master/LICENSE.md) | 项目仓库所附条款。 | 可据原条款规划非商业研究使用、保留 citation/notice。 | 不得假定可再分发完整数据或派生几何；实验发布必须只发布 manifest、脚本说明或许可允许的最小元数据。 |
| [NIST MBE/PMI FTC/STC/CTC](https://www.nist.gov/ctl/smart-connected-systems-division/smart-connected-manufacturing-systems-group/mbe-pmi-0) | 官方 STEP AP242/AP203、PMI、互操作和一致性 case family；本 benchmark 固定抽取 15 个 STEP，而不把页面案例系列误报为单一固定总数。 | STEP import/export、AP242/PMI 保持、互操作和几何有效性压力；FTC 07–10、CTC 02/04 可作为装配关系的人工复核候选。 | 不是已标注的 contact dataset，不可声称 face-pair、patch 或 graph ground truth。 |
| [ABC Dataset 项目页](https://deep-geometry.github.io/abc-dataset/)；[Koch et al., CVPR 2019](https://openaccess.thecvf.com/content_CVPR_2019/papers/Koch_ABC_A_Big_CAD_Model_Dataset_for_Geometric_Deep_Learning_CVPR_2019_paper.pdf) | 约一百万 CAD 模型，含 STEP、Parasolid、STL 和 meta-data。 | 单体 B-rep surface/topology diversity、STEP import 和几何鲁棒性。 | 没有 assembly occurrence、contact face-pair、contact graph 或 patch 真值，不能作为 contact-labeled benchmark。 |
| [Fusion Reconstruction](https://github.com/AutodeskAILab/Fusion360GalleryDataset/blob/master/docs/reconstruction.md)；[Fusion 360 Gallery 原始论文](https://www.research.autodesk.com/publications/fusion-360-gallery/) | 8,625 sequences，约 2.0 GB；单体 sequential sketch/extrude B-rep，SMT/STEP/OBJ 与 construction JSON。 | 单体 STEP 读入、construction-sequence 与几何有效性压力。 | 没有 assembly occurrence 或 contact 标签。 |
| [Fusion Segmentation](https://github.com/AutodeskAILab/Fusion360GalleryDataset/blob/master/docs/segmentation.md)；[BRepNet, CVPR 2021](https://openaccess.thecvf.com/content/CVPR2021/papers/Lambourne_BRepNet_A_Topological_Message_Passing_System_for_Solid_Models_CVPR_2021_paper.pdf) | 35,680 parts，约 3.1 GB；SMT/STEP、OBJ、point cloud、face-operation segmentation 与 timeline 信息。 | 单体 surface/topology diversity、STEP 读入与 feature-label 对应压力。 | face-operation label 不是 contact face-pair 或 patch 真值。 |
| [Fusion Segmentation Extended STEP](https://github.com/AutodeskAILab/Fusion360GalleryDataset/blob/master/docs/segmentation.md) | 42,912 STEP files，约 483 MB；B-rep-only 扩展 STEP 集。 | 单体 STEP interoperability / geometry robustness。 | Extended STEP 包本身只提供 B-rep STEP，**不声称随包提供 feature labels**；尤其不是 contact-labeled benchmark。 |
| [Open CASCADE Boolean / General Fuse 文档](https://github.com/Open-Cascade-SAS/OCCT/wiki/boolean_operations) | 官方 Boolean、General Fuse 与 fuzzy operation 使用资料。 | 近重合、tiny axial shift、narrow face、small planar gap、imprecise edge overlap、tangency、micro-edge 与 tolerance failure 的成熟 test pattern 来源。 | 不是版本化的 contact-labeled dataset；不应报告其为真实 contact 准确率。 |

本基准将 Autodesk 的 `0.1 mm` 仅作为 `τE` 的外部语义锚点；不据此推断官方未公开的距离聚合、face filtering 或 joint 生成规则。

### 1.1 许可证、引用与 face-label 风险登记

| 数据来源 | 许可证/再分发边界 | 建议引用 | face-label / 对应风险 |
|---|---|---|---|
| Autodesk Assembly / Joint / Fusion Extended STEP | [官方许可证](https://github.com/AutodeskAILab/Fusion360GalleryDataset/blob/master/LICENSE.md)：仅非商业研究；不得再分发完整数据；发布部分/修改版须保留来源归属及同等研究用途限制。 | Assembly/Joint 使用 [JoinABLe, CVPR 2022](https://openaccess.thecvf.com/content/CVPR2022/html/Willis_JoinABLe_Learning_Bottom-Up_Assembly_of_Parametric_CAD_Joints_CVPR_2022_paper.html) 与所用官方文档；Extended STEP 使用所对应的 BRepNet citation。 | Assembly/Joint 的 contact index 对应 SMT；Segmentation 的标签是单体 feature label，Extended STEP 为 B-rep-only，二者都不是 contact label。所有 STEP face-pair 使用须经 audit。 |
| NIST FTC/STC/CTC | 官方页面说明 test cases、CAD models 与 STEP files 可不受限制地使用，acknowledgement appreciated；发布时仍记录具体 case 和下载页版本。 | NIST MBE/PMI 页面及具体 FTC/STC/CTC case。 | 没有官方 contact face labels；几何可视的装配配合也只可做 `manual_adjudication` 候选。 |
| ABC | [代码仓库 LICENSE](https://github.com/deep-geometry/abc-dataset/blob/master/LICENSE) 为 MIT，但官方 ABC 项目页指向 [Onshape Terms](https://www.onshape.com/legal/terms-of-use)，且模型创建者保留其模型版权；因此不得把所有模型资产概括为无条件 MIT。使用前核验选定下载资产的来源/条款，并引用原始 CVPR 2019 论文。 | Koch et al., *ABC: A Big CAD Model Dataset for Geometric Deep Learning*, CVPR 2019。 | `feat`/OBJ 索引为单体 patch/mesh feature 对应，非 assembly occurrence 或 contact face-pair；不能映射为 contact truth。 |
| OCCT 文档与测试模式 | 采用 [OCCT 官方仓库许可证](https://github.com/Open-Cascade-SAS/OCCT/blob/master/LICENSE_LGPL_21.txt) 和具体示例/数据的版权说明；不把文档片段再包装为 dataset。 | OCCT Boolean/General Fuse 官方文档及所用版本。 | 没有 benchmark face labels；只可用作 construction pattern 或人工 diagnostic 说明。 |

## 2. Autodesk 标签与格式 correspondence

Autodesk contact label 的 face index 明确相对于其 SMT B-rep 表示。STEP 导入、heal、split/merge 或不同 kernel 的修剪重建都可能改变 face 顺序与 face identity。因此所有 Level D face-pair 指标前必须完成 `SMT/OBJ/STEP correspondence audit`：

1. 对 manifest 中每一个带标签 occurrence 保留原始 SMT face index、surface type、面积、质心和边界/采样签名；
2. 在导入 STEP 后以 occurrence transform、support surface、面积、采样几何和邻接上下文构建一对一/一对多映射；
3. 人工复核歧义映射，并报告 face split、merge、unmapped 与重复 occurrence；
4. 映射覆盖率低于 **95%** 时，不得声称任何 STEP face-pair precision/recall/F1 有效；可只报告读入/几何有效性结果和 `unmapped-face rate`。

SMT 标签可用于 native-format 评价；STEP 仅在该 audit 合格后的映射子集上用来评价 face-pair。任何 audit 后的样本剔除要公开列入 manifest，不能静默提高分数。

## 3. 固定小样本方案

### 3.1 Assembly Joint：240 个 joint sets

从官方 split 与 metadata 中按 joint set 为采样单位抽取 240 个。采样 bucket 仅为抽样平衡工具，**不是** taxonomy 的 `support_surface_family` 标签：每个 dataset face 的原始 `surface_type` 保留，汇总时再按 taxonomy 映射或报告 `other`。为使抽样可复现，一个 joint set 的 bucket 取其所有公开 contact face-pair 中优先级最高的类别（`torus`、`trimmed_bspline_nurbs_freeform/other`、`cone/sphere`、`cylinder`、`plane`），而不是用邻近类替代；target 分别为 `24,24,48,48,96`，总计 240，故 planar 至多 40%。

每个 bucket 内按 `(contact_count: 1, 2, ≥3) × (two-body combined face_count global tertile: low, mid, high)` 建立九个 sampling cell。将该 bucket target 按可用 cell 的样本数以 largest-remainder 比例分配；cell 内按发布的 fixed random seed 对 `joint_set_id` 的 hash 排序取前若干。若任一稀有 bucket 的可用数少于 20，则将其全部纳入、公开实际数；未填足的名额只能重分配给**非-planar**且仍低于其可用数的原始 bucket 的非空 cell，仍使用同一规则，绝不将样本改标为相邻 surface family。完成非-planar 选择后令其数量为 `m`，再以相同 deterministic cell rule 从 plane bucket 下采样，使最终 plane 数 `p≤min(96,floor(2m/3))`；因此 `p/(m+p)≤40%`。若该下采样及非-planar 可用数约束使总数不足 240，则发布实际 `n=m+p<240` 和各 bucket 缺额，而不是超出 40% 上限。

每条评价记录键为 **`(joint_set_id, joint_index)`**，并保留该 joint 的 assembled transforms、该 pose 的 contacts、occurrence ID、格式、原始 face index、sampling bucket、原始 surface label、taxonomy mapping、complexity bin 和 audit 状态。bootstrap cluster 仍是 `joint_set_id`，以处理同一 set 的多个 joint records。Joint 子集只报告 dataset-defined contact face-pair P/R/F1 与 surface-label bucket 分层；不被当成 exact-2D 或 patch-area 数据集。

### 3.2 Assembly：40 个完整 assemblies

从官方 test split 抽 40 个装配，按 `2–5`、`6–15`、`>15` bodies 三档覆盖；同时覆盖 low/mid/high contact-graph degree、重复几何 occurrence 与 cavity/perforation。若 metadata 没有可直接给出的 graph degree，先依据官方 face-pair labels 生成明确的 candidate graph；若标签不足以支持完整图，不对完整图 recall 做泛化声明。

Assembly 子集的主用途是 multi-body contact graph edge precision/recall/F1、occurrence identity 与复杂度分层。每个 assembly 是一个独立统计 cluster；不得把同一 assembly 内的数百 face-pair 当成独立样本。

### 3.3 置信区间与 acquisition

Joint 的 bootstrap 重采样单位为 joint set，Assembly 的单位为 assembly。每项汇总指标报告 1,000 次 cluster bootstrap 的 95% CI；稀有 strata 也显示原始分母，避免仅有宏平均掩盖样本量。后续只取得 manifest 所需几何。若官方打包方式不能随机访问样本，应记录为 `acquisition limitation`，不把“下载并运行全量数据”设为设计或论文完成的前置条件。

## 4. Level D 外部压力样本

除 Autodesk 小样本外，Level D 固定选择 NIST 15 个 STEP、ABC 100 个模型、Fusion Extended STEP 100 个模型，按格式、surface/topology complexity 形成可重复 manifest。Fusion Reconstruction 和 Fusion Segmentation 保留在 evidence map 中作为潜在单体几何来源，但不属于本版 Level D 执行样本或第一篇论文计数。压力样本只报告：`read success rate`、`valid solid retention rate`、`no-crash rate`、runtime、timeout、invalid-result，以及在明确构造/人工裁定子集上可用的 diagnostic notes。

它们不带 contact truth：不得从“成功导入”推断 contact correctness，不得计算 contact F1、patch IoU 或 graph 指标。若从 NIST 装配案例开展人工裁定，须另建 `manual_adjudication` 标签、列出双人复核协议与 `label_confidence`，并与官方真值严格区分。

## 5. 许可、引用与发布边界

论文和 benchmark card 必须引用上述官方仓库/原始论文并保留其许可证要求。可发布的研究附件限于自建 synthetic 定义、不可还原的统计、sample manifest、audit protocol 和许可允许的链接；不镜像 Autodesk 或 ABC 全量资产。每次正式实验要记录数据集 revision/release、访问日期、下载文件校验值和适用许可，避免数量与格式在后续 release 改变后失去可追溯性。
