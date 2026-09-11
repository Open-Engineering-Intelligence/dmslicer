# P2 Evidence Promotion and Semantic Snapshot Design

## Status and authority

This design implements the P2 objective on branch
`feat/evidence-promotion-semantic-snapshot`, based on
`origin/main@ea617b6b6fa8d074c1c89d6f61513fe4d892cef3`.

The authoritative policy inputs are the repository-root `AGENTS.md`,
`docs/evidence_preservation/EVIDENCE_PROMOTION_CI_REQUIREMENTS.md`, the
version 1.1.0 evidence manifest schema, and the P0/P1 reports. The frozen
`docs/research_v2/` contract and historical P0/P1 manifests remain unchanged.

## Goal

Build the smallest reusable, testable project pipeline that separates byte
integrity, B-rep geometry evidence, engineering semantics, and UI/display
state, and that promotes only explicitly allowlisted staging artifacts into a
stable evidence package through a fail-closed policy gate.

## Delivery model

This document is the long-term P2 architecture, not a promise to implement all
layers in one change. Delivery is split into two explicit phases:

1. **P2-MVP (immediate scope):** schema-compatible byte-integrity evidence,
   allowlisted local package creation, path/content safety gates, failure
   retention, result-domain separation, stable identity, copy recounting, and
   independent local-package/preservation/publication statuses.
2. **P2 phase 2 (deferred):** FreeCAD/OCCT snapshot extraction, tolerance-aware
   geometry comparison, rigid-transform support, generated CAD regression
   fixtures, and human-openable CAD demonstration packages.

P2-MVP is useful without pretending phase 2 exists. Every CAD result in an MVP
manifest is explicitly `GEOMETRIC_EQUIVALENCE_NOT_PROVEN`, carries an empty
geometry-evidence list, and cannot be upgraded by SHA-256, a snapshot digest,
or a software-test result.

## Long-term scope

P2 includes:

- file-level SHA-256 and byte-copy verification with an integrity-only role;
- versioned, deterministic CAD geometry/semantic, topology, and UI snapshots;
- tolerance-aware comparison backed by FreeCAD/OCCT B-rep operations;
- explicit byte, geometry, semantic, UI, pytest, validator, scientific, human
  inspection, and provenance result domains;
- a schema-backed promotion request and manifest;
- a CLI that validates an explicit allowlist, materializes a non-overwriting
  local package, and reports copy-policy status;
- UI-only, true-geometry-mutation, tolerance-boundary, serialization/hash,
  manifest, path, secret, SHA-misuse, and failure-retention regressions;
- three small FCStd demonstration artifacts plus a relative-path `VIEW_INDEX`;
- pure-Python GitHub Actions checks and clearly marked local FreeCAD tests; and
- `docs/evidence_preservation/EVIDENCE_PROMOTION_PIPELINE.md`.

Long-term P2 does not migrate the historical 02C-06D implementation tree, modify
historical outputs or manifests, create external object storage, publish a
Release, merge its pull request, or begin 07A geometry research.

## P2-MVP immediate scope

P2-MVP implements only:

- a small installable Python package and CLI;
- SHA-256 and exact source/copy byte verification, labeled byte integrity only;
- versioned promotion-request and P2 manifest schemas while preserving schema
  v1.1.0 and all historical manifests unchanged;
- stable package identity `goal_id + implementation_commit + run_id`;
- an explicit individual-file allowlist rooted below `outputs/` or `work/`;
- source existence, containment, traversal, reparse/symlink escape, duplicate
  destination, broad-selection, overwrite, and absolute-public-path checks;
- obvious secret and sensitive-local-path detection in public text/JSON;
- required implementation commit, valid run ID, explicit result domains, and
  unit-bearing tolerance validation when a tolerance is declared;
- policy rejection of SHA-256, file hashes, or snapshot hashes used as a
  geometry predicate;
- required retention of declared failures, mismatches, rejection cases, and
  reviewer findings;
- copied-file inventory, byte recount, machine-readable policy report, and a
  relocatable local evidence package; and
- pure-Python unit tests, documentation, and a minimal local/CI validation
  command.

