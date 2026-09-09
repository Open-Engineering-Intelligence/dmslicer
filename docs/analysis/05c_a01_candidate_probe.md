# 05C A01 候选面选择最小复现

本诊断只使用三个已记录的 A01 STEP。未修改生产算法、阈值、fixture、expected 或既有实验记录；未运行完整回归。

主样本 `A01_delta_m2tauE_s0_01` 的原始 STEP SHA-256 为 `5bff956f81e60806e0d52c6605f882e01cd26d71b3423bd5a034ba2c137c7159`。对重导入 STEP 按生产 `_measure` 的同一过滤、法向、signed 计算和 `(abs(signed), signed)` 排序，返回 `+0.08867513459481 mm`，与记录相符。

ROOT_CAUSE_CONFIRMED：最小 tuple 来自非名义水平 supporting-plane 对，其距离是当前实际的 `h + delta = +0.08867513459481 mm`；名义下体顶面与上体底面的诊断参考为 `-0.2 mm`。该样本同时有正共同体积，因此“任意平面候选的正距离”并不等同于实体材料间隙。q=-4 同样选择更近的非名义对；q=-1 中名义对成为最小候选，故测得正确。

建议未来固定的测量语义是：由构造/接口角色限定的对应面之间的 signed offset，而不是任意水平 supporting plane 的最小绝对距离。本轮未实施修复。

完整候选、面属性、同值最小候选、生产源 hash 与输入 hash 位于机器可读摘要。运行诊断时使用一个 FreeCADCmd 进程、每例新文档并关闭。FCStd：`outputs/contact_fixed_tolerance_05c/a01_candidate_probe/a01_candidate_selection.FCStd`。
