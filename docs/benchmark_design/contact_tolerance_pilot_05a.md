# 05A 工程容差小样本实施说明

本实验明确标为 `LEVEL_B_PILOT`，仅含 A01 平面贴合和 A07 同轴轴孔贴合。两例均为 nominal 尺度倍率 1、`tauE=0.1 mm`，并采用冻结的 15 个 `delta/tauE` 采样点；A01 为沿法向的刚体 pose，A07 为孔半径的 construction variant。

样本的 `expected.json` 由构造方程独立写入；实际分析只重导入 STEP、读取明确的 A01/A07 几何配置和容差，最后才进行比对。每行分别记录实际几何状态、工程状态和不带 fuzzy/吸附/补桥的直接 Fuse 状态。`|delta|=tauE` 是单独 strata，边界采用 inclusive 判定。

未执行：旋转、切向扰动、多尺度、因素组合、其余 canonical cases，以及任何 tolerance-aware repair。输出仅陈述 15 个采样点，绝不外推连续区间。
