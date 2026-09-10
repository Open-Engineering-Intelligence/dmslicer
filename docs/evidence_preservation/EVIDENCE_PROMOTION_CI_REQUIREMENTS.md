# Evidence Promotion CI Requirements

Status: requirements only. P1 does not implement the promotion gate or retroactively rerun historical experiments.

## Purpose

The future gate promotes an explicit allowlist of run artifacts from temporary `outputs/` or `work/` staging into stable Goal evidence. Promotion must be deterministic, fail closed, preserve failures, and produce enough machine-readable evidence for another environment to inspect the input, configuration, decisions, outputs, and validation.

## Required inputs

The gate must accept, without guessing:

- `goal_id`, `run_id`, source branch, `implementation_commit`, optional `policy_commit`, and parent baseline or merge-base;
- an explicit artifact allowlist rooted beneath approved staging directories;
- input fixture IDs and paths, with SHA-256 labeled byte integrity only;
- FreeCAD, OCCT, Python, and pytest versions;
- exact commands, exit codes, execution timestamps, and working-directory identity;
- every tolerance value, unit, role, and source;
- declared software-test, scientific-experiment, human-inspection, and provenance results;
- known mismatches, failure commits, fix commits, reviewer findings, and unresolved gaps; and
- destination URIs for Git, Release/object storage, and independent custody.

Missing required provenance must remain `null`/`U` and must block publication when the absent field is part of the Release binding. The gate must not infer execution commits from directory names, modification times, nearby Git commits, or chat text.

## Allowlist and path controls

The gate must:

1. Resolve every selected source and destination to an absolute path and reject traversal, symlink escape, broad repository-root selection, and unexpanded variables.
2. Read only explicitly allowlisted files; `outputs/**` and `work/**` cannot be promoted wholesale.
3. Reject secrets, credentials, private absolute paths, usernames, temporary Codex locations, environment values, and duplicate junk from public manifests/packages.
4. Preserve repository-relative logical paths or stable artifact IDs so references survive extraction and relocation.
5. Refuse overwrite. A changed artifact requires a new `run_id`, package version, and immutable manifest entry.

## Manifest validation

Before publication, CI must validate the Goal manifest against the repository schema and require stable identity `goal_id + implementation_commit + run_id`. It must verify:

- branch and implementation commit exist and have the asserted ancestry;
- `policy_commit`, if present, is separately labeled and is not substituted for an experiment commit;
- every selected artifact has kind, path/URI, size, byte-integrity digest, validation role, and confidence;
- JUnit, validator, STEP/BREP/FCStd, `VIEW_INDEX`, and `HUMAN_REVIEW` references are present when applicable;
- failures, mismatches, early failing tests, rejection scenarios, and review findings remain referenced;
- results are recorded in four independent domains: pytest, scientific experiment, human inspection, and provenance; and
- `CHAT` facts are never automatically promoted to `L` or `GH`.

## CAD evidence rules

CI must reject language or fields that use SHA-256, a stable fingerprint, FCStd save identity, or matching serialized bytes as geometric-equivalence proof. SHA-256 may verify input/copy/download integrity and byte duplication only.

A geometric-equivalence claim must cite artifact-backed comparisons appropriate to the claim, including applicable topology counts, adjacency/components/holes/closure, surface and boundary families, areas, volumes, bounding boxes, normals/local directions, allowed rigid transforms, bidirectional distances or Boolean differences, and explicit tolerance values with units.

Opening/closing snapshots must be new immutable artifacts named by role: `geometry_semantic_snapshot`, `topology_snapshot`, and `ui_state_snapshot`. UI/color/visibility/camera changes must remain separate from geometry evidence. The original CAD file must never be overwritten by inspection.

## Copy and publication gates

Promotion succeeds only when:

1. Source-to-custody copies match byte-for-byte and every selected file is independently recounted.
2. At least two recoverable copies exist, with at least one off-host or in a separately controlled store; two paths on one disk are not independent protection.
3. A candidate Release package is extracted into a fresh directory; internal paths, checksums, manifests, and `VIEW_INDEX` links validate there.
4. Release target/tag matches the implementation commit and the package manifest.
5. Remote asset name, size, and digest are re-read after upload.
6. Existing Releases and assets are never replaced in place. Corrections create a versioned supplemental Release with `supersedes`/`superseded_by` metadata.
7. Blocked Goals remain blocked. Publication count is never used as a success metric.

## Required outputs

The gate must emit:

- a schema-valid Goal manifest;
- a source-to-copy inventory with sizes, byte digests, and verification status;
- a public-safe Release inventory;
- a package extraction/link/checksum validation result;
- separate pytest, scientific, human-review, and provenance statuses;
- a machine-readable list of retained failures and unresolved gaps; and
- a worktree custody decision of `ARCHIVABLE` or `NOT_ARCHIVABLE`, which does not itself authorize deletion.

Until these checks are implemented and pass for a Goal, P1 does not claim full evidence preservation and does not recommend deleting its historical worktree.
