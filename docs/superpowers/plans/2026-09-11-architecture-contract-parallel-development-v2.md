# DM-Slicer Architecture Contract Parallel Development v2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the smallest versioned `GeometrySnapshot v0.1` and `SlicerDecision v0.1` contract surface needed to pass G1, then complete E0-E4 compatibility for G2 and one separately governed P07 integration-evidence run for I1.

**Architecture:** Geometry Goal adapters project already accepted Goal results into immutable `GeometrySnapshot` publications. Slicer and UI consume only that Snapshot; producer-private FreeCAD command/result DTOs never cross the contract boundary. Evidence artifacts and operation diagnostics stay in the existing P2 Evidence Track and are referenced, not embedded. G1 is JSON/schema/validator/mock based and FreeCAD-free; Goal adapters, E3/E4, and I1 follow behind independently.

**Tech Stack:** Python 3.11+, `jsonschema` Draft 2020-12, pytest, existing DM-Slicer identity/evidence helpers, existing 02C/06B/06C/07A runners, and the existing `dmslicer.evidence_promotion` P2 package.

**Spec:** `docs/superpowers/specs/2026-09-11-architecture-contract-parallel-development-v2-design.md`

## Global Constraints

- Do not implement a public `GeometryOperationEnvelope`. Existing runner results remain producer-internal inputs to Goal-specific projection functions.
- Do not modify `docs/research_v2/` or rewrite historical evidence. Canonical examples are new contract fixtures with explicit provenance back to existing Goals.
- Do not make P2 promotion a prerequisite for G1 or G2. P2 is invoked only by the separately authorized I1 run.
- A region geometry reference is `authoritative CAD artifact + stable locator`. Multiple regions may reference the same STEP/BREP/FCStd artifact. A separate `REGION_BREP` is required only when the shared artifact and locator cannot recover the region.
- A derived patch or partition gets its own BREP only when no existing authoritative CAD artifact plus stable locator can recover it. Do not generate binaries merely to fill a schema.
- Stable identity is limited to deterministic IDs for E0-E4 entities and current consumers. Do not implement generic subshape correspondence, cross-export matching, best-fit registration, or inferred before/after matching.
- `PLANE` and `CYLINDER` are native. `OTHER` is representable but every unregistered consumer strategy fails closed.
- Capability-dependent fields are omitted when inapplicable. Reject placeholder strings (`N/A`, `UNKNOWN` used as filler), dummy parents, empty parameter objects, and zero-valued tolerance records created only for schema completion.
- No task in this plan starts 07B, field solving, actual slicing, `SliceFieldMap`, toolpath, export, or governance cleanup.
- Use `py -3.12 -m pytest` on the current Windows development hosts. G1 commands must not import or launch FreeCAD/OCCT.
- Each implementation task ends with a narrow commit. Do not push, merge, rebase, reset, or force-push without separate authorization.

## Contract Shapes to Hold Constant

The JSON Schema and semantic validator divide responsibilities deliberately:

- JSON Schema checks shape, types, enums, required core fields, and discriminator-local parameter shape.
- Semantic validation resolves IDs/references, enforces cross-collection membership and applicability, rejects temporary artifact paths, and verifies deterministic IDs.
- Consumer logic turns a valid but unsupported/ambiguous/unbound Snapshot into a stable `SlicerDecision` rejection. It does not reinterpret geometry.

Every authoritative entity geometry reference has this minimum shape:

```json
{
  "artifact_ref": "artifact:...",
  "locator": {
    "scheme": "STEP_OCCURRENCE",
    "value": "product-path-or-persistent-label"
  }
}
```

Allowed locator schemes for v0.1 are intentionally finite: `STEP_OCCURRENCE`, `STEP_FACE`, `BREP_ROOT`, and `CAD_OBJECT`. They locate an entity inside one declared artifact; they do not claim correspondence between different exports.

The release-version rule is:

- G1 publishes examples as `0.1-rc1` and fixes field names/meaning.
- The v0.1 schema accepts only `0.1-rc1` and `0.1.0`.
- At G2, the publisher default changes to `0.1.0`; the immutable rc1 examples remain validation fixtures, and an in-memory version-only promotion test proves that each has identical semantic content under `0.1.0`.
- New publications after G2 use `0.1.0`. No rc1 example is silently rewritten.

## Dependency and Parallelization Map

```text
Tasks 1-6 (sequential contract foundation) -> G1
                                           |
            +------------------------------+---------------------------+
            |                    |                     |                |
        Task 7 E0           Task 8 E1            Task 9 E2         Task 11 E4
                                 |                     |
                          Task 13 I1a prep       Task 10 E3
            |                    |                     |                |
            +--------------------+----------+----------+----------------+
                                              |
                                          Task 12 G2

Task 13 I1a can run as soon as Task 8 is complete.
Task 13 I1b waits for an authorized representative run and a concrete Viewer
boundary, but does not wait for or affect G2.
```

After G1, these lanes may run in separate branches/worktrees without shared file ownership:

- Geometry E0 lane: Task 7, touching only the 02C adapter/test.
- Geometry E1/I1 lane: Task 8, then Task 13, touching the 06B adapter and I1 harness/evidence staging.
- Geometry E2/E3 lane: Tasks 9 then 10, serial within the lane because both extend the 06C adapter.
- Geometry E4 lane: Task 11, touching only the 07A adapter/test.
- Slicer Track: may replace the test mock behind the fixed `SlicerDecision` contract without importing Geometry internals.
- UI Track: may replace the test view-model mock behind its fixed JSON projection without importing Geometry internals.
- Evidence Track: may prepare I1 allowlists and review templates, but promotion execution is not part of G2.

Task 12 is the G2 join. Task 13 is not on that join path.

---

## Task 1: Define the v0.1 schema files and schema-only loader

**Files:**

- Create: `src/dmslicer/geometry_contract/__init__.py`
- Create: `src/dmslicer/geometry_contract/schema.py`
- Create: `src/dmslicer/geometry_contract/schemas/geometry_snapshot.v0.1.schema.json`
- Create: `src/dmslicer/geometry_contract/schemas/slicer_decision.v0.1.schema.json`
- Create: `tests/geometry_contract/test_schema_shape.py`

**Interfaces:**

```python
GEOMETRY_CONTRACT_NAME = "dmslicer.geometry-snapshot"
GEOMETRY_RC_VERSION = "0.1-rc1"
GEOMETRY_RELEASE_VERSION = "0.1.0"
CURRENT_GEOMETRY_VERSION = GEOMETRY_RC_VERSION
SLICER_CONTRACT_NAME = "dmslicer.slicer-decision"

def load_schema(name: Literal["geometry_snapshot", "slicer_decision"]) -> Mapping[str, Any]: ...
def schema_errors(value: Mapping[str, Any], *, schema_name: str) -> tuple[SchemaIssue, ...]: ...
```

The Geometry schema must require only the A-tier root fields: `contract`, `snapshot_id`, `source_documents`, `model_frame`, `regions`, `relations`, `artifact_references`, and `provenance_references`. B-tier collections are optional and become semantically required only when their capability is claimed. Define `$defs` for IDs, units, stable relative artifact URIs, placements, geometry references, source locators, regions, relations, interfaces, components, patches, boundaries, partitions, semantic bindings, and claim-specific tolerance records.

`patch.family` is exactly `PLANE`, `CYLINDER`, or `OTHER`. JSON Schema conditionals require planar parameters only for `PLANE` and cylinder parameters only for `CYLINDER`; they forbid the other native parameter object. `OTHER` carries a non-empty `family_name` and no native parameter object.

The Slicer schema requires common outcome fields (`contract`, `decision_id`, `input_snapshot_id`, `status`, `reason_code`, `provenance_reference`). When `status == DECIDED`, it additionally requires the selection/partition fields from the approved spec. For non-decided outcomes those selection fields are absent, not `null` or placeholder values.

- [ ] Write `tests/geometry_contract/test_schema_shape.py` with one minimum root Snapshot, one planar Snapshot, one cylindrical Snapshot, and one non-decided SlicerDecision. Assert that a minimum root does not require `patches`, `boundaries`, `parent_snapshot_ids`, cylinder parameters, or unused tolerances.
- [ ] Run `py -3.12 -m pytest tests/geometry_contract/test_schema_shape.py -q` and confirm failure because the package/schema files do not exist.
- [ ] Add the two Draft 2020-12 schemas and a loader that resolves them with `importlib.resources`, so installed-package tests do not depend on the repository working directory.
- [ ] Implement deterministic schema findings without echoing the entire rejected payload:

```python
@dataclass(frozen=True)
class SchemaIssue:
    code: str
    path: str
    message: str

def schema_errors(value: Mapping[str, Any], *, schema_name: str) -> tuple[SchemaIssue, ...]:
    validator = Draft202012Validator(load_schema(schema_name))
    return tuple(
        SchemaIssue("SCHEMA_INVALID", ".".join(map(str, error.absolute_path)) or "$", error.message)
        for error in sorted(validator.iter_errors(value), key=lambda error: list(error.absolute_path))
    )
```

- [ ] Add package-data configuration only if the installed-package test proves schemas are missing from a wheel. Keep it to `dmslicer.geometry_contract.schemas/*.json`; do not create a generalized resource registry.
- [ ] Run `py -3.12 -m pytest tests/geometry_contract/test_schema_shape.py -q` and confirm PASS.
- [ ] Commit: `git add src/dmslicer/geometry_contract pyproject.toml tests/geometry_contract/test_schema_shape.py && git commit -m "feat: define geometry and slicer contract schemas"`

## Task 2: Implement deterministic IDs and semantic/reference validation

**Files:**

- Create: `src/dmslicer/geometry_contract/ids.py`
- Create: `src/dmslicer/geometry_contract/validation.py`
- Create: `tests/geometry_contract/test_semantic_validation.py`
- Create: `tests/geometry_contract/test_contract_identity.py`

**Interfaces:**

