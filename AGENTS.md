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

## Geometry equivalence and hash policy

1. Raw FreeCAD/OCCT B-rep serialization hashes, `exportBrepToString()` hashes,
   STEP export hashes, and shape digests prove only exact representation identity.
   A mismatch proves only that the representation differs.
2. Never use a raw or quantized geometry hash as the final predicate for geometry
   equivalence, patch deduplication or correspondence, component/FaceSet matching,
   STEP round-trip acceptance, corrected/reference equality, scientific validation,
   or cross-process geometry repeatability.
3. Prove geometry equivalence with actual B-rep operations and declared unit-bearing
   tolerances: validity/closedness, area or volume, bidirectional `cut`, actual common,
   minimum distance, support surface, boundary/component/hole topology, and provenance
   as applicable. Apply an inverse rigid transform before comparing transformed shapes.
4. Compare continuous values directly against declared `mm`, `mm²`, `mm³`, or angle
   epsilons. Do not round or quantize values and then hash them into a binary decision.
5. If actual B-rep equivalence cannot be proved, report
   `GEOMETRIC_EQUIVALENCE_NOT_PROVEN` or `UNSUPPORTED`; never substitute a hash mismatch.
6. File hashes remain required for input integrity, exact-byte evidence, caching, and
   debugging, but those uses must stay separate from geometric acceptance.

## Human Inspection Deliverables

1. Every completed CAD / geometry Goal must provide human-inspectable artifacts
   in addition to machine-readable evidence.

2. `pytest PASS`, validator PASS, or JSON evidence PASS alone is not a complete
   human-review deliverable.

3. STEP/B-rep operations and machine validation remain authoritative geometry
   truth. FCStd, screenshots, review packages, and visualization are for human
   inspection only and must never replace geometry truth.

4. Every principal success scenario must provide an `operation_debug.FCStd` or an
   explicitly justified equivalent human-viewable artifact.

5. Principal rejection scenarios should also provide a human-viewable artifact
   when the geometric rejection is meaningful to inspect. Do not create an FCStd
   for every trivial NaN/missing-input unit test.

6. FreeCAD debug documents should use numbered, semantically meaningful tree
   groups where applicable, such as:

   00_Input
   01_Originals
   02_Selected_Interface
   03_Precommit_Preview
   04_Corrected_Assembly
   05_Common_Patches
   06_Remaining
   07_Components
   08_Boundaries
   09_Fused_Result
   10_Rejection_Evidence

   Only create groups relevant to the current Goal.

7. Opaque names such as `Shape001` or `Compound003` must not be the primary
   human inspection interface. Labels/groups must communicate engineering
   meaning.

8. Every formal geometry Goal output root must provide a human-oriented
   `VIEW_INDEX.md`.

9. `VIEW_INDEX.md` must number the principal scenarios and state for each:

   - scenario name;
   - FCStd path;
   - associated STEP/BREP paths;
   - which FreeCAD tree groups to toggle;
   - what geometric behavior should be visible;
   - what visible condition would indicate a likely failure.

10. When practical, provide a `HUMAN_REVIEW/` directory containing or clearly
    indexing only the artifacts needed for manual inspection.

11. A convenience `*_HUMAN_REVIEW.zip` may be produced when useful. It is not
    geometry truth and must not become validator input.

12. Before completion, reopen every principal FCStd and verify:

    - the file opens;
    - required groups exist;
    - required objects exist;
    - default visibility is useful;
    - success, rejection, and DISPLAY_ONLY preview states cannot be confused.

13. Preview geometry must be explicitly marked:
    `DISPLAY_ONLY`
    and
    `NOT_EXECUTED`.

14. Final Codex completion reports for CAD/geometry Goals must include a
    numbered `Human Inspection` section.

    For every principal scenario it must give:

    - exact absolute path;
    - repo-relative/output-relative path where applicable;
    - what file to open;
    - which groups to inspect in order;
    - what the human reviewer should observe.

15. If the Codex interface supports a reliable clickable local/workspace
    artifact link, include it. Otherwise do not invent a link; provide the exact
    absolute path.

16. File SHA-256 remains valid for byte integrity only. Human review artifacts
    remain subject to the existing Geometry Equivalence and Hash Policy.

17. Generated artifacts remain governed by `.gitignore` and artifact policy. Do
    not `git add -f` an entire output directory merely to satisfy human
    inspection.

18. Human inspection requirements must not trigger unrelated refactoring, a GUI
    framework, plugin architecture, or changes to geometry truth.

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

## External actions

Without separate authorization, do not push, merge, release, publish a package, configure a GitHub remote, or create a GitHub repository.

## Completion Git Policy

1. Every completed and verified Goal must leave its working tree clean.
2. Every formal source, test, documentation, or fixture change must be recorded in a local Git commit.
3. This repository has ongoing authorization for remote synchronization: after completing a stage or Goal, push the current feature branch to `origin`.
4. Never merge `main` automatically.
5. Never force-push.
6. Whether generated outputs are committed remains governed by `.gitignore` and the repository artifact policy; remote synchronization does not mean uploading every file.
7. If a task fails or reaches a STOP condition, do not present unverified results as a completed commit. A WIP branch may be preserved when needed, but it must be labeled explicitly.
8. Every completion report must include the branch, local HEAD, remote branch SHA, push status, and working tree status.
