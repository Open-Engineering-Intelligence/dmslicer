import copy
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from dmslicer.contact_canonical_03c import (
    _validate,
    analyze_contact_canonical_interface_topology,
    compare_topology_relations,
    generate_contact_canonical_interface_topology,
)


CASE_EXPECTATIONS = {
    "A11": {"components": 2, "boundaries": 2, "holes": 0, "area_factor": 2},
    "A12": {"components": 1, "boundaries": 2, "holes": 1, "area_factor": 1},
}


def _command(*arguments: str) -> subprocess.CompletedProcess[str]:
    environment = os.environ.copy()
    environment["PYTHONPATH"] = str(Path("src").resolve())
    return subprocess.run(
        [sys.executable, "-m", "dmslicer", *arguments],
        cwd=Path.cwd(), env=environment, text=True, capture_output=True, check=False,
    )


def test_topology_generator_creates_only_frozen_a11_and_a12(tmp_path: Path) -> None:
    fixture_root = tmp_path / "fixtures"

    completed = _command("generate-contact-canonical-interface-topology", str(fixture_root))

    assert completed.returncode == 0, completed.stderr
    assert {path.name for path in fixture_root.iterdir()} == set(CASE_EXPECTATIONS)
    for case_id, topology in CASE_EXPECTATIONS.items():
        expected = json.loads((fixture_root / case_id / "expected.json").read_text(encoding="utf-8"))
        assert (fixture_root / case_id / "fixture.step").is_file()
        assert expected["case_id"] == case_id
        assert expected["dimension"] == "2D"
        assert expected["ground_truth_mode"] == "analytic"
        assert "validation_tolerances" not in expected
        assert expected["patch_topology"]["component_count"] == topology["components"]
        assert expected["patch_topology"]["boundary_component_count"] == topology["boundaries"]
        assert expected["patch_topology"]["hole_count"] == topology["holes"]


@pytest.mark.parametrize("case_id", sorted(CASE_EXPECTATIONS))
def test_topology_analysis_reimports_two_connected_solids_and_reports_actual_components(tmp_path: Path, case_id: str) -> None:
    fixture_root = tmp_path / "fixtures"
    assert _command("generate-contact-canonical-interface-topology", str(fixture_root)).returncode == 0
    evidence_dir = tmp_path / "evidence" / case_id

    completed = _command("analyze-contact-canonical-interface-topology", str(fixture_root / case_id / "fixture.step"), str(evidence_dir))

    assert completed.returncode == 0, completed.stderr
    actual = json.loads((evidence_dir / "actual.json").read_text(encoding="utf-8"))
    relation = actual["relation"]
    expected = CASE_EXPECTATIONS[case_id]
    assert actual["analysis_input"] == "reimported_step"
    assert actual["imported_body_count"] == 2
    assert actual["imported_solid_counts"] == [1, 1]
    assert relation["relation"] == "exact"
    assert relation["dimension"] == "2D"
    assert relation["raw_common_face_count"] >= relation["patch_count"] >= relation["component_count"]
    assert relation["component_count"] == expected["components"]
    assert relation["boundary_component_count"] == expected["boundaries"]
    assert relation["hole_count"] == expected["holes"]
    assert relation["first_betti_number"] == expected["holes"]
    assert relation["annular_or_multiply_connected"] is (expected["holes"] > 0)
    assert len(relation["components"]) == expected["components"]
    assert sum(component["area_mm2"] for component in relation["components"]) == pytest.approx(relation["area_mm2"])
    assert all(component["source_face_linkage"] for component in relation["components"])
    assert all(patch["source_face_linkage"] for patch in relation["patches"])
    assert actual["validation"]["status"] == "PASS"


def test_a12_direct_normalized_generation_preserves_analytic_faces_before_and_after_step(tmp_path: Path) -> None:
    generated = generate_contact_canonical_interface_topology(tmp_path / "fixtures", case_ids=("A12",))

    assert [entry["case_id"] for entry in generated["cases"]] == ["A12"]
    evidence = generated["cases"][0]["generation_evidence"]
    for stage in ("pre_export", "post_step_import"):
        target = evidence[stage]
        assert target["surface_type"] == "Plane"
        assert target["boundary_curve_types"] == ["Circle", "Circle"]
        assert target["area_mm2"] == pytest.approx(1803.7852556496418, abs=1e-8, rel=0)
        assert target["coverage"] == pytest.approx([0.37699111843077515, 1.0], abs=1e-7, rel=0)


def test_tracked_a12_reimport_keeps_analytic_geometry_and_strict_area_coverage_contract(tmp_path: Path) -> None:
    fixture = Path(__file__).resolve().parents[1] / "benchmarks" / "contact_canonical_03c" / "A12" / "fixture.step"
    actual = analyze_contact_canonical_interface_topology(fixture, tmp_path / "analysis")
    relation = actual["relation"]

    assert relation["analytic_geometry"]["surface_type"] == "Plane"
    assert relation["analytic_geometry"]["boundary_curve_types"] == ["Circle", "Circle"]
    assert relation["area_mm2"] == pytest.approx(1803.7852556496418, abs=1e-8, rel=0)
    assert [relation["coverage_a"], relation["coverage_b"]] == pytest.approx([0.37699111843077515, 1.0], abs=1e-7, rel=0)
    assert (relation["patch_count"], relation["component_count"], relation["boundary_component_count"], relation["hole_count"]) == (1, 1, 2, 1)