```python
def snapshot_id(snapshot_without_id: Mapping[str, Any]) -> str: ...
def relation_id(region_ids: Sequence[str], taxonomy: str, confirmation: str) -> str: ...
def interface_id(relation_identifier: str) -> str: ...
def component_id(interface_identifier: str, patch_ids: Sequence[str]) -> str: ...
def partition_id(source_geometry_ref: Mapping[str, Any], role: str, patch_ids: Sequence[str]) -> str: ...
def decision_id(decision_without_id: Mapping[str, Any]) -> str: ...

@dataclass(frozen=True)
class ValidationIssue:
    code: str
    path: str
    message: str

def validate_geometry_snapshot(snapshot: Mapping[str, Any], repository_root: Path) -> tuple[ValidationIssue, ...]: ...
```

`snapshot_id()` canonicalizes only contract-semantic content: it excludes `snapshot_id` and C-tier display/reference metadata, and sorts set-like entity collections by their declared IDs. It does not compare B-reps or infer that entities in two source documents correspond. `relation_id`, `interface_id`, `component_id`, and `partition_id` derive only from already declared IDs and v0.1 discriminators.

Semantic issue codes are fixed at G1:

```text
SCHEMA_INVALID
DUPLICATE_ID
UNRESOLVED_REFERENCE
UNRESOLVED_ARTIFACT
NON_PORTABLE_ARTIFACT_URI
INVALID_INTERFACE_CONFIRMATION
MEMBERSHIP_MISMATCH
CAPABILITY_FIELD_MISSING
CAPABILITY_FIELD_FORBIDDEN
INVALID_SEMANTIC_BINDING
PLACEHOLDER_VALUE
IDENTITY_MISMATCH
```

- [ ] Write failing tests for duplicate IDs, an interface attached to a non-confirmed or non-2D relation, inconsistent interface/component/patch membership, missing planar/cylinder parameters, forbidden cross-family parameters, unresolved artifact IDs/URIs, Windows/absolute/parent-traversal paths, invalid semantic activation, placeholder data, and an incorrect deterministic ID.
- [ ] Add the explicit shared-artifact test: three regions may all point to the same tracked STEP artifact when each has a distinct valid `STEP_OCCURRENCE` locator. Assert that validation does not demand three `REGION_BREP` artifacts.
- [ ] Add the identity-boundary test: reordering regions, relations, interfaces, components, patches, boundaries, partitions, bindings, artifacts, or provenance references does not change `snapshot_id`; changing a semantic member such as patch area does change it. Do not test or implement cross-document correspondence.
- [ ] Run `py -3.12 -m pytest tests/geometry_contract/test_semantic_validation.py tests/geometry_contract/test_contract_identity.py -q` and confirm the expected failures.
- [ ] Implement the six narrow ID functions by calling existing `dmslicer.identity.canonical_digest`; do not alter existing face/solid fingerprint algorithms.
- [ ] Implement schema-first validation, then ID indexing/reference resolution, applicability checks, artifact path resolution under `repository_root`, and deterministic identity recomputation. Keep operation diagnostics and file-content geometry checks out of this validator.
- [ ] Run the two test files and confirm PASS.
- [ ] Commit: `git add src/dmslicer/geometry_contract/ids.py src/dmslicer/geometry_contract/validation.py tests/geometry_contract/test_semantic_validation.py tests/geometry_contract/test_contract_identity.py && git commit -m "feat: validate geometry contract semantics and references"`

## Task 3: Add G1 canonical E0-E2 and negative examples

**Files:**

- Create: `contract_examples/v0.1/geometry/planar_full.json`
- Create: `contract_examples/v0.1/geometry/planar_partial.json`
- Create: `contract_examples/v0.1/geometry/planar_multipatch.json`
- Create: `contract_examples/v0.1/negative/ambiguous_relation.json`
- Create: `contract_examples/v0.1/negative/unsupported_family.json`
- Create: `contract_examples/v0.1/negative/missing_semantic_binding.json`
- Create: `contract_examples/v0.1/negative/unresolved_artifact.json`
- Create only if required for direct recovery: `contract_examples/v0.1/artifacts/*.brep`
- Create: `tests/geometry_contract/test_canonical_examples.py`
- Create: `tests/geometry_contract/test_negative_examples.py`

**Exact example claims:**

| Example | Required contract content | Required measured value |
|---|---|---|
| E0 `planar_full` | A/G and G/B confirmed full-face interfaces; A/B confirmed disjoint; semantic source boundaries | two patch areas of `400 mm2` |
| E1 `planar_partial` | one confirmed partial interface; common and two remaining partitions; active semantic binding | common `480 mm2`; remaining `320/320 mm2` |
| E2 `planar_multipatch` | one confirmed interface; two distinct patches in two distinct components | two patch areas of `192 mm2` |

Each region references its tracked benchmark STEP plus a stable occurrence locator. Do not create per-region BREP files when that pair is recoverable. A patch/partition BREP may be placed in `contract_examples/v0.1/artifacts/` only when its derived entity cannot be recovered from an existing authoritative CAD artifact and locator. Every such file must be individually named, byte-hashed as integrity metadata only, and cited from the example; no directory-wide allowlist.

