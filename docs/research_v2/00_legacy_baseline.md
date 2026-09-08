# Legacy AMF Baseline 快照

## 证据状态

- **[CODE-CONFIRMED]** 本文中的仓库状态、测试结果、旧 AMF 数据流和模块职责来自 2026-09-08 的只读 Git/代码/运行检查。
- **[DESIGN-DECISION]** 旧算法在 v2 与论文中固定命名为 **Legacy Surface-Mesh Interface Heuristic Baseline**，只作为 legacy backend、对照方法、人工复核辅助和调试证据，不承担 STEP/B-rep geometry truth。
- **[CODE-CONFIRMED]** 当前旧主线没有可工作的完整 slicer、连续体材料场或 STEP/B-rep interface engine。

## 1. 快照身份

记录日期：2026-09-08，时区 Asia/Shanghai。

| 项目 | 值 |
|---|---|
| 仓库 | `D:/Agent/raw/gradient-slicing/legacy-code/Slicer/DMSlicer-AI-mod` |
| branch | `master` |
| HEAD | `1207c97f88df047b29218c324084a1c8e542f386` |
| commit time | `2026-08-11 13:57:47 +0800` |
| subject | `docs: plan interface adjacency viewer` |
| origin | `https://github.com/neomakers/DMSlicer-Core.git` |

该工作树在记录时为 dirty。HEAD 只能定位已提交内容，不能单独重现当前运行状态。当前 tracked diff 的 SHA-256 是 `d43a7e350805731617b88cabfc6c5d3377e41eeb24973ec27bac50c03640ef34`，字节数为 `19522`；这个摘要不覆盖 untracked 文件。未来论文若使用当前 dirty 行为，必须另行保存并审核精确 diff/工件，不能只写 `1207c97`。

本文件是在不执行 commit、stash、reset、checkout、删除或覆盖的前提下记录的快照。

## 2. 已修改 tracked 文件

```text
 M gradient_source_conformal_remesh/src/model_material_node/assignment_store.py
 M gradient_source_conformal_remesh/src/model_material_node/data_model.py
 M gradient_source_conformal_remesh/tests/test_amf_parser.py
 M src/dmslicer/geometry_kernel/regiontriangle/topology_repair.py
 M test/test_20260123_geom_kernel.py
```

差异规模为 5 个文件、389 行增加、11 行删除。检查时 Git 同时报告这些 working-copy 文件下次被 Git 处理时可能发生 LF→CRLF 转换；因此复现实验不应依赖未经保存的工作树换行状态。

## 3. 已存在的 untracked 内容

普通 `git status --short` 折叠后的完整顶层清单如下。目录内部文件可用 `git status --porcelain=v1 -uall` 展开；它们均为本轮开始前已存在的用户内容。

```text
?? .codex_tmp_verify_marching_lessons.js
?? .superpowers/
?? AI/
?? DMSlicer_Gem_Knowledge.zip
?? DMSlicer_Gem_Knowledge/
?? ai_handoff_conformal_remesh/
?? algorithm_pseudocode.md
?? assets/
?? assets_raw/
?? debug_log/openvcad_viewer_8502.png
?? debug_log/openvcad_viewer_8503.png
?? debug_log/openvcad_viewer_8503_column3.png
?? debug_log/openvcad_viewer_8503_column3_fixed.png
?? debug_log/openvcad_viewer_8504_column3.png
?? debug_log/openvcad_viewer_8504_column6.png
?? dmslicer_sdf_integration_notes.md
?? gradient_source_conformal_remesh/src/model_material_node/identity.py
?? gradient_source_conformal_remesh/tmp.md
?? marching_cubes_lesson.html
?? marching_squares_lesson.html
?? paper.md
?? paper.pdf
?? pypdf_pages/
?? raw_blocks.json
?? raw_pages/
?? sdf_lesson_01_distance_field.html
?? source_map.json
?? translation_notes.md
```

审计 baseline 当时没有 `docs/research_v2/`。本次恢复检查开始时，九个目标 Markdown 已经存在，判定为上一次被人工停止留下的 interrupted partial artifacts；它们在本阶段允许范围内被逐份复核和续写，并与上述 pre-existing dirty state 分开记录。

