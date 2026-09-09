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
    ValidationError,
    _compare_repeatability_snapshots,
    _repeatability_snapshot,
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


def write_semantics(path: Path) -> None:
    """Write CASE01 input roles, deliberately separate from expected truth."""
    path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "case_id": "CASE01_planar_agb_exact",
                "semantic_order": ["A", "G", "B"],
                "occurrences": [
                    {
                        "product_path": ["A"],
                        "source_label": "A",
                        "semantic_id": "A",
                        "semantic_role": "SOURCE",
                        "material_key": "A",
                        "participation_policy": {"mode": "ACTIVE", "source_eligible": True, "gradient_eligible": False},
                        "source_boundary": {"boundary_role": "SOURCE_A", "condition_kind": "DIRICHLET_SCALAR", "scalar_value": 0.0},
                    },
                    {
                        "product_path": ["G"],
                        "source_label": "G",
                        "semantic_id": "G",
                        "semantic_role": "GRADIENT",
                        "material_key": "Gradient",
                        "participation_policy": {"mode": "ACTIVE", "source_eligible": False, "gradient_eligible": True},
                    },
                    {
                        "product_path": ["B"],
                        "source_label": "B",
                        "semantic_id": "B",
                        "semantic_role": "SOURCE",
                        "material_key": "B",
                        "participation_policy": {"mode": "ACTIVE", "source_eligible": True, "gradient_eligible": False},
                        "source_boundary": {"boundary_role": "SOURCE_B", "condition_kind": "DIRICHLET_SCALAR", "scalar_value": 1.0},
                    },
                ],
            },
            sort_keys=True,
        ),
        encoding="utf-8",
    )


def refresh_truth_digest(expected: dict) -> None:
    payload = {key: value for key, value in expected.items() if key != "truth_digest"}
    expected["truth_digest"] = "sha256:" + canonical_digest(payload)


def geometry_evidence(output_dir: Path) -> dict:
    return json.loads((output_dir / "geometry.json").read_text(encoding="utf-8"))


@pytest.mark.parametrize("mutation", ["relation", "area", "region_order", "region_label"])
def test_expected_truth_mutations_cannot_change_frozen_geometry(tmp_path: Path, mutation: str) -> None:
    """Catches expected truth leaking into actual geometry construction or ordering."""
    step_path = make_fixture(tmp_path)
    semantics_path = tmp_path / "semantics.json"
    write_semantics(semantics_path)
    expected_path = tmp_path / "expected.json"
    baseline_dir = tmp_path / "baseline"
    baseline = analyze_case01(step_path, baseline_dir, expected_path=expected_path, semantics_path=semantics_path)

    expected = json.loads(expected_path.read_text(encoding="utf-8"))
    if mutation == "relation":
        expected["expected_relation_matrix"][0]["relation_type"] = "FACE_CONTACT"
    elif mutation == "area":
        expected["expected_relation_matrix"][0]["area_mm2"] = 399.0
    elif mutation == "region_order":
        expected["regions"].reverse()
    else:
        expected["regions"][0]["source_label"] = "not-an-occurrence"
    refresh_truth_digest(expected)
    expected_path.write_text(json.dumps(expected), encoding="utf-8")

    mutated_dir = tmp_path / mutation
    if mutation in {"relation", "area"}:
        with pytest.raises(ValidationError):
            analyze_case01(step_path, mutated_dir, expected_path=expected_path, semantics_path=semantics_path)
    else:
        changed = analyze_case01(step_path, mutated_dir, expected_path=expected_path, semantics_path=semantics_path)
        if mutation == "region_label":
            assert changed["semantic_digest"] == baseline["semantic_digest"]

    assert geometry_evidence(mutated_dir) == geometry_evidence(baseline_dir)
    assert baseline["geometry_digest"] == geometry_evidence(baseline_dir)["geometry_digest"]


def test_semantic_input_can_change_boundaries_without_changing_geometry(tmp_path: Path) -> None:
    """Catches a semantic role changing the B-rep geometry result."""
    step_path = make_fixture(tmp_path)
    expected_path = tmp_path / "expected.json"
    semantics_path = tmp_path / "semantics.json"
    write_semantics(semantics_path)
    baseline_dir = tmp_path / "baseline"
    baseline = analyze_case01(step_path, baseline_dir, expected_path=expected_path, semantics_path=semantics_path)

    semantics = json.loads(semantics_path.read_text(encoding="utf-8"))
    semantics["occurrences"][0]["source_boundary"]["scalar_value"] = 0.25
    semantics_path.write_text(json.dumps(semantics), encoding="utf-8")
    changed_dir = tmp_path / "semantic-change"
    changed = analyze_case01(step_path, changed_dir, expected_path=expected_path, semantics_path=semantics_path)

    assert geometry_evidence(changed_dir) == geometry_evidence(baseline_dir)
    assert changed["semantic_digest"] != baseline["semantic_digest"]