P2-MVP explicitly defers `cad.py`, `freecad_worker.py`, CAD snapshot extraction,
actual geometry or semantic equivalence, rigid transforms, FreeCAD-dependent
tests, FCStd/STEP/BREP demo fixtures, and CAD `VIEW_INDEX` generation. The MVP
schemas reserve structured, non-claiming locations for those future artifacts;
they do not contain fabricated metrics or placeholder PASS values.

Push, pull-request creation, Releases, external-storage writes, and off-host
copy registration require separate explicit authorization. They are not part
of P2-MVP execution even if local tooling and credentials are available.

## Existing repository constraints

Current `origin/main` contains evidence-governance documents and PowerShell
historical-ingestion scripts, but no Python package, geometry implementation,
or tests. The historical 06C/06D branches demonstrate useful OCCT techniques:
`distToShape`, bidirectional `cut`, `common`, validity/closure checks, topology
counts, boundary-loop inspection, and explicit unit-bearing tolerances. P2 may
reuse those demonstrated techniques, but it will not copy or cherry-pick the
historical research stack. This keeps the implementation a dedicated new
control-plane component and respects the migration boundary.

## Long-term architecture

The implementation is a focused Python package under
`src/dmslicer/evidence_promotion/`. Host-side modules handle deterministic JSON,
schema validation, policy decisions, path safety, and promotion. A dedicated
worker module runs only inside `FreeCADCmd` and exchanges JSON request/response
files with the host. This split keeps ordinary CI independent of FreeCAD while
ensuring geometry conclusions come from real B-rep operations rather than a
display mesh or a snapshot digest.

The package has five responsibility boundaries:

1. `integrity.py` computes SHA-256, sizes, and exact source/copy byte identity.
2. `cad.py` launches the headless worker, validates explicit tolerances, and
   writes immutable snapshot/comparison artifacts.
3. `freecad_worker.py` opens FCStd/STEP/BREP artifacts, generates the demo
   fixtures, extracts B-rep facts and UI facts separately, and performs actual
   OCCT comparisons.
4. `policy.py` validates schemas, result separation, paths, allowlists,
   failure retention, sensitive content, copy state, and prohibited SHA-based
   geometry predicates.
5. `promotion.py` builds a candidate package in a temporary sibling directory,
   verifies every copied file, writes inventories/results, and atomically
   installs a new stable destination without overwriting existing evidence.

`cli.py` and `python -m dmslicer.evidence_promotion` expose narrow `snapshot`,
`compare`, `generate-demo`, `validate`, and `promote` commands. No service,
plugin framework, event bus, repository abstraction, or storage adapter is
introduced.

## P2-MVP architecture

The MVP creates only the host-side control plane:

1. `integrity.py` computes file sizes and SHA-256 for byte integrity and copy
   verification.
2. `models.py` defines result/status constants and deterministic JSON helpers.
3. `policy.py` validates schemas, stable identity, result separation,
   unit-bearing tolerances, SHA misuse, failure retention, source/public paths,
   allowlists, secrets, and custody declarations.
4. `promotion.py` stages allowlisted copies, recounts bytes, writes inventories
   and validation reports, and refuses overwrite.
5. `cli.py` exposes `validate` and `promote` subcommands.

The phase-2 `cad.py` and `freecad_worker.py` boundaries described above remain
architectural guidance only and are not scaffolded in the MVP.

## Schemas and compatibility

The existing `docs/evidence_preservation/evidence_manifest.schema.json`
remains version 1.1.0 and continues to validate P0/P1 manifests unchanged.
P2 adds independent versioned schemas under
`docs/evidence_preservation/schemas/`:

- `promotion_request.schema.json` for explicit promotion inputs; and
- `evidence_manifest.v2.schema.json` for new Goal evidence packages.

Phase 2 will add `cad_snapshot.schema.json` and
`cad_comparison.schema.json` when the concrete FreeCAD evidence shapes are
implemented and tested. The MVP manifest schema already keeps byte, geometry,
semantic, and UI result objects separate; the geometry object requires
`GEOMETRIC_EQUIVALENCE_NOT_PROVEN` and no claimed comparison evidence in MVP
packages.

