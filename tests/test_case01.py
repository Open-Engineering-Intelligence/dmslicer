import json
import os
import subprocess
import sys
from copy import deepcopy
from pathlib import Path

import pytest

from dmslicer.evidence import sha256_file
from dmslicer.identity import canonical_digest, region_id
from dmslicer.runner import (
    analyze_case01,
    generate_case01_fixture,
    run_capability_probe,
    run_repeatability,
    validate_case01,
)


def make_fixture(tmp_path: Path) -> Path:
    step_path = tmp_path / "case01.step"
    generate_case01_fixture(step_path, tmp_path / "expected.json")
    return step_path


def analyze_fixture(tmp_path: Path) -> tuple[Path, dict]:
    step_path = make_fixture(tmp_path)
    output_dir = tmp_path / "evidence"
    return output_dir, analyze_case01(step_path, output_dir)


def relation_by_pair(result: dict, semantic_pair: list[str]) -> dict:
    return next(relation for relation in result["relations"] if relation["semantic_pair"] == semantic_pair)


def test_case01_reimports_step_into_exactly_three_solid_regions(tmp_path: Path) -> None:
    """Catches an adapter that analyzes generator memory rather than the re-imported STEP."""
    output_dir, result = analyze_fixture(tmp_path)

    assert result["manifest"]["analysis_input"] == "reimported_step"
    assert result["manifest"]["imported_solid_count"] == 3
    assert len(result["regions"]) == 3
    assert all(region["validation"]["is_valid"] for region in result["regions"])
    assert {region["source_locator"]["source_ordinal"] for region in result["regions"]} == {0, 1, 2}
    for filename in (
        "manifest.json",
        "regions.json",
        "relations.json",
        "interface_patches.json",
        "provenance.json",
    ):
        assert (output_dir / filename).is_file()


def test_case01_has_two_full_face_overlaps_and_one_disjoint_relation(tmp_path: Path) -> None:
    """Catches wrong pair classification or an AABB candidate being promoted without B-rep evidence."""
    _, result = analyze_fixture(tmp_path)

    for pair in (["A", "G"], ["G", "B"]):
        relation = relation_by_pair(result, pair)
        assert relation["relation_type"] == "FULL_FACE_OVERLAP"
        assert relation["intersection_dimension"] == 2
        assert relation["confirmed"] is True
        assert relation["evidence"]["method"] == "face_common_brep"
        assert relation["coverage_a"] == pytest.approx(1.0)
        assert relation["coverage_b"] == pytest.approx(1.0)
    relation_ab = relation_by_pair(result, ["A", "B"])
    assert relation_ab["relation_type"] == "DISJOINT"
    assert relation_ab["confirmed"] is True


def test_case01_patches_have_400_square_mm_and_two_sided_provenance(tmp_path: Path) -> None:
    """Catches accepted contact patches with wrong area or missing source-face lineage."""
    _, result = analyze_fixture(tmp_path)

    patches = result["interface_patches"]
    assert len(patches) == 2
    assert {patch["area_mm2"] for patch in patches} == {400.0}
    for patch in patches:
        assert patch["relation_type"] == "FULL_FACE_OVERLAP"
        assert patch["intersection_dimension"] == 2
        assert patch["source_face_a_id"]
        assert patch["source_face_b_id"]
        assert patch["provenance_method"] == "DIRECT_BREP_FACE_COMMON"
        assert patch["provenance_status"] == "COMPLETE_FOR_DIRECT_COMMON"
        assert patch["coverage_a"] == pytest.approx(1.0)
        assert patch["coverage_b"] == pytest.approx(1.0)
    assert {record["provenance_completeness"] for record in result["provenance"]} == {"COMPLETE_FOR_DIRECT_COMMON"}


def test_case01_validates_actual_against_expected_truth(tmp_path: Path) -> None:
    """Catches evidence publication that bypasses the tracked expected truth."""
    _, result = analyze_fixture(tmp_path)

    assert result["validation"]["status"] == "PASS"
    assert result["manifest"]["validation_status"] == "PASS"


