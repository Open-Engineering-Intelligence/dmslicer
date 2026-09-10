# P1 Artifact Reconciliation

The companion `artifact_reconciliation.json` contains one record per observed source instance. Counts below are source-instance counts, not counts of unique scientific artifacts. SHA-256 is used only to verify byte identity, byte divergence, copy integrity, or Release payload presence. It is never used as geometric-equivalence evidence.

## Sources and method

The inventory covers the formal 02C–06D and DOC01 worktrees, the P0 canonical custody inventory, the P1 risk-goal copies, existing local Release staging for 06A/06C/06D, the historical 04A task directory, the historical 06D Codex output directory, and located legacy audit/sync artifacts. Every readable file was hashed with shared-read access. Classification is by Goal, normalized logical path, byte digest, and Release digest presence.

`DIVERGENT_REQUIRES_REVIEW` means bytes differ at the same Goal/logical path. For STEP/BREP/FCStd it would carry cause `unknown` until a tolerance-aware geometry/topology comparison exists. No such byte divergence was found in the inventoried sources.

## Reconciliation counts

| Goal | Records | Bytes | Identical duplicate | Only worktree | Only Codex history | Only preservation | Present in Release | Divergent |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 02C | 46 | 290,194 | 46 | 0 | 0 | 0 | 0 | 0 |
| 03A | 160 | 453,342 | 160 | 0 | 0 | 0 | 0 | 0 |
| 03B | 124 | 363,802 | 124 | 0 | 0 | 0 | 0 | 0 |
| 03C | 102 | 992,822 | 102 | 0 | 0 | 0 | 0 | 0 |
| 04A | 200 | 818,087 | 0 | 84 | 58 | 58 | 0 | 0 |
| 04B | 180 | 592,350 | 180 | 0 | 0 | 0 | 0 | 0 |
| 05A | 1,152 | 2,091,196 | 1,152 | 0 | 0 | 0 | 0 | 0 |
| 05B | 940 | 1,438,198 | 940 | 0 | 0 | 0 | 0 | 0 |
| 05C | 1,210 | 3,747,801 | 1,202 | 4 | 0 | 4 | 0 | 0 |
| 06A | 146 | 697,977 | 8 | 0 | 0 | 0 | 138 | 0 |
| 06B | 98 | 515,496 | 90 | 4 | 0 | 4 | 0 | 0 |
| 06C | 250 | 3,027,597 | 4 | 0 | 0 | 0 | 246 | 0 |
| 06D | 533 | 7,003,087 | 18 | 0 | 0 | 0 | 515 | 0 |
| DOC01 | 4 | 71,904 | 0 | 4 | 0 | 0 | 0 | 0 |
| LEGACY | 5 | 56,597 | 0 | 0 | 5 | 0 | 0 | 0 |
| **Total** | **5,150** | **22,160,450** | **4,026** | **96** | **63** | **66** | **899** | **0** |

## Newly preserved P1 risk sets

P1 copied the complete currently located formal output/work sets for Goals omitted from the P0 canonical copy pass:

| Goal | Files | Bytes | Copy verification |
|---|---:|---:|---|
| 03A | 80 | 226,671 | 80/80 source and copy SHA-256 equal |
| 03B | 62 | 181,901 | 62/62 equal |
| 04B | 90 | 296,175 | 90/90 equal |
| 05A | 576 | 1,045,598 | 576/576 equal |
| **Total** | **808** | **1,750,345** | **808/808 equal** |

The copies are local custody, not an independent off-host copy. They improve recoverability but do not make these Goals Release-ready or their worktrees deletable.

## Focused 06D reconciliation

The 06D comparison includes 129 formal-worktree files, 129 historical Codex-output files, 129 P0 custody files, and the expanded Release-staging payload. The normalized formal, historical, and preservation files are byte-identical where paths correspond. Across all source instances, 18 are classified as identical duplicates and 515 have a byte-identical payload present in the existing Release staging set.

This resolves the custody question, not geometric equivalence. No FreeCAD file was opened or resaved, no historical experiment was rerun, and no geometry claim was inferred from matching hashes.

## Remaining single-location classes

The 96 `ONLY_IN_WORKTREE` records are 84 formal 04A `shell_fill_04a2` files, four 05C repository/work records, four 06B work records, and four DOC01 workflow files. The 66 `ONLY_IN_PRESERVATION` records are the corresponding historically selected 04A/05C/06B custody paths whose normalized logical paths do not have a current-worktree counterpart. They remain retained for review; nothing was deleted or overwritten.
