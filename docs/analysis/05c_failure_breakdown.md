# 05C 失败分型与下一步决策

**NON_AUTHORITATIVE_ANALYSIS_OF_RECORDED_EVIDENCE**。本轮仅读取保存的 05C 证据；未新增 FreeCAD 测量、未调用 revalidate、未重跑 120 项回归。

## 核对结果

- 计划/可构造/域外：90/86/4。
- 通过/不一致：75/11；与 summary 一致。
- 有效样本两轮 actual 与 validation 均存在；11 条失败两轮 actual 一致。

## 分型

- 去重失败样本：11。事件：SIGNED_OFFSET_MISMATCH=2, ENGINEERING_STATE_MISMATCH=1, MEASURE_ONLY_OVER_LIMIT=9.
- `MEASURE_ONLY_OVER_LIMIT` 为数值测量超过既有绝对面积/体积阈值，且分类、维数和构造记录正确；不将其称为浮点噪声。
- `SIGNED_OFFSET_MISMATCH`/`ENGINEERING_STATE_MISMATCH` 仅见于 A01 0.01× 的 q=-4、-2；现有记录支持“测量值与构造参考不符”，不支持仅凭记录断定面选择根因。

## 失败明细

### A01_delta_m4tauE_s0_01
- 类型：SIGNED_OFFSET_MISMATCH; 根因：NOT_DETERMINED。
- set/measured δ：-0.4 / -0.111324865405 mm；τE/L=0.10998533626595748；OUTSIDE。
- expected/actual state：penetration_beyond_tolerance / penetration_beyond_tolerance；维数：3D / 3D。
- failures：measured_signed_offset_mm；Fuse：executed=True solids=1 valid=True closed=True；两轮一致=True。
- 证据：`batch_1/samples/A01_delta_m4tauE_s0_01/actual.json`，`batch_1/samples/A01_delta_m4tauE_s0_01/validation.json`。
### A01_delta_m2tauE_s0_01
- 类型：SIGNED_OFFSET_MISMATCH, ENGINEERING_STATE_MISMATCH; 根因：NOT_DETERMINED。
- set/measured δ：-0.2 / 0.08867513459481 mm；τE/L=0.11117564655710467；OUTSIDE。
- expected/actual state：penetration_beyond_tolerance / positive_gap_within_tolerance；维数：3D / 3D。
- failures：engineering_state, measured_signed_offset_mm；Fuse：executed=True solids=1 valid=True closed=True；两轮一致=True。
- 证据：`batch_1/samples/A01_delta_m2tauE_s0_01/actual.json`，`batch_1/samples/A01_delta_m2tauE_s0_01/validation.json`。
### A01_delta_m4tauE_s100
- 类型：MEASURE_ONLY_OVER_LIMIT; 根因：CONFIRMED_BY_EVIDENCE。
- set/measured δ：-0.4 / -0.40000000000009095 mm；τE/L=1.0000230940107875e-05；OUTSIDE。
- expected/actual state：penetration_beyond_tolerance / penetration_beyond_tolerance；维数：3D / 3D。
- failures：material_common_volume_mm3；Fuse：executed=True solids=1 valid=True closed=True；两轮一致=True。
- 证据：`batch_1/samples/A01_delta_m4tauE_s100/actual.json`，`batch_1/samples/A01_delta_m4tauE_s100/validation.json`。
### A01_delta_m2tauE_s100
- 类型：MEASURE_ONLY_OVER_LIMIT; 根因：CONFIRMED_BY_EVIDENCE。
- set/measured δ：-0.2 / -0.20000000000027285 mm；τE/L=1.0000115470054253e-05；OUTSIDE。
- expected/actual state：penetration_beyond_tolerance / penetration_beyond_tolerance；维数：3D / 3D。
- failures：material_common_volume_mm3；Fuse：executed=True solids=1 valid=True closed=True；两轮一致=True。
- 证据：`batch_1/samples/A01_delta_m2tauE_s100/actual.json`，`batch_1/samples/A01_delta_m2tauE_s100/validation.json`。
### A01_delta_p0tauE_s100
- 类型：MEASURE_ONLY_OVER_LIMIT; 根因：CONFIRMED_BY_EVIDENCE。
- set/measured δ：0.0 / 0.0 mm；τE/L=1.0000000000000446e-05；WITHIN。
- expected/actual state：exact / exact；维数：2D / 2D。
- failures：positive_common_area_mm2；Fuse：executed=True solids=1 valid=True closed=True；两轮一致=True。
- 证据：`batch_1/samples/A01_delta_p0tauE_s100/actual.json`，`batch_1/samples/A01_delta_p0tauE_s100/validation.json`。
### A07_delta_m4tauE_s100
- 类型：MEASURE_ONLY_OVER_LIMIT; 根因：CONFIRMED_BY_EVIDENCE。
- set/measured δ：-0.4 / -0.40000000000009095 mm；τE/L=1.0000000000000446e-05；OUTSIDE。
- expected/actual state：penetration_beyond_tolerance / penetration_beyond_tolerance；维数：3D / 3D。
- failures：material_common_volume_mm3；Fuse：executed=True solids=1 valid=True closed=True；两轮一致=True。
- 证据：`batch_1/samples/A07_delta_m4tauE_s100/actual.json`，`batch_1/samples/A07_delta_m4tauE_s100/validation.json`。
### A07_delta_m1_1tauE_s100
- 类型：MEASURE_ONLY_OVER_LIMIT; 根因：CONFIRMED_BY_EVIDENCE。
- set/measured δ：-0.11000000000000001 / -0.11000000000012733 mm；τE/L=1.0000000000000446e-05；OUTSIDE。
- expected/actual state：penetration_beyond_tolerance / penetration_beyond_tolerance；维数：3D / 3D。
- failures：material_common_volume_mm3；Fuse：executed=True solids=1 valid=True closed=True；两轮一致=True。
- 证据：`batch_1/samples/A07_delta_m1_1tauE_s100/actual.json`，`batch_1/samples/A07_delta_m1_1tauE_s100/validation.json`。
### A07_delta_m1tauE_s100
- 类型：MEASURE_ONLY_OVER_LIMIT; 根因：CONFIRMED_BY_EVIDENCE。
- set/measured δ：-0.1 / -0.10000000000013642 mm；τE/L=1.0000000000000446e-05；BOUNDARY。
- expected/actual state：penetration_within_tolerance / penetration_within_tolerance；维数：3D / 3D。
- failures：material_common_volume_mm3；Fuse：executed=True solids=1 valid=True closed=True；两轮一致=True。
- 证据：`batch_1/samples/A07_delta_m1tauE_s100/actual.json`，`batch_1/samples/A07_delta_m1tauE_s100/validation.json`。
### A07_delta_m0_9tauE_s100
- 类型：MEASURE_ONLY_OVER_LIMIT; 根因：CONFIRMED_BY_EVIDENCE。
- set/measured δ：-0.09000000000000001 / -0.09000000000014552 mm；τE/L=1.0000000000000446e-05；WITHIN。
- expected/actual state：penetration_within_tolerance / penetration_within_tolerance；维数：3D / 3D。
- failures：material_common_volume_mm3；Fuse：executed=True solids=1 valid=True closed=True；两轮一致=True。
- 证据：`batch_1/samples/A07_delta_m0_9tauE_s100/actual.json`，`batch_1/samples/A07_delta_m0_9tauE_s100/validation.json`。
### A07_delta_m0_5tauE_s100
- 类型：MEASURE_ONLY_OVER_LIMIT; 根因：CONFIRMED_BY_EVIDENCE。
- set/measured δ：-0.05 / -0.049999999999954525 mm；τE/L=1.0000000000000446e-05；WITHIN。
- expected/actual state：penetration_within_tolerance / penetration_within_tolerance；维数：3D / 3D。
- failures：material_common_volume_mm3；Fuse：executed=True solids=1 valid=True closed=True；两轮一致=True。
- 证据：`batch_1/samples/A07_delta_m0_5tauE_s100/actual.json`，`batch_1/samples/A07_delta_m0_5tauE_s100/validation.json`。
### A07_delta_p0tauE_s100
- 类型：MEASURE_ONLY_OVER_LIMIT; 根因：CONFIRMED_BY_EVIDENCE。
- set/measured δ：0.0 / 0.0 mm；τE/L=1.0000000000000446e-05；WITHIN。
- expected/actual state：exact / exact；维数：2D / 2D。
- failures：positive_common_area_mm2；Fuse：executed=True solids=1 valid=True closed=True；两轮一致=True。
- 证据：`batch_1/samples/A07_delta_p0tauE_s100/actual.json`，`batch_1/samples/A07_delta_p0tauE_s100/validation.json`。

## 唯一建议

优先建立 **A01、0.01×、q=-2 的独立最小测量复现**，只审计平面候选选择及 signed-offset 计算路径。这是唯一同时处于工程容差带外侧附近、出现 signed offset 与工程状态不符的已确认症状代表；不改变阈值、不改算法，也不扩大实验矩阵。
