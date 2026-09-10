# DM-Slicer Evidence Preservation

This directory records the public, sanitized control plane for DM-Slicer research evidence preservation. It does not replace geometry evidence, historical outputs, or the frozen research contract in `docs/research_v2/`.

## Result domains

Every Goal manifest keeps these results independent:

- `software_pytest`: software test execution only.
- `scientific_experiment`: the scientific result, including mismatches and retained failures.
- `human_inspection`: the state and findings of manual CAD inspection.
- `provenance`: confidence that inputs, implementation, execution, outputs, validation, and review are bound together.

A passing pytest result does not imply a passing scientific experiment or completed human inspection.

## Confidence labels

- `GH`: verified from Git/GitHub commit, tree, tag, Release, or PR state.
- `L`: verified from a local artifact or local Git object during preservation.
- `CHAT`: present only in a historical task record and not promoted to local or GitHub fact.
- `U`: unknown, missing, or not safely inferable.

Historical execution fields are never inferred from file modification times, chat context, directory names, or adjacent commits. Unknown values remain JSON `null` with confidence `U`.

## Public and private records

Public files use repository-relative paths, Release asset names, stable artifact IDs, GitHub URIs, and SHA-256 values. They must not contain usernames, Codex task paths, secrets, environment-variable values, or private absolute paths.

Exact source locations and source-to-preserved-copy mappings are stored separately in the non-Git local custody inventory. That private inventory is required for custody operations but is not a public Release asset.

## Integrity and geometry

SHA-256 is used only for file and download integrity. It is not a B-rep geometry-equivalence test. Geometry conclusions must cite actual criteria such as B-rep validity, closure, topology, bidirectional cut/common results, minimum distance, area, volume, and explicit tolerances with units.

FreeCAD open/close/save operations may change serialized bytes without proving a geometric change. Such a hash difference does not block historical preservation and does not justify rerunning or deleting evidence. A future cross-version geometry-equivalence protocol must be designed in a separate task/branch around a semantic snapshot and explicit unit-bearing tolerance comparisons. This P0 phase does not implement that protocol or rerun historical experiments.

## Release history

Evidence Releases are append-only by policy, not inherently immutable. Each Release/tag is versioned and bound to the supported implementation commit. Published assets are not replaced in place. A correction creates a new Release version and records `supersedes` and `superseded_by` relationships.

## Documents

- `P0_PRESERVATION_INVENTORY.md`: prioritized evidence and preservation state.
- `BRANCH_DEPENDENCY_DAG.md`: command-backed ancestry and integration dependencies.
- `RELEASE_UPLOAD_INVENTORY.md`: Release gates, files, sizes, SHA-256 values, and outcomes.
- `SENSITIVITY_DUPLICATION_CHECK.md`: public-content and staging selection checks.
- `WORKTREE_CUSTODY_REPORT.md`: worktree lifecycle classification without deletion.
- `HUMAN_INSPECTION_POLICY_PR.md`: isolated policy integration evidence.
- `P0_PRESERVATION_REPORT.md`: final A–J preservation report.
- `manifests/goal-*.json`: machine-readable per-Goal evidence manifests.