Negative outcomes are split by layer:

| File | Snapshot validation | Slicer outcome |
|---|---|---|
| `ambiguous_relation.json` | PASS; ambiguous relation is visible and creates no interface | `REJECTED / AMBIGUOUS_INTERFACE` |
| `unsupported_family.json` | PASS; `OTHER` is a valid fail-closed family | `UNSUPPORTED / UNSUPPORTED_GEOMETRY_FAMILY` |
| `missing_semantic_binding.json` | PASS; geometry remains valid without activation | `REJECTED / MISSING_SEMANTIC_BINDING` |
| `unresolved_artifact.json` | FAIL with `UNRESOLVED_ARTIFACT` | `FAILED / INVALID_SNAPSHOT` if presented to a consumer |

- [ ] Write parameterized tests for the three positive claim tables and the four negative layer-specific expectations. First use empty fixture files so tests fail on validation and claim assertions.
- [ ] Run `py -3.12 -m pytest tests/geometry_contract/test_canonical_examples.py tests/geometry_contract/test_negative_examples.py -q` and confirm failure.
- [ ] Project the accepted historical facts into hand-reviewable JSON without importing entire runner `operation` dictionaries. Include stable Goal ID, source commit, fixture path, and evidence URI in `provenance_references`.
- [ ] Resolve every positive artifact URI. Prefer the tracked source STEP plus locator for regions. Add only the minimum derived patch/partition artifacts needed for direct recovery; record their SHA-256 as `byte_integrity_only`.
- [ ] Calculate all entity IDs with the Task 2 functions, then store them as literal golden values. Do not use array indexes or process order.
- [ ] Run both test files and confirm PASS without FreeCAD on `sys.modules` or PATH.
- [ ] Commit: `git add contract_examples/v0.1 tests/geometry_contract/test_canonical_examples.py tests/geometry_contract/test_negative_examples.py && git commit -m "test: add canonical geometry contract examples"`

## Task 4: Add the FreeCAD-free Slicer consumer mock

**Files:**

- Create: `tests/contract_consumers/__init__.py`
- Create: `tests/contract_consumers/slicer_mock.py`
- Create: `tests/contract_consumers/test_slicer_mock.py`

**Interface:**

```python
def decide(snapshot: Mapping[str, Any], repository_root: Path) -> dict[str, Any]:
    """Return one deterministic SlicerDecision without invoking geometry code."""
```

Decision precedence is deterministic:

1. Any schema/semantic/reference issue -> `FAILED / INVALID_SNAPSHOT`.
2. No eligible confirmed interface but an ambiguous relation exists -> `REJECTED / AMBIGUOUS_INTERFACE`.
3. Eligible interface exists but no active target/source semantic binding -> `REJECTED / MISSING_SEMANTIC_BINDING`.
4. Selected patch family `OTHER` or a mixed set containing `OTHER` -> `UNSUPPORTED / UNSUPPORTED_GEOMETRY_FAMILY`.
5. No registered planar/cylindrical strategy -> `UNSUPPORTED / UNSUPPORTED_STRATEGY`.
6. Otherwise select by semantic role then stable ID, never list position, and return `DECIDED`.

For E1 the exact positive fields are:

```python
{
    "status": "DECIDED",
    "reason_code": "NONE",
    "strategy_kind": "PLANAR_INTERFACE_PARTITION",
    "partition_operation": "SPLIT_COMMON_AND_REMAINING",
}
```

- [ ] Write tests showing E1 returns a schema-valid deterministic decision; the three consumer-negative snapshots return their specified outcomes; unresolved artifact returns `FAILED / INVALID_SNAPSHOT`; and collection reversal produces byte-identical canonical decision JSON.
- [ ] Add an import guard test that fails if `FreeCAD`, `Part`, any `freecad_*` module, or a Goal runner enters `sys.modules` while the mock runs.
- [ ] Run `py -3.12 -m pytest tests/contract_consumers/test_slicer_mock.py -q` and confirm failure because the mock does not exist.
- [ ] Implement direct ID-indexed selection and compute `decision_id` with Task 2. Do not call 02C-07A runners or read BREP/STEP geometry.
- [ ] Validate every returned object against `slicer_decision.v0.1.schema.json` inside the test, not by embedding schema knowledge in `decide()`.
- [ ] Run the test file and confirm PASS.
- [ ] Commit: `git add tests/contract_consumers && git commit -m "test: add slicer decision contract mock"`

## Task 5: Add the FreeCAD-free UI consumer mock

**Files:**

- Create: `tests/contract_consumers/ui_mock.py`
- Create: `tests/contract_consumers/test_ui_mock.py`

**Interface:**

```python
def build_view_model(
    snapshot: Mapping[str, Any],
    decision: Mapping[str, Any] | None,
    repository_root: Path,
) -> dict[str, Any]:
    """Build a deterministic display/navigation model from public contracts only."""
```

