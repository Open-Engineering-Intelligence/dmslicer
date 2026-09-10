# Contact Tolerance Pilot 05A Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a reproducible, isolated 30-sample A01/A07 tolerance pilot with truthful actual-vs-expected evidence.

**Architecture:** A host module creates independent sample truth and orchestrates FreeCADCmd.  A narrow FreeCAD adapter reimports each STEP and measures only planes or coaxial cylinders, then observes raw direct Fuse without recovery behavior.  Validation and reporting stay on the host side and compare stored artifacts only after analysis.

**Tech Stack:** Python 3, pytest, FreeCADCmd/OCC, STEP, JSON, CSV.

**Spec:** `docs/superpowers/specs/2026-09-09-contact-tolerance-pilot-05a-design.md`

## Global Constraints

- `LEVEL_B_PILOT`; only A01/A07; exactly 15 frozen offsets per case; nominal scale 1; `tauE=0.1 mm`.
- Actual analysis must not read expected truth, configured delta, or sample-name delta.
- `|delta|=tauE` uses the inclusive frozen engineering-state boundary and is reported separately.
- Preserve all existing fixtures and production behavior; do not use fuzzy tolerances, snapping, filling, or repair.
- Generated `outputs/` remains untracked; source, fixtures, tests, and concise protocol note are committed.

---

### Task 1: Pilot data contract and independent truth

**Files:**
- Create: `tests/test_contact_tolerance_pilot_05a.py`
- Create: `src/dmslicer/contact_tolerance_pilot_05a.py`
- Create: `src/dmslicer/freecad_contact_tolerance_pilot_05a.py`

**Interfaces:**
- Produces `generate_contact_tolerance_pilot(root: Path) -> dict[str, Any]`.
- Produces `validate_tolerance_actual(actual: dict[str, Any], expected: dict[str, Any]) -> dict[str, Any]`.

- [ ] **Step 1: Write failing contract tests**

```python
def test_generator_writes_two_cases_with_the_frozen_15_offsets(tmp_path: Path) -> None:
    generated = generate_contact_tolerance_pilot(tmp_path)
    assert len(generated["samples"]) == 30
    assert {row["case_id"] for row in generated["samples"]} == {"A01", "A07"}

def test_validation_detects_mutated_expected_or_actual() -> None:
    assert validate_tolerance_actual(_actual("exact"), _expected("exact"))["status"] == "PASS"
    assert validate_tolerance_actual(_actual("exact"), _expected("positive_gap_within_tolerance"))["status"] == "FAIL"
```

- [ ] **Step 2: Run the contract tests and verify missing-module failure**

Run: `py -3 -m pytest tests/test_contact_tolerance_pilot_05a.py -q`

Expected: collection failure because `dmslicer.contact_tolerance_pilot_05a` is absent.

- [ ] **Step 3: Implement the smallest host contract**

```python
OFFSETS = (-4, -2, -1.1, -1, -0.9, -0.5, -0.1, 0, 0.1, 0.5, 0.9, 1, 1.1, 2, 4)

def engineering_state(offset: float, tau_e: float) -> str:
    if offset == 0: return "exact"
    if offset > 0: return "positive_gap_within_tolerance" if offset <= tau_e else "positive_gap_beyond_tolerance"
    return "penetration_within_tolerance" if offset >= -tau_e else "penetration_beyond_tolerance"
```

Generate immutable per-sample STEP/parameters/expected records.  Truth uses only construction equations: plane displacement for A01, bore radius change for A07.

- [ ] **Step 4: Run the contract tests and verify pass**

Run: `py -3 -m pytest tests/test_contact_tolerance_pilot_05a.py -q`

Expected: PASS.

### Task 2: Actual B-rep measurement and direct Fuse evidence

**Files:**
- Modify: `src/dmslicer/contact_tolerance_pilot_05a.py`
- Modify: `src/dmslicer/freecad_contact_tolerance_pilot_05a.py`
- Modify: `tests/test_contact_tolerance_pilot_05a.py`

**Interfaces:**
- Produces `run_contact_tolerance_pilot_case(case_dir: Path, output_dir: Path) -> dict[str, Any]`.
- Actual record contains `geometry_state`, `engineering_state`, `direct_fuse`, `measured_signed_offset_mm`, `tauE_mm`, `tauK_mm`, and source STEP hash.

- [ ] **Step 1: Add failing tests for actual isolation and missing fields**

