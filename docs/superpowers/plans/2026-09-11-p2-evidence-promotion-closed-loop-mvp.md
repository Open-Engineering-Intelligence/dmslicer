# P2 Evidence Promotion Closed-Loop MVP Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Prove and promote one UI-only CAD mutation and one real hole-radius mutation while keeping byte, geometry, semantic, UI, test, scientific, and human-review results separate.

**Architecture:** Extend the existing P2 promotion package with one host-side CAD orchestration module, one FreeCAD worker, and one versioned schema covering three independent snapshots plus comparison evidence. Reuse the existing explicit-allowlist, copy-verification, no-overwrite, sensitive-content, failure-retention, and manifest pipeline; add only the checks required to admit artifact-backed Case A/B claims.

**Tech Stack:** Python 3.12, pytest 8.4.2, jsonschema draft 2020-12, FreeCAD 1.1.1, OCCT 7.8.1, `pathlib`, `subprocess`, FreeCAD `Part`, PowerShell, and GitHub Actions.

**Spec:** `docs/superpowers/specs/2026-09-10-p2-evidence-promotion-semantic-snapshot-closed-loop-mvp-design.md`

## Global Constraints

- Formal baseline: `feat/cylindrical-interface-repairability@d65ac32e04115e5627f1c2988fd486e2353cada9`; merge reconciliation commit: `83fde03f71553ff0db1752d90405a96176e45f6b`.
- Work only in `D:\Agent\worktrees\dmslicer-p2-evidence-promotion` on `feat/evidence-promotion-semantic-snapshot`.
- SHA-256 is byte identity/copy integrity only and is never a geometry predicate.
- Keep byte, geometry, semantic, UI, pytest, validator, scientific, and human-review results independent.
- Emit separate immutable `geometry_semantic_snapshot`, `topology_snapshot`, and `ui_state_snapshot` JSON artifacts.
- Every tolerance has a finite numeric value, unit, role, and source.
- Geometry truth comes from reopened B-rep/FreeCAD shapes, never a display mesh or JSON digest.
- Use only the fixture-specific component role `fixture_body`, interface role `through_hole_wall`, and allowed transform `IDENTITY`.
- General subshape correspondence, arbitrary descriptors, Hausdorff metrics, registration, general manifold/loop inference, and universal CAD abstractions are out of scope.
- Preserve `docs/research_v2/`, the historical v1.1.0 schema, all 13 historical manifests, and the two already-promoted P2-MVP manifests byte-for-byte.
- Promotion reads only explicitly allowlisted files below `outputs/` or `work/`, refuses overwrite, preserves failures, and does not delete sources.
- Two local paths are `LOCAL_TWO_PATHS_NOT_OFF_HOST_REDUNDANCY` and `NOT_FULLY_PRESERVED`.
- Do not modify 07A implementation unless a separately documented integration defect makes it unavoidable.
- Do not merge the PR or start 07A/07B follow-on work.
- Follow red-green-refactor for every production behavior; before each test, name the production mutation it catches.

---

### Task 1: Versioned CAD evidence contract and pure comparison boundaries

**Files:**
- Create: `docs/evidence_preservation/schemas/cad_evidence.schema.json`
- Create: `src/dmslicer/evidence_promotion/cad_evidence.py`
- Modify: `src/dmslicer/evidence_promotion/models.py`
- Create: `tests/test_cad_evidence_schema.py`
- Create: `tests/test_cad_evidence.py`

**Interfaces:**
- Produces constants `GEOMETRY_EQUIVALENT`, `GEOMETRY_DIFFERENT`, `SEMANTIC_EQUIVALENT`, `SEMANTIC_DIFFERENT`, `UI_SAME`, `UI_DIFFERENT`, and `UI_COMPARISON_NOT_PROVEN` in `models.py`.
- Produces `validate_cad_artifact(value: Mapping[str, Any]) -> list[str]`.
- Produces `within_tolerance(measured: float, tolerance: Mapping[str, Any], expected_unit: str) -> bool`.
- Produces `compare_semantics(first: Mapping[str, Any], second: Mapping[str, Any]) -> dict[str, Any]`.
- Produces `compare_ui_states(first: Mapping[str, Any], second: Mapping[str, Any]) -> dict[str, Any]`.
- Later tasks consume the same artifact keys and status constants.

- [ ] **Step 1: Write schema tests that fail because the schema and module do not exist**

Name the breaks: accepting a snapshot without units, collapsing snapshot types, accepting non-finite evidence, or treating a JSON digest as geometry proof.

Create literal valid examples for each `artifact_type` and assert the new schema accepts them:

```python
def measured(value: float, unit: str) -> dict[str, object]:
    return {"value": value, "unit": unit}


def test_geometry_snapshot_requires_unit_bearing_actual_measurements() -> None:
    snapshot = geometry_snapshot_literal()
    _cad_validator().validate(snapshot)
    del snapshot["shape"]["volume"]["unit"]
    with pytest.raises(ValidationError):
        _cad_validator().validate(snapshot)


def test_snapshot_types_remain_separate() -> None:
    geometry = geometry_snapshot_literal()
    geometry["artifact_type"] = "ui_state_snapshot"
    with pytest.raises(ValidationError):
        _cad_validator().validate(geometry)


def test_geometry_comparison_forbids_sha_as_method() -> None:
    comparison = geometry_comparison_literal("GEOMETRY_EQUIVALENT")
    comparison["method"] = "SHA256_EQUALITY"
    with pytest.raises(ValidationError):
        _cad_validator().validate(comparison)
```