The view model lists, sorted by stable ID: regions, all relations including ambiguous ones, interfaces, patches, components, applicable boundaries/partitions, semantic activation, selected decision state, and artifact/provenance links. It may include display labels but no display value is fed back into identity or Slicer selection.

- [ ] Write tests for E0 region/interface/disjoint visibility, E2 two-component visibility, the absence of boundaries for E0-E2 when not claimed, ambiguous relation visibility without a fabricated interface, artifact links, and selected E1 decision display.
- [ ] Add reorder invariance and import-guard tests equivalent to the Slicer mock tests.
- [ ] Run `py -3.12 -m pytest tests/contract_consumers/test_ui_mock.py -q` and confirm failure.
- [ ] Implement direct read-only projection from IDs/references. Do not add camera, color, mesh generation, GUI toolkit, service, repository, factory, or event-bus code.
- [ ] Run the test file and confirm PASS.
- [ ] Commit: `git add tests/contract_consumers/ui_mock.py tests/contract_consumers/test_ui_mock.py && git commit -m "test: add ui geometry contract mock"`

## Task 6: Establish and verify G1

**Files:**

- Create: `tests/geometry_contract/test_g1_gate.py`

**G1 test contract:**

```python
G1_POSITIVE = ("planar_full.json", "planar_partial.json", "planar_multipatch.json")
G1_NEGATIVE = {
    "ambiguous_relation.json": ("REJECTED", "AMBIGUOUS_INTERFACE"),
    "unsupported_family.json": ("UNSUPPORTED", "UNSUPPORTED_GEOMETRY_FAMILY"),
    "missing_semantic_binding.json": ("REJECTED", "MISSING_SEMANTIC_BINDING"),
    "unresolved_artifact.json": ("FAILED", "INVALID_SNAPSHOT"),
}
```

- [ ] Write one gate test that loads the literal fixtures, validates positives, checks each negative at its correct layer, runs both mocks, reverses every set-like collection, and compares canonical outputs.
- [ ] Add assertions that no example contains a public operation/result/validator/diagnostic object and no test imported FreeCAD/OCCT.
- [ ] Run the complete FreeCAD-free gate:

```powershell
py -3.12 -m pytest `
  tests/geometry_contract/test_schema_shape.py `
  tests/geometry_contract/test_semantic_validation.py `
  tests/geometry_contract/test_contract_identity.py `
  tests/geometry_contract/test_canonical_examples.py `
  tests/geometry_contract/test_negative_examples.py `
  tests/geometry_contract/test_g1_gate.py `
  tests/contract_consumers/test_slicer_mock.py `
  tests/contract_consumers/test_ui_mock.py `
  -q
