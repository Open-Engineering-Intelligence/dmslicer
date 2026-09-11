# DM-Slicer Architecture Contract Parallel Development v2

Date: 2026-09-11

Status: proposed for user review; architecture-only; no implementation authorized

Goal ID: `ARCHITECTURE-CONTRACT-PARALLEL-DEVELOPMENT-V2`

Canonical baseline: `origin/feat/cylindrical-interface-repairability@b2536357dc07bf4b222a86c01fccde41c58e2eaf`

Baseline composition: 07A cylindrical-interface research through `d65ac32e04115e5627f1c2988fd486e2353cada9`, plus merged P2 evidence-promotion and semantic-snapshot capability through `ef590daf9cce8fb536cbb2123a75321b802568a5`.

## 1. Goal, scope, and stop conditions

### Goal

Define the smallest stable Geometry contract that lets Geometry, Slicer, UI, and Evidence development proceed in parallel without treating continued Geometry research as a universal prerequisite.

The concrete outcome is a versioned `GeometrySnapshot v0.1` downstream contract, a first `SlicerDecision v0.1` consumer contract, a five-experiment capability ladder, and three independent gates:

- G1 starts parallel development;
- G2 freezes `GeometrySnapshot v0.1.0` compatibility;
- I1 proves one representative end-to-end integration and evidence path.

### In scope

- Reinterpret existing 02C-07A results as inputs to a minimal downstream contract.
- Treat merged P2 as the existing Evidence Track foundation.
- Define the boundary between downstream geometry facts and evidence artifacts.
- Define field applicability rather than forcing every Snapshot to carry every capability.
- Define consumer mocks, compatibility rules, development tracks, and gate criteria.
- Record governance duplication and applicability findings without changing repository policy.

### Out of scope

- Implementing schemas, adapters, validators, consumers, UI, slicing, or export.
- Starting Slicer implementation or 07B.
- Modifying `AGENTS.md`, `README.md`, `docs/research_v2/`, source, tests, benchmarks, or historical evidence.
- Re-running or rewriting historical 02C-07A or P0-P2 results.
- General CAD correspondence, arbitrary healing, field solving, actual slicing, toolpath, or G-code.

### Stop conditions

This architecture Goal stops when this spec is reviewed and approved. It must not transition automatically into an implementation plan, schema implementation, branch publication, or downstream feature work.

Future implementation stops are defined separately by G1, G2, and I1. Neither G2 nor I1 authorizes cone/freeform research, 07B, field solving, actual slicing, toolpath, or export.

## 2. Current-state conclusion

DM-Slicer already has enough distinct Geometry results to define a downstream interface:

- 02C establishes stable STEP document/region/face provenance and full planar contacts.
- 06B establishes partial common/remaining partitions.
- 06C establishes disconnected patches, components, boundaries, and an annular hole.
- 07A establishes one curved family and a constrained before/after repair case.
- P2 establishes evidence-domain separation, CAD evidence snapshots, measurement-backed comparison, fail-closed promotion, explicit allowlisting, immutable destinations, and custody status.

The remaining architecture problem is therefore not a lack of Geometry experiments. It is the absence of a deliberately small consumer contract and a gate that lets consumers use canonical examples before all runtime adapters exist.

P2 does not itself provide the downstream contract. Its `geometry_semantic_snapshot`, `topology_snapshot`, and `ui_state_snapshot` artifacts are fixture-scoped evidence records. They do not model multi-region interfaces, common/remaining partitions, Slicer selections, or the full 02C-07A domain.

## 3. Final system boundary

The public architecture is:

```text
Geometry implementation / Goal adapter
├── GeometrySnapshot v0.1 ───────────────► Slicer / UI
└── Evidence artifacts ──────────────────► P2 Evidence Track
                                              │
                                              ▼
                              promotion request / stable manifest
```

There is no public `GeometryOperationEnvelope`.

Geometry implementations may use private command/result DTOs to cross a host/FreeCAD process boundary. Those DTOs:

- are producer-internal APIs;
- are not versioned as downstream contracts;
- may change with a Goal or backend;
- must not be imported or interpreted by Slicer or UI;
- must not be embedded wholesale in `GeometrySnapshot`.

Operation failures, diagnostics, validator details, execution environment, and scientific/human-review results belong to Evidence Track artifacts. A failed operation does not publish a new downstream-ready Snapshot. Existing valid Snapshots remain immutable.

The long-term product flow is:

```text
CAD / STEP
→ Geometry implementation
→ GeometrySnapshot
→ SlicerDecision
→ future FieldQuery / Actual Slicing
→ SliceFieldMap
→ Fabrication policy / Toolpath / Export
```

`SliceFieldMap` retains the meaning frozen in `docs/research_v2/`: a future topology-aware 2D material map. `SlicerDecision` is deliberately earlier and smaller.

## 4. GeometrySnapshot v0.1

### 4.1 Contract role

`GeometrySnapshot v0.1` is the only core Geometry domain contract consumed by Slicer and UI. It is an immutable publication of accepted geometry/topology facts, semantic bindings when supplied, and stable references to authoritative CAD artifacts.

It is not:

- a serialization of FreeCAD or OCCT objects;
- a geometry-equivalence certificate;
- an operation log;
- a validator report;
- a P2 promotion request or manifest;
- a UI saved-state snapshot;
- a display mesh promoted to geometry truth.

### 4.2 Root shape

```json
{
  "contract": {
    "name": "dmslicer.geometry-snapshot",
    "version": "0.1-rc1"
  },
  "snapshot_id": "snapshot:...",
  "source_documents": [],
  "model_frame": {},
  "regions": [],
  "relations": [],
  "artifact_references": [],
  "provenance_references": [],
  "interfaces": [],
  "patches": []
}
```

The example shows capability fields but does not make every shown field universally required. Applicability is normative and defined below.

### 4.3 A. Core required fields

These fields exist in every valid Snapshot:

| Field | Required content | Contract rule |
|---|---|---|
| `contract` | exact contract name and compatible version | No Goal-specific contract names. |
| `snapshot_id` | deterministic immutable Snapshot identity | Identity is not geometry-equivalence evidence. |
| `source_documents[]` | at least one document ID, source artifact reference, and declared source/internal units | A source hash identifies exact bytes only. |
| `model_frame` | stable frame ID, length unit, and placement | UI camera and display orientation are excluded. |
| `regions[]` | at least one stable region ID, source locator, validity state, frame reference, and authoritative geometry artifact reference | A region is not an interface, source boundary, or material field. |
| `relations[]` | normalized region pairs with relation taxonomy and confirmation state | An empty list is valid only when the Snapshot explicitly represents no evaluated region pairs; absence is not used to mean failure. |
| `artifact_references[]` | stable references needed to recover authoritative source/region geometry | Every URI is repository-relative or stable; temporary absolute paths are forbidden. |
| `provenance_references[]` | stable references binding the Snapshot to its source Goal/run/commit evidence | This references evidence; it does not copy the P2 manifest into the Snapshot. |

Core fields never contain placeholder values merely to satisfy shape. If a core fact cannot be established, the Snapshot is not downstream-ready and must not be published.

### 4.4 B. Capability-dependent fields

These fields are required only when the represented capability exists or the Snapshot makes the corresponding claim:

