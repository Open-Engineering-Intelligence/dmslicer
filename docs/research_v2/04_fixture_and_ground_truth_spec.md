# STEP Fixture 与 Ground Truth 规格

## 证据状态

- **[DESIGN-DECISION]** CASE 01–10 的参数、关系、容差和拒绝条件是 future fixture generator/validator 的规范性输入；本轮不生成 STEP、FCStd 或 AMF。
- **[HYPOTHESIS]** 这些 cases 能否充分暴露 legacy 与 B-rep 方法差异，需要后续实验验证；truth 本身不由任一被测 backend 输出决定。
- **[OPEN-QUESTION]** `TOUCH_POINT`、严格 `CONTAINMENT`、明确 interior `CROSSING` 和坏 B-rep `AMBIGUOUS` 不塞入核心十例，留作扩展 relation suite。

## 1. 目的和状态

本文件定义第一批解析 benchmark。它没有生成或修改任何 STEP/FCStd/AMF 文件。未来 fixture 工件必须由声明式参数生成，并由独立 validator 回读；算法输出不得反写 truth。

坐标单位统一为 mm，所有 box bounds 都是闭区间。解析面积单位为 mm²。case ID 延续现有多材料样例库设计中的稳定命名原则。

## 2. CASE 01：A | G | B 标准模型

### 2.1 身份

```text
case_id: S0_planar_agb_exact
case_number: CASE_01
intent: exact planar A-G-B baseline
```

### 2.2 几何

三个相邻、互不重叠的封闭长方体：

| Region | role | x bounds | y bounds | z bounds | volume |
|---|---|---|---|---|---:|
| `A` | `SOURCE` | `[-15,-5]` | `[-10,10]` | `[-10,10]` | 4000 mm³ |
| `G` | `GRADIENT` | `[-5,5]` | `[-10,10]` | `[-10,10]` | 4000 mm³ |
| `B` | `SOURCE` | `[5,15]` | `[-10,10]` | `[-10,10]` | 4000 mm³ |

材料元数据：`A.material_key=A`，`G.material_key=Gradient`，`B.material_key=B`。A/B 为 `source_eligible=true`；G 为 `gradient_eligible=true`。三者 `mode=ACTIVE`。

### 2.3 稳定 face locator

Truth 使用语义 locator，不使用 `Face1` 之类导出顺序：

| face ID | region | 几何定义 | outward normal |
|---|---|---|---|
| `A:x_max` | A | `x=-5, y,z∈[-10,10]` | `(+1,0,0)` |
| `G:x_min` | G | `x=-5, y,z∈[-10,10]` | `(-1,0,0)` |
| `G:x_max` | G | `x=5, y,z∈[-10,10]` | `(+1,0,0)` |
| `B:x_min` | B | `x=5, y,z∈[-10,10]` | `(-1,0,0)` |

运行时 source face ID 由 STEP locator/fingerprint 解析到这些语义 face；若不能唯一解析，fixture import 失败，而不是改用面序号。

### 2.4 Ground truth interfaces

| patch | region pair | source faces | relation | plane | area |
|---|---|---|---|---|---:|
| `ΓA.patch0` | A/G | `A:x_max`, `G:x_min` | `FULL_FACE_OVERLAP` | `x=-5` | 400 |
| `ΓB.patch0` | G/B | `G:x_max`, `B:x_min` | `FULL_FACE_OVERLAP` | `x=5` | 400 |

其他 pair：A/B 为 `DISJOINT`，最小欧氏距离 10 mm，不产生 candidate-confirmed interface。

### 2.5 Expected topology

- region adjacency graph：`A — G — B`；A 与 B 无边；
- confirmed interface count：2；
- atomic patch count：2；每个 region pair 1 个 connected component；
- 每个 patch 是一个平面矩形 disk，1 个 outer wire、0 个 inner wire、4 条非退化边、4 个顶点、Euler characteristic 1；
- patch 两侧 source-face outward normals 反向；
- 三个 solids 各自闭合、可定向、正体积；solid common volume 均为 0；
- `ΓA` 相对 G 的 outward normal 为 `(-1,0,0)`，边界值 `φ=0`；
- `ΓB` 相对 G 的 outward normal 为 `(+1,0,0)`，边界值 `φ=1`；
- `∂G \ (ΓA ∪ ΓB)` 是四个外壁面，第一版场模型不在本文件指定其 PDE boundary condition。

