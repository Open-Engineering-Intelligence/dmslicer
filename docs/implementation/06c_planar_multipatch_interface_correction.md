# 06C 多块与带孔平面接口校正

06C 将 06B 的单个 `InterfaceCarrier` 扩展为由一个或多个共面平面 B-rep Faces 组成的 `InterfaceFaceSet`。本轮仍只处理两个已明确绑定为 `Side_1` / `Side_2` 的刚体；`Side_1` 固定，`Side_2` 只允许沿参考法向整体平移。实现没有修改 06A/06B，也没有建立通用 STEP 接口识别器。

## FaceSet 构造与选择

FreeCAD 后端只读取实际 STEP 重导入后的 B-rep。它用 `face.normalAt()` 判断 outward normal，以 supporting Plane 上一点与参考方向的点积记录 support coordinate，再以 `abs(si-sj) <= linear_epsilon` 分组。Plane 自身 Axis 的符号不替代 face outward normal。FaceSet 成员按几何摘要稳定序列化；Face ordinal 只是本次运行的人类标签。

程序对所有相向、平行、正间隙且位于 `tauE` 与 motion budget 内的 FaceSet pair，在 Side_2 整体 disposable copy 上执行 prospective 纯法向平移，然后重新按同一几何语义寻找 FaceSet，并计算实际 face-pair B-rep common。只有一个合规 pair 时执行；多个 pair 时返回 `UNSUPPORTED_AMBIGUOUS_INTERFACE_SET`，不会按最近距离、最大面积、成员数或遍历顺序挑选。原始平面 FaceSet 与 eligible pair 分别记录，因此 P10 远处 bridge underside 仍保留为真实 B-rep 证据，但不进入可校正候选。

## P10、P11 与 P12

- P10 的 Side_2 是两个 feet 与 upper bridge 的一个 valid closed Solid。两个 z=5.05 mm 底面组成同一 FaceSet；整体移动约 -0.05 mm 后保留两个位置不同但面积同为 192 mm² 的 common patches。它们的最短 B-rep 距离大于线性容差，因此形成两个 components、两个 outer loops、零 holes。
- P11 直接以最终尺寸创建 outer cylinder 并 cut inner cylinder，不调用 `transformGeometry`。校正后实际 common 是一个 `Plane` Face，其边界由两个解析 `Circle` 组成；同一 Face 的两个 Wires 被解释为一个 outer loop 和一个 hole，面积为 `300π` mm²，第一 Betti 数为 1。
- P12 的两个 feet 分别位于 z=5.05 mm 和 z=5.08 mm，并由上部实体连接成一个 Solid。两个 support groups 都能在各自 prospective rigid translation 后产生 192 mm² common，因此记录两个候选并拒绝执行。输出不包含 `corrected_assembly.step` 或 `fused.step`；FCStd 中的候选仅标记为 `DISPLAY_ONLY / NOT_EXECUTED`。

## Partition、Fuse 与 provenance

实际 common faces 以完整 B-rep geometry digest 去重，不能仅按面积去重。组件以 `distToShape <= linear_epsilon` 分组。每个 source carrier member Face 分别执行 `face.cut(linked_common)`；结果保留 source member linkage，零结果以显式 `EMPTY` JSON 与 FCStd 节点表示。双方分别检查面积守恒、Common/Remaining 正面积无交叠，以及双向 B-rep cut 所证明的无遗漏和无越界。Coverage 使用唯一 common 面积除以所选 FaceSet 总面积，超界直接失败，绝不 clamp。

成功路径在校正后 Fuse，并检查单一 valid closed Solid、体积守恒以及每个 common patch 都未作为正面积外边界残留。Corrected assembly 和 fused STEP 均重导入；重导入检查角色、support plane、residual gap、patch/component/loop/hole topology、coverage、remaining、solid validity、closedness 与 volume。

每个 FaceSet 保存成员、support/normal 与选择证据。每个 Common patch 保存 source STEP hash、双方 occurrence、双方 FaceSet、source member pair、实际 common digest、component id 和操作类型；每个 selected source member 都保存一项或多项 partition outcome，完全被 common 消耗的成员也有带 source FaceSet/member digest 与 linked common digests 的显式 `EMPTY` 记录。当前 FreeCAD binding 未提供可信的 native Generated/Modified/Deleted 历史，因此证据明确标注 `native_history_claimed=false`，只声称直接 B-rep 几何 provenance。

Host 为每个发布 artifact 保存 SHA-256，并启动独立 FreeCADCmd 进程重新读取 common、逐 patch BREP、remaining BREP、corrected assembly STEP 与 fused STEP；validator 再进行一次 artifact-backed 重读，核对 FaceSet support/gap、patch/component/provenance parity、完整 round-trip 字段和文件 hash。这样仅篡改 JSON、替换 BREP/STEP 或伪造摘要都不能保持 PASS。

## 验证与限制

`expected.json` 仅由 host-side validator 在实际操作完成后读取。解析面积和拓扑真值独立来自 P10 矩形尺寸、P11 `π(ro²-ri²)` 与 P12 “多个合法候选必须拒绝”的合同。测试覆盖 expected mutation、face/patch traversal reversal、同面积异位置 patch、patch 删除/重复、component mapping、hole/loop 篡改、NaN/无穷、bool-as-numeric、coverage 越界、未授权、tauE、budget，以及失败验收不覆盖既有成功输出。

真实支持范围仅为：两个明确角色的 body、planar/parallel/opposing/coplanar FaceSet、uniform normal gap 与 Side_2 rigid translation。当前简单平面拓扑合同不猜测相连 multi-face component 的 outer/hole：出现时返回 `UNSUPPORTED_COMPLEX_MULTIFACE_COMPONENT_BOUNDARY`。不支持成员不同位移、tilt、rotation、penetration separation、曲面径向校正、sphere、cone、NURBS、mesh、field、gradient、多体 collision、自动 lateral alignment、slicing 或 G-code；缺少角色匹配平面 FaceSet 的曲面输入返回结构化 `UNSUPPORTED`，不能静默降级。

FCStd 先由 FreeCADCmd 写入实际几何树，再通过隐藏的 FreeCAD GUI helper 持久化 `GuiDocument.xml` 并复开核对 visibility profile。P10/P11 默认只显示 `Fused_Result/Fused_Solid`；P12 默认显示 Originals 与 rejection evidence，candidate preview 保持隐藏并标为 `DISPLAY_ONLY / NOT_EXECUTED`。
