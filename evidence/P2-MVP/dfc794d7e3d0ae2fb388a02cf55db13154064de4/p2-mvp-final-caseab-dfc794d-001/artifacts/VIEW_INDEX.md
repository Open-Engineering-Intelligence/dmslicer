# P2 Final Human Review View Index

## Tree order

1. `cad/original.FCStd` — authoritative source fixture.
2. `cad/ui_only_changed.FCStd` — Case A UI-only saved variant.
3. `cad/geometry_changed.FCStd` — Case B through-hole radius mutation.
4. `cad/serialization_reopen.FCStd` — open/save-as-new/reopen variant.
5. Matching `.brep` and `.step` files — independent geometry inspection inputs.
6. `snapshots/<variant>/<opening|closing>/` — immutable geometry-semantic, topology, and UI snapshots.
7. `comparisons/` — tolerance-aware Case A, Case B, and reopen comparisons.

## Expected observations and failure conditions

1. Case A: geometry and semantics remain equivalent while visibility, color, or transparency differs. Fail if geometry differs or UI is unchanged.
2. Case B: geometry differs because measured area, volume, or bidirectional Boolean cut exceeds its explicit tolerance. Fail if the decision relies on bytes or all geometric checks pass.
3. Reopen: bytes may differ while geometry remains equivalent. Fail if a byte difference is treated as geometry evidence.
4. Opening/closing pairs: geometry-semantic and topology snapshots remain stable for each saved artifact. Fail if an original artifact is overwritten or a snapshot is missing.