### 2.6 Acceptance assertions

在 nominal fuzzy value 0 下：

1. 精确得到 3 个 regions，且 semantic digest 与声明一致；
2. 得到 2 个 confirmed 2D patches；
3. 每片 B-rep area 与 400 的绝对误差不超过 `max(1e-8, 1e-10×400)` mm²；
4. source face sets 精确匹配上表；
5. A/B 不产生 point、edge、face 或 volume relation；
6. provenance completeness 为 100%；
7. 重复运行 semantic digest 相同。

## 3. Truth 文件逻辑结构

未来每个 case 的 `truth.json` 至少具有：

```json
{
  "schema_version": 1,
  "case_id": "S0_planar_agb_exact",
  "units": {"length": "mm", "area": "mm2", "volume": "mm3"},
  "regions": [],
  "relations": [],
  "atomic_patches": [],
  "source_boundaries": [],
  "topology_assertions": {},
  "tolerance_protocol": {},
  "analytic_derivation": {},
  "truth_digest": "sha256:..."
}
```

`truth_digest` 由 canonical JSON 计算，但不能包含自身字段。数值同时保存精确表达式（例如 `20*20`、`2*pi*r*h`）和高精度 decimal expectation，避免从算法输出复制浮点数。

## 4. CASE 01–10 benchmark

### CASE 01 — `S0_planar_agb_exact`

规则平面 A|G|B，定义见第 2 节。Expected：A/G 与 G/B 各一个 `FULL_FACE_OVERLAP`，面积各 400；A/B `DISJOINT`。

### CASE 02 — `S1_unequal_full_face_areas`

目的：两个 source interface 面积不同，但两侧各自都是 full-face contact。

- A 为 x=`[-15,-5]`、截面 `20×20` 的 box；
- G 为 x=`[-5,5]` 的截头四棱柱，左端截面 `20×20`，右端居中截面 `10×10`；
- B 为 x=`[5,15]`、截面 `10×10` 的 box；
- A/G：`FULL_FACE_OVERLAP`，面积 400；
- G/B：`FULL_FACE_OVERLAP`，面积 100；
- expected patch count 2，area ratio 4:1。

该 case 防止实现错误地把所有 source boundary 归一到同一面积。

### CASE 03 — `S2_small_face_contained`

目的：小 source face 完全包含于大 gradient face interior。

- A：x=`[-10,0]`，y,z=`[-5,5]`；
- G：x=`[0,10]`，y,z=`[-10,10]`；
- 接触 patch：x=0，y,z=`[-5,5]`，面积 100；
- A source face coverage=1，G source face coverage=0.25；
- relation=`PARTIAL_FACE_OVERLAP`；patch 1 个、无 holes。

分类规则明确采用双侧 coverage；“一侧 full”不足以标为 `FULL_FACE_OVERLAP`。

### CASE 04 — `S3_partial_same_domain_overlap`

目的：两个 same-domain trimmed faces 部分重叠，且任一 face 都不包含另一个。

- A：x=`[-10,0]`，y=`[-10,5]`，z=`[-5,5]`；
- G：x=`[0,10]`，y=`[-5,10]`，z=`[-5,5]`；
- 两 source faces 各面积 150；
- overlap：x=0，y=`[-5,5]`，z=`[-5,5]`，面积 100；
- 双侧 coverage 均为 2/3；
- relation=`PARTIAL_FACE_OVERLAP`，patch count 1。

### CASE 05 — `S4_nonparallel_curve_intersection`

目的：验证非共面 face 相交只形成 curve/edge，不能生成二维 patch。

构造两个闭合 box：

- A：x=`[-10,0]`，y=`[-10,0]`，z=`[-10,10]`；
- G：x=`[0,10]`，y=`[0,10]`，z=`[-10,10]`。

