import json
import os
import subprocess
import sys
from pathlib import Path

import pytest


CASE_EXPECTATIONS = {
    "A01": {"relation": "full_full", "dimension": "2D", "measure_key": "area_mm2"},
    "A02": {"relation": "partial_partial", "dimension": "2D", "measure_key": "area_mm2"},
    "A03": {"relation": "small_face_contained_in_large_face", "dimension": "2D", "measure_key": "area_mm2"},
    "A04": {"relation": "point_touch", "dimension": "0D", "measure_key": "point_count"},
    "A05": {"relation": "edge_touch", "dimension": "1D", "measure_key": "length_mm"},
    "A06": {"relation": "solid_material_interference", "dimension": "3D", "measure_key": "volume_mm3"},
}


def _command(*arguments: str) -> subprocess.CompletedProcess[str]:
    environment = os.environ.copy()
    environment["PYTHONPATH"] = str(Path("src").resolve())
    return subprocess.run(
        [sys.executable, "-m", "dmslicer", *arguments],
        cwd=Path.cwd(), env=environment, text=True, capture_output=True, check=False,
    )


def test_canonical_generator_creates_six_independent_tracked_style_step_bundles(tmp_path: Path) -> None:
    """Catches a missing fixture generator or a generator that omits a required canonical case."""
    fixture_root = tmp_path / "fixtures"

    completed = _command("generate-contact-canonical", str(fixture_root))

    assert completed.returncode == 0, completed.stderr
    for case_id in CASE_EXPECTATIONS:
        case_dir = fixture_root / case_id
        assert (case_dir / "fixture.step").is_file()
        expected = json.loads((case_dir / "expected.json").read_text(encoding="utf-8"))
        assert expected["case_id"] == case_id
        assert expected["relation"] == CASE_EXPECTATIONS[case_id]["relation"]
        assert expected["tolerances"]["linear_epsilon_mm"] > 0


@pytest.mark.parametrize("case_id", sorted(CASE_EXPECTATIONS))
def test_canonical_analysis_reimports_step_and_reports_actual_brep_dimension(
    tmp_path: Path, case_id: str
) -> None:
    """Catches expected truth, generator memory, or AABB candidates being used as geometry truth."""
    fixture_root = tmp_path / "fixtures"
    assert _command("generate-contact-canonical", str(fixture_root)).returncode == 0
    evidence_dir = tmp_path / "evidence" / case_id

    completed = _command("analyze-contact-canonical", str(fixture_root / case_id / "fixture.step"), str(evidence_dir))

    assert completed.returncode == 0, completed.stderr
    result = json.loads((evidence_dir / "actual.json").read_text(encoding="utf-8"))
    expected = CASE_EXPECTATIONS[case_id]
    assert result["analysis_input"] == "reimported_step"
    assert result["imported_solid_count"] == 2
    assert result["relation"]["relation"] == expected["relation"]
    assert result["relation"]["dimension"] == expected["dimension"]
    assert result["relation"]["evidence"]["source"] == "actual_brep"
    assert result["validation"]["status"] == "PASS"


@pytest.mark.parametrize("case_id", ["A01", "A02", "A03"])
def test_canonical_planar_cases_report_coverage_and_direct_face_provenance(tmp_path: Path, case_id: str) -> None:
    """Catches planar cases losing side coverage or face-to-patch linkage."""
    fixture_root = tmp_path / "fixtures"
    assert _command("generate-contact-canonical", str(fixture_root)).returncode == 0
    evidence_dir = tmp_path / "evidence" / case_id
    assert _command("analyze-contact-canonical", str(fixture_root / case_id / "fixture.step"), str(evidence_dir)).returncode == 0

    relation = json.loads((evidence_dir / "actual.json").read_text(encoding="utf-8"))["relation"]
    assert relation["area_mm2"] > 0
    assert 0 < relation["coverage_a"] <= 1
    assert 0 < relation["coverage_b"] <= 1
    assert relation["patches"]
    assert all(patch["provenance"]["source_face_a"] and patch["provenance"]["source_face_b"] for patch in relation["patches"])


