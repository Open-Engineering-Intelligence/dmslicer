import copy
import json
import math
import sys
from pathlib import Path

import pytest

from dmslicer.planar_partial_overlap_correction_06b import (
    FIXTURE_ROOT,
    generate_partial_overlap_fixtures,
    run_partial_overlap_case,
    validate_partial_overlap_evidence,
)


def test_generator_creates_three_independent_tracked_step_bundles(tmp_path: Path) -> None:
    manifest = generate_partial_overlap_fixtures(tmp_path)
    assert [row["scenario_id"] for row in manifest["scenarios"]] == ["P07", "P08", "P09"]
    for row in manifest["scenarios"]:
        case = tmp_path / row["scenario_id"]
        assert (case / "inputs.step").is_file()
        assert (case / "policy.json").is_file()
        assert (case / "expected.json").is_file()


@pytest.mark.parametrize(
    ("scenario_id", "status", "area", "coverage", "remaining"),
    [
        ("P07", "CORRECTED_PARTIAL_INTERFACE_FUSED", 480.0, (0.6, 0.6), (320.0, 320.0)),
        ("P08", "CORRECTED_PARTIAL_INTERFACE_FUSED", 200.0, (0.2, 1.0), (800.0, 0.0)),
        ("P09", "NO_POSITIVE_AREA_INTERFACE", 0.0, None, None),
    ],
)
def test_real_tracked_cases_measure_partial_interfaces_and_preserve_lateral_pose(tmp_path: Path, scenario_id, status, area, coverage, remaining) -> None:
    result = run_partial_overlap_case(FIXTURE_ROOT, scenario_id, tmp_path / "runs")
    operation = result["operation"]
    assert result["validation"]["status"] == "PASS"
    assert operation["status"] == status
    assert operation["prospective_interface"]["common_area_mm2"] == pytest.approx(area, abs=1e-8)
    assert operation["pose_invariants"]["tangential_translation_norm_mm"] == pytest.approx(0.0, abs=1e-8)
    assert operation["pose_invariants"]["tangential_projection_relation_preserved"] is True
    if coverage is None:
        assert operation["decision"]["executed_translation_norm_mm"] == 0.0
        assert operation["fuse"]["executed"] is False
    else:
        assert operation["partition"]["common_area_mm2"] == pytest.approx(area, abs=1e-8)
        assert tuple(operation["partition"]["coverage"][key] for key in ("Side_1", "Side_2")) == pytest.approx(coverage)
        assert tuple(operation["partition"]["remaining_area_mm2"][key] for key in ("Side_1", "Side_2")) == pytest.approx(remaining)
        assert operation["partition"]["area_conserved"] is True
        assert operation["partition"]["spatial_coverage"] is True
        assert operation["fuse"]["solid_count"] == 1


def test_expected_mutation_cannot_change_actual_partial_overlap_geometry(tmp_path: Path) -> None:
    first = run_partial_overlap_case(FIXTURE_ROOT, "P07", tmp_path / "first")["operation"]
    source = FIXTURE_ROOT / "P07"
    mutated = tmp_path / "P07"
    mutated.mkdir()
    for name in ("inputs.step", "policy.json", "expected.json"):
        (mutated / name).write_bytes((source / name).read_bytes())
    expected = json.loads((mutated / "expected.json").read_text(encoding="utf-8"))
    expected["common_area_mm2"] = 1.0
    expected["status"] = "NO_POSITIVE_AREA_INTERFACE"
    (mutated / "expected.json").write_text(json.dumps(expected), encoding="utf-8")
    second = run_partial_overlap_case(tmp_path, "P07", tmp_path / "second")["operation"]
    assert second["decision"] == first["decision"]
    assert second["partition"] == first["partition"]
    assert second["status"] == first["status"]


def test_validator_rejects_tangential_motion_coverage_nan_and_tampered_partition(tmp_path: Path) -> None:
    evidence = run_partial_overlap_case(FIXTURE_ROOT, "P07", tmp_path / "source")["operation"]
    tangent = copy.deepcopy(evidence)
    tangent["decision"]["executed_translation_mm"][0] = 0.01
    tangent["decision"]["executed_translation_norm_mm"] = math.sqrt(0.05**2 + 0.01**2)
    tangent["pose_invariants"]["tangential_translation_norm_mm"] = 0.01
    assert any(item["kind"] == "tangential_translation" for item in validate_partial_overlap_evidence(tangent, {"status": tangent["status"]})["failures"])
    bad_coverage = copy.deepcopy(evidence)
    bad_coverage["partition"]["coverage"]["Side_1"] = math.nan
    assert any(item["kind"] == "coverage" for item in validate_partial_overlap_evidence(bad_coverage, {"status": bad_coverage["status"]})["failures"])
    bad_partition = copy.deepcopy(evidence)
    bad_partition["partition"]["remaining_area_mm2"]["Side_1"] = 0.0
    assert any(item["kind"] == "area_conservation" for item in validate_partial_overlap_evidence(bad_partition, {"status": bad_partition["status"]})["failures"])