## 4. Legacy 算法身份

论文中的 **Legacy AMF baseline** 固定指以下链路：

```text
AMF parser
→ object AABB overlap
→ triangle BVH candidates
→ unsigned normal-angle gate
→ scale-aware approximate gap gate
→ projected 2D overlap gate
→ pair / patch / ACAG / connected component
→ material role/manual selection
→ section / RegionTriangle / topology-repair experiment outputs
```

它是表面三角网格 heuristic，不是 B-rep 几何真值，不产生体材料场，也不是完整切片器。主要代码位置：

- AMF 解析：`src/dmslicer/file_parser/amf_parser.py`；
- 量化、候选和接触门控：`src/dmslicer/geometry_kernel/canonicalize.py`；
- BVH：`src/dmslicer/geometry_kernel/bvh.py`；
- patch/component：`src/dmslicer/geometry_kernel/patch_level.py`；
- 材料角色：`src/dmslicer/materials/materials.py`；
- section：`src/dmslicer/geometry_kernel/partial_triangle_resolver.py`；
- RegionTriangle：`src/dmslicer/geometry_kernel/regiontriangle/RegionTriangle.py`；
- 分阶段运行器：`src/dmslicer/experiments/`。

### 4.1 AMF parser 的真实语义

**[CODE-CONFIRMED]** `src/dmslicer/file_parser/amf_parser.py` 将每个 AMF `<object>` 读取为一份三角表面 `MeshData`，把该 object 下所有 descendant triangles 扁平合并。它保留顶点、三角形、颜色和文件内容 hash，但不保留 AMF object 原始 ID、volume 分区与 material ID、unit、constellation/instance、placement、metadata、texture 或 composite 语义。内部对象 ID 来自进程级计数器而不是源文件稳定身份；因此该 parser 是 legacy surface-mesh importer，不是严格 AMF 语义解析器。

### 4.2 pair / patch / component / section 的真实语义

**[CODE-CONFIRMED]** 这些词在旧系统中具有以下固定含义：

| 旧术语 | 旧代码中的含义 | 明确边界 |
|---|---|---|
| pair | 对象 AABB 粗筛后，由两棵 triangle BVH 给出的三角形候选及 angle/gap/projected-overlap 证据 | 不是 confirmed B-rep region relation |
| patch | 由通过门控的 triangle-pair evidence 组织出的局部接触证据集合 | 不是 OCCT split 后的二维 face fragment |
| component | patch/ACAG 或对象三角拓扑中的连通分量 | singleton 处理和 non-manifold 情况受旧实现限制 |
| section | Gradient–Source pair 上按 coverage 与邻域扩展得到的 `full/other` 表面三角集合及边界 loop | 不是打印 layer，也不是 STEP plane section |
| RegionTriangle | 单个表面三角形局部二维投影中的 clip/union/remain 与 repair-preview | 不是三维 Boolean、体网格或连续材料场 |

旧接触链先要求对象 AABB 精确重叠，再做 triangle BVH、无向法线角、近似 gap 和投影 overlap；因此小正 gap 可能在进入容差判断前就被排除。patch coverage 采用旧启发式累计而非 B-rep 面积真值。

### 4.3 source / gradient / isolation 的旧定义

**[CODE-CONFIRMED]** 三者都是附着于整个自定义 `Object` 的 Python 材料角色：

- `SourceMaterial` 表示材料来源对象和常量组成，不表示接触面或场边界；其构造器当前存在 `ConstantComposition` 参数顺序错误，不能把现有 composition 行为当成可靠科学真值。
- `GradientMaterial` 保存中心对象及 include/exclude 邻居对象 ID，并持有离散 composition 容器；它不是闭合 `GradientDomain`，也没有计算 `φ(x,y,z)`。
- `IsolationMaterial` 继承 `SourceMaterial`，当前主要用于从 gradient 邻居候选中排除对象；它不是几何分离或 Boolean cut，且旧 section 分类中存在继承判断次序导致的不可达分支。