| Field | Required when | Required content |
|---|---|---|
| `tolerances[]` | a relation, comparison, classification, partition, or parameter acceptance uses a tolerance | Only the tolerances actually applied, each with finite value, unit, role, and source. No universal linear/area/volume/angle template. |
| `interfaces[]` | a confirmed 2D relation exists | Interface ID, relation ID, normalized region pair, and member patch IDs. |
| `interface_components[]` | an interface has one or more connectivity components | Component ID, interface ID, and exact member patch IDs. |
| `patches[]` | a confirmed interface is represented by one or more atomic patches | Patch ID, interface/component references, family, local frame, source-face references, area where applicable, and authoritative patch artifact reference. |
| `boundaries[]` | a patch exposes boundary loops needed by a consumer | Boundary ID, patch ID, closedness, `OUTER` or `INNER`, and authoritative wire/curve artifact reference. Hole data is required only when inner boundaries exist. |
| `surface_partitions[]` | common/remaining surface partitioning has actually been performed | Source surface reference, `COMMON`, `REMAINING`, or `EMPTY`, linked patch IDs, and non-empty authoritative artifact references. |
| `semantic_bindings[]` | source/target/material/gradient roles or activation were supplied | Referenced regions/interfaces/patches and explicit activation; bindings do not modify geometry truth. |
| `parent_snapshot_ids[]` | the Snapshot is a published descendant of one or more earlier Snapshots | Exact parent Snapshot IDs. It is omitted for root/import Snapshots. |
| planar parameters | `patch.family = PLANE` | Local origin, unit normal, and stable tangent axes in the declared frame. |
| cylindrical parameters | `patch.family = CYLINDER` | Axis origin/direction, radius, axial interval, periodic/full-period state, and their applicable units/tolerances. |

Capability-dependent fields are omitted when the capability does not exist. They are not populated with fabricated `N/A`, empty parameter objects, zero tolerances, dummy parents, or synthetic holes.

### 4.5 C. Optional/reference-only fields

These fields may be supplied for navigation or display but are never geometry authority and cannot change a Geometry or Slicer decision:

- human-readable labels and descriptions;
- product/material metadata not required by a current binding;
- display mesh artifact references;
- thumbnails and viewer presets;
- stable Evidence Track promotion-manifest references;
- non-normative summary metrics derived from authoritative artifacts;
- namespaced `extensions` that consumers may ignore.

Optional fields must not contain FreeCAD handles, Python object identity, process counters, private absolute paths, or Goal-specific diagnostics.

### 4.6 Geometry families

`GeometrySnapshot v0.1` natively defines:

```text
PLANE
CYLINDER
OTHER
```

- `PLANE` and `CYLINDER` have the capability-dependent parameters above.
- `OTHER` preserves family name, local frame, authoritative artifact reference, and an optional namespaced extension.
- A consumer without a registered strategy for `OTHER` must return `UNSUPPORTED_GEOMETRY_FAMILY`; it must not silently approximate it as planar, mesh-only, or empty.

Cone, sphere, freeform, and NURBS-specific consumer behavior is outside v0.1.

### 4.7 Relations, interfaces, and semantics

The relation taxonomy remains aligned with the frozen research contract:

```text
DISJOINT
NEAR_MISS
TOUCH_POINT
TOUCH_EDGE
FACE_CONTACT
PARTIAL_FACE_OVERLAP
FULL_FACE_OVERLAP
CONTAINMENT
CROSSING
VOLUME_OVERLAP
AMBIGUOUS
```

Confirmation states are:

```text
CANDIDATE
CONFIRMED
REJECTED
AMBIGUOUS
```

Only a confirmed 2D relation may create an interface or patch. `AMBIGUOUS` remains visible to UI and Evidence but cannot produce a successful `SlicerDecision`.

Semantic activation is independent:

```text
UNASSIGNED
ACTIVE
INACTIVE
```

Changing activation does not create, delete, or rewrite a region, relation, interface, patch, boundary, or CAD artifact.

### 4.8 Identity, hash, and geometry-equivalence rules

`SourceDocumentId`, stable IDs, fingerprints, and deterministic digests are allowed for:

- provenance;
- stable contract identity;
- lookup and reproducible references;
- cache or candidate-deduplication hints;
- detecting exact payload or byte replacement.

They are not allowed as final predicates for B-rep equivalence, patch correspondence, cross-export identity, topology equality, or scientific validation.

