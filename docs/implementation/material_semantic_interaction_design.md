# 09B 材料与语义交互设计修订

Goal: `WORKBENCH-MATERIAL-SEMANTIC-UI-01`。本设计记录了 2026-09-12 对本地 `localhost:8501` 参考页的人工交互审计结论。它只借鉴布局和交互意图；09B 不复制 Streamlit、PyVista、AMF 或参考页源码。56810 是冻结的 09A 参考样板；56811 是 09B 独立开发/评审预览。

## 对象选择与编辑

对象表始终展示所有案例对象和可编辑性原因。选择行只形成明确的选择集；不改变几何显隐、案例、网格或几何证据。选择任何对象（包括已完成/已配置对象）都可打开或更新材料与语义编辑区。对象行色块可点击，进入该对象的当前材料/显示颜色配置；它只更新 annotation draft，不能写入包、STEP/B-rep 或显示证据。

编辑区显示选中对象数，并维护独立 assignment draft。`Apply` 只通过原子 `applyAssignment` 应用该草稿到明确选择集；失败时现有 annotation 和草稿都保留。`Save` 才验证并持久化完整 annotation。Source 必须选择材料；Gradient 禁止直接材料、使用 G/G1/G2 或用户定义贯通组；Isolator 保留对象级策略和 `UNDECIDED` 的材料要求；Unassigned 不推断任何激活。

“重置所选/清除所选分配”只清除选中对象的 annotation draft。它必须确认或可撤销，绝不卸载案例、清空表格、重置几何状态或重新读取包。

## 材料库

材料库有可发现的“添加材料”入口。添加与编辑使用同一非破坏性编辑器：编辑只创建临时副本，取消不改变库。材料颜色是顶层一等字段：库行显示可点击色块，新增/编辑编辑器直接提供颜色选择，不能藏在扩展 properties。

从 assignment 编辑区新增材料后，创建成功应返回原 assignment 草稿，不自动分配新材料。材料名称、ID、颜色、描述、类别与结构化 properties 分别存储和验证。数值 property 仍要求 `value`、`unit`、`source`、`evidence`；材料组成使用独立结构化编辑器，绝不复用颜色或上一个 property 的输入值。

## 参考页问题的明确排除

- 不实现会卸载模型/上传会话的 Initialize；改为仅 annotation draft 的受确认重置。
- 不实现只显示 Pending/InProgress 的独立 Processing 下拉；所有对象都保持可重新编辑。
- 不让 Show/可见性兼任材料选择。
- 不采用“先从材料库删除、再编辑”的破坏性 Edit 流程。
- 不让 `#000000` 或任何颜色值进入 composition/property 状态。
