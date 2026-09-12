# 09B 材料与语义 Tab 集成契约

Goal：`WORKBENCH-MATERIAL-SEMANTIC-UI-01`。09B 不拥有几何查看器、Canvas、相机、命中测试、对象显隐、透明度、结果包导入服务或最终端口。最终几何显示入口为 09A 的 `http://127.0.0.1:56810/`；09B 的 56811 仅是历史开发/回归预览，不是发布入口。

09A 应在自己的工作台中嵌入“材料与语义”Tab。该 Tab 消费已打开案例的稳定对象描述，返回独立 workspace annotation JSON。它不修改 STEP、B-rep、patch、interface、显示网格或 09A 的查看器状态。

## 可复用资源

| 资源 | 09A 用途 | 不可承担的职责 |
|---|---|---|
| `src/dmslicer/workspace_annotations.js` | 纯状态、验证、材料库、持久化键和 group policy；浏览器直接加载或 Node `require` | 几何读取、几何等价、字段求解、关系激活 |
| `src/dmslicer/material_workspace.js` | 当前开发版 Tab 控制器；09A 可按本契约重接其 UI 事件 | Canvas 绘制、导入包、选择或修改几何对象 |
| `tests/workspace_annotations.test.cjs` | 领域契约回归：11 个可执行行为 | 09A 的画布回归 |
| `tests/material_workspace_browser.cjs` | 开发预览的 UI 行为清单；09A 应把等价交互迁入自己的 e2e 测试 | 将 56811 作为最终入口 |
| `docs/implementation/workbench_material_semantics.md` | 字段、验证和 provenance 解释 | 09A 集成的唯一规范；本文件优先定义边界 |

## 09A → 09B 输入

09A 在打开一个结果案例后，传给状态模块的最小 `case`：

```js
const workspace = WorkspaceAnnotations.create({
  case_id,
  provenance: { source_evidence, package_case },
  scene: { entities: [
    {
      entity_ref,              // 已有稳定对象引用；绝不由显示网格生成
      identity_status,         // 仅 STABLE_REFERENCE 可持久配置
      reference_provenance,    // 稳定引用出处
      source,                  // 已有源几何资产引用，可为空
      entity_kind,
      scene_role,
      display_name
    }
  ]}
});
```

`entity_ref`、`reference_provenance`、`source` 和 case provenance 是恢复配置时的严格匹配条件。它们是 provenance 校验，不是 B-rep 几何等价判断。输入对象为 `Input` 才可配置；Interface、Patch、Fused output 与运行内诊断对象应显示为只读。

## Tab 状态、输出与持久化

Tab 维护一份 `dmslicer.workspace-annotation.v2`。调用方应将它与结果包分开保存、导出与导入：

```js
const restored = WorkspaceAnnotations.restore(case, importedJson);
const storageKey = WorkspaceAnnotations.key(case);
WorkspaceAnnotations.save(case, workspace, window.localStorage);
const displayColor = WorkspaceAnnotations.color(workspace, entity_ref);
```

`save` 在写入前验证；`restore` 拒绝 v1 和不匹配的 case / 稳定引用 / 资产 provenance。09A 在异步读文件或切换案例后，必须重新检查当前 case 与草稿 revision，不能把旧 case 的 annotation 绑定到新 case。未保存草稿应阻止覆盖性导入。

材料库是 `dmslicer.material-library.v1`：由 `library()` 取得预置 PLA、ABS、PETG、TPO；用 `putMaterial()` 新增/编辑；用 `replaceLibrary()` 导入经验证的库。数值属性必须包含 `value`、`unit`、`source`、`evidence`。材料 ID 的稳定性只限材料库，不能作为几何身份。

## 语义规则

`semantic_type` 是 `Unassigned`、`Source`、`Gradient`、`Isolator`，独立于 `material_id`。

- Source：保存时 `material_id` 必须引用材料库。
- Gradient：`material_id` 必须为 null；`gradient_group_id` 默认为 `G`，可为 `G1`、`G2` 等。它是贯通组标识，不是材料或显示名。
- Isolator：实例由 source context + `owner_entity_ref` 作用域化；同名不跨对象合并；`isolator_material_requirement` 目前固定 `UNDECIDED`，不擅自强制材料。
- `display_override` 是显式显示色；为空时才读取材料默认色。颜色不能反推材料或语义。

如 09A 已有可信的几何关系记录，可调用 `connectionPolicy(workspace, aRef, bRef, geometryRelation)`。只有同 `gradient_group_id`、`status: 'CONFIRMED'`、`allows_connection: true` 且 relation 端点明确匹配时，结果才为 `allowed: true`。结果始终 `activated: false`；不同组保留几何接触事实但返回 `DIFFERENT_GRADIENT_GROUP`。09B 不合并域、传播梯度状态或创建 InterfaceSourceBoundary。

## UI 适配边界

09A 负责 Tab 容器、可访问性、对象列表、脏状态提示、文件选择和最终浏览器测试。材料/语义 Tab 至少提供：材料库入口、对象 `semantic_type`、材料下拉、Gradient group 输入、Isolator 所有者说明、显示覆盖色、保存/导出/导入状态。Gradient 行禁用直接材料下拉；所有完整运行细节继续由 09A 的“证据与溯源”区域展示。

09A 可以调用 `color()` 向自己的画布传入显示色，但只能把它作为 display override/material preview，不能将其写回、推断或验证几何。09B 不复制 09A 画布、三角网格、边界线、包读取器或端口启动脚本。

## 验收交接

09A 集成后应复跑：状态模型 11 项测试，并在 56810 验证材料新增/编辑/回到原对象、Source 材料要求、Gradient 无直接材料和 G/G1/G2、Isolator 对象作用域、v1 拒绝、保存失败、脏草稿/异步导入保护及桌面/窄屏 Tab 可达性。09B 的 56811 浏览器记录只能作为开发期证据，不能作为 09A 最终画布验收。
