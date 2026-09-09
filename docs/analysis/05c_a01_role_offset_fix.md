# 05C A01 对应界面偏移修复

测量语义由任意水平 supporting plane 的最小距离改为 `ROLE_CONSTRAINED_INTERFACE_SIGNED_OFFSET`。有限 A01 adapter 将 STEP 中 `Side_1` 绑定为基体、`Side_2` 绑定为平移实体，并用实际 face outward normal 选择 Side_1 的 `+z` 接口面与 Side_2 的 `-z` 接口面；缺失、歧义或非平行候选明确返回 `UNSUPPORTED`，不回退到最近面算法。

主样本 `A01_delta_m2tauE_s0_01` 由旧的 `+0.08867513459481 mm` / `positive_gap_within_tolerance` 改为从实际 B-rep 平面测得的 `-0.2 mm` / `penetration_beyond_tolerance`。几何交集、Fuse、容差、fixture 和 expected 未修改。该 adapter 只声明适用于带明确 Side_1/Side_2 A01 约定的输入，不是任意 STEP 的自动接口识别。
