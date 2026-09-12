# 材料与语义配置工作区：可评审设计

Goal ID: WORKBENCH-MATERIAL-SEMANTIC-UI-01. Baseline: 91e4d98 (existing workbench). Branch: codex/workbench-material-semantic-ui-01.

用户已授权先形成设计/原型再测试优先实施，无需另行确认。任务正式名称为「DM-Slicer｜Workbench 材料与语义配置工作区」；08J 仅为历史映射。研究阶段、架构职责、任务编号分别记录。本目标是下游体材料场的准备能力，不代表进入或通过 Phase II。

## Scope / Acceptance / Stop

Scope: 现有 Canvas 查看器的选择与显示控制、一个证据抽屉、独立领域 annotation、材料库、浏览器保存/导出/导入。无新框架、后端几何服务或领域实体激活。

Acceptance: 默认全选；全选/全不选/反选与显示/隐藏所选可达；筛选不改变选择集，显示已选数量和名称；透明度 0–100% 只作用于选择集，空集禁用、混合值明确；每行独立选择/显隐/透明度；interface 与 patch 独立；证据默认收起且可读完整来源；四层字段独立；材料添加/编辑后返回原对象；保存和加载验证、失败保留；测试及浏览器证据。

Stop: 上述验收及证据保存后停止。不修改 docs/research_v2，不推送/合并/发布，不运行几何实验，不声明几何等价、材料区域或界面源边界已激活。保留原输入文件。

## 方案选择

选择：扩展现有页面，三个工作区页签，浏览器本地明确保存 + 可移植 annotation JSON 导出/导入。这样复用现有包读取和安全边界，用户可保存独立文件，不必引入任意服务端写路径。

备选：服务端持久化（需存储位置、并发和访问边界，超出最小范围）；只下载 JSON（缺乏日常恢复便利）。本实现提供本地保存，并清楚说明浏览器缓存不是备份，导出文件可跨端口恢复。材料库有独立全局存储键、schema、版本和验证，annotation 引用库版本并携带版本快照，不修改结果包。

## 交互布局

顶部包入口与页签：几何查看 / 材料与语义配置 / 材料库。几何查看保留整体/操作对照。原证据视图入口改为打开唯一「证据与溯源」抽屉；无悬停弹层。选择对象只显示名称、派生几何角色、人工语义状态和材料简要信息；运行细节只在抽屉。

对象行：选择框（只改变集合）、名称按钮（单选并聚焦）、显隐框、透明度滑块及百分比。顶层选择命令覆盖全部对象，过滤仅影响列表可见行。批量滑块显示集合名称、数量和当前混合状态。透明度是 0%=不透明，100%=全透明；渲染 alpha=1-transparency/100。B-rep 穿透边界可独立开关，使用对象相同 alpha。

配置行：Geometry role 只读，来自 entity_kind/scene_role，不从名称、位置或颜色推断。Input / Interface / Patch / Fused output；校正和剩余对象明确保留原生角色，不伪装为四类之一。Semantic role 默认 Unassigned，可人工选择 Isolated region / Source / Gradient；始终 annotation only / 未激活。Material assignment 下拉引用材料 ID。Display color 默认材料色，未分配为中性灰；可勾选覆盖并记录覆盖颜色，不反写材料。源/梯度选择不创建 MaterialRegion、InterfaceSourceBoundary 或场。

材料库：人工提供唯一稳定材料键、名称、颜色、说明、JSON 扩展属性。重命名不改变键；材料键不是持久几何 ID。每次修改增加库版本并记录时间/人工修改。对象行「添加材料」跳转库页，保存返回并定位原对象，新材料可供显式选择（不自动分配）。

## 数据与验证边界

展示层选择集/显隐/透明度只保存在内存，独立于几何和领域数据。领域层为独立 workspace annotation manifest：schema、case_id、source provenance、稳定 entity_ref/reference_provenance、Geometry role、Semantic role、material_id、display_override、材料库版本/快照、决策历史、保存时间、未激活能力。实体引用原样保留，不计算几何 hash 或用序号生成几何身份。RUN_LOCAL_DIAGNOSTIC 对象可显示操作，但领域配置禁用并解释缺少稳定引用。

加载 annotation 必须匹配显式来源上下文及稳定引用集合/引用来源；不做几何等价判断。错包、重复/缺失引用、未知材料/角色、非法颜色/属性拒绝，保留当前状态。保存先校验再写入单个本地存储值；写入异常显示失败，保留未保存修改和旧已保存内容。材料库单独保存；workspace 导入携带的库快照只用于当前工作区，不静默覆盖全局库。切换包前有未保存修改则保留当前包并提示先保存或导出。

## 证据与验证

先保留静态原型，然后运行状态模型测试取得 RED，再实现并取得 GREEN；浏览器验证实际绘制 alpha、集合控制、材料添加返回、三字段分离、保存恢复、存储失败/错包导入、窄屏、完整抽屉和五个真实包。结果分为软件 PASS、字节完整性 PASS、科学实验 NOT_RERUN、用户人工验收 PENDING。所有运行证据置于 evidence/<goal>/<run>/，保留失败版本；选择性复制两份并建立 manifest，不声称异地灾备。