- [ ] **Step 2: Run the schema tests and verify RED**

Run:

```powershell
py -3.12 -m pytest tests/test_cad_evidence_schema.py -q
```

Expected: collection/import failure because `cad_evidence.py` and `cad_evidence.schema.json` do not exist.

- [ ] **Step 3: Add the single discriminated CAD evidence schema and status constants**

Implement one schema version `1.0.0` with a top-level `oneOf` keyed by `artifact_type`. The four literal types are:

```json
[
  "geometry_semantic_snapshot",
  "topology_snapshot",
  "ui_state_snapshot",
  "geometry_comparison"
]
```

Use a shared measurement definition:

```json
{
  "type": "object",
  "additionalProperties": false,
  "required": ["value", "unit"],
  "properties": {
    "value": {"type": "number"},
    "unit": {"enum": ["mm", "mm2", "mm3", "rad", "count", "unitless"]}
  }
}
```

Require `method: "BREP_BOOLEAN_AND_MEASUREMENTS"` for proven geometry results and the fixed SHA role `file_and_copy_integrity_only_not_geometry_equivalence`. UI unsupported fields use `{ "status": "UNSUPPORTED", "reason": <non-empty string> }` rather than a numeric placeholder.

- [ ] **Step 4: Write failing pure comparison tests**

Name the breaks: a boolean used as a number, a unit mismatch, the wrong inclusive boundary, missing fixture semantics accepted as PASS, or a UI difference altering geometry state.

```python
@pytest.mark.parametrize(
    ("delta", "expected"),
    [(0.000999, True), (0.001, True), (0.001001, False)],
)
def test_tolerance_boundary_is_inclusive(delta: float, expected: bool) -> None:
    tolerance = {"value": 0.001, "unit": "mm", "role": "bbox", "source": "P2 fixture"}
    assert within_tolerance(delta, tolerance, "mm") is expected


def test_semantics_support_only_the_fixture_binding() -> None:
    binding = {
        "component_role": "fixture_body",
        "interface_role": "through_hole_wall",
        "allowed_transform": "IDENTITY",
    }
    assert compare_semantics(binding, dict(binding))["status"] == "SEMANTIC_EQUIVALENT"
    missing = dict(binding)
    del missing["interface_role"]
    assert compare_semantics(binding, missing)["status"] == "SEMANTIC_EQUIVALENCE_NOT_PROVEN"


def test_ui_difference_is_reported_only_in_ui_domain() -> None:
    first = ui_snapshot_literal(visibility=True, color=[0.8, 0.8, 0.8], transparency=0)
    second = ui_snapshot_literal(visibility=False, color=[0.2, 0.4, 0.8], transparency=60)
    result = compare_ui_states(first, second)
    assert result["status"] == "UI_DIFFERENT"
    assert "geometry" not in result
```

- [ ] **Step 5: Run the pure tests and verify RED**

Run:

```powershell
py -3.12 -m pytest tests/test_cad_evidence.py -q
```

Expected: import failures for the missing comparison functions.

- [ ] **Step 6: Implement the minimal pure functions**

Implement strict finite-number handling and exact fixture semantics:

```python
def within_tolerance(measured, tolerance, expected_unit):
    value = measured
    limit = tolerance.get("value")
    if isinstance(value, bool) or isinstance(limit, bool):
        raise ValueError("tolerance inputs must be finite numbers")
    if not isinstance(value, (int, float)) or not math.isfinite(float(value)):
        raise ValueError("measured value must be finite")
    if not isinstance(limit, (int, float)) or not math.isfinite(float(limit)) or limit < 0:
        raise ValueError("tolerance value must be finite and nonnegative")
    if tolerance.get("unit") != expected_unit:
        raise ValueError("tolerance unit does not match measurement")
    return abs(float(value)) <= float(limit)
```

`compare_semantics` returns NOT_PROVEN for absent/unknown fields, DIFFERENT for a proven mismatch, and EQUIVALENT only for the three exact required fields. `compare_ui_states` compares only supported `visibility`, `shape_color`, and `transparency`, returns NOT_PROVEN if any required property is unreadable, and never emits a geometry field.

- [ ] **Step 7: Run focused and historical-schema tests and verify GREEN**

Run:

```powershell
py -3.12 -m pytest tests/test_cad_evidence_schema.py tests/test_cad_evidence.py tests/test_schema_contracts.py -q
```

Expected: PASS, including validation of all 13 historical manifests.

- [ ] **Step 8: Commit Task 1**

```powershell
git add docs/evidence_preservation/schemas/cad_evidence.schema.json src/dmslicer/evidence_promotion/models.py src/dmslicer/evidence_promotion/cad_evidence.py tests/test_cad_evidence_schema.py tests/test_cad_evidence.py
git commit -m "feat: define fixture-scoped CAD evidence contracts"
```

---

### Task 2: Actual FreeCAD fixture and immutable snapshots