```python
def test_actual_analysis_does_not_change_when_expected_truth_is_mutated(tmp_path: Path) -> None:
    # Analyze the same tracked STEP before and after only expected.json is changed.
    assert first_actual == second_actual

def test_validation_rejects_missing_actual_or_expected_fields() -> None:
    assert validate_tolerance_actual({}, _expected("exact"))["status"] == "FAIL"
```

- [ ] **Step 2: Run only the new tests and verify their expected failure**

Run: `py -3 -m pytest tests/test_contact_tolerance_pilot_05a.py -q`

Expected: FAIL because no actual-analysis interface exists.

- [ ] **Step 3: Implement bounded FreeCAD actions**

The `analyze` action must import the STEP, require exactly two solids, identify either opposing parallel planar carriers or coaxial cylindrical carriers, and return `UNSUPPORTED` otherwise.  Measure plane separation or radius difference from imported surfaces.  Determine current dimension from direct B-rep common material volume and positive common face area; do not synthesize a 2D patch for gap/3D cases.  Copy inputs before raw `fuse()` and report success, solid count, valid/closed, material volume, conservation error, and whether one connected solid resulted.  The `view` action must only generate the six specified representative FCStd documents.

- [ ] **Step 4: Run targeted tests and verify pass**

Run: `py -3 -m pytest tests/test_contact_tolerance_pilot_05a.py -q`

Expected: PASS.

### Task 3: Validation, aggregation, repeatability, and CLI

**Files:**
- Modify: `src/dmslicer/contact_tolerance_pilot_05a.py`
- Modify: `src/dmslicer/__main__.py`
- Modify: `tests/test_contact_tolerance_pilot_05a.py`
- Create: `docs/benchmark_design/contact_tolerance_pilot_05a.md`

**Interfaces:**
- Produces `run_contact_tolerance_pilot_suite(fixture_root: Path, output_root: Path) -> dict[str, Any]`.
- Produces `run_contact_tolerance_pilot_repeatability(fixture_root: Path, output_root: Path) -> dict[str, Any]`.

- [ ] **Step 1: Add failing suite tests**

```python
def test_suite_writes_30_rows_six_fcstd_and_chinese_view_index(tmp_path: Path) -> None:
    result = run_contact_tolerance_pilot_suite(FIXTURES, tmp_path)
    assert len(result["samples"]) == 30
    assert len(list((tmp_path / "views").glob("*.FCStd"))) == 6
    assert "实际" in (tmp_path / "VIEW_INDEX.md").read_text(encoding="utf-8")
```

- [ ] **Step 2: Run suite test and verify failure**

Run: `py -3 -m pytest tests/test_contact_tolerance_pilot_05a.py -q`

Expected: FAIL because the suite/report API is absent.

- [ ] **Step 3: Implement aggregation and CLI commands**

Write one actual and one validation JSON per sample, `summary.json`, `results.csv`, separate boundary strata, `METHOD_MISMATCH` count, Chinese `VIEW_INDEX.md`, conclusion, and a two-process comparison that ignores only runtime/timestamps/temporary paths.  Add commands to generate and run the pilot.  Document protocol mapping and non-executed factors.

- [ ] **Step 4: Run targeted test file and verify pass**

Run: `py -3 -m pytest tests/test_contact_tolerance_pilot_05a.py -q`

Expected: PASS.

### Task 4: Tracked fixtures, evidence execution, and final verification

**Files:**
- Create: `benchmarks/contact_tolerance_pilot_05a/**`
- Generated: `outputs/contact_tolerance_pilot_05a/**`

- [ ] **Step 1: Generate the tracked 30-sample fixtures**

Run: `py -3 -m dmslicer generate-contact-tolerance-pilot benchmarks/contact_tolerance_pilot_05a`

Expected: 30 immutable STEP inputs and matching independent parameter/expected records.

- [ ] **Step 2: Run pilot suite once**

Run: `py -3 -m dmslicer run-contact-tolerance-pilot-suite benchmarks/contact_tolerance_pilot_05a outputs/contact_tolerance_pilot_05a`

Expected: durable bundle with all samples recorded, regardless of direct-Fuse result.

- [ ] **Step 3: Run full regression once and inspect artifacts**

Run: `py -3 -m pytest -q`

Expected: existing regressions plus pilot tests pass; any honest analyzer mismatch appears in pilot summary rather than as an unrecorded tool error.

- [ ] **Step 4: Check and commit**

Run: `git diff --check && git status --short`

Stage source, tests, fixtures, and documentation only; commit with `feat: add contact tolerance pilot`; push `feat/contact-tolerance-pilot` without force, merge, rebase, or amend.