A 的 `x_max` face 与 G 的 `y_min` face 的 supporting planes 以 90° 相交；两个 solid 仅沿 `x=0,y=0,z∈[-10,10]` 共享长度 20 的边界线，interiors 不重叠，且不存在 coincident surface area。

Expected：

- section 产生一条几何长度 20 的 edge component；
- 最大交集维度为 1；
- relation=`TOUCH_EDGE`；若 future generator 选择横截 interior 的变体，则另立 case 并分类 `CROSSING`；
- atomic 2D patch count=0，interface area=0；
- source boundary count=0。

### CASE 06 — `S5_curved_concentric_contact`

目的：验证解析曲面接触和曲面面积。

- A：半径 `r=10`、高度 `h=20` 的实心圆柱；
- G：同轴 annular solid，半径 `[10,15]`、高度 20；
- B：同轴 annular solid，半径 `[15,20]`、高度 20；
- A/G patch：圆柱侧面，面积 `2π×10×20 = 400π`；
- G/B patch：圆柱侧面，面积 `2π×15×20 = 600π`；
- relation 均为 `FULL_FACE_OVERLAP`；
- expected patch count 2，每片 1 个 connected component，周期 seam 不得被误算成 disconnected patch。

顶/底环面不互相接触；若 exporter 产生 seam edge，truth 仍按一个 cylindrical patch 计数。

### CASE 07 — `S6_disconnected_interface_patches`

目的：同一 region pair 的 source interface 分裂成多个 disconnected patches。

- G：box x=`[0,10]`，y=`[-10,10]`，z=`[-5,5]`；
- A 由两个接触 pad 与背部 bridge 做 exact union，形成一个 connected solid：
  - pad 1：x=`[-5,0]`，y=`[-9,-3]`，z=`[-5,5]`；
  - pad 2：x=`[-5,0]`，y=`[3,9]`，z=`[-5,5]`；
  - bridge：x=`[-10,-5]`，y=`[-9,9]`，z=`[-5,5]`；
- A/G 在 x=0 有两个 `6×10` rectangles；
- expected atomic patch count=2，area 各 60，总面积 120；
- 两片属于同一 region pair 和同一个 semantic source boundary，但 component IDs 不同。

### CASE 08 — `S7_near_miss_gap`

目的：小 gap 不得被 nominal contact 吞掉。

- A：x=`[-10,-0.02]`，y,z=`[-5,5]`；
- G：x=`[0,10]`，y,z=`[-5,5]`；
- exact minimum gap=`0.02`；near-miss band=`0.05`；
- nominal relation=`NEAR_MISS`；confirmed patch count=0；
- diagnostic fuzzy run 可以记录首次形成 face result 的阈值，但不能覆盖 nominal truth。

### CASE 09 — `S8_tolerance_perturbation_sweep`

目的：测量分类对 STEP/Boolean tolerance 的敏感性。

基础为两个 `10×10` 接触面：A max x=0，G min x=`δ`。预注册：

```text
δ ∈ {-1e-2, -1e-4, 0, 1e-4, 1e-2, 5e-2, 1e-1} mm
near_miss_max_gap = 5e-2 mm
```

解析 nominal truth：

- `δ<0`：正厚度穿插，`VOLUME_OVERLAP`；
- `δ=0`：`FULL_FACE_OVERLAP`，面积 100；
- `0<δ≤0.05`：`NEAR_MISS`，无 patch；
- `δ>0.05`：`DISJOINT`。

另对每个正 δ 运行预注册 fuzzy sweep，记录 classification transition curve。Fuzzy 结果不改变 nominal labels。

### CASE 10 — `S9_multi_source_single_gradient`

目的：多个 SourceRegion 同时接触一个 GradientDomain。