def test_a12_strict_validation_rejects_old_area_and_excess_coverage_without_digest_shortcut(tmp_path: Path) -> None:
    generated = generate_contact_canonical_interface_topology(tmp_path / "fixtures", case_ids=("A12",))
    fixture = Path(generated["cases"][0]["step"])
    actual = analyze_contact_canonical_interface_topology(fixture, tmp_path / "analysis")
    expected = json.loads(fixture.with_name("expected.json").read_text(encoding="utf-8"))

    old_area = copy.deepcopy(actual)
    old_area["relation"]["area_mm2"] = 1803.7424900293495
    area_failures = _validate(old_area, expected)["failures"]
    assert any(failure["kind"] == "area_mm2" for failure in area_failures)

    old_coverage = copy.deepcopy(actual)
    old_coverage["relation"]["coverage_b"] = 1.0 - 2e-7
    coverage_failures = _validate(old_coverage, expected)["failures"]
    assert any(failure["kind"] == "coverage_b" for failure in coverage_failures)


def test_topology_expected_mutation_fails_closed_without_changing_actual_evidence(tmp_path: Path) -> None:
    fixture_root = tmp_path / "fixtures"
    assert _command("generate-contact-canonical-interface-topology", str(fixture_root)).returncode == 0
    case_dir = fixture_root / "A12"
    baseline_dir = tmp_path / "baseline"
    assert _command("analyze-contact-canonical-interface-topology", str(case_dir / "fixture.step"), str(baseline_dir)).returncode == 0
    baseline = json.loads((baseline_dir / "actual.json").read_text(encoding="utf-8"))["relation"]
    expected_path = case_dir / "expected.json"
    expected = json.loads(expected_path.read_text(encoding="utf-8"))
    expected["patch_topology"]["hole_count"] = 0
    expected["measures"]["area_mm2"] = 123.0
    expected_path.write_text(json.dumps(expected), encoding="utf-8")

    completed = _command("analyze-contact-canonical-interface-topology", str(case_dir / "fixture.step"), str(tmp_path / "changed"))

    assert completed.returncode != 0
    changed = json.loads((tmp_path / "changed" / "actual.json").read_text(encoding="utf-8"))["relation"]
    assert changed == baseline
    assert json.loads((tmp_path / "changed" / "validation.json").read_text(encoding="utf-8"))["status"] == "FAIL"


def test_topology_snapshot_mutations_change_expected_comparison_not_actual_evidence(tmp_path: Path) -> None:
    fixture_root = tmp_path / "fixtures"
    assert _command("generate-contact-canonical-interface-topology", str(fixture_root)).returncode == 0
    evidence_dir = tmp_path / "evidence"
    assert _command("analyze-contact-canonical-interface-topology", str(fixture_root / "A11" / "fixture.step"), str(evidence_dir)).returncode == 0
    actual = json.loads((evidence_dir / "actual.json").read_text(encoding="utf-8"))["relation"]
    reversed_actual = analyze_contact_canonical_interface_topology(
        fixture_root / "A11" / "fixture.step", tmp_path / "reversed", reverse_raw_order=True,
    )["relation"]
    assert all(compare_topology_relations(actual, reversed_actual).values())
    mutated = copy.deepcopy(actual)
    mutated["components"][0]["source_face_linkage"] = []
    comparison = compare_topology_relations(actual, mutated)
    assert comparison["component_membership_match"] is False
    mutated_linkage = copy.deepcopy(actual)
    mutated_linkage["patches"][0]["source_face_linkage"] = []
    assert compare_topology_relations(actual, mutated_linkage)["provenance_linkage_match"] is False


def test_topology_repeatability_and_debug_models_publish_durable_component_views(tmp_path: Path) -> None:
    fixtures = Path(__file__).resolve().parents[1] / "benchmarks" / "contact_canonical_03c"
    output_root = tmp_path / "contact_canonical_03c"

    completed = _command("run-contact-canonical-interface-topology-suite", str(fixtures), str(output_root))

    assert completed.returncode == 0, completed.stderr
    summary = json.loads((output_root / "summary.json").read_text(encoding="utf-8"))
    assert summary["status"] == "PASS"
    assert set(summary["cases"]) == set(CASE_EXPECTATIONS)
    for case_id in CASE_EXPECTATIONS:
        assert (output_root / case_id / "debug.FCStd").is_file()
        comparison = json.loads((output_root / case_id / "repeatability" / "repeatability.json").read_text(encoding="utf-8"))["comparison"]
        assert all(comparison.values())
    view_index = (output_root / "VIEW_INDEX.md").read_text(encoding="utf-8")
    assert "Component_1" in view_index
    assert "hole" in view_index.lower()