Every schema is JSON Schema draft 2020-12, rejects unknown properties where
practical, records its own version, and requires units beside every tolerance
or measured dimensional quantity. P2 uses general, bounded identifiers instead
of weakening the historical schema's 02C-06D patterns.

Snapshot JSON is key-sorted and newline-terminated. Arrays whose order is not
semantically meaningful are sorted by stable keys. Snapshot digests may be
recorded for byte integrity or fast lookup, but schemas and policy language
state that they are not geometry predicates.

## Stable CAD identity and semantic evidence

The demonstration FCStd objects carry explicit custom properties:
`EvidenceEntityId`, `SemanticRole`, and `MaterialKey`. The stable entity ID is
the comparison key. It is a human-selected deterministic identifier, not a
random UUID, process counter, or traversal index.

For other documents, the worker accepts an explicit semantic sidecar mapping
FreeCAD object names to stable entity IDs and engineering properties. A native
`EvidenceEntityId` property may be used when unique. Labels, list order, and
shape hashes are not silently promoted to persistent identity. Missing,
duplicate, or ambiguous semantic identity yields
`GEOMETRIC_EQUIVALENCE_NOT_PROVEN` for correspondence-dependent comparison and
an unproven semantic result; it never yields an inferred PASS.

`geometry_semantic_snapshot` records stable entity identity, source object
name, shape kind, engineering role/material data, shape measures, analytic
surface/curve families, and the declared identity source. It does not include
color, visibility, camera, or display caches.

`topology_snapshot` separately records solid, compsolid, shell, face, wire,
edge, and vertex counts; validity and closedness; connected-solid components;
face adjacency represented by a deterministic degree/signature multiset; and
boundary-loop/hole evidence. The initial supported hole measure is the sum of
inner face-wire loops, with the method named in the snapshot. It is evidence
appropriate to the supported fixtures, not a universal genus oracle.

`ui_state_snapshot` records object color, shape color, line color, point color,
transparency, visibility, display mode, line/point size, and document camera
orientation when available. Unavailable headless-view properties remain
explicitly unavailable and never contaminate geometry status.

## Tolerance-aware geometry comparison

The comparison request requires explicit values and units for:

- linear distance and bounding-box comparison in `mm`;
- surface area and bidirectional surface residuals in `mm^2`;
- volume and bidirectional Boolean residuals in `mm^3`;
- angular/rigid-transform validation in `rad`; and
- rigid-matrix orthonormality and determinant checks as `dimensionless`.

No tolerance has a hidden runtime default. A checked-in demo request may carry
explicit fixture values, but the CLI rejects an omitted value, unit, role, or
source.

For each stable entity pair, the FreeCAD worker records:

- shape type, validity, closure, and topology-count agreement;
- connected-component and supported hole-count agreement;
- absolute area and volume deltas;
- axis-aligned bounding-box deltas;
- OCCT minimum distance;
- `A cut B` and `B cut A` volume residuals for solids;
- corresponding area residuals for face/shell comparisons where applicable;
- common volume or area where appropriate; and
- analytic surface and boundary-curve family agreement.

An entity is `GEOMETRY_EQUIVALENT` only when every required applicable check
passes. An actual contradictory metric yields `GEOMETRY_DIFFERENT` with the
failing metric and measured value. Missing identity, unreadable CAD, invalid
shape, unsupported dimensional comparison, or unavailable proof yields
`GEOMETRIC_EQUIVALENCE_NOT_PROVEN`; UNKNOWN is never converted to PASS or FAIL.

Rigid-transform-aware comparison is opt-in. The caller supplies a complete
4x4 transform and explicit transform tolerances. The worker validates a proper
rigid transform before applying it to the designated side. P2 does not perform
automatic best-fit alignment, because that could hide an unauthorized
translation or geometry edit.

Semantic equivalence compares the explicit stable engineering fields after
entity correspondence is established. It remains independent of B-rep
geometry. UI comparison considers only UI snapshots. Byte identity compares
only original file bytes. Therefore a hash mismatch cannot set geometry status.

## Regression fixtures