`stepdoc:v1:<sha256>` identifies exact source bytes. Different source hashes do not prove different engineering geometry. Equal file hashes do not replace the tolerance-aware validation required by a specific geometry claim.

## 5. Evidence Track and P2 applicability

### 5.1 P2 capabilities retained

Evidence Track reuses the merged P2 implementation for:

- `promotion_request.schema.json` and `evidence_manifest.v2.schema.json`;
- explicit individual-file allowlists;
- repository-relative public paths and sensitive-content checks;
- immutable destination and overwrite refusal;
- copy byte recount and byte-integrity hashes;
- preservation of failures, mismatches, and reviewer findings;
- separate byte, geometry, semantic, UI, pytest, human-review, preservation, and publication results;
- CAD evidence schema validation and measurement-backed comparison;
- local package and custody status.

P2 artifacts remain evidence-specific. In particular, P2 `geometry_semantic_snapshot` is not renamed or reused as `GeometrySnapshot`; the two schemas have different purposes and consumers.

### 5.2 Applicability matrix

| Requirement | Geometry Track | Slicer Track | UI Track | Evidence Track |
|---|---|---|---|---|
| Stable source/derived identity | Required | Required for referenced inputs/outputs | Required for referenced inputs/view state | Required |
| No hash-as-geometry proof | Required | Must not infer geometry from hashes | Must not infer geometry from hashes | Enforced by policy |
| Claim-specific unit-bearing tolerance | Required when a Geometry claim uses it | Only for decision thresholds actually used | Only for UI calculations that use it | Recorded for the claim being preserved |
| FreeCAD/OCCT runtime | Goal-dependent | Forbidden for contract-only consumer tests | Forbidden for contract-only viewer tests | Required only for CAD-backed comparison runs |
| FCStd/HUMAN_REVIEW/VIEW_INDEX | Formal CAD/geometry Goals as applicable | Not required unless the Goal creates CAD review output | Not required for ordinary viewer work | Preserved when declared by the source Goal |
| P2 opening/closing three-snapshot loop | Only when the Goal claims serialization/reopen or UI-vs-geometry equivalence | Not required | Not required | Required only for that class of CAD comparison/promotion |
| Stable Goal manifest | Required | Required | Required | Required and promotable |
| Full P2 stable promotion package | Not a per-commit requirement | Not a per-commit requirement | Not a per-commit requirement | Required only at an authorized evidence/integration gate |

This matrix does not weaken current repository instructions. It prevents future Architecture plans from turning a fixture-scoped P2 workflow into an unconditional dependency for unrelated consumers.

### 5.3 Governance findings

Current `AGENTS.md` contains overlapping hash/geometry-equivalence sections, human-inspection language that needs applicability guidance for non-CAD Goals, and conflicting external-action/push language. This task does not edit the file or reinterpret an explicit task prohibition. Any consolidation is a separate governance Goal and is not a G1, G2, or I1 dependency.

## 6. Minimal experiment ladder

P2 does not reduce this ladder. Its single-body through-hole fixture validates evidence behavior, not multi-region interface, patch, or hole-boundary semantics.

| ID | Existing fixture | Geometry claim | Unique Snapshot capability | Downstream unlock | Priority |
|---|---|---|---|---|---|
| E0 | 02C CASE01 planar A/G/B | Two 400 mm2 full planar interfaces; A/B disjoint | Core regions/relations, confirmed interfaces, source semantics, stable source references | Basic UI and full-planar consumer | M0/G1 |
| E1 | 06B P07 planar partial | 480 mm2 common and 320/320 mm2 remaining | Coverage and `COMMON`/`REMAINING` partitions | First `SlicerDecision` | M0/G1 |
| E2 | 06C P10 planar multipatch | Two disconnected 192 mm2 patches | Patch membership and two interface components | Multipatch Slicer/UI | M0/G1 |
| E3 | 06C P11 planar annular | One 300-pi mm2 patch with one hole | `OUTER`/`INNER` boundaries and hole semantics | Hole-aware strategy | M1/G2 |
| E4 | 07A C01/C02 cylindrical | Exact cylinder plus one authorized axis-translation correction | Cylinder parameters and optional before/after Snapshot lineage | Cylindrical strategy | M1/G2 |