**Files:**
- Create: `src/dmslicer/evidence_promotion/freecad_cad_evidence.py`
- Modify: `src/dmslicer/evidence_promotion/cad_evidence.py`
- Create: `tests/test_cad_demo.py`

**Interfaces:**
- Produces `run_freecad_worker(request: Mapping[str, Any], output_root: Path, *, gui: bool) -> dict[str, Any]` in `cad_evidence.py`.
- Produces the initial `generate_demo(output_root: Path) -> dict[str, Any]` generation/snapshot flow; Task 3 extends its result with comparisons.
- FreeCAD worker accepts operations `generate_fixture_set` and `snapshot_and_compare` through a JSON request path and writes one JSON response path.
- Produces CAD files under `<output_root>/cad/{original,ui_only_changed,geometry_changed}/`.
- Produces separate snapshot files under `<output_root>/snapshots/<case>/`.

- [ ] **Step 1: Write the failing real-FreeCAD fixture test**

Name the breaks: using an in-memory primitive without save/reopen, overwriting the original, missing BREP/STEP/FCStd, or reporting geometry from a display mesh.

Mark the test `@pytest.mark.freecad` and skip only when the required executable is absent:

```python
@pytest.mark.freecad
def test_demo_generates_three_distinct_reopenable_cad_sets(tmp_path: Path) -> None:
    result = generate_demo(tmp_path / "demo")
    assert result["status"] == "PASS"
    for case in ("original", "ui_only_changed", "geometry_changed"):
        case_root = tmp_path / "demo" / "cad" / case
        assert (case_root / "fixture.FCStd").is_file()
        assert (case_root / "fixture.brep").is_file()
        assert (case_root / "fixture.step").is_file()
```

Do not assert byte equality for any CAD serialization. The later geometry result comes from actual reopened-shape comparison.

- [ ] **Step 2: Run the fixture test and verify RED**

Run:

```powershell
py -3.12 -m pytest tests/test_cad_demo.py::test_demo_generates_three_distinct_reopenable_cad_sets -q
```

Expected: import failure because `generate_demo` and the worker do not exist.

- [ ] **Step 3: Implement the FreeCAD fixture generator and host launcher**

The worker creates a fixed block and subtracts a through-cylinder:

```python
def _fixture_shape(Part, radius_mm):
    block = Part.makeBox(40.0, 30.0, 12.0)
    bore = Part.makeCylinder(radius_mm, 12.0, FreeCAD.Vector(20.0, 15.0, 0.0))
    return block.cut(bore).removeSplitter()
```

Use nominal radius `4.0 mm` for `original` and `ui_only_changed`, and `5.0 mm` for `geometry_changed`. Save each case to a new directory. The GUI-capable run sets original UI to visible, neutral color, transparency 0; it sets the UI-only case to a different color, transparency 60, and visibility false before saving. It never edits the original file.

The host launcher uses list-form `subprocess.run`, a unique temporary request/response directory, and a timeout. It selects `FreeCAD.exe` for the GUI generation operation and `FreeCADCmd.exe` for headless reopen/comparison. It returns a public-safe error code without echoing a private absolute path.

- [ ] **Step 4: Write failing snapshot extraction tests**

Name the breaks: snapshots emitted as one combined object, topology inferred from list indexes, a missing unit, or saved UI properties not surviving reopen.

```python
@pytest.mark.freecad
def test_each_case_emits_three_schema_valid_snapshots(tmp_path: Path) -> None:
    generate_demo(tmp_path / "demo")
    validator = _cad_validator()
    for case in ("original", "ui_only_changed", "geometry_changed"):
        paths = [
            tmp_path / "demo/snapshots" / case / "geometry_semantic_snapshot.json",
            tmp_path / "demo/snapshots" / case / "topology_snapshot.json",
            tmp_path / "demo/snapshots" / case / "ui_state_snapshot.json",
        ]
        values = [read_json(path) for path in paths]
        assert [value["artifact_type"] for value in values] == [
            "geometry_semantic_snapshot",
            "topology_snapshot",
            "ui_state_snapshot",
        ]
        for value in values:
            validator.validate(value)


@pytest.mark.freecad
def test_ui_properties_survive_actual_fcstd_reopen(tmp_path: Path) -> None:
    generate_demo(tmp_path / "demo")
    original = read_json(tmp_path / "demo/snapshots/original/ui_state_snapshot.json")
    changed = read_json(tmp_path / "demo/snapshots/ui_only_changed/ui_state_snapshot.json")
    assert compare_ui_states(original, changed)["status"] == "UI_DIFFERENT"
```

- [ ] **Step 5: Run snapshot tests and verify RED**

Run:

```powershell
py -3.12 -m pytest tests/test_cad_demo.py -k "snapshot or ui_properties" -q
```

Expected: files or required schema fields are missing.

- [ ] **Step 6: Implement fixture-scoped snapshot extraction**

After reopening each FCStd, extract one `Part::Feature` named `FixtureBody`; reject zero or multiple candidates. Record counts, area, volume, bounding box, validity, closedness, and explicit fixture roles. Select the through-hole wall only when exactly one cylindrical face has radius equal to the declared case radius within `0.001 mm`; otherwise record through-hole status `UNKNOWN` with a reason.

Extract saved UI properties from the reopened GUI document. For display mode/camera, emit `UNSUPPORTED` with the observed reason if the build does not expose a stable saved value. Do not substitute defaults for missing required color/transparency/visibility.