`generate-demo` creates, through FreeCAD itself:

- `original.FCStd`: one named box body with stable semantic properties;
- `ui_only_changed.FCStd`: the same body geometry and semantic properties with
  changed color, transparency, and visibility; and
- `geometry_changed.FCStd`: the same identity and semantics with one dimension
  changed, producing a measurable volume/bounding-box/Boolean difference.

The generated evidence includes separate snapshots, comparison JSON, the
original byte-integrity result, environment versions, and `VIEW_INDEX.md`.
The UI-only expected result is geometry equivalent, semantic equivalent, and
UI different regardless of whether serialized bytes match. The geometry-change
case must fail from actual B-rep metrics, never from the file hash.

A save/reopen case records both byte outcomes honestly. If this FreeCAD build
does not produce different bytes, the test does not fabricate a mismatch. A
pure policy regression independently proves that a supplied hash mismatch does
not drive geometry failure.

## Evidence promotion flow

The flow is:

```text
outputs/work staging
        -> explicit allowlist
        -> CAD snapshots and comparison evidence
        -> schema-valid manifest
        -> fail-closed policy checks
        -> evidence/<goal_id>/<implementation_commit>/<run_id>/
```

The request supplies `goal_id`, `run_id`, branch, full implementation commit,
parent baseline/merge-base, source staging root, explicit file allowlist,
artifact kinds and validation roles, environment versions, commands and exit
codes, timestamps, all tolerances, all independent result domains, retained
failure references, and custody locations. The gate does not infer these from
paths, dates, Git proximity, or chat.

Allowlisted entries must be individual regular files below an approved
`outputs/` or `work/` root. The gate rejects empty/broad directory selection,
wildcards, traversal, unexpanded variables, symlink/reparse-point escape,
duplicate destinations, absolute public paths, Codex/user temporary paths,
credential-like values, and missing source files. It scans public JSON and
text artifacts for obvious secrets and prohibited local path patterns.

Promotion stages copies into a fresh sibling directory, recalculates source
and destination size/SHA-256, emits a copy inventory, validates all package
links and schemas, and refuses any existing final destination. A failed gate
retains the candidate validation report and source failure evidence; it does
not delete or overwrite prior evidence merely to obtain a green result.

The pipeline may materialize a valid local evidence package when source and
promoted copies are the only recoverable paths. Local creation success is
independent of preservation and publication readiness. In that state it
reports:

```text
recoverable_copy_count: 2
recoverable_copy_policy: LOCAL_TWO_PATHS_NOT_OFF_HOST_REDUNDANCY
local_package_status: LOCAL_PACKAGE_CREATED
preservation_status: NOT_FULLY_PRESERVED
publication_status: PUBLICATION_NOT_AUTHORIZED
```

The MVP CLI returns zero when local package creation and every local gate pass.
It returns nonzero for an unsafe or incomplete local request. It does not use
the absence of an off-host copy to turn a valid local package into a failed
creation. Instead, preservation remains `NOT_FULLY_PRESERVED` and publication
remains `PUBLICATION_NOT_AUTHORIZED` or `PUBLICATION_BLOCKED_OFF_HOST_COPY`.
An explicit, separately authorized off-host custody record is required before
either status can advance; P2-MVP neither creates nor registers that copy.

CAD package manifests support explicit FCStd, STEP/BREP, `VIEW_INDEX`, and
`HUMAN_REVIEW` artifact kinds. Human inspection can record findings but cannot
replace validator or B-rep evidence.

## Result model and failure semantics

The manifest keeps these results independent:

- `byte_identity_result`;
- `geometry_equivalence_result`;
- `semantic_equivalence_result`;
- `ui_state_result`;
- `pytest_result`;
- `validator_result`;
- `scientific_experiment_result`; and
- `human_inspection_result`.

