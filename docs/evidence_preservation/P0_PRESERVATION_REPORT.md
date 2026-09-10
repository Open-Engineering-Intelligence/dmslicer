# DM-Slicer P0 Research Evidence Preservation Report

Date: 2026-09-10

No 07A work was started. No historical output, failure evidence, worktree, or source artifact was deleted, moved, overwritten, rebased, or force-pushed.

SHA-256 was used only to verify bytes across copy, staging, upload, and download metadata. A different CAD serialization hash was never treated as a geometry mismatch or a preservation blocker. Cross-version geometry equivalence requires a separately designed semantic snapshot plus explicit unit-bearing tolerance comparison; this phase deliberately did not implement that protocol or rerun historical experiments.

## A. P0 evidence preserved

The custody pass copied 1,513 files totaling 6,567,706 bytes and verified every source/copy SHA-256 pair. The selected sets cover 02C, 03C, 04A, 05B, 05C, 06A, 06B, 06C, and 06D. Highest-priority 04A A02/A08 historical task evidence was copied first and includes BREP, FCStd, STEP, validation, repeatability, summary, and VIEW_INDEX.

Historical failures and mismatches remain intact: 03C A12 pre-fix failure, 05B native `16/90` and normalized `1/90`, 05C retained area-method exceedance, 06B early failures, and the 06C reviewer/hash-policy fix chain.

## B. Evidence still lacking an independent remote copy

Within the 1,513 selected files, none remains at only one local filesystem path: every source has a verified preservation copy. However, the two local paths are not treated as independent protection against host/storage loss.

Published curated ZIP payloads contain byte-identical content for 258 selected source artifacts. The remaining 1,255 selected artifacts do not have an off-host byte-identical payload copy and therefore keep their source worktrees under custody. This count includes blocked-Goal full/debug evidence plus raw logs and pre-sanitization JUnit retained locally by design.

Additional 03A, 03B, 04B, and 05A output sets were not selected into this P0 copy pass and remain single-location/P1 risks pending a dedicated inventory.

## C. Historical evidence not fully recoverable

- 02C: no located final-tip JUnit, BREP, FCStd, or VIEW_INDEX; the existing bundle binds `79f60fa`, not `b646027`.
- 03C: no formal JUnit for the analytic-geometry fix; post-fix execution does not explicitly bind `4a2aad8`.
- 04A: no JUnit in the located A02/A08 task tree and no explicit run-to-`1935427` binding.
- 06D: exact wording of two historical reviewer findings was not recovered; the closeout summary remains `CHAT`, exact text `U`.
- Historical commands, versions, timestamps, or exit codes absent from durable evidence remain JSON `null` / confidence `U`.

## D. Evidence manifests established

Thirteen schema-backed manifests were generated for every Goal from 02C through 06D. All 13 pass the repository JSON Schema. They separately record software/pytest, scientific experiment, human inspection, and provenance results. SHA-256 is explicitly limited to file/download integrity.

## E. GitHub Evidence Releases

Published:

- [goal-06a-evidence-aadf996](https://github.com/Open-Engineering-Intelligence/dmslicer/releases/tag/goal-06a-evidence-aadf996), target `aadf996a05bf87efee862964141b6aeb7f872baf`.
- [goal-06c-evidence-58ec93a](https://github.com/Open-Engineering-Intelligence/dmslicer/releases/tag/goal-06c-evidence-58ec93a), target `58ec93a67d8214c69bc92d5710c60d91aa1fe30c`.
- [goal-06d-evidence-b7054f3](https://github.com/Open-Engineering-Intelligence/dmslicer/releases/tag/goal-06d-evidence-b7054f3), target geometry commit `b7054f303896aa4a0762248a0b54686d8e733ead`.

GitHub was queried after publication: all three are non-draft, non-prerelease Releases; every asset name, byte size, and GitHub SHA-256 digest matches staging. Total: 16 assets, 826,192 bytes.

Blocked with `RELEASE_BLOCKED_PROVENANCE`: 02C, 03C, 04A, 05B, 05C, and 06B. Out of this P0 Release scope: 03A, 03B, 04B, and 05A. No blocked Goal was guessed or force-published.

## F. 06D self-contained Human Review

`goal-06d-human-review-v2-b7054f3.zip` was created without altering `06D_HUMAN_REVIEW.zip`. It contains README, relative-path VIEW_INDEX, D01/D02/D03 FCStd files, six corrected/fused STEP files, reviewer/failure notes, a package manifest, and checksums.

Independent extraction validation passed: 14 files extracted, all 9 VIEW_INDEX links resolve within the extracted package, no absolute or parent-escaping path is present, and every package checksum matches. The v2 ZIP is 87,802 bytes with SHA-256 `d412caba96a801f4331ac47425014638c647a766d2aea15e5346c1d267fc4675`.

## G. Human Inspection policy PR

Status: `BLOCKED_CHERRY_PICK_CONFLICT`.

The isolated branch was created from current `origin/main@5c09db9` and the exact source was `b42ba9e`. The source commit changes only `AGENTS.md`, but cherry-pick produced a content conflict because its parent context includes the Geometry Equivalence and Hash Policy section absent from current main.

Per the gate, the conflict was not resolved or continued; the branch was not pushed, no PR/checks were created, and no merge occurred. PR URL and merge commit are `null`. No 06D implementation history was imported.

## H. Branch Dependency DAG

The command-backed DAG confirms the executable research chain:

`main → 02C → 03A core bd831be → 03B → 03C → 04A → 04B → 05A → 05B → 05C → 06A → 06B → 06C → 06D geometry b7054f3`.

03A packaging `a1fc48b` and 03B are sibling children of `bd831be`; packaging is not an ancestor of 03B–06D. DOC01 branches from 05C and is not inherited by 06A–06D. 06D policy `b42ba9e` is a child of geometry commit `b7054f3` and is not an experiment-run commit. No batch merge plan or execution was performed.

## I. Worktrees that remain non-deletable

02C, 03A, 03B, 03C, 04A, 04B, 05A, 05B, 05C, 06B, DOC01, the active repository checkout, the preservation worktree, and the conflict-preserving policy worktree remain `NOT_ARCHIVABLE`, `ACTIVE`, or `BLOCKED_ACTIVE`. Their detailed reasons are in `WORKTREE_CUSTODY_REPORT.md`.

No worktree was deleted this round.

## J. Worktrees meeting ARCHIVABLE conditions

06A, 06C, and 06D meet the evidence-side `ARCHIVABLE` conditions: exact source commits exist remotely, manifests validate, canonical Releases are published and digest-verified, local preservation copies remain, and applicable rejection/reviewer/human-review evidence is retained.

They were not deleted. `ARCHIVABLE` is a custody state only and does not override the explicit no-deletion rule.

## Final control summary

- Releases created: 06A, 06C, 06D.
- Releases blocked: 02C, 03C, 04A, 05B, 05C, 06B.
- Policy PR URL / merge commit: `null` / `null` (`BLOCKED_CHERRY_PICK_CONFLICT`).
- Preserved artifacts: 1,513 files / 6,567,706 bytes.
- Remaining without off-host byte-identical payload copy: 1,255 selected artifacts; plus uncounted P1 output sets for 03A/03B/04B/05A.
- Manifest validation: `13/13 PASS`.
- Self-contained Human Review validation: `PASS` (9/9 links, checksums pass).
- Branch DAG: complete; numbering is not ancestry, 03A packaging is not inherited.
- Worktree custody: no deletions; 06A/06C/06D `ARCHIVABLE`, all others retained.

## Follow-up project governance — not implemented in this phase

A separate window/branch should design and implement project-level evidence placement and custody rules:

- `AGENTS.md` should define mandatory evidence placement, custody, and lifecycle policy.
- Every Goal should have a project-tracked manifest and stable artifact URI connecting Goal → commit → input → output → validation → review.
- `outputs/` and `work/` should be staging/debug locations only and must never be the sole evidence copy.
- A script/CI gate should validate manifest completeness, source implementation commit, public-safe paths, stable artifact URIs, integrity metadata, and the required independent-copy count.
- Chat/task history remains `CHAT` provenance and cannot replace a project artifact or be upgraded to a current geometry PASS.
- Cross-version CAD equivalence should use a separately designed semantic snapshot plus explicit unit-bearing tolerance comparisons; serialization hashes remain byte-integrity metadata only.

This future capability was intentionally not hand-built into the P0 preservation pass and requires its own scoped design and implementation task.