- [ ] **Step 7: Run Task 2 tests and verify GREEN**

```powershell
py -3.12 -m pytest tests/test_cad_demo.py -k "generates or snapshot or ui_properties" -q
py -3.12 -m pytest tests/test_cad_evidence_schema.py tests/test_cad_evidence.py -q
```

- [ ] **Step 8: Commit Task 2**

```powershell
git add src/dmslicer/evidence_promotion/cad_evidence.py src/dmslicer/evidence_promotion/freecad_cad_evidence.py tests/test_cad_demo.py
git commit -m "feat: generate immutable CAD evidence snapshots"
```

---

### Task 3: Case A/B B-rep comparison and serialization regression

**Files:**
- Modify: `src/dmslicer/evidence_promotion/freecad_cad_evidence.py`
- Modify: `src/dmslicer/evidence_promotion/cad_evidence.py`
- Modify: `tests/test_cad_evidence.py`
- Modify: `tests/test_cad_demo.py`

**Interfaces:**
- Produces `generate_demo(output_root: Path) -> dict[str, Any]` with separate `case_a`, `case_b`, and `serialization` results.
- Produces `comparisons/case_a_ui_only.json`, `comparisons/case_b_geometry_changed.json`, and `comparisons/serialization_reopen.json`.
- Geometry comparison uses actual FreeCAD `Shape.cut`, `Shape.distToShape`, topology counts, area, volume, and bounding boxes.

- [ ] **Step 1: Write failing Case A test**

Name the breaks: byte inequality forcing geometry failure, UI properties leaking into geometry comparison, skipped Boolean cuts, or missing semantic evidence.

```python
@pytest.mark.freecad
def test_case_a_proves_geometry_and_semantics_while_ui_differs(tmp_path: Path) -> None:
    result = generate_demo(tmp_path / "demo")
    case = result["case_a"]
    assert case["geometry_status"] == "GEOMETRY_EQUIVALENT"
    assert case["semantic_status"] == "SEMANTIC_EQUIVALENT"
    assert case["ui_status"] == "UI_DIFFERENT"
    assert case["byte_status"] in {"BYTE_SAME", "BYTE_DIFFERENT"}
    comparison = read_json(tmp_path / "demo/comparisons/case_a_ui_only.json")
    assert comparison["sha256_role"] == "file_and_copy_integrity_only_not_geometry_equivalence"
    assert comparison["measurements"]["first_minus_second_volume"]["value"] <= 0.001
    assert comparison["measurements"]["second_minus_first_volume"]["value"] <= 0.001
```

- [ ] **Step 2: Run Case A and verify RED**

```powershell
py -3.12 -m pytest tests/test_cad_demo.py::test_case_a_proves_geometry_and_semantics_while_ui_differs -q
```

Expected: comparison is absent or cannot return GEOMETRY_EQUIVALENT.

- [ ] **Step 3: Implement the minimum-sufficient geometry predicate**

For valid closed single solids, compare:

```python
checks = {
    "topology_counts": first_counts == second_counts,
    "area_delta": abs(first.Area - second.Area) <= area_tolerance_mm2,
    "volume_delta": abs(first.Volume - second.Volume) <= volume_tolerance_mm3,
    "bounding_box": max_bbox_delta_mm <= linear_tolerance_mm,
    "first_minus_second": first.cut(second).Volume <= volume_tolerance_mm3,
    "second_minus_first": second.cut(first).Volume <= volume_tolerance_mm3,
}
```

Return EQUIVALENT only if every required operation executed and every check passed. Return DIFFERENT when an executed measurement exceeds a threshold. Return NOT_PROVEN on invalid shapes, ambiguous fixture binding, or Boolean-operation failure. Record all values and units in the comparison JSON.

- [ ] **Step 4: Write failing Case B and threshold tests**

Name the breaks: using a changed hash as the failure reason, accepting the larger hole because topology matches, or making the boundary exclusive.

```python
@pytest.mark.freecad
def test_case_b_reports_actual_geometry_measurement_reasons(tmp_path: Path) -> None:
    result = generate_demo(tmp_path / "demo")
    case = result["case_b"]
    assert case["geometry_status"] == "GEOMETRY_DIFFERENT"
    comparison = read_json(tmp_path / "demo/comparisons/case_b_geometry_changed.json")
    assert "SHA" not in " ".join(comparison["reasons"]).upper()
    assert any(
        check in comparison["failed_checks"]
        for check in ("area_delta", "volume_delta", "first_minus_second", "second_minus_first")
    )
    assert comparison["measurements"]["volume_delta"]["unit"] == "mm3"
```

Extend the pure threshold parameterization to `mm2` and `mm3` and verify inside/on/outside values.

- [ ] **Step 5: Run Case B and threshold tests and verify RED**

```powershell
py -3.12 -m pytest tests/test_cad_demo.py::test_case_b_reports_actual_geometry_measurement_reasons tests/test_cad_evidence.py -q
```

- [ ] **Step 6: Implement Case B classification and literal measurement reasons**

