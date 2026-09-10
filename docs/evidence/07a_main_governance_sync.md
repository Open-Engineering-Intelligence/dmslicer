# P1.5 07A Main Governance Sync Provenance

## Stable identity

- Goal ID: `P1.5-07A-MAIN-GOVERNANCE-SYNC`
- Run ID: `p1.5-07a-main-governance-sync-c7db350-e4b6bb5-run-01`
- Sync branch: `chore/07a-main-governance-sync`
- Pre-sync research tip: `9f0a2bc605f573657f72c406044a01ec1821561b`
- 07A implementation commit: `c7db3501cdfc1971ecb2a4f81e1dcd17eddff18b`
- Main governance tip: `ea617b6b6fa8d074c1c89d6f61513fe4d892cef3`
- Merge commit: `e4b6bb5160878729e91a88d0ccfaf532c7f9bf3a`
- Merge parents, in order: `9f0a2bc605f573657f72c406044a01ec1821561b` and `ea617b6b6fa8d074c1c89d6f61513fe4d892cef3`
- 06D archival ref: `archive/06d-orientation-invariant-planar-correction@b42ba9e7b6efc6dd5a9dd9f7b1584b5a89066f8b`

The merge used a normal, non-rewriting merge. No rebase, reset, amend,
force-push, branch deletion, worktree deletion, or worktree move was used.

## Governance and infrastructure sources

- CAD evidence policy entered `main` through merge commit
  `cea98d7` (PR #1) and is inherited through `ea617b6`.
- P0/P1 evidence-preservation infrastructure entered `main` through the P0
  line ending at `4f77c8a`, the P1 line ending at `05eaeb7`, and merge commit
  `ea617b6` (PR #2).
- The inherited control plane includes the P0 and P1 reports, per-Goal
  manifests, evidence schema, conversation evidence, artifact reconciliation,
  Branch Dependency DAG, CI requirements, and evidence-preservation scripts.
- Historical P0/P1 factual content and the manifest schema were inherited
  without reinterpretation or modification. The schema remains intentionally
  scoped to the historical Goals `02C` through `06D`; this integration record
  does not expand that frozen P0/P1 schema.

## AGENTS.md semantic resolution

Git completed the textual merge without an unmerged-file conflict. The merged
file was nevertheless reviewed semantically. It preserves the research-line
Geometry Equivalence and Hash Policy and all Human Inspection Deliverables,
while also inheriting the current `main` rules for:

- SHA-256 as byte integrity only, never geometry equivalence;
- artifact-backed B-rep/topology comparison with explicit tolerances and units;
- separation of geometry, semantics, UI state, file hashes, pytest results,
  and scientific results;
- immutable geometry-semantic, topology, and UI snapshots;
- stable evidence manifests, failure and reviewer-finding retention, and
  controlled evidence promotion; and
- prohibition on treating chat, `outputs/`, or `work/` as the sole final
  evidence copy.

The overlapping policies are compatible. No still-applicable Human Inspection
rule was removed, and no genuine semantic conflict was found.

## Research implementation preservation

`git diff --exit-code 9f0a2bc HEAD -- src tests benchmarks
docs/implementation` returned zero after the merge. Therefore the 07A source,
tests, tracked benchmark fixtures, and implementation document are unchanged
from the pre-sync research tip. No geometry algorithm or scientific result was
intentionally modified, and no historical experiment was rerun.

## Integration validation

The following integration-scoped validation completed successfully after the
merge:

- 14 non-experiment 07A logic tests passed with Python 3.12.0 and pytest 8.4.2.
- All 21 tests in `test_cylindrical_interface_repair_07a.py` collected
  successfully; the B-rep/experiment-bearing tests were not executed.
- Five inherited PowerShell evidence-preservation scripts parsed without
  syntax errors.
- Seventeen JSON files under `docs/evidence_preservation/` parsed successfully.
- All 13 historical Goal manifests validated against
  `evidence_manifest.schema.json`.
- Nine required governance clauses were present in the merged `AGENTS.md`.
- The inherited evidence directories passed the local sensitive-path/token
  pattern scan.
- Required P0/P1 report, manifest/schema, conversation, reconciliation, DAG,
  CI, and script paths were present.
- `b7054f3 -> b42ba9e -> c7db350 -> 9f0a2bc` ancestry remains reachable from
  the merge commit, and `ea617b6` is also an ancestor of the merge commit.

These are software and repository-integration results only. They do not assert
a new scientific experiment result, geometric-equivalence result, or human CAD
inspection result.

## Conflicts and retained limitations

- Textual conflicts encountered: none.
- Semantic policy conflicts encountered: none.
- Source or test conflicts encountered: none.
- Historical evidence deletions: none.
- The pre-existing canonical 07A worktree remains classified as
  `WORKTREE_PATH_BRANCH_MISMATCH`. This task did not move or rename it; its
  machine-local absolute path remains outside this public provenance document.