@pytest.mark.parametrize("field, wrong_value", [("relation_type", "FACE_CONTACT"), ("area_mm2", 399.0)])
def test_case01_validator_fails_closed_for_wrong_expected_truth(tmp_path: Path, field: str, wrong_value: object) -> None:
    """Catches a validator that accepts a relation or area disagreement as PASS."""
    _, result = analyze_fixture(tmp_path)
    expected = json.loads((tmp_path / "expected.json").read_text(encoding="utf-8"))
    expected = deepcopy(expected)
    expected["expected_relation_matrix"][0][field] = wrong_value
    expected_without_digest = {key: value for key, value in expected.items() if key != "truth_digest"}
    expected["truth_digest"] = "sha256:" + canonical_digest(expected_without_digest)

    validation = validate_case01(result, expected, tmp_path / "negative")

    assert validation["status"] == "FAIL"
    assert validation["failures"]
    assert any(failure["kind"] == field or failure["kind"] == "interface_area_mm2" for failure in validation["failures"])
    assert (tmp_path / "negative" / "validation.json").is_file()


def test_case01_validator_rejects_unexpected_relation_and_patch(tmp_path: Path) -> None:
    """Catches a subset-only validator that lets extra geometric output pass."""
    _, result = analyze_fixture(tmp_path)
    expected = json.loads((tmp_path / "expected.json").read_text(encoding="utf-8"))
    unexpected = deepcopy(result)
    unexpected["relations"].append({"semantic_pair": ["A", "X"], "relation_type": "FACE_CONTACT", "intersection_dimension": 2})
    unexpected["interface_patches"].append({"semantic_pair": ["A", "X"], "area_mm2": 1.0})

    validation = validate_case01(unexpected, expected, tmp_path / "unexpected")

    assert validation["status"] == "FAIL"
    assert {failure["kind"] for failure in validation["failures"]} >= {"unexpected_relation", "unexpected_interface_patch"}


def test_case01_validator_rejects_duplicate_relation_pair(tmp_path: Path) -> None:
    """Catches duplicate relation evidence hidden by pair-key dictionary collapse."""
    _, result = analyze_fixture(tmp_path)
    expected = json.loads((tmp_path / "expected.json").read_text(encoding="utf-8"))
    duplicated = deepcopy(result)
    duplicated["relations"].append(deepcopy(duplicated["relations"][0]))

    validation = validate_case01(duplicated, expected, tmp_path / "duplicate")

    assert validation["status"] == "FAIL"
    assert any(failure["kind"] == "duplicate_actual_relation" for failure in validation["failures"])


def test_case01_validator_rejects_stale_expected_truth_digest(tmp_path: Path) -> None:
    """Catches a changed expected manifest whose tracked truth digest was not refreshed."""
    _, result = analyze_fixture(tmp_path)
    expected = json.loads((tmp_path / "expected.json").read_text(encoding="utf-8"))
    expected["truth_digest"] = "sha256:" + "0" * 64

    validation = validate_case01(result, expected, tmp_path / "stale-digest")

    assert validation["status"] == "FAIL"
    assert any(failure["kind"] == "expected_truth_digest" for failure in validation["failures"])


def test_case01_constructs_two_semantic_source_boundaries_and_digest(tmp_path: Path) -> None:
    """Catches a geometry-only result that does not activate the two CASE01 Γ boundaries."""
    _, result = analyze_fixture(tmp_path)

    boundaries = result["interface_source_boundaries"]
    assert len(boundaries) == 2
    assert {boundary["source_material_region_id"] for boundary in boundaries} == {
        next(region["region_id"] for region in result["regions"] if region["semantic_id"] == "A"),
        next(region["region_id"] for region in result["regions"] if region["semantic_id"] == "B"),
    }
    assert {boundary["boundary_role"] for boundary in boundaries} == {"SOURCE_A", "SOURCE_B"}
    assert {boundary["boundary_value_placeholder"] for boundary in boundaries} == {0.0, 1.0}
    assert result["semantic_digest"].startswith("sha256:")


def test_region_ids_distinguish_identical_geometry_at_different_occurrences() -> None:
    """Catches collapsing two same-shaped STEP occurrences into one region identity."""
    document = "stepdoc:v1:" + "a" * 64
    geometry = "solidgeo:v1:" + "b" * 64

    assert region_id(document, geometry, {"product_path": ["Assembly", "occurrence-A"]}) != region_id(
        document, geometry, {"product_path": ["Assembly", "occurrence-B"]}
    )


