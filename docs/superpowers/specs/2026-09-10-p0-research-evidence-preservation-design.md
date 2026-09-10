# P0 Research Evidence Preservation Design

## Goal

Preserve the highest-risk DM-Slicer research evidence without rerunning or rewriting historical experiments, publish only provenance-qualified canonical evidence, and establish a traceable basis for later main integration and worktree lifecycle decisions.

## Scope

This preservation phase covers Goals 02C, 03A, 03B, 03C, 04A, 04B, 05A, 05B, 05C, 06A, 06B, 06C, and 06D. It also records DOC01 ancestry where needed by the branch report. The highest-priority binary evidence is 04A A02/A08, 03C A12, 05C recovery and mismatch evidence, 06A/06B failure and validation evidence, 06C artifact-backed validation and reviewer history, and 06D geometry and human-review evidence.

This phase does not start 07A, merge any 02C–06D feature branch, merge DOC01, rebase or rewrite historical branches, delete worktrees, clean `outputs/` or `work/`, overwrite prior artifacts, or rerun historical experiments merely to fill missing provenance.

## Architecture

The preservation system has three deliberately separate layers:

1. Public Git documentation contains sanitized, machine-readable evidence manifests and human-readable reports. Public files use repository-relative paths, stable artifact identifiers, Release asset names, GitHub URIs, and SHA-256 digests. They do not contain usernames, Codex task directories, secrets, environment-variable values, or private absolute paths.
2. A private local custody root at `D:\Agent\evidence-preservation\dmslicer\p0-20260910` records exact source locations, copies canonical evidence without modifying its source, and stores source-to-copy SHA-256 verification. This directory is not added to Git.
3. GitHub Releases contain curated, versioned evidence assets bound to the implementation commit actually supported by the evidence. Published assets are append-only: corrections create a new version with `supersedes` and `superseded_by` metadata instead of replacing an existing asset.

SHA-256 is used only for byte/download integrity. Geometry validation remains expressed through the recorded B-rep operations, topology, distance, area, volume, validity, closure, and tolerance criteria present in the historical evidence.

## Public document structure

`docs/evidence_preservation/` contains:

- `README.md`: confidence vocabulary, public/private separation, and navigation.
- `evidence_manifest.schema.json`: required fields and result-domain separation.
- `manifests/goal-02c.json` through `goal-06d.json`: one public manifest per formal Goal.
- `P0_PRESERVATION_INVENTORY.md`: preserved, single-copy, missing, and unrecoverable evidence.
- `BRANCH_DEPENDENCY_DAG.md`: real Git ancestry and merge-base evidence.
- `RELEASE_UPLOAD_INVENTORY.md`: proposed and completed Release assets, sizes, SHA-256, source aliases, target commits, and gate decisions.
- `SENSITIVITY_DUPLICATION_CHECK.md`: secret/path scan and duplication decisions.
- `WORKTREE_CUSTODY_REPORT.md`: `NOT_ARCHIVABLE` or `ARCHIVABLE` status with criterion-by-criterion evidence.
- `HUMAN_INSPECTION_POLICY_PR.md`: policy branch, cherry-pick, diff, PR, checks, and merge evidence.
- `P0_PRESERVATION_REPORT.md`: final A–J report plus requested execution totals.

Unknown historical fields are represented as JSON `null` with confidence `U`. File timestamps, task summaries, and contextual clues are not promoted into execution timestamps, version facts, commands, exit codes, or commit bindings.

## Manifest model

Every Goal manifest records:

- identity: `goal_id`, branch, implementation commit, policy commit, parent baseline, and merge-base;
- inputs: fixture identifiers, stable paths or asset names, and SHA-256;
- environment: FreeCAD, OCCT, Python, and pytest versions;
- execution: command, exit code, and execution timestamp;
- tolerances: value, unit, role, and source evidence;
- artifacts: JUnit, validator, STEP, BREP, FCStd, VIEW_INDEX, HUMAN_REVIEW, reviewer findings, and Release URIs;
- history: failure commit, fix commit, known mismatch or failure mode;
- validation: actual geometry criteria and explicit statement that hashes are not geometry-equivalence criteria;
- four independent result domains: software/pytest, scientific experiment, human inspection, and provenance confidence;
- confidence labels: `GH`, `L`, `CHAT`, or `U` per material assertion.

The 05B manifest preserves native mismatch `16/90` and normalized mismatch `1/90`. The 05C manifest preserves the retained area-method exceedance. The 03C, 06B, and 06C manifests preserve their failure and reviewer/fix histories. A pytest pass never changes a scientific mismatch into a scientific pass.

## Canonical preservation workflow

For each selected P0 source:

1. Enumerate files without changing the source.
2. Calculate source size and SHA-256.
3. Copy to a new versioned custody location with source-relative structure preserved.
4. Calculate the preserved-copy SHA-256 and require an exact match.
5. Record the mapping in private `LOCAL_CUSTODY_INVENTORY.json` and a sanitized public manifest.
6. Stop only the affected artifact if reading, copying, or hashing fails; do not delete or repair the source.

The 04A historical Codex task directory is processed first. No existing archive or artifact is overwritten.

## 06D self-contained human-review package

The new asset is named `goal-06d-human-review-v2-b7054f3.zip`. It contains:

- `README.md`;
- `VIEW_INDEX.md` using only package-relative links;
- `D01/operation_debug.FCStd`, `D02/operation_debug.FCStd`, and `D03/operation_debug.FCStd`;
- each case's `corrected_assembly.step` and `fused.step`;
- `REVIEWER_AND_FAILURE_NOTES.md` distinguishing known findings, fixes, remaining uncertainty, pytest result, scientific result, and human-inspection status.

The historical `06D_HUMAN_REVIEW.zip` remains unchanged. Validation extracts the V2 archive to a newly created independent temporary directory, parses every required file reference from `VIEW_INDEX.md`, and proves each reference resolves inside the extraction root. The temporary validation directory is not used as evidence and may be left in place if safe cleanup would be ambiguous.

## Release gates

Each formal Goal receives a proposed Release identity. Publication is allowed only when all of these are true:

- the implementation commit supported by the evidence is explicit;
- artifact-to-commit provenance is sufficiently supported and not guessed;
- every source, size, SHA-256, and target Release is enumerated;
- secret, personal-path, and temporary-path scans pass for public assets;
- obvious duplicate reruns and caches are excluded while failure/mismatch evidence remains;
- the public manifest and staged assets agree;
- the Release target is the supported implementation commit, not a later policy-only commit.

Failures are recorded as `RELEASE_BLOCKED_PROVENANCE` or the specific failed gate while other Goals continue. Goal 02C remains blocked unless existing evidence independently proves a binding to final commit `b646027`; no rerun is authorized. Goal 06D binds to `b7054f3`; `b42ba9e` is recorded only as policy history.

## Branch dependency report

The DAG is generated from `git rev-parse`, `git show --format=%P`, `git merge-base`, and `git merge-base --is-ancestor`. Goal numbering is never treated as ancestry. The report must show that 03A's artifact-packaging commit `a1fc48b` is a sibling continuation from `bd831be`, while 03B starts from `bd831be`; therefore 03B–06D do not inherit `a1fc48b`.

No batch research-branch integration plan or merge may occur before the DAG is complete.

## Human Inspection policy integration

Policy integration uses a separate branch created from the then-current `main`. It cherry-picks source commit `b42ba9e`, verifies that the complete PR diff contains only the intended `AGENTS.md` policy and no implementation or evidence artifacts, pushes that branch, creates a PR, waits for checks and review state, and merges only if all authorized gates pass. A conflict, extra file, failed check, or unresolved review finding blocks the merge. The 06D implementation history is never pulled into the policy branch.

## Worktree lifecycle

No worktree is deleted in this phase. A worktree is marked `ARCHIVABLE` only when its implementation exists remotely, implementation commit is explicit, manifest is complete, canonical evidence is in a remote Release or approved persistent store, SHA-256 is verified, an independent local source or preserved copy remains, failures and mismatches are preserved, applicable human review is preserved, and no provenance blocker remains. Otherwise it remains `NOT_ARCHIVABLE` with the failed criteria listed.

## Acceptance criteria

- The current checkout remains untouched apart from its pre-existing `work/` state.
- The preservation branch is based exactly on `main@5c09db91a5a2cf363beb4750384f532a3308f995`.
- All 13 Goal manifests parse as JSON and contain every required field.
- Public files pass scans for the prohibited local user path, username, Codex task path, token/key patterns, and secret-looking environment values.
- Every preserved file has source and copy SHA-256 values that match.
- Failure and mismatch evidence is included, not filtered out.
- The new 06D package passes isolated extraction and internal-link validation.
- Each published Release passes its upload manifest gate and is bound to the supported commit.
- The policy PR either merges after all gates pass or records an explicit blocker without broadening its diff.
- `BRANCH_DEPENDENCY_DAG.md` is backed by actual Git commands.
- The final report answers A–J and reports Releases, blockers, PR/merge state, counts, sizes, manifest validation, human-review validation, DAG conclusions, and custody status.
- No worktree, historical output, failure record, or old ZIP is deleted or overwritten.

## Stop conditions

Stop the affected public or destructive action when provenance cannot be bound, a secret/proprietary/personal datum is detected, the policy diff exceeds `AGENTS.md`, a copy/hash verification fails, ancestry materially contradicts the audited model, or an operation risks deleting, overwriting, or rewriting evidence. Preserve the state, record the blocker, and continue independent safe tasks.