Use reason codes such as `VOLUME_DELTA_EXCEEDS_TOLERANCE`, `AREA_DELTA_EXCEEDS_TOLERANCE`, `FIRST_MINUS_SECOND_VOLUME_EXCEEDS_TOLERANCE`, and `SECOND_MINUS_FIRST_VOLUME_EXCEEDS_TOLERANCE`. Never generate a reason from a digest field.

- [ ] **Step 7: Write and implement the serialization/reopen regression**

Name the break: a save/reopen byte difference directly setting geometry status.

```python
@pytest.mark.freecad
def test_serialization_reopen_geometry_is_not_decided_by_bytes(tmp_path: Path) -> None:
    result = generate_demo(tmp_path / "demo")
    serialization = result["serialization"]
    assert serialization["byte_status"] in {"BYTE_SAME", "BYTE_DIFFERENT"}
    assert serialization["geometry_status"] == "GEOMETRY_EQUIVALENT"
    assert serialization["geometry_decision_inputs"] == [
        "topology",
        "area",
        "volume",
        "bounding_box",
        "bidirectional_boolean_cut",
    ]
```

Save to `cad/serialization_reopen/fixture.FCStd`, reopen, snapshot, and compare against original through the same actual B-rep path. Also retain the pure policy test where a literal `BYTE_DIFFERENT` coexists with geometry equivalent.

- [ ] **Step 8: Run all CAD tests and verify GREEN**

```powershell
py -3.12 -m pytest tests/test_cad_evidence_schema.py tests/test_cad_evidence.py tests/test_cad_demo.py -q
```

- [ ] **Step 9: Commit Task 3**

```powershell
git add src/dmslicer/evidence_promotion/cad_evidence.py src/dmslicer/evidence_promotion/freecad_cad_evidence.py tests/test_cad_evidence.py tests/test_cad_demo.py
git commit -m "feat: compare fixture B-reps independently of bytes"
```

---

### Task 4: Admit artifact-backed CAD claims through the existing promotion gate

**Files:**
- Modify: `docs/evidence_preservation/schemas/promotion_request.schema.json`
- Modify: `docs/evidence_preservation/schemas/evidence_manifest.v2.schema.json`
- Modify: `src/dmslicer/evidence_promotion/policy.py`
- Modify: `src/dmslicer/evidence_promotion/promotion.py`
- Modify: `tests/conftest.py`
- Modify: `tests/test_schema_contracts.py`
- Modify: `tests/test_policy.py`
- Modify: `tests/test_promotion.py`

**Interfaces:**
- Request/manifest result statuses accept proven Case A/B values only with non-empty `evidence_artifact_ids`.
- Produces policy finding codes `CAD_EVIDENCE_SCHEMA_INVALID`, `CAD_EVIDENCE_REFERENCE_MISSING`, and `CAD_RESULT_MISMATCH`.
- Existing `validate_request(...)` and `promote(...)` signatures remain unchanged.
- Produces pytest factory fixture `valid_cad_request(mutation: str | None = None) -> dict[str, Any]`, fixture `repository_root: Path`, and fixture `valid_cad_request_file: Path` in `tests/conftest.py`.

- [ ] **Step 1: Write failing request/manifest schema tests**

Name the breaks: accepting a proven result without artifacts, rejecting a valid artifact-backed result, or weakening historical compatibility.

```python
def test_request_allows_proven_cad_results_only_with_evidence(valid_cad_request) -> None:
    request = valid_cad_request()
    _validator("promotion_request.schema.json").validate(request)
    request["results"]["geometry_equivalence_result"]["evidence_artifact_ids"] = []
    with pytest.raises(ValidationError):
        _validator("promotion_request.schema.json").validate(request)


def test_historical_manifests_still_validate_after_cad_extension() -> None:
    schema = load_schema(HISTORICAL_SCHEMA)
    for manifest in sorted(HISTORICAL_MANIFESTS.glob("goal-*.json")):
        Draft202012Validator(schema).validate(read_json(manifest))


def test_existing_p2_mvp_manifests_remain_valid() -> None:
    schema = load_schema(SCHEMA_ROOT / "evidence_manifest.v2.schema.json")
    for manifest in sorted((REPOSITORY_ROOT / "evidence/P2-MVP").glob("*/*/manifest.json")):
        Draft202012Validator(schema).validate(read_json(manifest))
```

- [ ] **Step 2: Run schema tests and verify RED**

```powershell
py -3.12 -m pytest tests/test_schema_contracts.py -q
```

Expected: the current v2 schema rejects all proven CAD statuses.

- [ ] **Step 3: Extend v2 result definitions without changing v1.1.0**

Permit new outputs while retaining the existing `UI_STATE_NOT_PROVEN` legacy value so the two immutable P2-MVP manifests remain valid:

```json
{
  "geometry": ["GEOMETRY_EQUIVALENT", "GEOMETRY_DIFFERENT", "GEOMETRIC_EQUIVALENCE_NOT_PROVEN"],
  "semantic": ["SEMANTIC_EQUIVALENT", "SEMANTIC_DIFFERENT", "SEMANTIC_EQUIVALENCE_NOT_PROVEN"],
  "ui": ["UI_SAME", "UI_DIFFERENT", "UI_COMPARISON_NOT_PROVEN", "UI_STATE_NOT_PROVEN"]
}
```