### E0 done definition

- Input: tracked CASE01 STEP, semantics, and explicit applicable tolerances.
- Structured output: three regions, A/G and G/B confirmed interfaces, two patches, A/B disjoint.
- Validation: actual B-rep relation/area evidence and stable source references.
- Human artifact: existing Goal artifact reference; no new experiment run.
- Stop: canonical example and consumer mock pass. No extra rectangular variants.

### E1 done definition

- Input: tracked P07 STEP/result and existing common/remaining artifacts.
- Structured output: one partial interface, common partition, both remaining partitions, and semantic selection inputs.
- Validation: 480 mm2 common, 320/320 mm2 remaining, reference integrity, and area/space conservation evidence.
- Downstream unlock: deterministic planar `SlicerDecision`.
- Stop: decision consumer passes. No extra contained/offset cases for G1.

### E2 done definition

- Input: tracked P10 STEP/result and existing patch artifacts.
- Structured output: two patches, two components, zero holes, complete source-member links.
- Validation: equal-area but spatially distinct patches remain distinct.
- Downstream unlock: multipatch selection and display.
- Stop: canonical membership and consumer tests pass. No complex connected multi-face boundary expansion.

### E3 done definition

- Input: tracked P11 STEP/result and existing common BREP.
- Structured output: one patch, one component, one outer boundary, one inner boundary.
- Validation: area `300*pi mm2`, analytic boundary family, and hole count one.
- Downstream unlock: hole-aware decision strategy.
- Stop: annular example passes. No nested or complex multi-face holes.

### E4 done definition

- Input: tracked C01/C02 STEP/results and existing correction evidence.
- Structured output: cylindrical patch parameters; C02 descendant Snapshot references its parent.
- Validation: axis, radius, area, actual common, correction postcheck, and artifact-backed before/after comparison.
- Downstream unlock: cylindrical decision strategy.
- Stop: C01/C02 contract examples pass. Angular/radial/ambiguous repair expansion remains deferred.

## 7. Canonical contract examples and consumer mocks

The implementation Goal will create versioned examples under:

```text
contract_examples/v0.1/
├── geometry/
│   ├── planar_full.json
│   ├── planar_partial.json
│   ├── planar_multipatch.json
│   ├── planar_annular.json
│   └── cylindrical.json
└── negative/
    ├── ambiguous_relation.json
    ├── unsupported_family.json
    ├── missing_semantic_binding.json
    └── unresolved_artifact.json
```

The examples are canonical projections from tracked historical fixtures and evidence, not new scientific experiment results. Their provenance references must identify the originating Goal, commit, fixture, and stable artifact.

Consumer mocks operate only on these JSON examples and referenced test artifacts. They do not invoke Goal runners or FreeCAD.

## 8. SlicerDecision v0.1

### 8.1 Purpose

`SlicerDecision v0.1` is the first Slicer-owned contract. It records a deterministic selection and partition-planning decision. It does not claim that a slice plane, layer, contour, field map, toolpath, or exported machine instruction exists.

### 8.2 Required structure

```json
{
  "contract": {
    "name": "dmslicer.slicer-decision",
    "version": "0.1-rc1"
  },
  "decision_id": "decision:...",
  "input_snapshot_id": "snapshot:...",
  "selected_interface_id": "interface:...",
  "selected_patch_ids": ["patch:..."],
  "target_region_id": "region:...",
  "strategy_kind": "PLANAR_INTERFACE_PARTITION",
  "local_frame_ref": "frame:...",
  "partition_direction": [0.0, 0.0, 1.0],
  "partition_operation": "SPLIT_COMMON_AND_REMAINING",
  "expected_partition_refs": ["partition:..."],
  "status": "DECIDED",
  "reason_code": "NONE",
  "provenance_reference": "provenance:..."
}
```