```

- [ ] Confirm PASS and capture the exact command, Python/jsonschema/pytest versions, exit code, commit, and timestamp in the implementation handoff. This is a software contract result, not a P2 promotion package or scientific rerun.
- [ ] Run `py -3.12 -m pytest -q` to detect regressions in the existing non-FreeCAD suite.
- [ ] Commit: `git add tests/geometry_contract/test_g1_gate.py && git commit -m "test: establish geometry contract G1 gate"`
- [ ] Stop for G1 review. Do not begin parallel lanes until the G1 fixture IDs, field meanings, issue codes, and consumer reason codes are accepted.

## Task 7: Add the E0 / 02C CASE01 adapter (post-G1 Geometry lane A)

**Files:**

- Create: `src/dmslicer/geometry_contract/adapters/__init__.py`
- Create: `src/dmslicer/geometry_contract/adapters/case01_02c.py`
- Create: `tests/geometry_contract/test_case01_02c_adapter.py`

**Interface:**

```python
def snapshot_from_case01(
    accepted_result: Mapping[str, Any],
    *,
    artifact_uris: Mapping[str, str],
    provenance_uri: str,
) -> dict[str, Any]: ...
```

- [ ] Write a pure unit test from a minimal accepted-result mapping, plus a `@pytest.mark.freecad` conformance test that calls existing `runner.analyze_case01()` in a temporary output directory and compares the adapter's contract-semantic projection with `planar_full.json`.
- [ ] Assert that the adapter rejects any result whose existing 02C validation status is not PASS and emits no Snapshot for it.
- [ ] Run the unit test without the marker and confirm failure because the adapter is absent.
- [ ] Implement direct field projection for regions, relations, two interfaces/patches, semantics, source artifacts, and provenance. Reuse existing stable 02C IDs where their semantics match; derive only missing contract container IDs.
- [ ] Keep raw candidates, elapsed time, FreeCAD diagnostics, and validator details out of the Snapshot.
- [ ] Run the unit test, then the marked conformance test on a FreeCAD-capable host.
- [ ] Commit: `git add src/dmslicer/geometry_contract/adapters tests/geometry_contract/test_case01_02c_adapter.py && git commit -m "feat: project CASE01 into geometry snapshot"`

## Task 8: Add the E1 / 06B P07 adapter (post-G1 Geometry lane B)

**Files:**

- Create: `src/dmslicer/geometry_contract/adapters/partial_overlap_06b.py`
- Create: `tests/geometry_contract/test_partial_overlap_06b_adapter.py`

**Interface:**

```python
def snapshot_from_p07(
    accepted_result: Mapping[str, Any],
    *,
    source_artifact_uri: str,
    derived_artifact_uris: Mapping[str, str],
    provenance_uri: str,
) -> dict[str, Any]: ...
```

- [ ] Write a pure projection test and a `@pytest.mark.freecad` test using existing `run_partial_overlap_case(FIXTURE_ROOT, "P07", output_root)`.
- [ ] Assert exact common/remaining values (`480`, `320`, `320` mm2), conservation links, active semantic selection, schema/reference validity, and contract-semantic equality with `planar_partial.json`.
- [ ] Add a rejected-result test proving P09/private preview diagnostics cannot publish a Snapshot.
- [ ] Run the unit test and confirm the missing-adapter failure.
- [ ] Implement only the P07 fields needed by E1/Slicer. Do not expose the runner's internal `decision`, `fuse`, `pose_invariants`, debug view, or validator report wholesale.
- [ ] Reuse the shared source STEP for both regions. Require a derived BREP reference only for a common/remaining entity that lacks a recoverable locator.
- [ ] Run unit and marked conformance tests; confirm the G1 Slicer/UI mocks still pass unchanged against the runtime-projected Snapshot.
- [ ] Commit: `git add src/dmslicer/geometry_contract/adapters/partial_overlap_06b.py tests/geometry_contract/test_partial_overlap_06b_adapter.py && git commit -m "feat: project P07 into geometry snapshot"`

## Task 9: Add the E2 / 06C P10 adapter (post-G1 Geometry lane C, stage 1)

**Files:**

- Create: `src/dmslicer/geometry_contract/adapters/multipatch_06c.py`
- Create: `tests/geometry_contract/test_multipatch_06c_adapter.py`

**Interface:**

```python
def snapshot_from_06c(
    scenario_id: Literal["P10", "P11"],
    accepted_result: Mapping[str, Any],
    *,
    source_artifact_uri: str,
    derived_artifact_uris: Mapping[str, str],
    provenance_uri: str,
) -> dict[str, Any]: ...
```

- [ ] Start with P10 tests only: two `192 mm2` patches remain distinct, each belongs to exactly one interface component, and reversing Goal traversal order preserves contract IDs/content.
- [ ] Add a marked conformance test using existing `run_multipatch_case(FIXTURE_ROOT, "P10", output_root)`.
- [ ] Run the P10 tests and confirm the missing-adapter failure.
- [ ] Implement P10 projection from accepted `face_sets`, `partition`, `topology`, and provenance fields. Ignore output list position; key member identity from existing source/member IDs and contract IDs.
- [ ] Do not introduce an abstract adapter base class. Keep 06C-specific mapping in this module.
- [ ] Run P10 tests and unchanged G1 consumer tests; confirm PASS.
- [ ] Commit: `git add src/dmslicer/geometry_contract/adapters/multipatch_06c.py tests/geometry_contract/test_multipatch_06c_adapter.py && git commit -m "feat: project P10 multipatch snapshot"`

## Task 10: Extend the 06C adapter for E3 / P11 annular capability (post-G1 Geometry lane C, stage 2)

**Files:**

- Modify: `src/dmslicer/geometry_contract/adapters/multipatch_06c.py`
- Modify: `tests/geometry_contract/test_multipatch_06c_adapter.py`
- Create: `contract_examples/v0.1/geometry/planar_annular.json`
- Add only if needed: `contract_examples/v0.1/artifacts/planar_annular*.brep`
- Create: `tests/geometry_contract/test_planar_annular_example.py`

- [ ] Write failing tests requiring one patch/component, area `300 * pi mm2` within the claim's declared area tolerance, one `OUTER` and one `INNER` closed boundary, and hole count one.
- [ ] Assert boundary/hole data is absent from E0-E2 and required only for this P11 claim.
- [ ] Add a marked conformance test using `run_multipatch_case(FIXTURE_ROOT, "P11", output_root)` and compare its projection to the canonical example.
- [ ] Run the new tests and confirm failure before P11 mapping/example exists.
- [ ] Extend the existing 06C adapter with one explicit P11 branch. Preserve analytic boundary family and geometry references; do not implement arbitrary loop nesting or a generalized topology service.
- [ ] Populate only the linear/area tolerances actually used by P11 validation.
- [ ] Run P10/P11 adapter tests, all positive/negative example tests, and both G1 consumer mocks. Confirm no G1 breaking change.
- [ ] Commit: `git add src/dmslicer/geometry_contract/adapters/multipatch_06c.py tests/geometry_contract/test_multipatch_06c_adapter.py contract_examples/v0.1/geometry/planar_annular.json contract_examples/v0.1/artifacts tests/geometry_contract/test_planar_annular_example.py && git commit -m "feat: add annular geometry snapshot capability"`

## Task 11: Add the E4 / 07A C01-C02 cylindrical and lineage adapter (post-G1 Geometry lane D)

**Files:**

- Create: `src/dmslicer/geometry_contract/adapters/cylindrical_07a.py`
- Create: `contract_examples/v0.1/geometry/cylindrical.json`
- Add only if needed: `contract_examples/v0.1/artifacts/cylindrical*.brep`
- Create: `tests/geometry_contract/test_cylindrical_07a_adapter.py`
- Create: `tests/geometry_contract/test_cylindrical_example.py`

**Interface:**

```python
def snapshots_from_c01_c02(
    c01_result: Mapping[str, Any],
    c02_result: Mapping[str, Any],
    *,
    artifact_uris: Mapping[str, str],
    provenance_uris: Mapping[str, str],
) -> tuple[dict[str, Any], dict[str, Any]]: ...
```

- [ ] Write failing tests for axis origin/direction, radius, axial interval, periodic state, applicable units/tolerances, and C02 descendant `parent_snapshot_ids == [c01_snapshot_id]`.
- [ ] Test C01 as a root Snapshot with no `parent_snapshot_ids` field. Test that plane parameters and boundary/hole data are absent unless independently claimed.
- [ ] Add marked tests using existing `run_cylindrical_repair_case()` for C01 and C02. Require existing validation PASS before publication.
- [ ] Add the critical identity-scope test: the adapter uses the authorized 07A before/after relationship supplied by the Goal; it must not search source subshapes or infer correspondence from fingerprints/hashes.
- [ ] Run tests and confirm missing-adapter/example failures.
- [ ] Implement C01/C02 projection and stable lineage IDs. Keep correction vectors, failure diagnostics, postcheck details, and validator output in Evidence references rather than Snapshot fields.
- [ ] Ensure file SHA-256 is labeled byte integrity only and never used to assert C01/C02 geometry equivalence.
- [ ] Run E4 tests, then all G1 tests unchanged.
- [ ] Commit: `git add src/dmslicer/geometry_contract/adapters/cylindrical_07a.py contract_examples/v0.1/geometry/cylindrical.json contract_examples/v0.1/artifacts tests/geometry_contract/test_cylindrical_07a_adapter.py tests/geometry_contract/test_cylindrical_example.py && git commit -m "feat: add cylindrical geometry snapshot capability"`

## Task 12: Verify and freeze G2 without Evidence Track coupling

**Files:**

- Modify: `src/dmslicer/geometry_contract/schema.py`
- Create: `tests/geometry_contract/test_g2_gate.py`

**G2 assertions:**

```text
E0-E4 runtime adapters and examples validate against the same v0.1 schema
E3 boundaries/hole and E4 cylinder/lineage semantics pass
Every G1 mock and negative reason remains unchanged
Publisher default is 0.1.0
No consumer import reaches adapters, Goal runners, FreeCAD, or P2 internals
No P2 package or promotion status is inspected
```

- [ ] Write a failing G2 test that loads E0-E4 rc1 examples, clones each in memory with `contract.version = "0.1.0"`, recomputes the version-sensitive publication and decision IDs, and asserts that all non-ID semantic selections/rejections are unchanged. Separately assert that the untouched literal rc1 examples still produce their byte-identical G1 outputs.
- [ ] Add import-boundary tests: `tests/contract_consumers` may import only `schema`, `validation`, and `ids` from the contract package, never `adapters`, 02C-07A runners, `FreeCAD`, or `evidence_promotion`.
- [ ] Add a test that monkeypatches P2 promotion APIs to raise if called; G2 must still pass.
- [ ] Run `py -3.12 -m pytest tests/geometry_contract/test_g2_gate.py -q` and confirm failure while the default publisher version is rc1.
- [ ] Change the publication default constant to `0.1.0`; do not delete rc1 schema compatibility or rewrite literal rc1 examples.
- [ ] Run the complete G1 suite plus E0-E4 unit/conformance tests and `test_g2_gate.py`. Run FreeCAD-marked adapter tests on the recorded FreeCAD/OCCT host.
- [ ] Run `py -3.12 -m pytest -q` for repository regression coverage.
- [ ] Record G2 command, versions, commit, exit code, and timestamp as ordinary Goal evidence. Do not create or require a P2 promotion package.
- [ ] Commit: `git add src/dmslicer/geometry_contract/schema.py tests/geometry_contract/test_g2_gate.py && git commit -m "feat: freeze geometry snapshot v0.1.0 compatibility"`
- [ ] Stop for G2 review. Any new required core field or changed semantic meaning after this point requires a separately reviewed `0.2.0` design.

## Task 13: Prepare and later execute I1 as an independent P07 integration-evidence gate

This task has two checkpoints. I1a may proceed after Task 8 and in parallel with Tasks 10-12. I1b requires separate authorization to execute the representative run and requires a concrete Viewer boundary compatible with the G1 UI projection. Neither checkpoint changes G1/G2 status.

**Files:**

- Create: `scripts/architecture_contract/run_i1_p07.py`
- Create: `tests/geometry_contract/test_i1_p07_integration.py`
- Create at run time only: `outputs/architecture-contract-i1/<run_id>/...`
- Create at authorized promotion time only: `evidence/<goal_id>/<implementation_commit>/<run_id>/...`

**Concrete flow:**

```python
def run_i1_p07(
    repository_root: Path,
    output_root: Path,
    *,
    run_id: str,
    implementation_commit: str,
) -> dict[str, Any]:
    """P07 runner -> Snapshot -> SlicerDecision -> Viewer projection -> P2 request."""
