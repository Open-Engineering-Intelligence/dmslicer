import copy
import hashlib
import json
import math
import sys
from pathlib import Path

import pytest

from dmslicer.planar_gap_assembly_correction_06a import (
    DEFAULT_NUMERIC_RULES,
    decide_correction,
    load_operation_policy,
    run_planar_gap_case,
    validate_operation_evidence,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
MANIFEST = REPO_ROOT / "benchmarks" / "planar_gap_assembly_correction_06a" / "manifest.json"


def _successful_evidence() -> dict:
    return {
        "status": "CORRECTED_AND_FUSED",
        "pre_measurement": {"measured_signed_offset_mm": 0.05, "reference_direction": [0.0, 0.0, 1.0]},
        "decision": {
            "motion_authorized": True,
            "executed_translation_mm": [0.0, 0.0, -0.05],
            "executed_translation_norm_mm": 0.05,
        },
        "policy": {"policy_valid": True, "allow_motion": True, "max_translation_mm": 0.1, "tauE_mm": 0.1},
        "post_measurement": {"measured_signed_offset_mm": 0.0},
        "contact_patch": {
            "dimension": "2D",
            "area_mm2": 10.0,
            "side_1_area_mm2": 10.0,
            "side_2_area_mm2": 10.0,
            "fused_boundary_overlap_area_mm2": 0.0,
        },
        "fuse": {
            "executed": True,
            "solid_count": 1,
            "valid": True,
            "closed": True,
            "volume_conservation_error_mm3": 0.0,
        },
        "invariants": {
            "input_step_hash_unchanged": True,
            "input_manifest_hash_match": True,
            "original_shapes_unchanged": True,
            "side_1_unchanged": True,
            "side_2_inverse_transform_match": True,
            "side_2_volume_unchanged": True,
            "rotation_is_identity": True,
            "scale_is_one": True,
        },
        "reimport": {
            "corrected_assembly": {
                "role_binding": {"Side_1": "Side_1", "Side_2": "Side_2"},
                "residual_offset_mm": 0.0,
                "contact_dimension": "2D",
                "contact_area_mm2": 10.0,
            },
            "fused": {"solid_count": 1, "valid": True, "closed": True},
        },
    }


def _failure_fields(result: dict) -> set[tuple[str, str | None]]:
    return {(item["kind"], item.get("field")) for item in result["failures"]}


@pytest.mark.parametrize(
    ("offset", "policy", "status", "translation"),
    [
        (0.05, {"allow_motion": True, "max_translation_mm": 0.1, "tauE_mm": 0.1}, "CORRECTED_AND_FUSED", 0.05),
        (0.05, {"allow_motion": False, "max_translation_mm": 0.1, "tauE_mm": 0.1}, "MOTION_NOT_AUTHORIZED", 0.0),
        (0.05, {"allow_motion": True, "max_translation_mm": 0.02, "tauE_mm": 0.1}, "TRANSLATION_BUDGET_EXCEEDED", 0.0),
        (0.11, {"allow_motion": True, "max_translation_mm": 0.2, "tauE_mm": 0.1}, "ENGINEERING_TOLERANCE_EXCEEDED", 0.0),
        (0.0, {"allow_motion": True, "max_translation_mm": 0.1, "tauE_mm": 0.1}, "ALREADY_CONTACT", 0.0),
        (-0.05, {"allow_motion": True, "max_translation_mm": 0.1, "tauE_mm": 0.1}, "PENETRATION_OUT_OF_SCOPE", 0.0),
    ],
)
def test_policy_decision_covers_the_six_required_states(offset, policy, status, translation) -> None:
    decision = decide_correction(offset, policy, DEFAULT_NUMERIC_RULES)
    assert decision["status"] == status
    assert decision["executed_translation_norm_mm"] == pytest.approx(translation)


@pytest.mark.parametrize("raw", [None, {}, {"allow_motion": "yes", "max_translation_mm": 0.1, "tauE_mm": 0.1}])
def test_missing_or_illegal_policy_defaults_to_no_motion(tmp_path: Path, raw) -> None:
    path = tmp_path / "policy.json"
    if raw is not None:
        path.write_text(json.dumps(raw), encoding="utf-8")
    policy = load_operation_policy(path)
    decision = decide_correction(0.05, policy, DEFAULT_NUMERIC_RULES)
    assert policy["allow_motion"] is False
    assert decision["status"] == "MOTION_NOT_AUTHORIZED"


def test_validator_rejects_tampered_translation_direction_and_norm() -> None:
    evidence = _successful_evidence()
    assert validate_operation_evidence(evidence, "CORRECTED_AND_FUSED")["status"] == "PASS"
    wrong_direction = copy.deepcopy(evidence)
    wrong_direction["decision"]["executed_translation_mm"] = [0.0, 0.0, 0.05]
    assert validate_operation_evidence(wrong_direction, "CORRECTED_AND_FUSED")["status"] == "FAIL"
    wrong_norm = copy.deepcopy(evidence)
    wrong_norm["decision"]["executed_translation_norm_mm"] = 0.2
    assert validate_operation_evidence(wrong_norm, "CORRECTED_AND_FUSED")["status"] == "FAIL"


@pytest.mark.parametrize(
    ("mutate", "expected_failure"),
    [
        (lambda value: value["policy"].__setitem__("allow_motion", False), ("authorization", "policy.allow_motion")),
        (lambda value: value["policy"].__setitem__("tauE_mm", 0.01), ("policy_constraint", "policy.tauE_mm")),
        (lambda value: value["policy"].__setitem__("policy_valid", False), ("authorization", "policy.policy_valid")),
        (lambda value: value["decision"].__setitem__("motion_authorized", False), ("authorization", "decision.motion_authorized")),
        (lambda value: value["post_measurement"].__setitem__("measured_signed_offset_mm", math.nan), ("invalid_numeric", "post_measurement.measured_signed_offset_mm")),
        (lambda value: value["fuse"].__setitem__("volume_conservation_error_mm3", math.nan), ("invalid_numeric", "fuse.volume_conservation_error_mm3")),
        (lambda value: value["contact_patch"].__setitem__("fused_boundary_overlap_area_mm2", math.nan), ("invalid_numeric", "contact_patch.fused_boundary_overlap_area_mm2")),
        (lambda value: value["reimport"]["corrected_assembly"].__setitem__("residual_offset_mm", math.nan), ("invalid_numeric", "reimport.corrected_assembly.residual_offset_mm")),
    ],
)
def test_validator_rejects_the_eight_authorization_and_nonfinite_counterexamples(mutate, expected_failure) -> None:
    evidence = _successful_evidence()
    mutate(evidence)

    result = validate_operation_evidence(evidence, "CORRECTED_AND_FUSED")

    assert result["status"] == "FAIL"
    assert expected_failure in _failure_fields(result)


@pytest.mark.parametrize(
    ("path", "value"),
    [
        (("pre_measurement", "measured_signed_offset_mm"), math.nan),
        (("pre_measurement", "measured_signed_offset_mm"), math.inf),
        (("pre_measurement", "measured_signed_offset_mm"), -math.inf),
        (("pre_measurement", "reference_direction", 1), math.nan),
        (("decision", "executed_translation_mm", 2), math.inf),
        (("decision", "executed_translation_norm_mm"), math.nan),
        (("policy", "tauE_mm"), math.nan),
        (("policy", "max_translation_mm"), math.inf),
        (("contact_patch", "area_mm2"), math.nan),
        (("contact_patch", "side_1_area_mm2"), -math.inf),
        (("contact_patch", "side_2_area_mm2"), math.inf),
        (("post_measurement", "measured_signed_offset_mm"), math.inf),
        (("fuse", "volume_conservation_error_mm3"), -math.inf),
        (("reimport", "corrected_assembly", "residual_offset_mm"), math.nan),
    ],
)
def test_validator_rejects_nonfinite_required_numeric_evidence(path, value) -> None:
    evidence = _successful_evidence()
    target = evidence
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = value

    result = validate_operation_evidence(evidence, "CORRECTED_AND_FUSED")

    assert result["status"] == "FAIL"
    assert ("invalid_numeric", ".".join(str(key) for key in path)) in _failure_fields(result)


@pytest.mark.parametrize(
    ("path", "expected_field"),
    [
        (("pre_measurement", "measured_signed_offset_mm"), "pre_measurement.measured_signed_offset_mm"),
        (("pre_measurement", "reference_direction"), "pre_measurement.reference_direction"),
        (("decision", "executed_translation_mm"), "decision.executed_translation_mm"),
        (("policy", "tauE_mm"), "policy.tauE_mm"),
        (("contact_patch", "area_mm2"), "contact_patch.area_mm2"),
        (("fuse", "volume_conservation_error_mm3"), "fuse.volume_conservation_error_mm3"),
        (("reimport", "corrected_assembly", "residual_offset_mm"), "reimport.corrected_assembly.residual_offset_mm"),
    ],
)
def test_validator_rejects_missing_required_numeric_evidence(path, expected_field) -> None:
    evidence = _successful_evidence()
    target = evidence
    for key in path[:-1]:
        target = target[key]
    target.pop(path[-1])

    result = validate_operation_evidence(evidence, "CORRECTED_AND_FUSED")

    assert result["status"] == "FAIL"
    assert ("invalid_numeric", expected_field) in _failure_fields(result)


@pytest.mark.parametrize(
    ("path", "expected_field"),
    [
        (("decision", "executed_translation_norm_mm"), "decision.executed_translation_norm_mm"),
        (("policy", "tauE_mm"), "policy.tauE_mm"),
        (("policy", "max_translation_mm"), "policy.max_translation_mm"),
        (("contact_patch", "area_mm2"), "contact_patch.area_mm2"),
        (("contact_patch", "side_1_area_mm2"), "contact_patch.side_1_area_mm2"),
        (("contact_patch", "side_2_area_mm2"), "contact_patch.side_2_area_mm2"),
        (("contact_patch", "fused_boundary_overlap_area_mm2"), "contact_patch.fused_boundary_overlap_area_mm2"),
        (("fuse", "volume_conservation_error_mm3"), "fuse.volume_conservation_error_mm3"),
    ],
)
def test_validator_rejects_negative_nonnegative_evidence(path, expected_field) -> None:
    evidence = _successful_evidence()
    target = evidence
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = -0.01

    result = validate_operation_evidence(evidence, "CORRECTED_AND_FUSED")

    assert result["status"] == "FAIL"
    assert ("numeric_constraint", expected_field) in _failure_fields(result)


def test_validator_rejects_non_unit_or_boolean_reference_normal() -> None:
    non_unit = _successful_evidence()
    non_unit["pre_measurement"]["reference_direction"] = [0.0, 0.0, 0.5]
    bool_component = _successful_evidence()
    bool_component["pre_measurement"]["reference_direction"] = [False, 0.0, 1.0]

    assert ("numeric_constraint", "pre_measurement.reference_direction") in _failure_fields(
        validate_operation_evidence(non_unit, "CORRECTED_AND_FUSED")
    )
    assert ("invalid_numeric", "pre_measurement.reference_direction.0") in _failure_fields(
        validate_operation_evidence(bool_component, "CORRECTED_AND_FUSED")
    )


def test_validator_accepts_already_contact_with_zero_motion_without_motion_authorization() -> None:
    evidence = _successful_evidence()
    evidence["status"] = "ALREADY_CONTACT"
    evidence["pre_measurement"]["measured_signed_offset_mm"] = 0.0
    evidence["decision"].update(
        {
            "motion_authorized": False,
            "executed_translation_mm": [0.0, 0.0, 0.0],
            "executed_translation_norm_mm": 0.0,
        }
    )
    evidence["policy"]["allow_motion"] = False

    assert validate_operation_evidence(evidence, "ALREADY_CONTACT")["status"] == "PASS"


@pytest.mark.parametrize(
    ("status", "offset", "policy"),
    [
        ("MOTION_NOT_AUTHORIZED", 0.05, {"policy_valid": True, "allow_motion": False, "max_translation_mm": 0.1, "tauE_mm": 0.1}),
        ("TRANSLATION_BUDGET_EXCEEDED", 0.05, {"policy_valid": True, "allow_motion": True, "max_translation_mm": 0.02, "tauE_mm": 0.1}),
        ("ENGINEERING_TOLERANCE_EXCEEDED", 0.11, {"policy_valid": True, "allow_motion": True, "max_translation_mm": 0.2, "tauE_mm": 0.1}),
        ("PENETRATION_OUT_OF_SCOPE", -0.05, {"policy_valid": True, "allow_motion": True, "max_translation_mm": 0.1, "tauE_mm": 0.1}),
    ],
)
def test_validator_accepts_legal_rejections_with_zero_motion_and_no_fuse(status, offset, policy) -> None:
    evidence = _successful_evidence()
    evidence["status"] = status
    evidence["pre_measurement"]["measured_signed_offset_mm"] = offset
    evidence["decision"].update(
        {
            "motion_authorized": False,
            "executed_translation_mm": [0.0, 0.0, 0.0],
            "executed_translation_norm_mm": 0.0,
        }
    )
    evidence["policy"] = policy
    evidence["fuse"] = {"executed": False}
    evidence["post_measurement"] = {}
    evidence["contact_patch"] = {}
    evidence["reimport"] = {}

    assert validate_operation_evidence(evidence, status)["status"] == "PASS"


def test_six_scenario_manifest_reuses_four_tracked_inputs_by_hash() -> None:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    assert [row["scenario_id"] for row in manifest["scenarios"]] == ["P01", "P02", "P03", "P04", "P05", "P06"]
    assert len({row["input"]["step_path"] for row in manifest["scenarios"]}) == 4
    for row in manifest["scenarios"]:
        path = REPO_ROOT / row["input"]["step_path"]
        assert path.is_file()
        assert hashlib.sha256(path.read_bytes()).hexdigest() == row["input"]["step_sha256"]


@pytest.mark.parametrize("scenario_id", ["P01", "P02", "P03", "P04", "P05", "P06"])
def test_required_scenario_runs_from_real_tracked_step(tmp_path: Path, scenario_id: str) -> None:
    result = run_planar_gap_case(MANIFEST, scenario_id, tmp_path / "runs")
    assert result["validation"]["status"] == "PASS"
    assert result["operation"]["status"] == result["expected"]["status"]
    assert result["operation"]["input_step_sha256"] == result["manifest_row"]["input"]["step_sha256"]


def test_expected_mutation_does_not_change_measured_action(tmp_path: Path) -> None:
    first = run_planar_gap_case(MANIFEST, "P01", tmp_path / "first")["operation"]
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    expected_path = REPO_ROOT / manifest["scenarios"][0]["expected_path"]
    mutated = json.loads(expected_path.read_text(encoding="utf-8"))
    mutated["status"] = "MOTION_NOT_AUTHORIZED"
    custom_expected = tmp_path / "mutated_expected.json"
    custom_expected.write_text(json.dumps(mutated), encoding="utf-8")
    manifest["scenarios"][0]["expected_path"] = str(custom_expected)
    custom_manifest = tmp_path / "manifest.json"
    custom_manifest.write_text(json.dumps(manifest), encoding="utf-8")
    second = run_planar_gap_case(custom_manifest, "P01", tmp_path / "second", repo_root=REPO_ROOT)["operation"]
    assert second["pre_measurement"] == first["pre_measurement"]
    assert second["decision"] == first["decision"]
    assert second["status"] == first["status"]
    assert second["contact_patch"] == first["contact_patch"]
    assert second["fuse"] == first["fuse"]


def test_object_and_face_traversal_order_do_not_change_action(tmp_path: Path) -> None:
    normal = run_planar_gap_case(MANIFEST, "P01", tmp_path / "normal")["operation"]
    reversed_run = run_planar_gap_case(MANIFEST, "P01", tmp_path / "reversed", traversal_order="reverse")["operation"]
    assert reversed_run["pre_measurement"]["measured_signed_offset_mm"] == pytest.approx(normal["pre_measurement"]["measured_signed_offset_mm"])
    assert reversed_run["decision"] == normal["decision"]
    assert reversed_run["contact_patch"]["area_mm2"] == pytest.approx(normal["contact_patch"]["area_mm2"])


def test_corrected_output_is_idempotent_and_two_processes_match(tmp_path: Path) -> None:
    first = run_planar_gap_case(MANIFEST, "P01", tmp_path / "one")["operation"]
    second = run_planar_gap_case(MANIFEST, "P01", tmp_path / "two")["operation"]
    for key in ("status", "pre_measurement", "decision", "contact_patch", "fuse", "invariants", "reimport"):
        assert second[key] == first[key]
    rerun = run_planar_gap_case(
        MANIFEST,
        "P01",
        tmp_path / "idempotent",
        step_override=Path(first["artifacts"]["corrected_assembly_step"]),
    )["operation"]
    assert rerun["status"] == "ALREADY_CONTACT"
    assert rerun["decision"]["executed_translation_norm_mm"] == 0.0


def test_failed_run_does_not_overwrite_previous_success(tmp_path: Path, monkeypatch) -> None:
    from dmslicer import planar_gap_assembly_correction_06a as module

    root = tmp_path / "runs"
    run_planar_gap_case(MANIFEST, "P01", root)
    prior = (root / "P01" / "operation.json").read_bytes()
    monkeypatch.setattr(module, "_run_freecad", lambda request: (_ for _ in ()).throw(RuntimeError("injected failure")))
    with pytest.raises(RuntimeError, match="injected failure"):
        run_planar_gap_case(MANIFEST, "P01", root)
    assert (root / "P01" / "operation.json").read_bytes() == prior


def test_postcheck_failure_is_diagnostic_and_does_not_replace_success(tmp_path: Path, monkeypatch) -> None:
    from dmslicer import planar_gap_assembly_correction_06a as module

    root = tmp_path / "runs"
    successful = run_planar_gap_case(MANIFEST, "P01", root)["operation"]
    prior = (root / "P01" / "operation.json").read_bytes()
    failed = copy.deepcopy(successful)
    failed["status"] = "POSTCHECK_FAILED"
    failed["postcheck_failures"] = ["injected"]
    monkeypatch.setattr(module, "_run_freecad", lambda request: failed)
    result = run_planar_gap_case(MANIFEST, "P01", root)
    assert result["operation"]["status"] == "POSTCHECK_FAILED"
    assert result["validation"]["status"] == "FAIL"
    assert (root / "P01" / "operation.json").read_bytes() == prior
    assert (root / "P01_failed_attempt" / "operation.json").is_file()


def test_cli_returns_nonzero_when_case_validation_fails(monkeypatch, tmp_path: Path) -> None:
    from dmslicer import planar_gap_assembly_correction_06a as module

    monkeypatch.setattr(module, "run_planar_gap_case", lambda *args, **kwargs: {"validation": {"status": "FAIL"}})
    monkeypatch.setattr(sys, "argv", ["planar-gap-06a", "case", str(MANIFEST), str(tmp_path)])

    with pytest.raises(SystemExit) as result:
        module._main()

    assert result.value.code == 1


def test_p01_and_rejection_fcstd_reopen_with_unambiguous_visibility(tmp_path: Path) -> None:
    success = run_planar_gap_case(MANIFEST, "P01", tmp_path / "runs", create_view=True)["operation"]
    rejected = run_planar_gap_case(MANIFEST, "P02", tmp_path / "runs", create_view=True)["operation"]
    assert Path(success["artifacts"]["fcstd"]).is_file()
    assert Path(rejected["artifacts"]["fcstd"]).is_file()
    assert success["view_reopen"]["visible_objects"] == ["Actual_Fused_Result"]
    assert set(rejected["view_reopen"]["visible_objects"]) == {"Original_Side_1", "Original_Side_2"}
