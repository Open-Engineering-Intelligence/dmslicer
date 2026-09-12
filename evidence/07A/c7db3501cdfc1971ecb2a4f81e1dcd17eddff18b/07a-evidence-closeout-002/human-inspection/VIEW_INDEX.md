# 07A Cylindrical Interface Repair — View Index

STEP/B-rep operations and JSON validation are authoritative. FCStd files are human-inspection aids only.

1. **C01 — exact cylindrical contact**: open `C01/operation_debug.FCStd`; inspect `01_Originals`, `02_Selected_Interface`, then `05_Common_Patches`. Confirm `NO_CORRECTION_REQUIRED` and a full cylindrical common band.
2. **C02 — axis translational misalignment**: open `C02/operation_debug.FCStd`; inspect originals and axes, `03_Precommit_Preview`, `04_Corrected_Assembly`, `05_Common_Patches`, then `09_Fused_Result`. The arrow is `DISPLAY_ONLY / NOT_EXECUTED`; the corrected shaft is the sole executed translation.
3. **C03 — dimensional radial clearance**: open `C03/operation_debug.FCStd`; confirm coaxial axes, different radii, and zero executed motion.
4. **C04 — dimensional radial interference**: open `C04/operation_debug.FCStd`; inspect `10_Rejection_Evidence` for actual material common and confirm zero executed motion.
5. **C05 — angular axis misalignment**: open `C05/operation_debug.FCStd`; inspect the nonparallel axes and confirm translation-only rejection.

Control: `AMBIGUOUS/operation_debug.FCStd` shows all role-valid candidates without selecting one. A likely failure is any corrected/fused success artifact or nonzero motion for C03/C04/C05/AMBIGUOUS.

Orientation control: `ROTATED_C02/operation_debug.FCStd` applies the same C02 geometry under a proper world rotation and translation; its measured correction must remain perpendicular to the rotated axis.
