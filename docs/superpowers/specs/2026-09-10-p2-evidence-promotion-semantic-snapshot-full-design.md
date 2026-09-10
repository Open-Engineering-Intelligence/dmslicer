# P2 Evidence Promotion and Semantic Snapshot — Full-Scope Design

Date: 2026-09-10

Status: approved in chat on 2026-09-10; written-spec review pending

Goal ID: `P2-EVIDENCE-PROMOTION-SEMANTIC-SNAPSHOT`

## 1. Purpose and scope

P2 implements the repository CAD-evidence governance as a small, executable, fail-closed pipeline. It extends the already committed P2-MVP promotion control plane with artifact-backed CAD snapshots, a real tolerance-aware B-rep comparison, separate engineering-semantic and UI-state comparisons, regression fixtures, a human-review package, and P2's own promoted evidence.

This design does not refine the 07A cylindrical repair algorithm, start 07B research, create a universal CAD framework, introduce remote orchestration or storage services, migrate all historical artifacts, or modify `docs/research_v2/`.

The permanent separation is:

```text
SHA-256             -> byte identity and copy integrity only
B-rep + topology    -> geometry evidence under explicit unit-bearing tolerances
semantic binding    -> engineering meaning evidence
FCStd GUI state     -> display-state evidence
JSON                -> evidence carrier, never geometry truth
```

## 2. Repository and branch reconciliation

The formal implementation baseline is `feat/cylindrical-interface-repairability@d65ac32e04115e5627f1c2988fd486e2353cada9`.

An earlier P2-MVP branch and PR already existed from `ea617b6`, with 14 promotion-only commits and PR #3 based on `main`. Rewriting or force-pushing that history would violate the Goal. The approved reconciliation is therefore a normal merge of `d65ac32e` into `feat/evidence-promotion-semantic-snapshot`. Merge commit `83fde03f71553ff0db1752d90405a96176e45f6b` makes the formal baseline an ancestor while preserving both histories. The only textual conflicts were `.gitattributes`, `pyproject.toml`, and `src/dmslicer/__init__.py`; their resolutions retain both baseline and promotion requirements.

The existing physical worktree remains:

`D:\Agent\worktrees\dmslicer-p2-evidence-promotion`

The existing PR will be retargeted to `feat/cylindrical-interface-repairability` after implementation and verification. P2 will not merge the PR.

## 3. Architecture

The implementation has five narrow units:

1. `cad_snapshot.py`: host-side request validation, FreeCAD process execution, deterministic evidence loading, and public CLI-facing functions.
2. `freecad_cad_snapshot.py`: FreeCAD/OCCT worker that imports authoritative CAD/B-rep, extracts geometry and topology, applies an explicitly declared rigid transform when authorized, and performs the actual B-rep comparison.
3. `fcstd_ui_state.py`: standard-Python FCStd ZIP/XML reader for serialized GUI state. It never opens or interprets geometry.
4. Four JSON Schemas: geometry-semantic snapshot, topology snapshot, UI-state snapshot, and geometry comparison.
5. The existing `evidence_promotion` package, extended so the promotion request and manifest can carry proven CAD result artifacts without collapsing byte, geometry, semantic, UI, pytest, scientific, human-review, preservation, or publication status.

FreeCAD execution follows the repository's established worker pattern: standard Python writes a request to a temporary directory, invokes `FreeCADCmd` with an argument list, and reads deterministic JSON output. The worker owns no persistent daemon or service.

## 4. Snapshot artifacts

Every snapshot is a new immutable JSON artifact. Opening and closing snapshots use different artifact paths and never overwrite the source CAD file.

### 4.1 Geometry-semantic snapshot

The geometry-semantic snapshot records:

- schema name and version;
- artifact role (`OPENING` or `CLOSING`);
- source artifact ID and public-safe logical path;
- source format and length unit;
- object provenance and stable semantic object key;
- solid, shell, face, edge, and vertex counts;
- surface area in `mm2`, volume in `mm3`, and bounding box in `mm`;
- validity, closedness, and connected-component state;
- applicable interface geometry family, normal/axis, local direction, correspondence identity, and permitted rigid transformation;
- explicit `UNKNOWN`, `UNSUPPORTED`, or `NOT_PROVEN` records when an applicable fact cannot be established.