def test_case01_ids_relations_and_provenance_are_repeatable_across_processes(tmp_path: Path) -> None:
    """Catches identities derived from process-specific topology ordering or object addresses."""
    step_path = make_fixture(tmp_path)
    repeatability = run_repeatability(step_path, tmp_path / "evidence")

    assert repeatability["status"] == "PASS"
    assert repeatability["comparison"]["document_ids_match"] is True
    assert repeatability["comparison"]["region_ids_match"] is True
    assert repeatability["comparison"]["face_ids_match"] is True
    assert repeatability["comparison"]["patch_ids_match"] is True
    assert repeatability["comparison"]["relation_mappings_match"] is True
    assert repeatability["comparison"]["provenance_mappings_match"] is True
    assert repeatability["comparison"]["semantic_digest_match"] is True
    assert repeatability["comparison"]["source_boundary_mappings_match"] is True
    assert repeatability["comparison"]["region_geometry_fingerprints_match"] is True
    assert repeatability["comparison"]["candidate_final_status_match"] is True
    assert (tmp_path / "evidence" / "repeatability.json").is_file()


def test_capability_probe_records_actual_boolean_history_limit_and_face_common_path(tmp_path: Path) -> None:
    """Catches a probe that assumes unavailable native history or skips the working B-rep path."""
    output_path = tmp_path / "capability_probe.json"
    probe = run_capability_probe(output_path)

    assert probe["step_export"]["status"] == "AVAILABLE"
    assert probe["step_import"]["status"] == "AVAILABLE"
    assert probe["face_common"]["status"] == "AVAILABLE"
    assert probe["native_boolean_history"]["status"] == "NOT_AVAILABLE"
    assert json.loads(output_path.read_text(encoding="utf-8"))["opencascade"]["status"] == "AVAILABLE"


def test_case01_headless_cli_publishes_analysis_evidence(tmp_path: Path) -> None:
    """Catches a package that works only through Python imports rather than the required headless command."""
    step_path = make_fixture(tmp_path)
    output_dir = tmp_path / "cli_evidence"
    environment = os.environ.copy()
    environment["PYTHONPATH"] = str(Path("src").resolve())

    completed = subprocess.run(
        [sys.executable, "-m", "dmslicer", "analyze-case01", str(step_path), str(output_dir)],
        cwd=Path.cwd(),
        env=environment,
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    assert (output_dir / "manifest.json").is_file()


def test_case01_cli_fails_closed_and_publishes_failure_evidence(tmp_path: Path) -> None:
    """Catches a CLI that returns success after actual output contradicts tracked truth."""
    step_path = make_fixture(tmp_path)
    expected_path = step_path.with_name("expected.json")
    expected = json.loads(expected_path.read_text(encoding="utf-8"))
    expected["expected_relation_matrix"][0]["area_mm2"] = 399.0
    expected_path.write_text(json.dumps(expected), encoding="utf-8")
    output_dir = tmp_path / "cli_negative"
    environment = os.environ.copy()
    environment["PYTHONPATH"] = str(Path("src").resolve())

    completed = subprocess.run(
        [sys.executable, "-m", "dmslicer", "analyze-case01", str(step_path), str(output_dir)],
        cwd=Path.cwd(), env=environment, text=True, capture_output=True, check=False,
    )

    assert completed.returncode != 0
    assert json.loads((output_dir / "validation.json").read_text(encoding="utf-8"))["status"] == "FAIL"


def test_tracked_case01_fixture_and_expected_bundle_validate_directly(tmp_path: Path) -> None:
    """Catches tests that only exercise a freshly generated fixture instead of the tracked bundle."""
    repository_root = Path(__file__).resolve().parents[1]
    step_path = repository_root / "benchmarks" / "interface_case01" / "case01.step"
    expected_path = step_path.with_name("expected.json")
    expected = json.loads(expected_path.read_text(encoding="utf-8"))

    result = analyze_case01(step_path, tmp_path / "tracked")

    assert sha256_file(step_path) == "1cd94489b4709e5292acd8df177950b9acc4c0372016eeefbf889f26170f84de"
    assert expected["truth_digest"] == "sha256:9817ea951def9a559d35d6ccce138e7041fc567a52fce79db0ae46e7137a7a7d"
    assert result["validation"]["status"] == "PASS"