Use conditional schema branches so proven statuses require at least one evidence ID while NOT_PROVEN values allow an empty list. New code emits `UI_COMPARISON_NOT_PROVEN`; `UI_STATE_NOT_PROVEN` is accepted only for compatibility. `geometry_validation.evidence_method` is `BREP_BOOLEAN_AND_MEASUREMENTS` for proven results and `NOT_EVALUATED_P2_MVP` only for NOT_PROVEN.

- [ ] **Step 4: Write failing policy tests for artifact-backed admission**

Name the breaks: dangling CAD IDs, malformed snapshots, a request status inconsistent with the comparison file, or a hash-based method slipping through.

```python
def test_valid_case_a_cad_evidence_passes_policy(valid_cad_request, repository_root) -> None:
    report = validate_request(valid_cad_request(), repository_root)
    assert report["status"] == "PASS"


@pytest.mark.parametrize(
    ("mutation", "code"),
    [
        ("missing_comparison", "CAD_EVIDENCE_REFERENCE_MISSING"),
        ("malformed_snapshot", "CAD_EVIDENCE_SCHEMA_INVALID"),
        ("result_mismatch", "CAD_RESULT_MISMATCH"),
        ("sha_method", "SHA_GEOMETRY_MISUSE"),
    ],
)
def test_unbacked_cad_claims_fail_closed(valid_cad_request, repository_root, mutation, code) -> None:
    request = valid_cad_request(mutation=mutation)
    assert code in {finding["code"] for finding in validate_request(request, repository_root)["findings"]}
```

Build the fixtures by initializing a temporary Git repository with an implementation commit, writing literal schema-valid Case A/B CAD JSON files beneath `outputs/cad-policy/`, and adding each file as an individual allowlist entry. `valid_cad_request_file` writes the factory result to `outputs/cad-policy/promotion_request.json`; it does not call the production demo generator.

- [ ] **Step 5: Run policy tests and verify RED**

```powershell
py -3.12 -m pytest tests/test_policy.py -k cad -q
```

- [ ] **Step 6: Implement narrow CAD evidence validation**

Resolve only allowlisted artifacts. Geometry result IDs require a `geometry_comparison` artifact and at least one primary comparison whose status matches the request. Semantic result IDs require the two relevant `geometry_semantic_snapshot` artifacts; recompute `compare_semantics` from their explicit fixture binding and match the request status. UI result IDs require the two relevant `ui_state_snapshot` artifacts; recompute `compare_ui_states` and match the request status. Validate every CAD JSON artifact against `cad_evidence.schema.json`, and reject any `method`, `reason`, or validation role that says SHA/hash proves geometry. Keep existing path, secret, failure-retention, and Git ancestry checks unchanged.

- [ ] **Step 7: Write failing promotion tests**

Name the breaks: filtering Case B failure evidence, dropping independent domains, or copying an unvalidated CAD claim.

```python
def test_promotes_case_a_and_case_b_without_collapsing_results(valid_cad_request_file, repository_root) -> None:
    result = promote(valid_cad_request_file, repository_root)
    assert result["local_package_status"] == "LOCAL_PACKAGE_CREATED"
    manifest = read_json(repository_root / result["package_path"] / "manifest.json")
    assert manifest["results"]["geometry_equivalence_result"]["status"] == "GEOMETRY_DIFFERENT"
    assert manifest["results"]["semantic_equivalence_result"]["status"] == "SEMANTIC_EQUIVALENT"
    assert manifest["results"]["ui_state_result"]["status"] == "UI_DIFFERENT"
    assert manifest["history"]["failure_artifact_ids"]
```

Also assert a second run refuses overwrite and that a missing allowlisted snapshot installs no package.

- [ ] **Step 8: Run promotion tests and verify RED, then make the minimum manifest changes**

Run before implementation:

```powershell
py -3.12 -m pytest tests/test_promotion.py -k cad -q
```

Then preserve the existing transactional copy implementation and let `_manifest` carry the validated request results unchanged. Do not add a second promotion engine.

- [ ] **Step 9: Run all promotion tests and verify GREEN**

```powershell
py -3.12 -m pytest tests/test_schema_contracts.py tests/test_policy.py tests/test_promotion.py tests/test_integrity.py -q
```

- [ ] **Step 10: Commit Task 4**

```powershell
git add docs/evidence_preservation/schemas/promotion_request.schema.json docs/evidence_preservation/schemas/evidence_manifest.v2.schema.json src/dmslicer/evidence_promotion/policy.py src/dmslicer/evidence_promotion/promotion.py tests/conftest.py tests/test_schema_contracts.py tests/test_policy.py tests/test_promotion.py
git commit -m "feat: promote artifact-backed CAD comparison evidence"
```

---

### Task 5: Single demo command, minimal documentation, and portable CI

**Files:**
- Modify: `src/dmslicer/evidence_promotion/cli.py`
- Modify: `tests/test_cli.py`
- Modify: `pyproject.toml`
- Modify: `docs/evidence_preservation/EVIDENCE_PROMOTION_PIPELINE.md`
- Modify: `scripts/evidence_preservation/run_p2_mvp_checks.ps1`
- Modify: `.github/workflows/evidence-promotion.yml`

**Interfaces:**
- Adds only `python -m dmslicer.evidence_promotion demo --output-root <path>`.
- Existing `validate` and `promote` commands remain compatible.
- Marker `freecad` identifies local-required tests.