Semantic fields are supplied by an explicit, schema-validated binding for the fixture. They are not inferred from geometry statistics. The binding supports component identity, selected interface, source/gradient role, correspondence, repair role, and allowed rigid transformation.

### 4.2 Topology snapshot

The topology snapshot records:

- topology counts per object and aggregate;
- connected components;
- shell closedness and shape validity;
- face-edge and edge-vertex incidence;
- boundary-loop and hole counts when they are unambiguous;
- manifold state when the current API can establish it, otherwise `UNKNOWN`;
- deterministic entity descriptors used for matching.

OCC list position, Python object identity, process counters, and random UUIDs are never persistent identities. Object keys derive from explicit semantic role plus source provenance. Face and edge descriptors derive from canonical, unit-bearing analytic family, measures, bounds, centers, and incidence descriptors. These descriptors are lookup/matching aids only. Duplicate descriptors or ambiguous correspondence cause `GEOMETRIC_EQUIVALENCE_NOT_PROVEN`; they never prove equality.

### 4.3 UI-state snapshot

`FreeCADCmd` 1.1.1 exposes no usable `ViewObject` in headless mode, so UI evidence is extracted independently from the FCStd ZIP's GUI serialization rather than guessed from B-rep state. The UI snapshot records, where present:

- object visibility;
- shape/line/point colors;
- transparency;
- display mode;
- camera or view state;
- extraction support status and missing-field reasons.

Absence of `GuiDocument.xml`, a property, or camera state yields `UNSUPPORTED` or `UNKNOWN`. It never changes a geometry result.

## 5. Stable schemas

The following draft-2020-12 schemas are versioned and use `additionalProperties: false` on governed objects:

- `geometry_semantic_snapshot.schema.json`
- `topology_snapshot.schema.json`
- `ui_state_snapshot.schema.json`
- `geometry_comparison.schema.json`

Each measurable value uses an object containing `value` and `unit`. Units are restricted to explicit values used by P2 (`mm`, `mm2`, `mm3`, `rad`, `count`, or `unitless`). Unknown facts use a status field and a factual reason instead of a fabricated numeric value.

JSON serialization is deterministic where practical: sorted keys, stable list ordering by semantic/entity key, finite numbers only, UTF-8, and a final newline. Determinism supports inspection and repeatability; neither JSON equality nor a JSON hash is a geometry predicate.

The historical v1.1.0 schema and 13 P0/P1 manifests remain byte-for-byte unchanged and continue to validate. Promotion schema changes use a new compatible version; historical files are never rewritten.

## 6. Geometry comparison contract

The comparison request names two authoritative CAD artifacts, their snapshot artifacts, semantic bindings, an optional explicitly permitted rigid transform, and all tolerances with value, unit, role, and source.

P2 supports solid-body comparison with either:

- identity placement; or
- one caller-declared rigid transform that is applied to the comparison candidate and recorded in evidence.

Arbitrary registration, best-fit alignment, scale, reflection, and inferred transforms are out of scope. An unsupported transform yields `GEOMETRIC_EQUIVALENCE_NOT_PROVEN`.

For every applicable matched solid, the worker evaluates:

- solid/shell/face/edge/vertex counts;
- validity and shell closedness;
- connected-component, adjacency, boundary-loop, and hole correspondence;
- absolute area and volume deltas;
- per-axis bounding-box deltas;
- B-rep minimum distance;
- bidirectional Boolean cut volumes;
- analytic surface-family and applicable interface normal/axis/local-direction deltas.

The initial P2 fixture uses these explicit tolerances:

- `linear_distance`: `0.001 mm`;
- `area_difference`: `0.001 mm2`;
- `volume_difference`: `0.001 mm3`;
- `angular_difference`: `0.000001 rad`.

These values are fixture policy, not universal CAD defaults. They are recorded in the comparison and promotion manifests.

`GEOMETRY_EQUIVALENT` is returned only when every required check is supported, all topology predicates agree, and every measured delta is inside or on its declared threshold. A proven threshold exceedance or topology mismatch returns `GEOMETRY_DIFFERENT` with concrete failing measurements. Missing support, ambiguous matching, invalid input, Boolean failure, or incomplete evidence returns `GEOMETRIC_EQUIVALENCE_NOT_PROVEN`.

