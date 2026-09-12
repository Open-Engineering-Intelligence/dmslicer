# 几何结果包查看器

当前唯一正常入口是选择 **一个 `.dmslicer` 文件**。不是选择文件夹，也不要求用户挑选散落的 STEP/JSON。当前平台不提供裸 STEP 导入、不重跑 Boolean、不在导入时启动 FreeCAD。

在仓库根目录运行 `./start_geometry_viewer.ps1`，打开终端打印的本机 URL，点击 **导入 DM-Slicer 结果包**。本机端点只绑定 `127.0.0.1`；关闭终端或 Ctrl+C 停止。当前需要 Python 3.12 来读取 ZIP 包并提供页面；读取已保存显示缓存不需要 FreeCAD。浏览器 `file://` 下的 preview.html 是方便检查的离线快照，正常导入请使用上述入口。

## 当前样包

- `evidence/GEOMETRY-CASE-VIEWER-01/c02-package-004/C02.dmslicer`
- `evidence/GEOMETRY-CASE-VIEWER-01/u05-package-004/U05.dmslicer`
- `evidence/GEOMETRY-CASE-VIEWER-01/case01-package-002/CASE01.dmslicer`

两包都来源于 08C 的已有当前复跑结果。本次只采样这些结果的显示网格，不重新计算接触或融合。它们不是 U02 的替代证据；U02 由独立的 08F 任务准备，采用同一导入合约即可接入。

CASE01 单独复用 `case01-brep-display-20260912-006` 的现成显示网格、稳定引用和分析 JSON，不执行任何 CAD 调用。包含 A/G/B 三个对象和 A-G/G-B 两个公共补丁。本证据没有融合产物，融合组标为“本证据未产生”。可用 `python -m dmslicer.prepare_case01_package --output NEW_OUTPUT` 重现打包步骤。

默认显示两个输入几何对象和公共接口补丁；校正对象、剩余分区和融合结果可按组或逐项切换。C02 公共补丁来自已计算的校正后结果，不能据其显示位置推断原始输入已精确贴合。对照时启用校正组并隐藏原始输入组。融合结果默认隐藏，避免挡住输入；显示设置不改变计算事实。

`Export07A/Solid1`、`common_1` 等是 **run-local diagnostic**，只定位本包这次采样的对象；不能跨运行作稳定几何身份。`导入几何对象` 不代表 `MaterialRegion`。当前两个包没有材料区域绑定。开放或有边界的接口补丁是允许的，不用 solid closure 判定其有效性。

## 最小包合约 v1

`.dmslicer` 是 ZIP 容器，顶层 `manifest.json` 指定单一包的来源和资产：

```json
{
  "schema": "dmslicer.result-package.v1",
  "case": {"id": "U02", "label": "U02 球面接口结果"},
  "provenance": {"evidence_confidence": "L", "source_run_id": "..."},
  "assets": [
    {"path": "geometry/input.step", "role": "authoritative_geometry", "required": true, "sha256": "..."},
    {"path": "results/operation.json", "role": "operation", "required": true, "sha256": "..."},
    {"path": "results/validation.json", "role": "validation", "required": true, "sha256": "..."}
  ]
}
```

STEP + manifest + 已计算的 operation/validation JSON 是生产者的核心输出；结果 JSON 应保留计算状态、容差及单位、关系、来源 commit/run、已测事实和未知项。读取器会如实展示未提供的可选结果，不补造结论。读取器要求至少一个存在的 STEP 核心资产。

可选资产：`current_kernel_brep`（当前内核精确表示）、`human_review`（FCStd）、`display_cache`（可再生网格）、`source_manifest`（原证据清单）。FreeCAD 是应用，OCCT/Open CASCADE Technology 是其几何内核。FCStd 不作为 Boolean 事实来源，BREP 不假装是跨内核通用交换标准。缓存缺失时仍能读取包、文件清单和计算结果；当前查看平台不重建缓存。

每个列出的存在资产检查 SHA-256 **字节完整性**，不代表几何等价或验证 PASS。必须提供的资产缺失会拒绝导入；可选资产缺失显示 `MISSING_OPTIONAL`。无外部 URI 解析、无脚本执行、无 ZIP 文件解压落盘。上传上限 50 MiB，展开尺寸 200 MiB，最多 512 ZIP 项，拒绝路径穿越与重复名称。

可选 `display` 字段指向 `display/catalog.json`。缓存合约为：

```json
{
  "schema": "dmslicer.display-catalog.v1",
  "cases": [{"case_id": "U02", "label": "U02", "provenance": {},
    "scene": {"kind": "DISPLAY_ONLY_BREP_TESSELLATION", "entities": []}}]
}
```

实体字段：`entity_ref`、`identity_status`、`entity_kind`、`display_name`、`scene_role`、`default_visible`、`source`、`mesh`。`entity_kind` 兼容 MODEL/REGION/INTERFACE/PATCH，界面文案不把 REGION 自动称为材料区域。`scene_role` 为 `input` / `corrected` / `common_interface` / `remaining` / `fused_result`。稳定引用必须有 `reference_provenance`；其余使用 `RUN_LOCAL_DIAGNOSTIC`。

`mesh` 提供 `positions`、`triangles`、`provenance: BREP_TESSELLATION`、`linear_deflection_mm`。可选 `boundary_polylines` 必须声明 `boundary_provenance: BREP_WIRE_EDGE_DISCRETIZATION`。当前采样两个显示容差都是 **0.25 mm**，不改变原始实验容差。边界线取自 B-rep wire/edge；不是从三角网格推断拓扑环。网格前后面着色仅是显示方向，不是材料法向判据。

## 为已有运行准备新包（开发者操作）

`python -m dmslicer.prepare_result_package --run EXISTING_RUN --input-step INPUT.step --output NEW_OUTPUT --case-id ID --label LABEL`。

这是独立的打包工具，使用已有 STEP/BREP 结果和当前 FreeCAD/OCCT 生成可选显示缓存；不做接触/Boolean 计算，不改历史目录。可选 `--include-review` 包含已有 FCStd，但从不打开或修改 FCStd。所有输出目录必须新建。STEP 中多个 solids 被拆成各自可切换的诊断对象。每次只读采样保存 opening/closing 的 geometry_semantic_snapshot、topology_snapshot 和 ui_state_snapshot；这些局部观测不构成完整几何等价验证。

## 验证边界与人工验收

本地测试覆盖包解析、缺缓存降级、恶意路径、字节损坏、JS 语法、自包含 JSON 转义、HTTP 包导入不调用 CAD，以及实际 C02 STEP 的两对象显示采样。未完成浏览器人工视觉验收。

用户需实际确认：单文件导入成功、输入各自显隐、公共面与剩余分区可辨认、融合结果单独显示、选择追溯、拖动与缩放、透明度及内面着色、边界线与圆柱/球面的可读性。渲染是小型 Canvas painter，半透明排序和相交面的遮挡可能有误差；边界线为明确标注的穿透叠加。它不是 CAD 几何检查器。

当前样包面板采用中文输入/公共接口/校正/融合标签。原始 FreeCAD 产品名和 run-local locator 仅在折叠的“来源/诊断”中显示；标签更换不改几何或已有引用。