@pytest.mark.parametrize("mutation", ["measure", "coverage", "provenance"])
def test_canonical_expected_mutation_fails_validation_without_changing_actual_evidence(
    tmp_path: Path, mutation: str
) -> None:
    """Catches an expected manifest being consulted before actual B-rep evidence is completed."""
    fixture_root = tmp_path / "fixtures"
    assert _command("generate-contact-canonical", str(fixture_root)).returncode == 0
    case_dir = fixture_root / "A02"
    baseline_dir = tmp_path / "baseline"
    assert _command("analyze-contact-canonical", str(case_dir / "fixture.step"), str(baseline_dir)).returncode == 0
    baseline_actual = json.loads((baseline_dir / "actual.json").read_text(encoding="utf-8"))
    expected_path = case_dir / "expected.json"
    expected = json.loads(expected_path.read_text(encoding="utf-8"))
    if mutation == "measure":
        expected["measures"]["area_mm2"] = 999.0
    elif mutation == "coverage":
        expected["coverage"][0] = 0.1
    else:
        expected["provenance_scope"] = "wrong_linkage"
    expected_path.write_text(json.dumps(expected), encoding="utf-8")
    changed_dir = tmp_path / "changed"

    completed = _command("analyze-contact-canonical", str(case_dir / "fixture.step"), str(changed_dir))

    assert completed.returncode != 0
    changed_actual = json.loads((changed_dir / "actual.json").read_text(encoding="utf-8"))
    assert changed_actual["relation"] == baseline_actual["relation"]
    assert json.loads((changed_dir / "validation.json").read_text(encoding="utf-8"))["status"] == "FAIL"


def test_canonical_repeatability_compares_two_processes_and_rejects_measure_mutation(tmp_path: Path) -> None:
    """Catches repeatability checks that omit actual measure or provenance linkage."""
    fixture_root = tmp_path / "fixtures"
    assert _command("generate-contact-canonical", str(fixture_root)).returncode == 0
    evidence_dir = tmp_path / "repeatability"

    completed = _command("repeat-contact-canonical", str(fixture_root / "A01" / "fixture.step"), str(evidence_dir))

    assert completed.returncode == 0, completed.stderr
    report = json.loads((evidence_dir / "repeatability.json").read_text(encoding="utf-8"))
    assert report["status"] == "PASS"
    assert report["comparison"]["relation_measure_match"] is True
    assert report["comparison"]["provenance_linkage_match"] is True


@pytest.mark.parametrize("case_id", sorted(CASE_EXPECTATIONS))
def test_tracked_canonical_step_bundle_validates_directly(tmp_path: Path, case_id: str) -> None:
    """Catches acceptance relying on generator objects instead of the versioned STEP fixture."""
    case_dir = Path(__file__).resolve().parents[1] / "benchmarks" / "contact_canonical_03a" / case_id
    completed = _command("analyze-contact-canonical", str(case_dir / "fixture.step"), str(tmp_path / case_id))

    assert completed.returncode == 0, completed.stderr
    assert json.loads((tmp_path / case_id / "validation.json").read_text(encoding="utf-8"))["status"] == "PASS"


def test_canonical_suite_writes_view_index_summary_and_per_case_debug_files(tmp_path: Path) -> None:
    """Catches an acceptance run that leaves only temporary evidence or no way to inspect each debug model."""
    fixtures = Path(__file__).resolve().parents[1] / "benchmarks" / "contact_canonical_03a"
    output_root = tmp_path / "contact_canonical_03a"

    completed = _command("run-contact-canonical-suite", str(fixtures), str(output_root))

    assert completed.returncode == 0, completed.stderr
    summary = json.loads((output_root / "summary.json").read_text(encoding="utf-8"))
    assert summary["status"] == "PASS"
    assert set(summary["cases"]) == set(CASE_EXPECTATIONS)
    for case_id in CASE_EXPECTATIONS:
        assert (output_root / case_id / "debug.FCStd").is_file()
    assert "debug.FCStd" in (output_root / "VIEW_INDEX.md").read_text(encoding="utf-8")