- G：box x,y,z=`[-5,5]`；
- A1：x=`[-15,-5]`，y,z=`[-4,4]`，接触 G 的 x-min face；
- A2：x=`[5,15]`，y,z=`[-4,4]`，接触 G 的 x-max face；
- A3：y=`[5,15]`，x,z=`[-4,4]`，接触 G 的 y-max face；
- source materials 分别为 `M1/M2/M3`，均 `source_eligible=true`；
- expected confirmed interface count=3，patch count=3，relation 均为 `PARTIAL_FACE_OVERLAP`，面积各 64；
- expected region graph 为以 G 为中心的三叶 star；A1/A2/A3 两两 `DISJOINT`；
- 自动得到 3 个 `InterfaceSourceBoundary`，但 Phase I 不推断三材料场的插值公式。

采用内缩 `8×8` 接触面是为了让三个 source solids 的闭包也互不接触；若使用整张 `10×10` G face，source solids 会在 G 的棱处发生额外 `TOUCH_EDGE`，与三叶 star truth 冲突。

## 5. 每例完整验收矩阵

本节是 CASE 01–10 的规范性摘要。`dim` 表示最大交集维度；`components` 表示每个列出的 region pair 的二维 patch 连通分量数。除 CASE 08/09 外，nominal fuzzy value 均为 0；所有 source face 名称是语义 locator，不是 STEP 导出序号。

| Case | expected relations / dim | patch count；area/length | expected source faces | components | grading source mapping | tolerance 与拒绝条件 | ground-truth 方法 |
|---|---|---|---:|---:|---|---|---|
| 01 | A/G、G/B=`FULL_FACE_OVERLAP`/2D；A/B=`DISJOINT` | 2；400、400 mm² | `A:x_max↔G:x_min`；`G:x_max↔B:x_min` | 1、1 | `ΓA={AG.p0}, φ=0`；`ΓB={GB.p0}, φ=1` | area 误差≤`max(1e-8,1e-10A)`；拒绝数量/face/方向/graph/provenance 任一不符 | box bounds、平面矩形面积与独立 B-rep 回读 |
| 02 | A/G、G/B=`FULL_FACE_OVERLAP`/2D | 2；400、100 mm² | `A:x_max↔G:left_end`；`G:right_end↔B:x_min` | 1、1 | 左/右 patch 分别映射两个 source boundaries | 同 CASE01；另拒绝面积比不为 4:1 或把两边归一成同面积 | 端面解析多边形面积 + solid/face validator |
| 03 | A/G=`PARTIAL_FACE_OVERLAP`/2D | 1；100 mm²；coverage 1/0.25 | `A:x_max↔G:x_min` 的中心子面 | 1 | 单 boundary，source=A，domain=G | coverage 绝对误差≤1e-10；拒绝 `FULL_FACE_OVERLAP`、额外 fragment 或 source-face mismatch | contained rectangles 的解析 intersection |
| 04 | A/G=`PARTIAL_FACE_OVERLAP`/2D | 1；100 mm²；coverage 2/3、2/3 | `A:x_max↔G:x_min` | 1 | 单 boundary，source=A，domain=G | 拒绝 full/contained 分类、面积或边界 bounds 不符 | 两个错位 rectangles 的解析 intersection |
| 05 | A/G=`TOUCH_EDGE`/1D | 0 个 2D patch；1 edge，20 mm | `A:x_max` 与 `G:y_min` 的 intersection ancestors | 0 | 无 `InterfaceSourceBoundary` | length 误差≤1e-8 mm；拒绝任何正面积 patch、volume overlap 或 `CROSSING` | 两 box 闭包解析交集 `x=0,y=0` |
| 06 | A/G、G/B=`FULL_FACE_OVERLAP`/2D | 2；`400π`、`600π` mm² | 半径 10 的 A outer/G inner cylindrical faces；半径15的 G outer/B inner faces | 1、1 | 两 cylindrical boundaries，φ=0/1 | area 相对误差≤1e-10；拒绝把 periodic seam 拆成额外 component | 解析圆柱侧面积 + 曲面类型/半径/高度回读 |
| 07 | A/G=`PARTIAL_FACE_OVERLAP`/2D | 2；各60 mm²，总120 | `A:pad1_xmax↔G:xmin_subset1`；`A:pad2_xmax↔G:xmin_subset2` | 2 | 两 patch 合成同一个 A→G boundary | 拒绝 component 合并、丢片、bridge 伪接触或总面积不符 | 两个 disjoint rectangles + A union connectivity validator |
| 08 | A/G=`NEAR_MISS`/无交集 | 0；min gap 0.02 mm | proximity evidence 指向 `A:x_max/G:x_min`，但不是 source patch | 0 | 无 boundary | near-miss band 0.05；拒绝 nominal patch、`DISJOINT`、candidate 漏检或 fuzzy 覆盖 nominal | box bounds 的解析最小距离；fuzzy 只作 diagnostic |
| 09 | δ<0=`VOLUME_OVERLAP`/3D；δ=0=`FULL_FACE_OVERLAP`/2D；0<δ≤0.05=`NEAR_MISS`；δ>0.05=`DISJOINT` | δ=0 时1片100 mm²；其余0 | δ=0：`A:x_max↔G:x_min` | δ=0 为1，其余0 | 仅 δ=0 自动建 boundary | δ/fuzzy 使用预注册 sweep；拒绝 nominal labels 被 fuzzy result 改写、负δ被当 patch | 参数 δ 的解析区间、面积、gap/overlap volume |
| 10 | Ai/G=`PARTIAL_FACE_OVERLAP`/2D；Ai/Aj=`DISJOINT` | 3；各64 mm² | `A1:x_max↔G:x_min`；`A2:x_min↔G:x_max`；`A3:y_min↔G:y_max` | 各1 | 三个 source regions→三个独立 boundaries | 拒绝 source-source relation、boundary 合并、数量/面积/材料映射不符 | 三个 inset rectangles 与 pairwise positive separation |

