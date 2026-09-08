# DM-Slicer v2 研究问题

## 证据状态

- **[CODE-CONFIRMED]** 旧 DM-Slicer 的几何权威是 AMF 三角表面与启发式接触证据；当前没有 STEP/B-rep truth、连续体场或可工作的完整 slicer。
- **[DESIGN-DECISION]** v2 的研究主线固定为 CAD topology → confirmed interface → grading source boundary → volumetric field → slice-plane sampling。
- **[HYPOTHESIS]** 本文 H1–H5 是待 CASE 01–10 和后续真实模型实验证伪的假设，不是既有研究结论。

## 1. 研究目标

DM-Slicer v2 的首个研究目标不是工业切片器，而是建立一条可复现、可量化、可连接后续场求解的最小链路：

```text
STEP multi-region model
→ automatic interface detection
→ automatic grading-source construction
→ GradientDomain ΩG
→ volumetric material field
→ slice-plane field sampling
```

第一阶段只实现和评价前三项的几何合同；本轮只设计，不实现。体材料场和切片仅定义下游所需的数据接口。

### 1.1 核心场景与数学对象

**[DESIGN-DECISION]** 第一篇论文把问题限制为三个闭合实体区域：

```text
Material A | Gradient Region G | Material B
```

- `ΩA ⊂ ℝ³`：Material A 的有效 solid region；
- `ΩG ⊂ ℝ³`：闭合 GradientDomain；
- `ΩB ⊂ ℝ³`：Material B 的有效 solid region；
- `ΓA = ∂ΩA ∩ ∂ΩG`：A/G 的已确认二维 interface source boundary；
- `ΓB = ∂ΩB ∩ ∂ΩG`：G/B 的已确认二维 interface source boundary。

MVP 要求 `interior(ΩA)`、`interior(ΩG)`、`interior(ΩB)` 两两不重叠；允许闭包在 `ΓA/ΓB` 接触。`ΓA/ΓB` 必须由二维 confirmed patches 构成；点或曲线相交不能提升为 field source boundary。

### 1.2 科研贡献候选与成熟基础技术

**[EXTERNAL-API-CONFIRMED]** STEP 导入、B-rep Boolean/common/section/split、拓扑遍历、same-domain 归并、有限元体网格以及 Laplace 方程求解都是已有 CAD/数值技术能力。单独调用这些能力不构成 DM-Slicer v2 的科研创新。

**[DESIGN-DECISION]** 第一阶段的贡献候选是一个可检验的系统方法：从 multi-region STEP 的真实实体关系自动恢复具有稳定身份和 operation provenance 的 grading source boundaries，并把 CAD topology → source boundary → future field → slicing 连接成可复现数据链。

**[HYPOTHESIS]** 该连接是否相对 legacy mesh heuristic 提高正确性、分类能力和可审计性，必须由预注册 benchmark 验证；若实验不支持，则论文只能报告负结果或能力边界。

## 2. 核心科学问题

### RQ1：界面检测准确性

与旧 AMF surface-mesh heuristic 相比，STEP/B-rep 方法能否提高二维接触界面的 patch 检出率、关系分类准确率并降低界面面积误差？

### RQ2：复杂关系的可区分性

新方法能否稳定区分：点接触、边接触、同域二维重叠、非共面曲线相交、体积穿插、near-miss 和容差歧义，而不是统一归入“接触”？

### RQ3：来源可追溯性

每个输出 patch 能否回答它来自哪个 STEP 文档、product/solid、原始 face，以及经过哪些 common/section/split/unify 操作？

### RQ4：精度—代价权衡

B-rep 的准确性收益需要多少时间和内存代价？对规则、分片、曲面和扰动案例，代价是否可接受于科研批处理？

### RQ5：下游充分性

Interface Engine 的输出是否足以无歧义构造 `ΓA`、`ΓB`，并通过统一 `FieldQuery` 合同接入距离场或 Laplace 场，而无需回到 UI 猜测 source object？

## 3. 可证伪假设