- [ ] **Step 1: Write failing CLI behavior tests**

Name the breaks: adding unnecessary commands, allowing an output root outside `outputs/`/`work/`, or printing private paths on failure.

```python
def test_cli_exposes_only_validate_promote_and_demo() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "dmslicer.evidence_promotion", "--help"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0
    assert "{validate,promote,demo}" in result.stdout
    assert "snapshot" not in result.stdout
    assert "compare" not in result.stdout


def test_demo_rejects_output_outside_staging(repository_root: Path) -> None:
    result = _run_cli("demo", "--output-root", str(repository_root / "evidence"))
    assert result.returncode == 2
    assert "DEMO_OUTPUT_ROOT_INVALID" in result.stdout
```

- [ ] **Step 2: Run CLI tests and verify RED**

```powershell
py -3.12 -m pytest tests/test_cli.py -q
```

- [ ] **Step 3: Implement only the demo dispatch**

Add an argparse branch with `--output-root`, resolve it under the repository, require its first relative component to be `outputs` or `work`, call `generate_demo`, and emit public-safe JSON. Return 0 only when demo execution completed; Case B's `GEOMETRY_DIFFERENT` is an expected scientific result rather than a process error.

- [ ] **Step 4: Update the pipeline documentation**

Document one complete sequence:

```powershell
py -3.12 -m dmslicer.evidence_promotion demo --output-root outputs/p2-cad-demo
py -3.12 -m dmslicer.evidence_promotion validate --repository-root . --request outputs/p2-cad-demo/promotion_request.json
py -3.12 -m dmslicer.evidence_promotion promote --repository-root . --request outputs/p2-cad-demo/promotion_request.json
```

State Case A/B/C expected statuses, unit-bearing tolerances, SHA role, no-overwrite behavior, failure preservation, local-only custody limitation, and the local FreeCAD requirement.

- [ ] **Step 5: Split portable CI from local FreeCAD verification**

Register the marker in `pyproject.toml`:

```toml
markers = [
  "freecad: requires a local FreeCAD/OCCT installation",
]
```

The GitHub workflow runs:

```bash
python -m pytest -q -m "not freecad"
git diff --exit-code origin/feat/cylindrical-interface-repairability -- docs/research_v2
```

The local PowerShell gate runs the focused CAD tests and the full suite, checks CLI help, validates the frozen docs against the PR base, and stops on any nonzero exit. CI text must not claim FreeCAD validation.

- [ ] **Step 6: Run CLI and portable gates and verify GREEN**

```powershell
py -3.12 -m pytest tests/test_cli.py -q
py -3.12 -m pytest -q -m "not freecad"
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/evidence_preservation/run_p2_mvp_checks.ps1
```

- [ ] **Step 7: Commit Task 5**

```powershell
git add src/dmslicer/evidence_promotion/cli.py tests/test_cli.py pyproject.toml docs/evidence_preservation/EVIDENCE_PROMOTION_PIPELINE.md scripts/evidence_preservation/run_p2_mvp_checks.ps1 .github/workflows/evidence-promotion.yml
git commit -m "feat: expose P2 CAD evidence demo gate"
```

---

### Task 6: Artifact-backed acceptance, stable evidence, review, and PR update

**Files:**
- Create from explicit allowlist: `evidence/P2-EVIDENCE-PROMOTION-SEMANTIC-SNAPSHOT/<implementation_commit>/<run_id>/manifest.json`
- Create from explicit allowlist: `evidence/P2-EVIDENCE-PROMOTION-SEMANTIC-SNAPSHOT/<implementation_commit>/<run_id>/copy_inventory.json`
- Create from explicit allowlist: key files below the same run's `cad/`, `snapshots/`, `comparisons/`, and `artifacts/`
- Create: `VIEW_INDEX.md` and `HUMAN_REVIEW.md` inside the staged demo before promotion
- Modify only if factual paths/statuses need documentation: `docs/evidence_preservation/EVIDENCE_PROMOTION_PIPELINE.md`

**Interfaces:**
- Consumes the committed Task 1–5 implementation SHA.
- Produces one immutable stable evidence run.
- Produces the final PR state with base `feat/cylindrical-interface-repairability`, without merging.

- [ ] **Step 1: Freeze the implementation commit and environment facts**

Run:

```powershell
git status --short --branch
git rev-parse HEAD
git merge-base --is-ancestor d65ac32e04115e5627f1c2988fd486e2353cada9 HEAD
freecadcmd --version
freecadcmd -c "import Part; print(Part.OCC_VERSION)"
py -3.12 --version
py -3.12 -m pytest --version
```

Require a clean worktree and ancestor exit 0. Record actual versions; do not guess unavailable fields.

- [ ] **Step 2: Generate the demo and JUnit staging artifacts**

Use a stable run ID such as `p2-cad-closed-loop-001` and the full implementation commit:

```powershell
py -3.12 -m dmslicer.evidence_promotion demo --output-root outputs/p2-cad-closed-loop-001
py -3.12 -m pytest tests/test_cad_evidence_schema.py tests/test_cad_evidence.py tests/test_cad_demo.py tests/test_schema_contracts.py tests/test_policy.py tests/test_promotion.py tests/test_cli.py -q --junitxml=outputs/p2-cad-closed-loop-001/artifacts/pytest.xml
```