@pytest.mark.parametrize(
    ("path", "value", "kind", "field"),
    [
        (("policy", "allow_motion"), False, "authorization", "policy.allow_motion"),
        (("policy", "policy_valid"), False, "authorization", "policy.policy_valid"),
        (("decision", "motion_authorized"), False, "authorization", "decision.motion_authorized"),
        (("policy", "tauE_mm"), 0.01, "policy_constraint", "policy.tauE_mm"),
        (("pre_measurement", "measured_signed_offset_mm"), math.nan, "invalid_numeric", "pre_measurement.measured_signed_offset_mm"),
        (("pre_measurement", "reference_direction", 2), math.inf, "invalid_numeric", "pre_measurement.reference_direction.2"),
        (("decision", "executed_translation_norm_mm"), math.nan, "invalid_numeric", "decision.executed_translation_norm_mm"),
        (("post_measurement", "measured_signed_offset_mm"), math.nan, "invalid_numeric", "post_measurement.measured_signed_offset_mm"),
        (("partition", "common_area_mm2"), math.nan, "common_area", None),
        (("fuse", "volume_conservation_error_mm3"), math.inf, "volume_conservation", None),
        (("reimport", "corrected_assembly", "residual_offset_mm"), math.nan, "invalid_numeric", "reimport.corrected_assembly.residual_offset_mm"),
    ],
)
def test_validator_rejects_authorization_and_nonfinite_required_evidence(tmp_path: Path, path, value, kind, field) -> None:
    evidence = run_partial_overlap_case(FIXTURE_ROOT, "P07", tmp_path / "source")["operation"]
    target = evidence
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = value
    result = validate_partial_overlap_evidence(evidence, {"status": evidence["status"]})
    assert result["status"] == "FAIL"
    assert any(item["kind"] == kind and (field is None or item.get("field") == field) for item in result["failures"])


@pytest.mark.parametrize("path", [("partition", "common_area_mm2"), ("partition", "coverage", "Side_1"), ("fuse", "volume_conservation_error_mm3")])
def test_validator_rejects_missing_required_success_evidence(tmp_path: Path, path) -> None:
    evidence = run_partial_overlap_case(FIXTURE_ROOT, "P07", tmp_path / "source")["operation"]
    target = evidence
    for key in path[:-1]:
        target = target[key]
    target.pop(path[-1])
    assert validate_partial_overlap_evidence(evidence, {"status": evidence["status"]})["status"] == "FAIL"


def test_two_independent_processes_are_repeatable_and_p09_never_publishes_success_outputs(tmp_path: Path) -> None:
    first = run_partial_overlap_case(FIXTURE_ROOT, "P07", tmp_path / "one")["operation"]
    second = run_partial_overlap_case(FIXTURE_ROOT, "P07", tmp_path / "two", traversal_order="reverse")["operation"]
    for key in ("status", "pre_measurement", "decision", "prospective_interface", "partition", "fuse", "pose_invariants"):
        assert second[key] == first[key]
    rejected = run_partial_overlap_case(FIXTURE_ROOT, "P09", tmp_path / "rejected", create_view=True)["operation"]
    assert "artifacts" not in rejected
    assert rejected["decision"]["executed_translation_norm_mm"] == 0.0


def test_failed_validation_cannot_replace_previous_success_and_cli_is_nonzero(monkeypatch, tmp_path: Path) -> None:
    from dmslicer import planar_partial_overlap_correction_06b as module

    root = tmp_path / "runs"
    run_partial_overlap_case(FIXTURE_ROOT, "P07", root)
    prior = (root / "P07" / "operation.json").read_bytes()
    original = module._run_freecad
    def invalid(request):
        result = original(request)
        if request["action"] == "analyze":
            result["operation"]["fuse"]["volume_conservation_error_mm3"] = math.nan
        return result
    monkeypatch.setattr(module, "_run_freecad", invalid)
    result = module.run_partial_overlap_case(FIXTURE_ROOT, "P07", root)
    assert result["validation"]["status"] == "FAIL"
    assert (root / "P07" / "operation.json").read_bytes() == prior
    monkeypatch.setattr(module, "run_partial_overlap_case", lambda *args, **kwargs: {"validation": {"status": "FAIL"}})
    monkeypatch.setattr(sys, "argv", ["partial-06b", "case", str(FIXTURE_ROOT), "--output", str(tmp_path / "cli")])
    with pytest.raises(SystemExit) as exit_result:
        module._main()
    assert exit_result.value.code == 1
