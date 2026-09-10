# 06D branch/worktree provenance closeout

## Record identity

- Goal: `06D — Orientation-Invariant Planar Correction`
- Closeout date: `2026-09-10` (`Asia/Shanghai`)
- Geometry implementation: `b7054f303896aa4a0762248a0b54686d8e733ead`
- Final historical/policy commit: `b42ba9e7b6efc6dd5a9dd9f7b1584b5a89066f8b`
- Archival ref: `archive/06d-orientation-invariant-planar-correction`

## Verified ancestry

The first-parent relationships were verified directly from the Git object graph:

```text
b7054f303896aa4a0762248a0b54686d8e733ead
  -> b42ba9e7b6efc6dd5a9dd9f7b1584b5a89066f8b
  -> c7db3501cdfc1971ecb2a4f81e1dcd17eddff18b
```

Commit `c7db3501cdfc1971ecb2a4f81e1dcd17eddff18b` is titled
`feat: add cylindrical interface pose correction`. Its changed-file scope is
07A cylindrical-interface implementation, tests, fixtures, documentation, and
the corresponding CLI additions. It is not the 06D historical endpoint.

## Branch provenance anomaly

Status: `LEGACY_MISADVANCED_BRANCH_REF`

The historical branch `feat/orientation-invariant-planar-correction` was
advanced to `c7db3501cdfc1971ecb2a4f81e1dcd17eddff18b`. It therefore no longer
serves as an accurate final ref for 06D. The ref is retained unchanged as a
legacy remote-history reference; it was not reset, rewritten, or deleted.

The stable 06D historical identity is:

- geometry implementation: `b7054f303896aa4a0762248a0b54686d8e733ead`;
- final historical/policy commit: `b42ba9e7b6efc6dd5a9dd9f7b1584b5a89066f8b`;
- archival ref: `archive/06d-orientation-invariant-planar-correction`, fixed at
  `b42ba9e7b6efc6dd5a9dd9f7b1584b5a89066f8b`.

The canonical 07A development branch is
`feat/cylindrical-interface-repairability`. The legacy 06D branch name must not
be used for continued 07A development.

## Evidence Release binding

The existing GitHub Release/tag `goal-06d-evidence-b7054f3` was inspected
without modification. Its `targetCommitish` is
`b7054f303896aa4a0762248a0b54686d8e733ead`, so the misadvanced branch ref does
not change the Release's commit binding.

Release: <https://github.com/Open-Engineering-Intelligence/dmslicer/releases/tag/goal-06d-evidence-b7054f3>

## Worktree provenance anomaly

Status: `WORKTREE_PATH_BRANCH_MISMATCH`

- Physical path: `D:\Agent\worktrees\dmslicer-06d`
- Current branch at closeout: `feat/cylindrical-interface-repairability`

The physical path retains the older `dmslicer-06d` name while the worktree is
now assigned to the canonical 07A branch. This mismatch is recorded only. The
worktree was not moved, renamed, or deleted.

## Closeout constraints

This closeout created the archival branch and this provenance record only. It
did not modify algorithm code, rewrite commit history, move either existing
feature branch, modify the 06D Release, move or delete a worktree, merge
`main`, or rerun geometry or the full pytest suite.
