# P2 Evidence Promotion and Semantic Snapshot — Closed-Loop MVP Design

Date: 2026-09-10

Status: revised after user review; final approval pending

Goal ID: `P2-EVIDENCE-PROMOTION-SEMANTIC-SNAPSHOT`

## 1. MVP outcome

P2 is complete when three cases run as one stable, inspectable loop:

- Case A: changing only saved UI properties can produce different file bytes while real engineering geometry and fixture semantics remain equivalent.
- Case B: changing the fixture hole radius produces a geometry-different result backed by actual B-rep measurements, never by a hash.
- Case C: the CAD files, three snapshot types, comparison results, test result, and human-review index enter the existing fail-closed promotion flow through an explicit allowlist and stable manifest.

P2 does not become a general CAD comparison system. It implements only the behavior needed to prove these cases.

## 2. Fixed repository state

The formal baseline is `feat/cylindrical-interface-repairability@d65ac32e04115e5627f1c2988fd486e2353cada9`.

The pre-existing P2-MVP branch originally started from old `main`. The approved non-rewriting correction merged the formal baseline into `feat/evidence-promotion-semantic-snapshot` at `83fde03f71553ff0db1752d90405a96176e45f6b`. The required baseline is now an ancestor and the earlier promotion history is preserved.

Work remains in the existing independent worktree:

`D:\Agent\worktrees\dmslicer-p2-evidence-promotion`

The existing PR #3 will be retargeted to `feat/cylindrical-interface-repairability` after verification. It will not be merged by this Goal.

## 3. Invariants retained from governance

The implementation must preserve all of these distinctions:

```text
SHA-256          = BYTE_IDENTICAL or BYTE_DIFFERENT
B-rep comparison = GEOMETRY_EQUIVALENT, GEOMETRY_DIFFERENT,
                    or GEOMETRIC_EQUIVALENCE_NOT_PROVEN
semantic binding = SEMANTIC_EQUIVALENT, SEMANTIC_DIFFERENT,
                    or SEMANTIC_EQUIVALENCE_NOT_PROVEN
saved UI state   = UI_SAME, UI_DIFFERENT, or UI_COMPARISON_NOT_PROVEN
```

`BYTE_DIFFERENT + GEOMETRY_EQUIVALENT + SEMANTIC_EQUIVALENT + UI_DIFFERENT` is valid.

JSON records evidence and results. JSON equality, JSON hashes, CAD hashes, bounding-box equality, and volume equality are not geometry oracles.

Every tolerance has a finite numeric value, an explicit unit, a role, and a source. Unknown or unsupported facts are recorded as `UNKNOWN`, `UNSUPPORTED`, or `NOT_PROVEN`, never fabricated.

## 4. Minimal implementation shape

P2 adds two focused production modules to the existing `evidence_promotion` package:

1. `cad_evidence.py` validates demo requests, launches FreeCAD with argument lists, parses the three snapshot artifacts, compares explicit fixture semantics and UI state, and orchestrates the demo package.
2. `freecad_cad_evidence.py` runs inside FreeCAD, creates/reopens the fixture, extracts actual B-rep/topology measurements, and performs the fixture-specific geometry comparison.

The existing promotion modules remain responsible for allowlisting, path and secret checks, copy verification, collision refusal, failure preservation, manifest generation, and custody status. They are extended only enough to accept proven CAD result artifacts.

No service, plugin, database, entity repository, adapter hierarchy, registration engine, or event bus is introduced.

## 5. Versioned evidence schema

One new draft-2020-12 schema, `cad_evidence.schema.json`, defines four artifact types with a required `artifact_type` discriminator:

- `geometry_semantic_snapshot`;
- `topology_snapshot`;
- `ui_state_snapshot`;
- `geometry_comparison`.

Using one schema avoids shared-definition duplication while preserving three separate immutable snapshot JSON files and a separate comparison JSON file.

All numeric measurements use `{ "value": <finite number>, "unit": <unit> }`. P2 uses only `mm`, `mm2`, `mm3`, `rad`, `count`, and `unitless` where applicable. Governed objects reject unknown fields. JSON output uses sorted keys, stable fixture-defined ordering, UTF-8, and a trailing newline.

The historical `evidence_manifest.schema.json` v1.1.0 and all 13 P0/P1 manifests remain unchanged. Tests validate them against their existing schema. The current P2 request/manifest schemas advance compatibly and do not rewrite historical manifests.

## 6. Three snapshot types

### 6.1 `geometry_semantic_snapshot`

For the single P2 fixture body it records:

- fixture component ID and input provenance;
- solid, shell, face, edge, and vertex counts;
- area in `mm2`, volume in `mm3`, and bounding box in `mm`;
- shape validity and shell closedness;
- the explicit fixture interface role `through_hole_wall`;
- the allowed transform, which is `IDENTITY` for Cases A and B;
- length unit `mm`.

It does not infer general engineering semantics or build reusable entity correspondence.

### 6.2 `topology_snapshot`

For the same body it records:

- topology counts;
- connected solid count;
- validity and closedness;
- through-hole count only when the fixture's analytic cylindrical wall selection is unique.

Manifold state, general adjacency, and complex boundary-loop or hole inference are `UNKNOWN` unless FreeCAD exposes a reliable value needed by this fixture. OCC list indexes are not persisted as identities.

### 6.3 `ui_state_snapshot`

For the fixture object it records the saved values needed by Case A:

- visibility;
- shape color;
- transparency.

Display mode and camera are recorded only if the generated FCStd exposes stable values. Otherwise they are `UNSUPPORTED` with a reason.

The UI variant is created and saved as a new FCStd with a GUI-capable FreeCAD batch process. Geometry is then reopened independently through `FreeCADCmd`. If saved UI state cannot be created or read reliably, the run reports `UI_COMPARISON_NOT_PROVEN`; it does not synthesize a passing result.

## 7. Fixture and cases

The fixture is one deterministic solid: a rectangular block with one through-hole. Dimensions and units are declared in the request and evidence.

Three new artifact sets are generated without overwriting each other:

- `original`: nominal block and hole radius;
- `ui_only_changed`: the same shape with changed color, transparency, and visibility;
- `geometry_changed`: the same block with a different hole radius.

Each set includes FCStd, BREP, and STEP where the exporter supports them. Geometry truth comes from the reopened B-rep/shape, not the display tessellation.

The serialization regression saves the original to a new FCStd, reopens it, and regenerates snapshots. Same or different bytes are both acceptable. Geometry is decided only by the B-rep comparison. A pure-Python test additionally fixes the policy invariant that `BYTE_DIFFERENT` cannot set `GEOMETRY_DIFFERENT`.

## 8. Minimal sufficient geometry comparison

P2 does not require every possible geometry metric. The fixture claim is decided with the smallest sufficient set:

- actual solid count, validity, and closedness;
- face/edge/vertex counts as topology evidence;
- area and volume deltas;
- bounding-box deltas;
- bidirectional B-rep Boolean cut volumes.

Case A is `GEOMETRY_EQUIVALENT` only when the reopened shapes are valid closed single solids, topology counts agree, all scalar deltas are within tolerance, and both Boolean cut volumes are within the declared volume tolerance.

Case B is `GEOMETRY_DIFFERENT` when the real hole-radius mutation produces at least one measured failure. The comparison must report concrete reasons such as nonzero bidirectional cut volume and area/volume deltas exceeding tolerance. `SHA-256 changed` is never a reason.

The fixture tolerances are:

- linear/bounding-box tolerance: `0.001 mm`;
- area tolerance: `0.001 mm2`;
- volume and Boolean-cut tolerance: `0.001 mm3`.

These are P2 fixture policy, not universal defaults. Just-inside, exact-boundary, and just-outside behavior is tested in pure Python. If a Boolean or required measurement cannot be computed, geometry returns `GEOMETRIC_EQUIVALENCE_NOT_PROVEN`.

Hausdorff distance, best-fit registration, arbitrary rigid-transform discovery, general face/edge matching, and mesh comparison are not part of P2.

## 9. Minimal semantic and UI comparison

The semantic binding contains only:

- component role: `fixture_body`;
- selected interface role: `through_hole_wall`;
- allowed transform: `IDENTITY`.

Exact equality of these explicit fields yields `SEMANTIC_EQUIVALENT`. A proven value mismatch yields `SEMANTIC_DIFFERENT`; a missing required field yields `SEMANTIC_EQUIVALENCE_NOT_PROVEN`.

The UI comparison normalizes and compares the supported saved properties. At least one supported difference with otherwise readable snapshots yields `UI_DIFFERENT`. Missing required saved UI values yields `UI_COMPARISON_NOT_PROVEN`.

Neither comparison consumes a file hash as a predicate.

## 10. Evidence promotion closed loop

The existing promotion CLI keeps only its necessary commands:

```text
python -m dmslicer.evidence_promotion demo --output-root <path>
python -m dmslicer.evidence_promotion validate --repository-root <root> --request <json>
python -m dmslicer.evidence_promotion promote --repository-root <root> --request <json>
```

`demo` generates Case A/B artifacts and comparisons in a caller-selected `outputs/` or `work/` staging root. Separate public snapshot/compare commands are not added.

Promotion requires individual-file allowlist entries. It validates the request and manifest, sensitive paths and obvious secrets, tolerance values and units, referenced snapshot/comparison artifacts, distinct result domains, SHA misuse, and failure/reviewer evidence retention. It copies and recounts bytes, never deletes sources, refuses an existing destination, and writes a stable manifest.

Two same-host copies report `LOCAL_TWO_PATHS_NOT_OFF_HOST_REDUNDANCY` and `NOT_FULLY_PRESERVED`. P2 does not implement off-host storage or claim `FULLY_PRESERVED`.

## 11. Human-review demo and self-evidence

The minimal review package contains:

- original, UI-only, and geometry-changed FCStd/BREP/STEP files;
- the three snapshot types for each applicable case;
- Case A and Case B comparison JSON;
- `VIEW_INDEX.md` with relative artifact links and inspection order;
- `HUMAN_REVIEW.md` explaining machine geometry evidence versus display evidence.

P2's own stable evidence contains only:

- one promotion manifest and copy inventory;
- pytest/JUnit result;
- key CAD files;
- key snapshots and comparisons;
- `VIEW_INDEX.md` and `HUMAN_REVIEW.md`;
- a concise validator/result summary with versions, commands, commit, tolerances, known limitations, and separate result domains.

This is a single evidence run, not a recursive governance system. Temporary requests, probes, and duplicate artifacts remain under `outputs/` or `work/` and are not promoted.

## 12. CI boundary

GitHub Actions runs only portable checks:

- pure-Python schema, policy, promotion, and comparison-boundary tests;
- validation of all 13 historical manifests;
- sensitive-path/secret and SHA-misuse regressions;
- confirmation that `docs/research_v2/` is unchanged from the PR base.

FreeCAD-dependent Case A/B tests run locally with exact FreeCAD/OCCT versions and reproducible commands recorded in evidence. CI does not claim CAD execution it did not perform.

## 13. P2-MVP file scope

Expected production changes are limited to:

- create `src/dmslicer/evidence_promotion/cad_evidence.py`;
- create `src/dmslicer/evidence_promotion/freecad_cad_evidence.py`;
- create `docs/evidence_preservation/schemas/cad_evidence.schema.json`;
- modify the existing request/manifest v2 schemas only for referenced CAD evidence;
- modify `models.py`, `policy.py`, `promotion.py`, and `cli.py` only where the closed loop requires it;
- modify `__main__.py` only if command dispatch requires it;
- minimally update the existing evidence-promotion documentation and CI script/workflow;
- add the final allowlisted stable P2 evidence package.

No existing 07A implementation module is modified unless an integration defect makes that unavoidable and is separately recorded as a design deviation.

## 14. P2-MVP test scope

New focused tests are limited to:

- `test_cad_evidence_schema.py`: three snapshot types, comparison schema, units, unknown states, and deterministic serialization;
- `test_cad_evidence.py`: semantic/UI comparison and threshold boundaries;
- `test_cad_demo.py`: actual FreeCAD Case A, Case B, and serialization/reopen behavior;
- targeted additions to `test_policy.py`, `test_promotion.py`, and `test_cli.py` for CAD artifact admission and the single `demo` command;
- the inherited full suite to prove 07A and historical behavior remain intact.

Required regressions are:

- same and different bytes remain byte-only results;
- UI-only mutation -> geometry equivalent, semantic equivalent, UI different;
- hole-radius mutation -> geometry different with actual B-rep measurement reasons;
- serialization byte difference cannot drive geometry failure;
- tolerances just inside, on, and just outside the boundary;
- missing identity, unit, allowlisted file, or required evidence blocks promotion;
- absolute/sensitive paths, secret patterns, SHA-as-geometry logic, and overwrite attempts block promotion;
- declared failure evidence survives promotion;
- all 13 historical manifests still validate.

## 15. Explicitly deferred work

P2 defers:

- general CAD entity correspondence and persistent subshape identity;
- arbitrary face/edge deterministic descriptor matching;
- general adjacency, manifold, boundary-loop, and hole inference;
- Hausdorff-style metrics and mesh-derived geometry proof;
- arbitrary transforms, transform discovery, and best-fit registration;
- semantic roles beyond this fixture's component/interface/identity-transform binding;
- standalone public snapshot/compare CLIs;
- universal CAD-format adapters or framework abstractions;
- cloud FreeCAD runners, object storage, database services, dashboards, and full historical migration;
- recursive self-evidence promotion or governance-of-governance machinery.

Deferred fields are omitted when non-applicable or recorded as `UNKNOWN` when applicable but unproven.

## 16. Acceptance and stop conditions

P2-MVP is accepted only when artifact-backed evidence proves:

```text
Case A:
  geometry = GEOMETRY_EQUIVALENT
  semantic = SEMANTIC_EQUIVALENT
  UI       = UI_DIFFERENT
  byte     = BYTE_IDENTICAL or BYTE_DIFFERENT, with no geometry role

Case B:
  geometry = GEOMETRY_DIFFERENT
  reason   = actual B-rep/topology/area/volume/Boolean measurement

Case C:
  promotion = LOCAL_PACKAGE_CREATED
  allowlist = explicit files only
  collision = refused
  custody   = LOCAL_TWO_PATHS_NOT_OFF_HOST_REDUNDANCY
  preservation = NOT_FULLY_PRESERVED
```

Tests, scientific Case A/B results, and human inspection are reported separately. If geometry, semantics, or UI cannot be proven, the corresponding `NOT_PROVEN` result is recorded and P2 is not reported complete.

After implementation, review, evidence, push, and PR retargeting, P2 stops. It does not merge the PR or begin 07A/07B work.