Byte identity is computed separately with SHA-256 and cannot alter this decision.

## 7. Semantic and UI comparison

Semantic comparison operates only on explicit semantic bindings. Matching component identity, interface correspondence, source/gradient role, repair role, and permitted transform yields `SEMANTIC_EQUIVALENT`. A proven mismatch yields `SEMANTIC_DIFFERENT`. Missing or ambiguous required bindings yield `SEMANTIC_EQUIVALENCE_NOT_PROVEN`.

UI comparison evaluates only the UI snapshots. Exact normalized equality yields `UI_SAME`; a supported property difference yields `UI_DIFFERENT`; insufficient serialized UI information yields `UI_COMPARISON_NOT_PROVEN`.

The valid target combination is:

```text
BYTE_DIFFERENT
GEOMETRY_EQUIVALENT
SEMANTIC_EQUIVALENT
UI_DIFFERENT
```

## 8. Regression fixtures and demo package

P2 creates a small box-with-through-hole fixture with explicit component and interface semantics. The fixture is generated by FreeCAD from fixed dimensions and saved as a new FCStd plus exported BREP and STEP artifacts.

Three immutable cases are produced:

1. `original`: the baseline shape and UI state.
2. `ui_only_changed`: the same B-rep with changed color, transparency, and visibility. Creation uses FreeCAD GUI-capable execution when available; otherwise the case is recorded as unsupported rather than fabricated.
3. `geometry_changed`: the same construction with a changed through-hole radius, producing a topology-compatible but volume/area/Boolean-difference geometry mutation.

The serialization/reopen regression performs `open -> snapshot -> save-as-new-file -> reopen -> snapshot`. A byte difference is allowed and does not set geometry status. If this FreeCAD build serializes identical bytes, a pure-software regression still proves that `BYTE_DIFFERENT` does not imply `GEOMETRY_DIFFERENT`.

The human-review package contains:

- original FCStd, STEP, and BREP;
- UI-only changed FCStd, STEP, and BREP;
- geometry-changed FCStd, STEP, and BREP;
- opening and closing snapshot JSON files;
- comparison JSON files;
- `VIEW_INDEX.md` with relative links and inspection instructions;
- `HUMAN_REVIEW.md` that distinguishes machine geometry evidence from display inspection.

Human review records a separate result and never substitutes for the machine comparison.

## 9. Promotion pipeline extension

The existing promotion flow remains transactional:

```text
outputs/work staging
  -> explicit individual-file allowlist
  -> schemas and policy checks
  -> copy-and-recount in sibling staging directory
  -> manifest validation
  -> atomic install into evidence/<goal>/<commit>/<run>/
```

The request/manifest contract is extended to allow geometry PASS or FAIL only when referenced, allowlisted geometry-semantic snapshots, topology snapshots, and comparison artifacts validate and the comparison method is a recognized B-rep method. Semantic and UI results likewise require their own referenced artifacts.

The gate continues to reject:

- absent goal/run/implementation identity;
- invalid ancestry;
- non-file or implicit/broad allowlists;
- missing artifacts or unitless tolerances;
- path traversal, absolute private paths, symlink/reparse escapes, secrets, and sensitive content;
- destination collision or silent overwrite;
- SHA/fingerprint/serialized-byte fields used as geometry predicates;
- collapsed geometry, semantic, UI, pytest, scientific, or human results;
- dropped failure, mismatch, rejection, or reviewer evidence.

Promotion never deletes source files. Failed promotion retains a non-overwriting failure report. Two paths on the same host report `LOCAL_TWO_PATHS_NOT_OFF_HOST_REDUNDANCY` and `NOT_FULLY_PRESERVED`; P2 does not claim off-host preservation unless an independently verified remote copy actually exists.

## 10. CLI

The existing CLI retains `validate` and `promote`. It gains CAD commands with JSON output and nonzero fail-closed exits:

```text
python -m dmslicer.evidence_promotion snapshot --request <json>
python -m dmslicer.evidence_promotion compare --request <json>
python -m dmslicer.evidence_promotion demo --output-root <path>
python -m dmslicer.evidence_promotion validate --repository-root <root> --request <json>
python -m dmslicer.evidence_promotion promote --repository-root <root> --request <json>
```