材料选择的临时状态位于 Streamlit session，运行期状态位于 `Object.material`，持久状态是 workspace JSON；它们均不写回 AMF metadata，也不是 mesh scalar field。

### 4.4 PyVista 与 Streamlit 的职责

**[CODE-CONFIRMED]** PyVista 只负责 surface mesh、triangle、AABB、候选和结果的显示/检查；它不执行旧核心接触判定、二维 clip、B-rep Boolean、field solve 或 slicing。对象选择来自 Streamlit 表格/控件，而非 PyVista geometry picking。

**[CODE-CONFIRMED]** Streamlit 负责上传、工作流编排、对象级 source/gradient/isolate 标注、include/exclude 选择、JSON assignment 保存和可视化承载。它不是 geometry authority，widget/session state 也不是可复现实验真值。

### 4.5 当前 Slicer 与实验运行器边界

**[CODE-CONFIRMED]** `src/dmslicer/slicer/slicer.py` 当前为不可运行的占位层：存在错误相对导入、硬编码 Z 范围、未初始化的 spatial/topology 数据和未实现的路径规划。它不能作为“已完成切片能力”的证据。

**[CODE-CONFIRMED]** `src/dmslicer/experiments/` 的阶段链止于 section、RegionTriangle、repair working graph 与 summary metrics；产物不是稳定逐层轮廓、材料图、toolpath 或 G-code。

### 4.6 论文中的固定角色

**[DESIGN-DECISION]** 论文比较时，旧算法承担四种角色：

1. `backend=legacy_surface_contact` 的主要 mesh-heuristic baseline；
2. STEP/B-rep 方法失败时的诊断证据，而非自动 truth fallback；
3. 人工 Streamlit/PyVista ground-truth/review 工作流的历史实现基础；
4. pair/patch/component、manifest、metrics、regression fixture 和 stage invalidation 思想的工程来源。

旧算法不需要被“证明错误”。实验问题是量化它相对 B-rep 方法在不同关系类型、tessellation、容差、面积、provenance 和运行代价上的行为边界。

### 默认参数

默认值来自 `src/dmslicer/geometry_kernel/config.py` 和 `src/dmslicer/experiments/config.py`：

| 参数 | 默认值 | 解释 |
|---|---:|---|
| `geometry.acc` / `GEOM_ACC` | `4` | 坐标小数位量化精度 |
| `geometry.parallel_acc` | `0.1` | 旧并行判断阈值，代码注释称角度 |
| `contact.normal_angle_degrees` | `60.0°` | 无向法线软门控 |
| `contact.initial_gap_factor` | `0.01` | 初始 gap 相对局部尺度 `h` 的比例 |
| `contact.max_gap_factor` | `0.5` | 最大 gap 相对局部尺度 `h` 的比例 |
| `contact.overlap_ratio` | `0.1` | 投影覆盖率门槛；源码旁注“默认 0.5”已过时 |
| `repair.working_edge_angle_degrees` | `25.0°` | working-edge extension 角度阈值 |
| `repair.boundary_node_snap_tol` | `auto` | 拓扑修复自动吸附容差 |
| `runtime.fresh_model_parse` | `true` | 默认不复用 parser cache |
| `runtime.cold_geom_cache` | `false` | 默认允许 geometry cache |

论文运行必须把实际参数写入 manifest；不得只引用“默认参数”，因为工作树与默认值会变化。

## 5. 当前可重复运行的命令和结果

所有命令均在仓库根目录运行，使用项目 `.venv`，并禁用 pytest cache。

### 5.1 正式快速测试集合

```powershell
& '.\.venv\Scripts\python.exe' -m pytest -p no:cacheprovider -q tests `
  --ignore=tests/test_stpyvista_streamlit_app.py `
  --ignore=tests/test_regiontriangle_topology_point_snap_regression.py
```

2026-09-08 实测：`114 passed`，2 个 `UserWarning`，退出码 0。排除项分别是浏览器/Streamlit 入口和显式慢速真实几何回归，因此这个结果不能外推为“所有 tests 均通过”。