通用拒绝条件：输入 region 非 closed/valid/positive-volume、source locator 不能唯一解析、最大交集维度不符、unexpected volume overlap、patch count/component topology 不符、数值误差超限或 accepted patch provenance 不是 `COMPLETE`。被拒 fixture 进入 `quarantined`，不得通过放宽 truth 临时纳入主实验。

## 6. 关系覆盖矩阵

| relation | 直接覆盖 case |
|---|---|
| `DISJOINT` | CASE 01 的 A/B、CASE 09 δ>0.05 |
| `NEAR_MISS` | CASE 08、CASE 09 小正 δ |
| `TOUCH_EDGE` | CASE 05 |
| `PARTIAL_FACE_OVERLAP` | CASE 03、04 |
| `FULL_FACE_OVERLAP` | CASE 01、02、06、09(δ=0)、10 |
| `VOLUME_OVERLAP` | CASE 09 负 δ |
| disconnected patches | CASE 07 |
| multi-source | CASE 10 |

`TOUCH_POINT`、严格 `CONTAINMENT`、明确 `CROSSING` 和由坏 B-rep 触发的 `AMBIGUOUS` 已在 taxonomy 中定义，但不强行塞入首批十个核心 case。它们是扩展套件的首批候选，不能通过修改 CASE 01–10 的既有 truth 临时加入。

## 7. Fixture 工件合同

未来每个 active case 建议包含：

```text
case.json          声明式构造参数和 policy
truth.json         外部解析真值
model.FCStd        可审计设计树
model.step         Interface Engine 输入
model.amf          legacy baseline 输入（由同一 B-rep 派生）
preview.png        人工检查，不是 pass 证据
validation.json    独立回读和 hash 证据
```

STEP 和 AMF 必须来自同一已验证 FCStd build，保存 generator commit、FreeCAD/OCCT version 和 export parameters。AMF tessellation profile 固定后才允许比较 legacy method；不同 mesh density 属于单独消融实验。

## 8. Ground truth validator

独立 validator 必须检查：

- 文件 hash、单位、region count、solid validity 与体积；
- 语义 face locator 可唯一解析；
- 解析 pair relation、patch count、area 和 topology；
- STEP 回读后 truth 仍成立；
- AMF 仅检查派生一致性，不用 mesh 结果确认 B-rep truth；
- 两次独立构建的 semantic digest 相同；二进制文件 hash 可以因 exporter metadata 不同而不同。

任何 validation failure 都使 case 保持 `pending_build` 或进入 `quarantined`，不得进入论文主结果。
