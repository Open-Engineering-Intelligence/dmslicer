# Sensitivity and duplication check

## Public-content scan

The public manifests, documentation, and generated Release staging were scanned for user-home paths, usernames, Codex task paths, local worktree roots, token/key/secret assignments, and non-redacted JUnit hostnames.

Result: `PASS` — no prohibited string remained in the candidate public assets.

Raw pytest logs and the old 06D absolute-path review indexes were excluded from Release assets. Original copies remain in private custody. JUnit derivatives replace only hostname and local worktree prefixes; each derivative records the source SHA-256 and transformation in `SANITIZATION_RECORD.json`.

## Curated contents

| Staging set | Files | Bytes | BREP | FCStd | STEP | JUnit XML |
|---|---:|---:|---:|---:|---:|---:|
| 06A canonical evidence | 47 | 201,572 | 0 | 2 | 8 | 2 |
| 06C canonical evidence | 83 | 931,295 | 14 | 3 | 8 | 1 |
| 06D geometry evidence | 126 | 1,570,183 | 38 | 3 | 22 | 1 |
| 06D human review v2 | 14 | 196,399 | 0 | 3 | 6 | 0 |

These counts are staging-tree counts before ZIP compression and include README/control metadata added during preservation.

## Exact-hash duplication review

- 06A: 4 duplicate-hash groups / 10 files.
- 06C: 26 duplicate-hash groups / 57 files.
- 06D geometry: 28 duplicate-hash groups / 61 files.
- 06D human review v2: no duplicate-hash group.

The duplicate groups are retained because they are intentional cross-process repeatability or representation evidence. They are not temporary reruns or unrelated garbage. The Release selection excludes raw logs, the superseded packaging design, and unreviewed whole-output uploads while retaining the files required to audit repeatability.

## Scientific failures and mismatches

The selection and public manifests retain 03C pre-fix A12 evidence, 05B native `16/90` and normalized `1/90` mismatch counts, the 05C area-method exceedance, 06B early failures, and the 06C reviewer/hash-policy history. None is filtered to make pytest or experiment results appear greener.
