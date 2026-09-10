# DM-Slicer P1 Historical Evidence Report

Date: 2026-09-10

P1 implementation commit: `cdeca1cd8ea2ca98a44d3e3c7db0a368617d9397`

P0 parent baseline: `4f77c8ab8700a5cef9ef02667b6b7e4005472147`

Policy source / merge: `1c0718edf16e637048c8df6a2df8aefd6afcb72d` / `cea98d726e9e3a2f69d648db7b2920a48df41b6d`

No 07A work was started. No historical output, failure evidence, task record, worktree, Release, or source artifact was deleted, overwritten, rebased, force-pushed, or rewritten. `docs/research_v2/` was not modified.

## A. Conversation discovery and custody

The local Codex index contained 511 entries. P1 selected 36 DM-Slicer root tasks by title/reverse-search identity and recursively included reviewer/subagent descendants, producing 53 related task records. Fifty-one were fully readable; two were metadata-only. Every located raw JSONL file was copied read-only to private custody and independently rehashed: 53/53 source/copy digests match.

The public index contains sanitized metadata, archive IDs, task/parent relationships, Goal mapping, commit/review/diagnostic summaries, and confidence labels. It does not expose the private custody path or full conversation text. Raw task history remains `CHAT` provenance and is not promoted to current-environment validation.

Important correction: 06B was not missing. The 06A root task contains later 06B turns and records completion at `c23cc83a4c60620a8210e9aad01fb7adc1c72bde`; the public index models that one task with related Goals 06A and 06B.

## B. Recovered review and diagnostic chains

- 02C: a first closeout at `07655b8` reported 23 passing tests but lacked repeatability/provenance coverage. A later task at `b646027` reported 32 passing tests and two-process repeatability. The existing bundle remains bound to `79f60fa`; P1 does not silently rebind it.
- 03C/A12: a diagnostic task localized 0.0427656319 mm^2 of area error to `transformGeometry` before STEP export; the roundtrip added about 1.16e-8 mm^2. Direct normalized construction retained Plane/Circle and reduced error to about 4.46e-11 mm^2. The post-fix execution-to-`4a2aad8` binding remains incomplete.
- 04A: the task reported 83 tests with zero failures/errors/skips and 357.461 s duration at final `1935427`; historical A02/A08 evidence was recovered, but the output itself does not bind execution explicitly to that commit.
- 06D: reviewer task `01a0887c-0ff5-7303-83ac-7de7484077e5` reported Critical 0, Important 2. The first finding showed the covariance validator did not consume measured base normal/direction/translation and could pass corrupted base references. The second showed inverse-transform B-rep validation omitted complete solid/face topology and boundary/surface-family checks. Review preceded the single geometry commit, so there is no separately identifiable pre-fix commit; the parent closeout records both fixes in `b7054f3`, unresolved 0.

## C. Artifact inventory and risk copies

The final public reconciliation contains 5,150 source instances totaling 22,160,450 bytes across formal worktrees, P0/P1 custody, historical Codex directories, and expanded Release staging. The classifications are:

| Classification | Source instances |
|---|---:|
| `IDENTICAL_DUPLICATE` | 4,026 |
| `ONLY_IN_WORKTREE` | 96 |
| `ONLY_IN_CODEX_HISTORY` | 63 |
| `ONLY_IN_PRESERVATION` | 66 |
| `PRESENT_IN_RELEASE` | 899 |
| `DIVERGENT_REQUIRES_REVIEW` | 0 |

P1 copied all currently located formal output/work evidence for the four Goals omitted from the P0 canonical pass: 03A 80 files, 03B 62, 04B 90, and 05A 576. Total: 808 files / 1,750,345 bytes. Independent recount found 808 destination files and 808/808 source/copy hashes match.

These are two local paths on the same host, not independent off-host protection. Their worktrees therefore remain non-deletable.

## D. Focused 06D reconciliation