Statuses:

```text
DECIDED
REJECTED
UNSUPPORTED
FAILED
```

Initial stable reason codes:

```text
NONE
INVALID_SNAPSHOT
AMBIGUOUS_INTERFACE
MISSING_SEMANTIC_BINDING
UNRESOLVED_ARTIFACT
UNSUPPORTED_GEOMETRY_FAMILY
UNSUPPORTED_STRATEGY
```

E1 is the first positive input. Ambiguous relation, missing binding, unresolved artifact, and `OTHER` without a strategy are fail-closed inputs.

## 9. Gates

### G1 - Parallel Development Start Gate

G1 is contract-first and does not wait for E0-E2 runtime adapters.

G1 passes when:

1. `GeometrySnapshot 0.1-rc1` schema is fixed for required names and meanings.
2. Semantic/reference validation rules are executable.
3. E0, E1, and E2 canonical examples pass schema and semantic/reference validation.
4. The four initial negative examples fail closed with stable reason categories.
5. A FreeCAD-free Slicer mock converts E1 into a deterministic `SlicerDecision`.
6. A FreeCAD-free UI mock lists regions, interfaces, patches, components, applicable boundaries/partitions, semantics, and artifact links.
7. Reordering JSON collections does not alter semantic identity or consumer output.

At G1, Geometry, Slicer, UI, and Evidence Tracks start in parallel. Adapter implementation, E3/E4, and P2 promotion are not G1 blockers.

### G2 - GeometrySnapshot v0.1.0 Compatibility Freeze

G2 passes when:

1. E0-E4 adapters and canonical examples conform to the same `GeometrySnapshot` contract.
2. E3 boundary/hole and E4 cylindrical/lineage capabilities pass their schema and semantic/reference validation.
3. All G1 consumer mocks continue to pass without a breaking field or semantic change.
4. Positive and negative examples pass the final `0.1.0` schema and validator.
5. No consumer depends on Goal-private DTOs, FreeCAD handles, P2 CAD snapshot internals, or diagnostics.

G2 freezes `GeometrySnapshot v0.1.0`. It does not require or wait for a P2 stable evidence package.

### I1 - Representative Integration Evidence Gate

I1 is independent of G2 and may complete before or after G2 without changing Contract maturity.

I1 proves:

```text
06B P07
→ GeometrySnapshot
→ SlicerDecision
→ Viewer
→ representative P2 stable evidence package
```

I1 requires one traceable integration run, reference integrity across the three contracts/artifact sets, separate software/scientific/human/preservation results, and a P2 package created through the existing allowlist/promotion policy.

I1 failure blocks the representative integration evidence claim only. It does not revoke a valid G1 or block/falsify G2 compatibility.

## 10. Parallel tracks

### Geometry Track

- Build Goal-specific adapters that project accepted 02C-07A results into `GeometrySnapshot`.
- Complete E0-E4 conformance without rewriting historical results.
- Continue later robustness research behind the frozen contract when expressible.
- Emit claim-appropriate evidence to Evidence Track.

### Slicer Track

- Depend only on `GeometrySnapshot` examples/schema.
- Implement deterministic `SlicerDecision` selection and rejection behavior.
- Keep actual slicing, `FieldQuery`, `SliceFieldMap`, toolpath, and G-code outside the first Goal.

### UI Track

- Depend only on `GeometrySnapshot` and `SlicerDecision`.
- Display source regions, confirmed/ambiguous relations, patches, components, boundaries, partitions, selected decision, and artifact/provenance links.
- Treat display meshes, camera, color, and screenshots as display state only.

### Evidence Track

- Reuse P2 schema, policy, comparison, and promotion implementation.
- Accept references to new contract artifacts without embedding P2 fields into downstream contracts.
- Run full promotion only for an authorized evidence or integration Goal such as I1.
- Never turn P2 fixture-specific comparison into a prerequisite for ordinary consumer development.

