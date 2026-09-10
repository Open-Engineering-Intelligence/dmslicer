# AGENTS.md

## Repository purpose

This is a research-first repository. Every change must preserve the distinction between research hypotheses, geometric evidence, semantic decisions, and implemented behavior.

## Geometry and semantics

1. Never treat a derived display mesh as geometry truth.
2. Keep STEP/B-rep geometry authority distinct from every derived mesh used for display, sampling, acceleration, or export.
3. Legacy AMF algorithms are baselines and historical references only.
4. A candidate relation is not a confirmed geometry relation.
5. Geometry truth is not semantic activation.
6. `MaterialRegion` is not `InterfaceSourceBoundary`.
7. A gradient semantic role is not a volumetric field.

## Provenance and reproducibility

8. Stable provenance is mandatory for imported and derived entities.
9. Every tolerance must be explicit, carry a unit, and be recorded in the relevant manifest.
10. Do not use random UUIDs, process counters, or list indexes as persistent geometry identities.
11. Every implementation must emit machine-readable evidence sufficient to inspect its inputs, configuration, decisions, and outputs.
12. Every research claim must map to a test, benchmark, or experiment.

## Scope discipline

13. Do not perform unrelated refactors.
14. Do not build large plugin, service, repository, adapter, factory, or event-bus abstractions merely because they may be useful later.
15. Every Goal must define explicit Scope, Acceptance Criteria, and Stop Conditions.

## Frozen research contract

16. Treat `docs/research_v2/` as DESIGN FREEZE input and do not modify it by default.
17. Record design deviations in new evidence documents; do not silently rewrite the frozen contract to match an implementation.
18. Any future legacy-code migration must be evaluated module by module, preserve explicit source provenance, and be authorized as a dedicated migration task. Never copy the legacy source tree wholesale.

## CAD hashes and geometric equivalence

19. Use SHA-256 only for file-level byte integrity: preserving a source-file copy, verifying a Release asset upload or download, or detecting transmission or overwrite corruption.
20. Never use SHA-256 as evidence that BREP, STEP, or FCStd artifacts are geometrically equivalent. An `input_sha256` or any other file hash records byte integrity only.
21. Opening, closing, or saving a file in FreeCAD may change serialization, metadata, object ordering, display state, or precision representation. Such byte changes do not by themselves establish a geometry change and must not by themselves trigger a rerun of historical experiments.
22. Confirm geometric equivalence with artifact-backed geometry and topology comparisons, recording every applied tolerance with an explicit value and unit.
23. As applicable to the artifacts and claim, a geometry comparison must record:
    - solid, shell, face, edge, and vertex topology;
    - adjacency, connected components, hole counts, and closure;
    - area, volume, and bounding boxes;
    - interface normals, local directions, and allowed rigid transformations;
    - bidirectional distances, Hausdorff-style metrics, or Boolean differences; and
    - the actual tolerance value and tolerance unit used.
24. Keep UI and display-layer changes separate from geometry evidence, including color, visibility, camera or view direction, rendering mode, display caches, and non-geometric metadata.
25. Future CAD review workflows must create separate, immutable snapshots both when opening and when closing an artifact: `geometry_semantic_snapshot`, `topology_snapshot`, and `ui_state_snapshot`. Each snapshot must be a new evidence artifact and must never overwrite the original CAD file.
26. Use stable geometry fingerprints only for fast lookup or deduplication; they do not replace an actual tolerance-aware geometry comparison.
27. Record pytest PASS, matching file hashes, and scientific experiment PASS as separate results.

## Research evidence persistence and output paths

28. Codex chat content must never be the sole copy of critical research evidence.
29. Use `outputs/` and `work/` only for temporary run output, debugging, probes, failed process material, or rerun staging. Neither directory may be the sole storage location for a Goal's final evidence.
30. Every Goal must have a stable, traceable evidence manifest that associates at least:
    - `goal_id`;
    - `run_id`;
    - branch;
    - `implementation_commit`;
    - `policy_commit`, when applicable;
    - parent baseline or merge-base;
    - input fixture;
    - input SHA-256, for byte-integrity provenance only;
    - FreeCAD, OCCT, Python, and pytest versions;
    - command;
    - exit code;
    - execution timestamp;
    - tolerance value and tolerance unit;
    - JUnit, validator, STEP/BREP/FCStd, `VIEW_INDEX`, and `HUMAN_REVIEW` URI or path;
    - reviewer finding;
    - failure commit;
    - fix commit;
    - known mismatch or failure mode;
    - actual geometry validation criteria; and
    - evidence confidence: `GH`, `L`, `CHAT`, or `U`.
31. Prefer the stable layout `evidence/<goal_id>/<run_id>/`. Small manifests, policies, summaries, and review notes may enter Git; large CAD, JUnit, BREP, FCStd, and self-contained review packages should enter a GitHub Release or controlled object storage.
32. A date is metadata only and cannot be the sole evidence identity. Stable identity must include at least `goal_id + implementation_commit + run_id`.
33. Preserve failures, mismatches, early failing tests, reviewer findings, and pre-fix material. Never delete or overwrite them merely to make a result green.
34. Treat historical chat only as `CHAT` provenance: it may show that a result was recorded during a prior task, but it cannot be promoted automatically to a current-environment validation result and cannot replace an artifact-backed validator or geometry comparison.
35. A future project script or CI gate, rather than an Agent's ad hoc memory, must automate evidence promotion and integrity checks by:
    - reading only allowlisted artifacts from `outputs/`;
    - copying them to a stable evidence path;
    - generating the manifest;
    - recording the source commit, versions, command, tolerances, and URIs;
    - verifying at least two recoverable copies;
    - checking that SHA-256 has not been used as geometric-equivalence evidence;
    - checking for local temporary paths, sensitive information, and duplicate junk data; and
    - checking that failure evidence remains preserved.
36. Until a stable manifest and recoverable copies exist, an Agent must not claim that a Goal's research evidence is fully preserved and must not recommend deleting historical worktrees.
37. Never add all of `outputs/` indiscriminately to Git, Git LFS, or a Release. Select artifacts by Goal and by an explicit allowlist.

## External actions

Without separate authorization, do not push, merge, release, publish a package, configure a GitHub remote, or create a GitHub repository.