Normal CLI output is public-safe and does not echo private absolute paths or secrets. Input/schema/policy/worker failures exit `2`; proven geometry difference remains a successful comparison execution whose result is `GEOMETRY_DIFFERENT`.

## 11. Test strategy

All production behavior follows red-green-refactor. Each test names the production break it detects and asserts real outputs rather than source text or mock existence.

Pure-Python tests cover:

- byte same/different separation;
- all four schema contracts and deterministic JSON;
- historical 13-manifest compatibility;
- semantic PASS/FAIL/NOT_PROVEN;
- UI FCStd extraction and `UI_DIFFERENT`;
- tolerances just inside, exactly on, and just outside thresholds;
- missing goal/run/commit/unit/artifact;
- path, secret, SHA-misuse, collision, and failure-retention safety;
- promotion of valid CAD evidence and rejection of unbacked claims.

Local FreeCAD tests cover:

- snapshot extraction from actual B-rep/STEP/FCStd;
- UI-only mutation: geometry PASS, semantics PASS, UI DIFFERENT;
- hole-radius mutation: geometry FAIL with actual area/volume/Boolean reason;
- save/reopen classification;
- unsupported/ambiguous inputs fail closed;
- repeatability across independent FreeCAD processes.

The complete inherited 07A suite must remain green. FreeCAD-dependent tests are marked local-required if standard GitHub runners lack FreeCAD.

## 12. CI

The existing minimal GitHub Actions workflow is extended only for portable checks:

- install the package and pytest dependencies;
- run pure-Python snapshot/schema/promotion tests;
- validate all 13 historical manifests;
- run evidence-policy lint, sensitive-path checks, and SHA-misuse regressions;
- verify `docs/research_v2/` is unchanged from the PR base.

CI does not claim FreeCAD/OCCT validation when those binaries were not run. Local FreeCAD results are preserved as artifact-backed evidence with exact reproducible commands and versions.

## 13. P2 self-evidence

After implementation is committed, P2 creates a new immutable run under:

`evidence/P2-EVIDENCE-PROMOTION-SEMANTIC-SNAPSHOT/<implementation_commit>/<run_id>/`

The run records:

- branch, full implementation commit, `d65ac32e` baseline, and merge commit;
- input fixture IDs and SHA-256 labeled byte integrity only;
- FreeCAD 1.1.1, OCCT 7.8.1, Python, pytest, and jsonschema versions;
- exact commands, timestamps, exit codes, and unit-bearing tolerances;
- JUnit, validator, FCStd, STEP, BREP, snapshots, comparisons, `VIEW_INDEX.md`, and `HUMAN_REVIEW.md` references;
- separate byte, geometry, semantic, UI, pytest, scientific, human-review, provenance, custody, preservation, and publication results;
- retained negative tests, reviewer findings, failure/fix commits, and known limitations.

Large binary review artifacts remain selected by explicit allowlist. P2 does not add all of `outputs/` or `work/` to Git.

## 14. Failure handling and stop conditions

The system fails closed without converting uncertainty into failure or success:

- insufficient geometry evidence -> `GEOMETRIC_EQUIVALENCE_NOT_PROVEN`;
- insufficient semantic identity -> `SEMANTIC_EQUIVALENCE_NOT_PROVEN`;
- unavailable UI state -> `UI_COMPARISON_NOT_PROVEN`;
- invalid promotion inputs -> `PROMOTION_BLOCKED`;
- same-host two-path custody -> `NOT_FULLY_PRESERVED`.

No hash, bounding box, volume, snapshot equality, human review, or pytest result alone can establish geometry equivalence.

P2 stops after implementation, review, evidence, push, and PR update. It does not merge the PR or begin 07A/07B follow-on work.

## 15. Acceptance evidence

Completion requires authoritative evidence for each of the following:

- branch/worktree/base ancestry and clean status;
- implementation and schemas;
- actual geometry comparison methods and tolerances;
- UI-only, real-geometry-mutation, and serialization/reopen results;
- promotion result and custody classification;
- 13/13 historical manifest compatibility;
- focused, full-suite, and CI results;
- human-review package paths;
- stable P2 evidence paths;
- reviewer findings and their resolution;
- PR URL, correct base branch, remote SHA, and no merge.

The completion report must state byte, geometry, semantic, UI, pytest, scientific, and human-inspection results independently.