Provenance, local package, preservation, and publication statuses are also
explicit. Status enums include
`BYTE_SAME`, `BYTE_DIFFERENT`, `GEOMETRY_EQUIVALENT`, `GEOMETRY_DIFFERENT`,
`GEOMETRIC_EQUIVALENCE_NOT_PROVEN`, `SEMANTIC_EQUIVALENT`,
`SEMANTIC_DIFFERENT`, `SEMANTIC_EQUIVALENCE_NOT_PROVEN`, `UI_SAME`,
`UI_DIFFERENT`, `UI_STATE_NOT_PROVEN`, `PROVENANCE_INCOMPLETE`,
`LOCAL_PACKAGE_CREATED`, `LOCAL_PACKAGE_BLOCKED`, `NOT_FULLY_PRESERVED`,
`FULLY_PRESERVED`, `PUBLICATION_NOT_AUTHORIZED`, and
`PUBLICATION_BLOCKED_OFF_HOST_COPY`. Domain-specific unknown states remain
unproven states and are never collapsed into another domain's PASS or FAIL.

## P2-MVP test strategy

Pure-Python tests cover byte equality/difference, deterministic serialization,
schema compatibility, every required manifest rejection, allowlist and path
safety, secret detection, result separation, prohibited SHA predicates,
failure retention, copy recount, no-overwrite behavior, and local-two-path
copy-policy reporting. They also prove that a hash mismatch leaves the geometry
result `GEOMETRIC_EQUIVALENCE_NOT_PROVEN`, and that local package success is not
collapsed into full preservation or publication. Tests first fail for the
missing behavior and then drive the minimum implementation.

Standard CI installs the package, pytest, and JSON Schema support, then runs
the pure suite, schema checks, policy lint, prohibited-path scan, and SHA-misuse
regression. No FreeCAD installation or CAD claim is required in MVP CI.

## Phase-2 test strategy

FreeCAD-marked integration tests generate the actual fixtures and verify:

- UI-only mutation: geometry equivalent, semantics equivalent, UI different;
- true geometry mutation: geometry different with volume, bounding-box, or
  Boolean residual evidence;
- tolerance values immediately inside and outside declared boundaries;
- save/reopen serialization behavior without fabricating byte differences;
- snapshot schema validation and deterministic repeat generation; and
- readable FCStd/STEP/BREP human-inspection deliverables.

FreeCAD tests will remain explicitly marked and documented with the exact local
`FreeCADCmd` invocation and resulting evidence paths unless a reliable CAD CI
environment is separately approved.

## P2-MVP acceptance criteria

P2-MVP is complete when:

1. the promotion-request and manifest-v2 schemas plus every MVP implementation
   layer exist and are tested;
2. historical schemas/manifests still validate without modification;
3. every declared tolerance is explicit and unit-bearing, while no undeclared
   geometry tolerance or metric is invented;
4. every MVP CAD result is explicitly unproven and contains no geometry claim;
5. byte mismatch is proven unable to drive geometry status;
6. local package creation success remains separate from preservation and
   publication status;
7. promotion rejects every required incomplete or unsafe local request and retains
   failure evidence;
8. local-only custody is reported as blocked/not fully preserved;
9. the pure test and local CI-equivalent suites pass;
10. the pipeline documentation clearly distinguishes MVP from phase 2;
11. the feature branch is committed locally with a clean worktree; and
12. final reporting records branch, HEAD, tests, local CI-equivalent status,
    worktree status, methods, policy outcomes, and the fact that remote SHA/PR,
    CAD regression results, and human-inspection paths are deferred or not
    authorized rather than falsely reported complete.

## Phase-2 acceptance criteria

Phase 2 completes the remaining long-term criteria: concrete snapshot schemas,
explicit comparison tolerances, UI-only and geometry-mutation CAD regressions,
serialization/reopen evidence, FreeCAD-dependent tests, and human inspection
artifacts. Remote publication activities remain separately authorized even
after phase 2 implementation.

## Stop conditions

If the available FreeCAD/OCCT API cannot reliably prove a claimed equivalence,
the implementation records `GEOMETRIC_EQUIVALENCE_NOT_PROVEN` and continues
with independently provable layers. If semantic identity is absent or
ambiguous, semantic equivalence remains unproven. If FreeCAD-dependent behavior
is unstable, P2 preserves the artifacts and exact environment evidence and does
not replace the missing proof with SHA-256, a display mesh, or a JSON digest.