Generate `VIEW_INDEX.md`, `HUMAN_REVIEW.md`, and a concise validator result from actual outputs. `VIEW_INDEX.md` uses only relative links. `HUMAN_REVIEW.md` states that visual inspection does not replace B-rep validation.

- [ ] **Step 3: Build the explicit promotion request**

List each selected file individually: original/UI-only/geometry-changed FCStd/BREP/STEP, three snapshots per case, three comparisons, JUnit, validator summary, `VIEW_INDEX.md`, `HUMAN_REVIEW.md`, and one retained negative/failure evidence JSON. Do not use a directory glob.

Record:

```json
{
  "byte_identity_result": {
    "status": "BYTE_DIFFERENT",
    "evidence_artifact_ids": ["validator-summary"]
  },
  "geometry_equivalence_result": {
    "status": "GEOMETRY_DIFFERENT",
    "evidence_artifact_ids": ["case-b-geometry-comparison"]
  },
  "semantic_equivalence_result": {
    "status": "SEMANTIC_EQUIVALENT",
    "evidence_artifact_ids": ["original-geometry-semantic-snapshot", "ui-only-geometry-semantic-snapshot"]
  },
  "ui_state_result": {
    "status": "UI_DIFFERENT",
    "evidence_artifact_ids": ["original-ui-state-snapshot", "ui-only-ui-state-snapshot"]
  },
  "pytest_result": {
    "status": "PASS",
    "evidence_artifact_ids": ["pytest-junit"]
  },
  "scientific_experiment_result": {
    "status": "PASS",
    "evidence_artifact_ids": ["case-a-geometry-comparison", "case-b-geometry-comparison", "validator-summary"]
  },
  "human_inspection_result": {
    "status": "NOT_EVALUATED",
    "evidence_artifact_ids": ["human-review-guide"]
  }
}
```

If the observed Case A FCStd bytes are identical, record `BYTE_SAME` instead of the shown `BYTE_DIFFERENT`; do not force a byte mutation.

The manifest-level geometry result binds Case B while its evidence IDs also include the Case A comparison; the validator summary lists both results separately. Do not report human review PASS unless an actual review was performed.

- [ ] **Step 4: Validate, promote, and verify the installed package**

```powershell
py -3.12 -m dmslicer.evidence_promotion validate --repository-root . --request outputs/p2-cad-closed-loop-001/promotion_request.json
py -3.12 -m dmslicer.evidence_promotion promote --repository-root . --request outputs/p2-cad-closed-loop-001/promotion_request.json
```

Require `LOCAL_PACKAGE_CREATED`, `NOT_FULLY_PRESERVED`, `PUBLICATION_NOT_AUTHORIZED`, and `LOCAL_TWO_PATHS_NOT_OFF_HOST_REDUNDANCY`. Recompute every installed file's size and SHA-256 against `copy_inventory.json`; validate the manifest and every CAD JSON artifact; verify all VIEW_INDEX links stay within the package. Do not edit the installed immutable package after promotion.

- [ ] **Step 5: Run the full verification matrix**

```powershell
py -3.12 -m pytest -q
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/evidence_preservation/run_p2_mvp_checks.ps1
git diff --exit-code origin/feat/cylindrical-interface-repairability -- docs/research_v2
git diff --check origin/feat/cylindrical-interface-repairability...HEAD
git status --short
```

Record pytest PASS separately from Case A/B scientific PASS and from human inspection status.

- [ ] **Step 6: Commit stable evidence without temporary output**

```powershell
git add evidence/P2-EVIDENCE-PROMOTION-SEMANTIC-SNAPSHOT docs/evidence_preservation/EVIDENCE_PROMOTION_PIPELINE.md
git commit -m "evidence: record P2 CAD promotion closed loop"
```

Confirm `outputs/` and `work/` are not staged.

- [ ] **Step 7: Invoke required review and verification skills**

Use `superpowers:requesting-code-review` to review the complete branch against the approved spec. For each actionable finding, use `superpowers:receiving-code-review`, reproduce the issue, add a failing regression, implement the minimum fix, rerun focused and full verification, and preserve the finding/fix evidence. Then use `superpowers:verification-before-completion` before making any completion claim.

- [ ] **Step 8: Push and retarget the existing PR without merging**

After review and verification pass:

```powershell
git push -u origin feat/evidence-promotion-semantic-snapshot
gh pr edit 3 --base feat/cylindrical-interface-repairability --title "P2: evidence promotion and semantic snapshot closed loop"
gh pr view 3 --json number,url,state,baseRefName,headRefName,mergeStateStatus,statusCheckRollup
```

Update the PR body with Case A/B/C evidence paths, separate result domains, commands, tolerances, compatibility result, custody limitation, and known limitations. Do not merge the PR.

- [ ] **Step 9: Verify remote and working-tree state**

```powershell
git fetch origin
git status --short --branch
git rev-parse HEAD
git rev-parse origin/feat/evidence-promotion-semantic-snapshot
gh pr checks 3
```

Require local/remote SHA equality, clean status, PR base `feat/cylindrical-interface-repairability`, open PR state, and no merge commit created by P2 completion.