### 5.2 选定 legacy 数学与几何测试

```powershell
& '.\.venv\Scripts\python.exe' -m pytest -p no:cacheprovider -q `
  test/test_composition_position_key.py `
  test/test_contour_ops.py `
  test/test_overlap_area.py `
  test/test_triangle_dihedral_angle.py `
  test/test_canonicalize_result_update.py
```

2026-09-08 实测：`30 passed`，退出码 0。

### 5.3 已知失败：旧 BVH 测试收集

```powershell
& '.\.venv\Scripts\python.exe' -m pytest -p no:cacheprovider -q test/test_bvh.py
```

2026-09-08 实测：收集阶段失败，`test/test_bvh.py` 导入已经不存在的 `dmslicer.geometry_kernel.bvh.query_bvh`，退出码 1。本轮不修复。

### 5.4 独立 Model+Material Node

在 `gradient_source_conformal_remesh/` 中运行：

```powershell
& '.\.venv\Scripts\python.exe' -m pytest -p no:cacheprovider -q tests
```

2026-09-08 实测：`38 passed, 2 failed`，退出码 1。失败涉及 filename-stem workspace identity 与旧 hash-path/round-trip 合同不一致。本轮不修复。

### 5.5 慢速与交互测试

`test/README.md` 声明的慢速命令为：

```powershell
$env:RUN_SLOW_GEOM_TESTS='1'
uv run pytest tests/test_regiontriangle_topology_point_snap_regression.py
```

PyVista/Streamlit 交互入口需要人工环境，不属于无头论文验收。由于 `pyproject.toml` 同时收集 `test` 与 `tests`，裸 `uv run pytest` 当前不能作为稳定基线命令。

## 6. 本机环境

| 组件 | 已确认版本/状态 | 确认方法 |
|---|---|---|
| Windows PowerShell | `7.6.5` | 本机命令 |
| 项目 Python | `3.12.0` | `.venv/Scripts/python.exe --version` |
| uv | `0.10.2` | `uv --version` |
| pytest | `9.0.2` | 项目解释器导入 |
| NumPy | `2.4.1` | 项目解释器导入 |
| PyVista | `0.46.5` | 项目解释器导入 |
| Streamlit | `1.54.0` | 项目解释器导入 |
| Panel | `1.8.9` | 项目解释器导入 |
| FreeCADCmd | `1.1.1`, revision `20260414` | `C:/Program Files/FreeCAD 1.1/bin/FreeCADCmd.exe` |
| FreeCAD 内嵌 OpenCASCADE | `7.8.1` | FreeCADCmd 中 `Part.OCC_VERSION` |
| standalone PythonOCC | 未发现 | 项目解释器中 `OCC` module 不存在 |
| Gmsh executable | PATH/常见安装位置未发现 | 本机路径检查 |
| Gmsh Python module | 未发现 | 项目解释器中 `gmsh` module 不存在 |
| CadQuery | 未发现 | 项目解释器中 `cadquery` module 不存在 |

FreeCADCmd 版本探测成功并返回 0，但用户目录中的 `FreecadRobustMCPBridge/Init.py` 在无 GUI 模式访问 `FreeCAD.GuiUp` 时产生 `AttributeError` 日志。该插件初始化噪声必须与几何算法错误分开记录；未来 headless runner 应使用受控 FreeCAD 配置或至少保存 stdout/stderr。

## 7. 基线使用规则

1. Baseline 运行报告必须记录 HEAD、dirty 标志、tracked diff SHA-256、输入 AMF SHA-256、完整参数和依赖版本。
2. 自动实验优先执行 5.1 与 5.2；不得把交互截图作为 pass 条件。
3. 旧算法结果必须标记 `backend=legacy_surface_contact`，不得称为 CAD-exact 或 B-rep truth。
4. AMF parser 的对象/volume/单位语义损失、AABB exact hard gate、投影覆盖和近似 gap 是已知方法限制。
5. 只有在当前 dirty 改动被用户决定如何保存后，才能形成论文可公开引用的不可变 baseline revision；本文件本身只是可审计快照。