The inventory compares the 129-file formal worktree set, 129-file historical Codex set, 129-file P0 custody set, and expanded Release staging. Corresponding formal/historical/preservation files are byte-identical; 18 source instances are identical duplicates and 515 have matching payload bytes in existing Release staging.

This is a custody/integrity result only. No FreeCAD artifact was opened or resaved, no historical experiment was rerun, and no geometric equivalence was inferred from SHA-256.

## E. Manifest enrichment

All 13 P0 Goal manifests now include schema-valid `conversation_provenance` references and required stable preservation `run_id`/`run_role` fields. Schema revision 1.1.0 distinguishes the preservation control-plane run from an unrecovered historical experiment execution; it does not infer or manufacture an experiment run. Relevant manifests also retain recovered failure/fix/reviewer/diagnostic facts and historical test statements with `CHAT` confidence.

Validation result: 13/13 manifests pass `Test-Json` against `evidence_manifest.schema.json`.

The four result domains remain independent: pytest, scientific experiment, human inspection, and provenance. Passing tests or matching hashes are not treated as scientific PASS.

## F. Release decision

P1 created no supplemental Release. Conversation history improved traceability but did not resolve any blocked Goal strongly enough to satisfy run-to-implementation binding and independent-copy gates. Existing Releases remain unchanged and append-only:

- `goal-06a-evidence-aadf996`
- `goal-06c-evidence-58ec93a`
- `goal-06d-evidence-b7054f3`

02C, 03C, 04A, 05B, 05C, and 06B remain `RELEASE_BLOCKED_PROVENANCE`. 03A, 03B, 04B, and 05A remain outside the prior P0 Release scope and now have local custody only. Release count was not used as a success metric.

## G. Repository governance policy

An independent branch `policy/cad-evidence-governance` was created from `origin/main@5c09db9`; the historical policy commit `b42ba9e` is not in its ancestry. The branch changed only `AGENTS.md` and added rules for:

- byte hashes versus tolerance-aware geometry/topology evidence;
- immutable semantic/topology/UI snapshots;
- separation of pytest, scientific, human-review, and provenance results;
- stable Goal/run/commit manifests and recoverable copies;
- preservation of failures and prohibition on bulk `outputs/` publication.

PR [#1](https://github.com/Open-Engineering-Intelligence/dmslicer/pull/1) was non-draft, cleanly mergeable, limited to one file, and had no configured required checks. It was merged to `main` as `cea98d726e9e3a2f69d648db7b2920a48df41b6d`.

## H. Evidence promotion CI requirements

`EVIDENCE_PROMOTION_CI_REQUIREMENTS.md` defines the future fail-closed gate: explicit allowlists, path/sensitivity controls, complete schema validation, separate result domains, tolerance-aware CAD criteria, immutable packages, at least two recoverable copies including independent storage, Release extraction/link/checksum verification, and retention of failures.

P1 specifies but does not implement that gate. It also does not implement the future CAD semantic snapshot or geometry comparator.

## I. Remaining gaps and stop conditions

- Raw conversations and the new risk copies are preserved locally but not independently off-host.
- Historical commands, versions, timestamps, exit codes, or commit bindings absent from durable evidence remain `null`/`U`.
- The six provenance-blocked Goals remain blocked; no chat claim upgrades them.
- Ninety-six source instances remain only in formal worktrees, including 84 current 04A shell-fill files and four records each for 05C, 06B, and DOC01.
- `ARCHIVABLE` remains a custody classification, not deletion authorization. No worktree was deleted or recommended for deletion.

## J. Stable custody record

The private run manifest is `P1_RUN_MANIFEST.json` under run ID `run-p1-historical-ingestion-20260910-02`. Before that manifest was added, the custody run held 868 files / 141,010,188 bytes: 53 raw conversation files, 808 risk-goal files, and seven inventories/summaries. Earlier partial and superseded inventory versions remain preserved rather than overwritten; `PRIVATE_ARTIFACT_INVENTORY.v4.json` is the current inventory pointer.

P1 is complete only as historical ingestion and governance work. It does not claim that every Goal has fully preserved, independently recoverable research evidence.
