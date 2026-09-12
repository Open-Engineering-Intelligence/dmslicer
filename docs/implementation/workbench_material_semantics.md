# 09B 材料与语义配置工作区

Goal: `WORKBENCH-MATERIAL-SEMANTIC-UI-01`。当前任务标题：DM-Slicer｜09B 材料与语义配置工作区。基于 `91e4d98` 的现有工作台扩展材料/配置页，不承担 09A 的几何控件重设计。设计修订和早期失败在本 Goal 的 `evidence/` 下保留，最终验收以 `scope-002/SEMANTIC_TYPES_V2.md` 为准。

## 使用

打开结果包 → 材料与语义配置 → 为具备稳定引用的输入对象选择类型、材料或贯通组。对象行「添加材料」打开材料库，保存材料草稿后返回该对象，材料仍需显式选择。材料库可编辑名称、类别、颜色、说明、JSON 属性，支持独立保存、导出、导入。默认 PLA、ABS、PETG、TPO 没有物性数值；数值属性必须写成含 `value`、`unit`、`source`、`evidence` 的记录。

「保存材料」更新草稿；「保存材料库到此浏览器」保存独立库记录。「保存到此浏览器」保存当前对象配置和本次库快照。导出 JSON 才能形成可移植文件；浏览器缓存并非备份。未保存草稿会阻止新的包/配置导入，异步读取中发生案例或草稿变化也会拒绝提交。失败保留当前草稿和旧存储内容。

## v2 字段与规则

| 字段 | 含义 / 验证 |
|---|---|
| `schema` | `dmslicer.workspace-annotation.v2`；v1 有 Gradient 直接材料等歧义，明确拒绝，不自动迁移 |
| `source` | case_id、源 evidence provenance、包案例记录；恢复时逐字段验证来源一致 |
| `objects[].entity_ref` | 沿用输入稳定引用；不从网格、名称、序号或新 hash 生成身份 |
| `reference_provenance`, `source_geometry` | 输入稳定引用出处与资产引用，恢复必须匹配 |
| `geometry_role` | 只读派生；Input 才允许本阶段领域配置，Interface/Patch/其他派生对象只读 |
| `semantic_type` | Unassigned / Source / Gradient / Isolator，人工选择 |
| `material_id` | 材料库 ID 或 null；Source 保存时必填；Gradient 必须 null；Isolator 保留已有值，必填规则未决 |
| `gradient_group_id` | 仅 Gradient 使用，默认 G，可输入 G1/G2 等新组；它是贯通组身份，不是普通显示名或材料 ID |
| `isolator_instance` | 仅 Isolator 使用，包含 owner_entity_ref 和名称；有效身份为 source + owner_entity_ref，同名不跨对象合并 |
| `display_override` | 显式覆盖色或 null。null 时读材料默认色；没有材料为中性灰，不反推语义 |
| `material_library`, `material_library_version` | 独立材料库 schema v1 的版本快照；修改保留稳定材料键和版本历史 |
| `decisions` | 人工选择、类型转换时清除的旧材料/分组、时间和库版本；缺失 Gradient 组默认化记录 system 决策及规则原因 |
| `activation`, `active_relations` | MaterialRegion/InterfaceSourceBoundary/volumetric_field 全为 false；active_relations 必须为空，自关联明确拒绝 |
| `isolator_material_requirement` | 固定 UNDECIDED，避免把当前保留数据误当成最终必填政策 |

Gradient 类型转换会清除直接材料赋值，并在 decisions 中保留旧值和原因。组成只能由后续显式 Source 与已验证边界关系派生；本次没有组成计算、关联编辑器、域合并或场求解。没有证明或声称进入 Phase II。

## 09A 数据交接

`workspace_annotations.js` 为纯数据模块；Node 可 `require`。09A 读取经 `restore(case, json)` 验证的配置，用 `color(workspace, entity_ref)` 查询显示色。不得反向修改 B-rep、STEP 或显示网格来表达语义。源码内嵌到旧查看页只为本地预览，未改几何选择/透明度/证据布局。

`connectionPolicy(workspace, a_ref, b_ref, geometry_relation)` 返回机器可读资格判断。几何关系由上游提供 `relation_ref`、`region_refs`、`status=CONFIRMED`、`allows_connection=true`，09B 不用接触画面、颜色或相近位置补齐它。相同 group_id 且几何明确允许才返回 allowed=true；不同组始终返回 DIFFERENT_GRADIENT_GROUP。原 geometry_evidence 保留，activated 始终 false。该纯策略不验证几何来源真实性，调用方必须从受信的上游验证结果取得关系。

## 验证与局限

当前真实包中 CASE01 具备稳定引用，可配置三个输入对象。C02/U05/S04/P-MULTI 只有 RUN_LOCAL_DIAGNOSTIC 引用，显示仍可用，持久领域配置禁用。这不是自动生成稳定身份的授权。

几何显示和保存的科学事实沿用原结果包，未重跑 CAD。Node 领域规则、Python 查看器回归、浏览器交互、包字节完整性和人工视觉验收分别记录。主入口 56810 未替换；09B 预览在独立 56811，便于与 09A 分支隔离评审。

本 Goal 自包含样例索引准备完成后，可在该 worktree 运行：

```powershell
$env:PYTHONPATH = 'src'
py -3.12 -m dmslicer.geometry_import --serve --port 56811 --samples evidence/WORKBENCH-MATERIAL-SEMANTIC-UI-01/final-001/samples.json
```