def test_geometry_evidence_is_published_before_missing_expected_fails_validation(tmp_path: Path) -> None:
    """Catches a missing expected.json preventing independent geometry analysis."""
    step_path = make_fixture(tmp_path)
    semantics_path = tmp_path / "semantics.json"
    write_semantics(semantics_path)
    output_dir = tmp_path / "missing-expected"

    with pytest.raises(ValidationError):
        analyze_case01(step_path, output_dir, expected_path=tmp_path / "missing.json", semantics_path=semantics_path)

    assert geometry_evidence(output_dir)["geometry_digest"].startswith("sha256:")


def test_geometry_evidence_is_published_before_invalid_expected_fails_validation(tmp_path: Path) -> None:
    """Catches malformed expected truth aborting before actual geometry is preserved."""
    step_path = make_fixture(tmp_path)
    semantics_path = tmp_path / "semantics.json"
    write_semantics(semantics_path)
    expected_path = tmp_path / "invalid.json"
    expected_path.write_text("{ not-json", encoding="utf-8")
    output_dir = tmp_path / "invalid-expected"

    with pytest.raises(ValidationError):
        analyze_case01(step_path, output_dir, expected_path=expected_path, semantics_path=semantics_path)

    assert geometry_evidence(output_dir)["geometry_digest"].startswith("sha256:")
    assert json.loads((output_dir / "validation.json").read_text(encoding="utf-8"))["status"] == "FAIL"


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


@pytest.mark.parametrize(
    ("mutation", "expected_category"),
    [
        ("coverage_a", "coverage_a"),
        ("coverage_b", "coverage_b"),
        ("provenance_id", "provenance_id"),
        ("provenance_input", "provenance_input_entity_ids"),
        ("provenance_output", "provenance_output_entity_ids"),
        ("source_face_a", "source_face_a_id"),
        ("missing_coverage", "coverage_a"),
    ],
)
def test_repeatability_rejects_patch_and_provenance_mutations(
    tmp_path: Path, mutation: str, expected_category: str
) -> None:
    """Catches snapshot omissions that would let changed patch evidence report PASS."""
    _, actual = analyze_fixture(tmp_path)
    changed = deepcopy(actual)
    patch = changed["interface_patches"][0]
    provenance = next(record for record in changed["provenance"] if record["provenance_id"] == patch["provenance_id"])
    if mutation == "coverage_a":
        patch["coverage_a"] = 0.25
    elif mutation == "coverage_b":
        patch["coverage_b"] = 0.25
    elif mutation == "provenance_id":
        patch["provenance_id"] = "provenance:v1:changed"
    elif mutation == "provenance_input":
        provenance["input_entity_ids"][0] = "region:v1:changed"
    elif mutation == "provenance_output":
        provenance["output_entity_ids"][0] = "patch:v1:changed"
    elif mutation == "source_face_a":
        patch["source_face_a_id"] = "face:v1:changed"
    else:
        del patch["coverage_a"]

    comparison, failures = _compare_repeatability_snapshots(
        _repeatability_snapshot(actual), _repeatability_snapshot(changed)
    )

    assert comparison["patch_mappings_match"] is False
    assert any(
        failure["patch_id"] == actual["interface_patches"][0]["patch_id"]
        and failure["category"] == expected_category
        for failure in failures
    )
    assert not all(comparison.values())


def test_repeatability_snapshot_accepts_identical_records_and_unordered_output(tmp_path: Path) -> None:
    """Catches comparison logic that mistakes non-semantic list order for evidence change."""
    _, actual = analyze_fixture(tmp_path)
    reordered = deepcopy(actual)
    reordered["interface_patches"].reverse()
    reordered["provenance"].reverse()

    comparison, failures = _compare_repeatability_snapshots(
        _repeatability_snapshot(actual), _repeatability_snapshot(reordered)
    )

    assert all(comparison.values())
    assert failures == []


def test_repeatability_snapshot_rejects_two_missing_required_fields(tmp_path: Path) -> None:
    """Catches two absent values being treated as equal repeatability evidence."""
    _, actual = analyze_fixture(tmp_path)
    first = deepcopy(actual)
    second = deepcopy(actual)
    del first["interface_patches"][0]["coverage_a"]
    del second["interface_patches"][0]["coverage_a"]

    comparison, failures = _compare_repeatability_snapshots(
        _repeatability_snapshot(first), _repeatability_snapshot(second)
    )

    assert comparison["patch_mappings_match"] is False
    assert any(failure["category"] == "coverage_a" for failure in failures)


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

    assert sha256_file(step_path) == "089629b5d4e081bc208f49abad3329d0dade9b1de0525e97cb06d75ef43bdbae"
    assert expected["truth_digest"] == "sha256:9817ea951def9a559d35d6ccce138e7041fc567a52fce79db0ae46e7137a7a7d"
    assert result["validation"]["status"] == "PASS"
