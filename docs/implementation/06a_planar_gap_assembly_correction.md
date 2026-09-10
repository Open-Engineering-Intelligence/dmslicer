# 06A 平面间隙装配校正：短实施说明

## 输入

生产输入固定为仓库跟踪的 A01 两体 `inputs.step`、唯一 `Side_1` / `Side_2` 角色选择和独立 `operation_policy`。六场景 manifest 只引用 05A 的四份原始 STEP 及 SHA-256；旧 `parameters.json` 和 `expected.json` 不参与动作决策，也不修改。

## 操作策略与状态

FreeCADCmd 每次重新导入 STEP，按 `Side_1 +z` 与 `Side_2 -z` 的相向平面测量 signed offset。仅当正间隙不超过 `tauE_mm`、策略明确 `allow_motion=true` 且所需位移不超过 `max_translation_mm` 时，对 Side_2 的独立 Shape 副本执行一次 `translation=-d*n`；Side_1 和两个原始 Shape 保持不变。缺失或非法策略按不授权处理。

固定状态为 `CORRECTED_AND_FUSED`、`MOTION_NOT_AUTHORIZED`、`TRANSLATION_BUDGET_EXCEEDED`、`ENGINEERING_TOLERANCE_EXCEEDED`、`ALREADY_CONTACT`、`PENETRATION_OUT_OF_SCOPE`；实际后检查失败改报 `POSTCHECK_FAILED`，不以成功产物覆盖已有结果。

## 验收公式

长度、面积、体积与角度误差分别使用 manifest 中预先声明的阈值。成功或已贴合路径必须重新测得零残余 offset、得到覆盖双方所选接口面的实际二维 common、融合为一个有效闭合连通 Solid，并满足 `V(U) ≈ V(A_after)+V(B_after)-V(A_after∩B_after)`。校正后 Side_2 施加逆变换，与原 Side_2 做双向差体积和最短距离对照；融合边界不得保留正面积共同面。

## 代码位置

- `src/dmslicer/planar_gap_assembly_correction_06a.py`：策略解析、FreeCADCmd runner、独立 validator、原子发布和 checkpoint。
- `src/dmslicer/freecad_planar_gap_assembly_correction_06a.py`：角色解析、实测、授权判定、副本平移、common/fuse、STEP/FCStd 导出与重导入。
- `benchmarks/planar_gap_assembly_correction_06a/`：六场景 manifest、独立 policies 与 06A expected。
- `tests/test_planar_gap_assembly_correction_06a.py`：策略、六场景、篡改、顺序、幂等、两进程和失败不覆盖验收。