## 11. Versioning and compatibility

- G1 freezes `0.1-rc1` required field names, meanings, reference rules, family discriminators, and consumer-visible reason categories.
- Between G1 and G2, changes are limited to optional fields, newly applicable capability-dependent fields, or namespaced extensions that old consumers may ignore.
- `0.1.x` may not delete/rename existing fields, change units or identity semantics, reinterpret absence, or make an optional/capability field universally required.
- A new required core field, changed relation meaning, changed identity rule, or consumer-mandatory new geometry family requires `0.2.0`.
- P2 evidence schema versions remain independently versioned. A P2 schema change does not automatically change `GeometrySnapshot` or `SlicerDecision`.
- Historical examples are immutable; corrections create a new example version and explicit supersession record.

## 12. Test and acceptance plan for future implementation

### Contract tests

- Five positive examples: E0-E4.
- Four negative examples: ambiguous relation, unsupported family, missing semantic binding, unresolved artifact.
- Core-field absence rejects publication.
- Capability-dependent fields are required only when their discriminator/claim activates them.
- Planar examples do not require cylinder parameters; cylindrical examples do not require hole data.
- Root/import Snapshots do not require `parent_snapshot_ids`; C02 descendant Snapshot does.
- Snapshots include only tolerances actually used by their represented claim.
- No placeholder `N/A`, dummy zero tolerance, empty family-parameter object, or synthetic parent is accepted as satisfying applicability.

### Semantic/reference tests

- All IDs and references resolve exactly once.
- Interface-patch-component-boundary membership is consistent.
- Only confirmed 2D relations create interfaces.
- Semantic activation cannot alter geometry collections.
- Stable identities survive collection reorder and backend traversal reorder.
- SHA/fingerprint equality is never consumed as geometry-equivalence proof.

### Consumer tests

- Slicer/UI tests run without FreeCAD/OCCT imports.
- E1 produces a deterministic `SlicerDecision` by ID, not array position.
- E2 preserves both disconnected patches.
- E3 exposes the inner boundary only because the capability exists.
- E4 exposes cylinder parameters; unsupported `OTHER` fails closed.
- G1 examples continue unchanged through G2.

### Evidence boundary tests

- P2 evidence artifacts are never accepted as substitutes for `GeometrySnapshot`.
- Contract validation does not require a P2 promotion package.
- G2 can pass independently of I1.
- I1 records its evidence result separately and cannot rewrite Contract maturity.

## 13. Deferred research

The following remain M2/M3 or separate product Goals and cannot block G1/G2:

- 05A-05C extended tolerance and scale sweeps;
- 06D broader orientation covariance;
- additional 07A angular, radial, ambiguous, or repair strategies;
- cone, sphere, freeform, and NURBS-specific downstream behavior;
- dirty/invalid STEP healing and pathological topology;
- arbitrary registration, best-fit transforms, and general cross-export correspondence;
- volumetric field solvers and sampling;
- actual slice planes, layers, contours, and `SliceFieldMap` implementation;
- toolpath, machine control, and export;
- general Evidence dashboards, databases, services, or plugin frameworks;
- `AGENTS.md` consolidation or policy-profile refactoring.

## 14. Acceptance checklist for this architecture Goal

This spec is acceptable when the reviewer confirms:

- the canonical baseline includes 07A and merged P2;
- no public `GeometryOperationEnvelope` is introduced;
- `GeometrySnapshot` and P2 evidence artifacts remain separate;
- fields are classified as core required, capability-dependent, or optional/reference-only;
- absent capabilities do not require invented `N/A` payloads;
- P2 promotion is outside G2;
- G1, G2, and I1 have independent, testable meanings;
- E0-E4 remain the minimum sufficient ladder;
- `SlicerDecision` remains pre-slicing and does not overlap `SliceFieldMap`;
- P2 requirements do not become unconditional Slicer/UI dependencies;
- frozen research documents and historical evidence remain unchanged;
- no implementation or external publication has begun.
