import json
import math
import os
import subprocess
import sys
from pathlib import Path

import pytest


CASE_EXPECTATIONS = {
    "A07": {"relation": "exact", "dimension": "2D", "surface_family": "cylinder", "hole_count": 1, "coverage": [1.0, 0.75]},
    "A08": {"relation": "solid_cavity_wall_touch", "dimension": "2D", "surface_family": "sphere", "hole_count": 0, "coverage": [0.5, 1.0]},
    "A09": {"relation": "exact", "dimension": "2D", "surface_family": "cone", "hole_count": 1, "coverage": [1.0, 100.0 / 153.0]},
}


def _command(*arguments: str) -> subprocess.CompletedProcess[str]:
    environment = os.environ.copy()
    environment["PYTHONPATH"] = str(Path("src").resolve())
    return subprocess.run(
        [sys.executable, "-m", "dmslicer", *arguments],
        cwd=Path.cwd(), env=environment, text=True, capture_output=True, check=False,
    )


def test_analytic_generator_creates_only_the_three_frozen_curve_fixtures(tmp_path: Path) -> None:
    """Catches a missing frozen fixture or a generator that drifts into non-03B cases."""
    fixture_root = tmp_path / "fixtures"

    completed = _command("generate-contact-canonical-analytic", str(fixture_root))

    assert completed.returncode == 0, completed.stderr
    assert {path.name for path in fixture_root.iterdir()} == set(CASE_EXPECTATIONS)
    for case_id, expected_case in CASE_EXPECTATIONS.items():
        case_dir = fixture_root / case_id
        expected = json.loads((case_dir / "expected.json").read_text(encoding="utf-8"))
        assert (case_dir / "fixture.step").is_file()
        assert expected["case_id"] == case_id
        assert expected["relation"] == expected_case["relation"]
        assert expected["dimension"] == "2D"
        assert expected["ground_truth_mode"] == "analytic"
        assert expected["measures"]["area_mm2"] > 0


@pytest.mark.parametrize("case_id", sorted(CASE_EXPECTATIONS))
def test_analytic_analysis_reimports_step_and_reports_curved_brep_evidence(tmp_path: Path, case_id: str) -> None:
    """Catches expected truth, a planar-only filter, or generator memory being used as curve truth."""
    fixture_root = tmp_path / "fixtures"
    assert _command("generate-contact-canonical-analytic", str(fixture_root)).returncode == 0
    evidence_dir = tmp_path / "evidence" / case_id

    completed = _command("analyze-contact-canonical-analytic", str(fixture_root / case_id / "fixture.step"), str(evidence_dir))

    assert completed.returncode == 0, completed.stderr
    actual = json.loads((evidence_dir / "actual.json").read_text(encoding="utf-8"))
    expected_case = CASE_EXPECTATIONS[case_id]
    relation = actual["relation"]
    assert actual["analysis_input"] == "reimported_step"
    assert actual["imported_solid_count"] == 2
    assert relation["relation"] == expected_case["relation"]
    assert relation["dimension"] == expected_case["dimension"]
    assert relation["support_surface_family"] == expected_case["surface_family"]
    assert relation["area_mm2"] > 0
    assert 0 < relation["coverage_a"] <= 1
    assert 0 < relation["coverage_b"] <= 1
    assert [relation["coverage_a"], relation["coverage_b"]] == pytest.approx(expected_case["coverage"])
    assert relation["raw_common_face_count"] >= relation["patch_count"] >= relation["component_count"] == 1
    assert relation["hole_count"] == expected_case["hole_count"]
    assert relation["patches"]
    assert all(patch["provenance"]["source_face_a"] and patch["provenance"]["source_face_b"] for patch in relation["patches"])
    assert actual["validation"]["status"] == "PASS"


def test_analytic_expected_mutation_fails_closed_without_changing_actual_curve_evidence(tmp_path: Path) -> None:
    """Catches a curved-case expected manifest influencing actual B-rep selection or measurement."""
    fixture_root = tmp_path / "fixtures"
    assert _command("generate-contact-canonical-analytic", str(fixture_root)).returncode == 0
    case_dir = fixture_root / "A07"
    baseline_dir = tmp_path / "baseline"
    assert _command("analyze-contact-canonical-analytic", str(case_dir / "fixture.step"), str(baseline_dir)).returncode == 0
    baseline_relation = json.loads((baseline_dir / "actual.json").read_text(encoding="utf-8"))["relation"]
    expected_path = case_dir / "expected.json"
    expected = json.loads(expected_path.read_text(encoding="utf-8"))
    expected["measures"]["area_mm2"] = 123.0
    expected_path.write_text(json.dumps(expected), encoding="utf-8")

    completed = _command("analyze-contact-canonical-analytic", str(case_dir / "fixture.step"), str(tmp_path / "changed"))

    assert completed.returncode != 0
    changed = json.loads((tmp_path / "changed" / "actual.json").read_text(encoding="utf-8"))
    assert changed["relation"] == baseline_relation
    assert json.loads((tmp_path / "changed" / "validation.json").read_text(encoding="utf-8"))["status"] == "FAIL"


def test_analytic_repeatability_preserves_area_coverage_components_and_provenance(tmp_path: Path) -> None:
    """Catches a two-process comparison that omits curved area, topology, coverage, or linkage."""
    fixture_root = tmp_path / "fixtures"
    assert _command("generate-contact-canonical-analytic", str(fixture_root)).returncode == 0

    completed = _command("repeat-contact-canonical-analytic", str(fixture_root / "A09" / "fixture.step"), str(tmp_path / "repeatability"))

    assert completed.returncode == 0, completed.stderr
    comparison = json.loads((tmp_path / "repeatability" / "repeatability.json").read_text(encoding="utf-8"))["comparison"]
    assert comparison["relation_measure_match"] is True
    assert comparison["coverage_match"] is True
    assert comparison["component_information_match"] is True
    assert comparison["provenance_linkage_match"] is True
    assert comparison["geometry_digest_match"] is True


def test_analytic_suite_publishes_debug_models_and_curve_view_instructions(tmp_path: Path) -> None:
    """Catches acceptance that leaves curve evidence in temp or omits instructions for internal faces."""
    fixtures = Path(__file__).resolve().parents[1] / "benchmarks" / "contact_canonical_03b"
    output_root = tmp_path / "contact_canonical_03b"

    completed = _command("run-contact-canonical-analytic-suite", str(fixtures), str(output_root))

    assert completed.returncode == 0, completed.stderr
    summary = json.loads((output_root / "summary.json").read_text(encoding="utf-8"))
    assert summary["status"] == "PASS"
    assert set(summary["cases"]) == set(CASE_EXPECTATIONS)
    for case_id in CASE_EXPECTATIONS:
        assert (output_root / case_id / "debug.FCStd").is_file()
    view_index = (output_root / "VIEW_INDEX.md").read_text(encoding="utf-8")
    assert "hide" in view_index.lower()
    assert "debug.FCStd" in view_index