```

The staged allowlist is individual files only:

```text
geometry_snapshot.json
slicer_decision.json
viewer_projection.json
validator_result.json
scientific_result.json
pytest_result.json or junit.xml
VIEW_INDEX.md
HUMAN_REVIEW.md
promotion_request.json
```

CAD/STEP/BREP/FCStd files are included only when the P07 integration claim actually depends on them. Large or duplicate historical outputs are not copied merely because they exist.

### I1a - harness preparation

- [ ] Write an integration test with the existing P07 runner stubbed by an accepted-result fixture. Assert reference continuity: P07 source artifact -> Snapshot ID -> Decision input/selection IDs -> Viewer selected IDs -> P2 allowlist artifact IDs.
- [ ] Assert the harness records software validation, scientific P07 validation, human review, preservation, and publication as separate result domains.
- [ ] Assert a failed Geometry run writes failure evidence but publishes no Snapshot; a failed Viewer/evidence stage cannot rewrite G1/G2 status.
- [ ] Run `py -3.12 -m pytest tests/geometry_contract/test_i1_p07_integration.py -q` and confirm failure before the harness exists.
- [ ] Implement the concrete P07 harness using `run_partial_overlap_case`, `snapshot_from_p07`, the accepted Slicer consumer boundary, and the accepted Viewer projection. Write with existing `dmslicer.evidence.write_json`.
- [ ] Build a P2 `promotion_request.json` that references the staged files, then call existing `dmslicer.evidence_promotion` policy/promotion APIs. Do not copy P2 schema fields into GeometrySnapshot or SlicerDecision.
- [ ] Make dry-run/test mode stop after request validation; it must not install a stable package.
- [ ] Run the stubbed integration test and confirm PASS.
- [ ] Commit: `git add scripts/architecture_contract/run_i1_p07.py tests/geometry_contract/test_i1_p07_integration.py && git commit -m "feat: prepare P07 I1 integration harness"`

### I1b - separately authorized representative run

- [ ] Verify the selected Viewer is a concrete boundary compatible with the G1 UI projection. If only the mock exists, report I1 as not yet established; do not relabel a unit mock as production Viewer evidence.
- [ ] Run the existing P07 Goal once in a fresh `outputs/architecture-contract-i1/<run_id>/` staging directory on a recorded FreeCAD/OCCT host.
- [ ] Run Snapshot validation, SlicerDecision validation, Viewer reference checks, and pytest/JUnit capture. Confirm every ID/reference resolves without array-position fallback.
- [ ] Complete `HUMAN_REVIEW.md` and `VIEW_INDEX.md` for the representative artifacts; keep UI/display findings separate from geometry claims.
- [ ] Validate the explicit P2 allowlist and promotion request. Preserve any rejection/failure package rather than overwriting it.
- [ ] When authorized, invoke the existing P2 local promotion path and verify immutable destination, manifest schema, copy recount, byte-integrity labeling, and preservation/publication statuses.
- [ ] Report I1 independently as PASS or FAIL. A FAIL blocks only the representative integration-evidence claim; it does not alter G1 or G2.
- [ ] Commit only small allowlisted manifests/review notes if the Evidence Goal authorizes Git storage. Do not add all of `outputs/`, large CAD artifacts, or historical evidence wholesale.

## Final Verification Before Any Completion Claim

- [ ] Run `git diff --check`.
- [ ] Run the exact G1 suite and confirm it remains FreeCAD-free.
- [ ] If claiming G2, run all E0-E4 adapter/example tests, including the marked FreeCAD conformance tests, plus the entire G1 suite and repository regression suite.
- [ ] If claiming I1, inspect the generated P2 manifest and copy inventory and report its custody status exactly; do not say “fully preserved” unless the P2 conditions actually establish it.
- [ ] Search for forbidden coupling and placeholders:

```powershell
rg -n "GeometryOperationEnvelope|FreeCAD|Part|evidence_promotion|N/A|TODO|TBD" `
  src/dmslicer/geometry_contract `
  tests/contract_consumers `
  contract_examples/v0.1
```

- [ ] Review every match. `FreeCAD` may appear only in post-G1 marked adapter/integration tests or explicit import guards; `evidence_promotion` may appear only in I1; `GeometryOperationEnvelope`, `N/A`, `TODO`, and `TBD` must not appear in implemented contract payloads/code.
- [ ] Run `git status --short --branch` and list every changed file. Confirm no changes to `AGENTS.md`, `README.md`, `docs/research_v2/`, historical evidence, or unrelated source/tests.
- [ ] Stop and present the relevant gate evidence for review. Do not push, merge, start 07B, or proceed to the next gate without authorization.
