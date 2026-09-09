# 06A 验收补齐：授权与有效数值

## 实际漏检

06A 的 host validator 原先只做部分类型和阈值比较。NaN 可绕过 Python 的上限比较；CORRECTED_AND_FUSED 也没有独立核对策略授权、策略有效性、动作授权和 tauE_mm。这些问题只影响合成验收反例，不代表已保存 FreeCAD 几何运行失败。

## 新增约束

新增统一必填数值读取器：字段必须存在、类型严格为 int/float（排除 bool）、有限，并满足正数或非负约束后才参与比较。成功校正还必须同时证明合法策略、allow_motion=True、policy_valid=True、motion_authorized=True、正实测间隙、offset <= tauE_mm、位移在预算内，以及向量等于 -offset * unit_normal。

ALREADY_CONTACT 继续允许零移动且不要求运动授权，但需要零位移、当前规则下的接触和后检查。拒绝状态必须零位移且 fuse.executed=false；POSTCHECK_FAILED 不可作为可发布成功结果。CLI 在任一 operation/suite validator 失败时返回非零。

## 反例与重验收

参数化 host 测试覆盖八个原始反例、NaN/±∞/缺失/负值、单位法向与 bool 数值伪装、合法已贴合及四种合法拒绝。对已保存的 P01–P06 operation.json 仅做重新验收（不调用 FreeCAD）；全部通过。几何算法、STEP、policy、expected 和既有数值阈值均未修改。
