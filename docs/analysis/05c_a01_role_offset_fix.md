# 05C A01 对应界面偏移修复

测量语义由任意水平 supporting plane 的最小距离改为 `ROLE_CONSTRAINED_INTERFACE_SIGNED_OFFSET`。有限 A01 adapter 将 STEP 中 `Side_1` 绑定为基体、`Side_2` 绑定为平移实体，并用实际 face outward normal 选择 Side_1 的 `+z` 接口面与 Side_2 的 `-z` 接口面；缺失、歧义或非平行候选明确返回 `UNSUPPORTED`，不回退到最近面算法。

主样本 `A01_delta_m2tauE_s0_01` 由旧的 `+0.08867513459481 mm` / `positive_gap_within_tolerance` 改为从实际 B-rep 平面测得的 `-0.2 mm` / `penetration_beyond_tolerance`。几何交集、Fuse、容差、fixture 和 expected 未修改。该 adapter 只声明适用于带明确 Side_1/Side_2 A01 约定的输入，不是任意 STEP 的自动接口识别。

本轮将 q=-2 与 q=-4 的原始 STEP/parameters/expected 以逐字节归档的最小测试数据置于 `tests/data/contact_fixed_tolerance_05c/`，来源与 SHA-256 见该目录 `MANIFEST.md`；q=-1、0、+0.5 控制项直接读取跟踪的 05A 包。实际 STEP 导入路径覆盖缺失角色、导入器消歧后的重复角色、以及父目录变化，均不会按对象顺序回退。最终完整回归为 128 passed（JUnit 与日志位于本轮 acceptance 输出目录）。

21 项有限重测已完成；其中 `A01_delta_p0tauE_s100` 保留面积方法超差：实测 `33333333.333330356 mm²`，固定 truth 为 `33333333.333333332 mm²`，差值约 `2.98e-6 mm²` 大于既有 `1e-8 mm²` 面积容差。其角色、偏移 `0.0 mm`、工程状态 `exact`、2D 交集与 Fuse 均通过；未为此修改阈值、输入或 expected。