- **[HYPOTHESIS H1]** 在 CASE 01–10 上，B-rep backend 的 patch-level macro F1 高于 legacy AMF backend。
- **[HYPOTHESIS H2]** 在具有二维接触的案例上，B-rep backend 的界面面积相对误差低于 legacy AMF backend。
- **[HYPOTHESIS H3]** B-rep backend 能把 CASE 05 的非共面 intersection curve 与二维 contact patch 区分；输出二维 patch 数为 0。
- **[HYPOTHESIS H4]** 在预先声明的 fuzzy 容差扫掠中，系统能报告从 `NEAR_MISS` 到接触的状态变化及其触发阈值，不会把结果静默固定成一种分类。
- **[HYPOTHESIS H5]** 所有被接受的 B-rep atomic patch 都具有完整的 region、source-face 和 operation provenance；缺失来源的结果必须被拒绝或标为不完整。

每条假设都可能被 benchmark 推翻。若 CASE 01 都不能满足双界面、面积和 provenance 断言，第一阶段不得进入 field solver。

## 4. 真值与证据层级

### 4.1 合成 fixture

合成案例的 ground truth 来自外部声明的构造参数与解析几何预期，例如长方体的接触平面和解析面积。生成器输出、B-rep backend 输出和人工标注都是被测对象，不能反向改写 truth。

### 4.2 真实 STEP 模型

没有解析解时采用独立 reference annotation：至少两名标注者分别检查原始 STEP/B-rep，再处理分歧；最终记录标注者、工具版本、选择的 source face、修改历史和置信度。单人 Streamlit 点击可以作为 fallback，不自动等于科学 ground truth。

### 4.3 三种论文比较方法

| 方法 | 角色 | 是否是真值 |
|---|---|---|
| Ground Truth / Reference: Manual annotation | 人工 UI 标注；真实数据的 reference/fallback | 合成数据否；真实数据仅在独立复核后作为 reference |
| Baseline 1: Legacy AMF mesh heuristic | 原研究方法；AABB/BVH/normal/gap/projected overlap/pair-patch-component | 否 |
| Proposed Method: STEP/B-rep interface | 新方法；被测主方法 | 否；必须与外部 truth 比较 |

这一区分防止“用新算法输出评价新算法”的循环论证。

## 5. 关键概念分离

1. `GradientMaterial` 是语义角色；`GradientDomain` 是封闭几何域 `ΩG`。一个对象被标为 gradient 不代表它已经是有效计算域。
2. `Material Source Object` 是材料区域；`InterfaceSourceBoundary` 是 `∂ΩG` 上用于施加场条件的二维子域。
3. `InterfaceCandidate` 只说明值得计算；`AtomicInterfacePatch` 表示经过精确运算与验证的二维接触结果。
4. intersection curve 是一维结果；same-domain overlap patch 是二维结果；两者不能使用同一个“interface area > 0”的判据。
5. 内部 source surface 必须在 geometry/topology 中保存；`SUPPRESS_INTERNAL_INTERFACE` 只是一项 fabrication policy。

## 6. 研究阶段

### Phase I：Interface Detection

输入 STEP multi-region model，输出带分类、面积、容差和 provenance 的 atomic patches。评价 CASE 01–10 和三种 baseline。

### Phase II：Volumetric Field

在通过验证的 `GradientDomain ΩG` 上，用 `ΓA/ΓB` 构造 normalized source-distance field 与 harmonic/Laplace field。该阶段不得改变 Phase I 的 interface 身份。

### Phase III：Slice-plane Sampling

计算 `ΩG ∩ {z=zk}`，在截面采样 `φ(x,y,zk)` 或材料 fractions，输出机器可读 2D material map。toolpath 与 G-code 在此阶段之外。

## 7. 成功与停止条件

第一阶段成功必须同时满足：

- CASE 01 的两个解析界面数量、面积、来源 face、方向和邻接图精确匹配；
- CASE 05 不生成伪二维 patch；
- CASE 08/09 明确记录 nominal 与 fuzzy 结果；
- 每个 accepted patch 有完整 provenance；
- 三个 baseline 使用同一 fixture truth 和统一匹配规则；
- 输出包含数值指标，不依赖截图。

以下不属于当前成功定义：修好旧 Slicer、产生 G-code、完成工业容错、验证打印机性能、重写 Streamlit，或证明 harmonic field 优于所有方法。

## 8. 论文主张边界

首篇论文可以主张“面向多区域 CAD 的可追溯界面检测及其相对 mesh heuristic 的实验比较”。在没有体网格收敛、边界条件验证和实体打印实验之前，不应主张“完整梯度切片器”“制造级稳健性”或“材料性能提升”。
