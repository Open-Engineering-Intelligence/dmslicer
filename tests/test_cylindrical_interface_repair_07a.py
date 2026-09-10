from __future__ import annotations

import math
from pathlib import Path
import json
import os
import subprocess
import sys

import pytest

from dmslicer.cylindrical_interface_repair_07a import (
    RULES,
    axis_relation,
    classify_cylindrical_error,
    decide_repair,
    generate_cylindrical_interface_repair_fixtures,
    operation_projection,
    radial_relation,
    run_cylindrical_repair_case,
    run_cylindrical_repair_suite,
    validate_published_artifacts,
)


def test_axis_relation_ignores_line_origins_and_direction_sign() -> None:
    relation = axis_relation(
        [3.0, -2.0, 10.0],
        [0.0, 0.0, 1.0],
        [3.05, -2.0, -40.0],
        [0.0, 0.0, -1.0],
    )

    assert relation["axis_angle_rad"] == pytest.approx(0.0, abs=1e-15)
    assert relation["axis_offset_vector_mm"] == pytest.approx([0.05, 0.0, 0.0])
    assert relation["axis_offset_mm"] == pytest.approx(0.05)


def test_axis_relation_is_covariant_under_proper_rotation() -> None:
    # +90 degrees about world Z maps +X to +Y.
    base = axis_relation([0, 0, 0], [0, 0, 1], [0.05, 0, 7], [0, 0, 1])
    rotated = axis_relation([0, 0, 0], [0, 0, 1], [0, 0.05, 7], [0, 0, 1])

    assert base["axis_offset_vector_mm"] == pytest.approx([0.05, 0.0, 0.0])
    assert rotated["axis_offset_vector_mm"] == pytest.approx([0.0, 0.05, 0.0])


def test_nonparallel_axis_distance_ignores_each_axis_point_parameterization() -> None:
    first = axis_relation([0, 0, 0], [0, 0, 1], [0, 0, 0], [0.001, 0, 1])
    shifted = axis_relation([0, 0, 10], [0, 0, 1], [5, 0, 5000], [0.001, 0, 1])

    assert first["axis_angle_rad"] == pytest.approx(shifted["axis_angle_rad"])
    assert first["axis_offset_mm"] == pytest.approx(0.0, abs=1e-12)
    assert shifted["axis_offset_mm"] == pytest.approx(0.0, abs=1e-9)


def test_axis_relation_rejects_nonfinite_and_boolean_components() -> None:
    for point in ([math.nan, 0, 0], [True, 0, 0]):
        with pytest.raises(ValueError, match="finite three-vector"):
            axis_relation(point, [0, 0, 1], [0, 0, 0], [0, 0, 1])


@pytest.mark.parametrize(
    ("bore_radius", "shaft_radius", "expected"),
    [
        (10.0, 10.0, "RADIUS_COMPATIBLE"),
        (10.05, 10.0, "DIMENSIONAL_RADIAL_CLEARANCE"),
        (10.0, 10.05, "DIMENSIONAL_RADIAL_INTERFERENCE"),
    ],
)
def test_radial_relation_preserves_a07_clearance_sign(
    bore_radius: float, shaft_radius: float, expected: str
) -> None:
    relation = radial_relation(bore_radius, shaft_radius)
    assert relation["radial_clearance_mm"] == pytest.approx(bore_radius - shaft_radius)
    assert relation["state"] == expected


def test_classification_keeps_dimensional_error_out_of_motion_path() -> None:
    result = classify_cylindrical_error(
        axis_angle_rad=0.0,
        axis_offset_mm=0.0,
        radial_clearance_mm=0.05,
        axial_overlap_mm=30.0,
        actual_common_area_mm2=0.0,
    )
    decision = decide_repair(result, [0.0, 0.0, 0.0], {
        "policy_valid": True,
        "allow_motion": True,
        "allow_pose_interference_resolution": True,
        "tauE_mm": 0.1,
        "max_translation_mm": 0.1,
    })

    assert result["classification"] == "DIMENSIONAL_RADIAL_CLEARANCE"
    assert decision["repairability"] == "RIGID_POSITION_CORRECTION_NOT_APPLICABLE"
    assert decision["executed_translation_mm"] == [0.0, 0.0, 0.0]


def test_exact_contact_requires_actual_positive_area_common() -> None:
    exact = classify_cylindrical_error(
        axis_angle_rad=0.0,
        axis_offset_mm=0.0,
        radial_clearance_mm=0.0,
        axial_overlap_mm=30.0,
        actual_common_area_mm2=100.0,
    )
    mismatch = classify_cylindrical_error(
        axis_angle_rad=0.0,
        axis_offset_mm=0.0,
        radial_clearance_mm=0.0,
        axial_overlap_mm=30.0,
        actual_common_area_mm2=0.0,
    )

    assert exact["classification"] == "EXACT_CYLINDRICAL_CONTACT"
    assert mismatch["classification"] == "GEOMETRY_RELATION_MISMATCH"


def test_compound_error_is_not_reduced_to_one_component() -> None:
    result = classify_cylindrical_error(
        axis_angle_rad=1e-3,
        axis_offset_mm=0.05,
        radial_clearance_mm=0.05,
        axial_overlap_mm=30.0,
        actual_common_area_mm2=0.0,
    )
    assert result["classification"] == "COMPOUND_ERROR_UNSUPPORTED"
    assert set(result["error_components"]) == {"ANGULAR", "POSITIONAL", "DIMENSIONAL"}


def test_positional_repair_requires_specific_interference_authorization() -> None:
    classification = classify_cylindrical_error(
        axis_angle_rad=0.0,
        axis_offset_mm=0.05,
        radial_clearance_mm=0.0,
        axial_overlap_mm=30.0,
        actual_common_area_mm2=0.0,
    )
    denied = decide_repair(classification, [0.05, 0.0, 0.0], {
        "policy_valid": True,
        "allow_motion": True,
        "allow_pose_interference_resolution": False,
        "tauE_mm": 0.1,
        "max_translation_mm": 0.1,
    })
    allowed = decide_repair(classification, [0.05, 0.0, 0.0], {
        "policy_valid": True,
        "allow_motion": True,
        "allow_pose_interference_resolution": True,
        "tauE_mm": 0.1,
        "max_translation_mm": 0.1,
    })

    assert denied["status"] == "MOTION_NOT_AUTHORIZED"
    assert denied["executed_translation_mm"] == [0.0, 0.0, 0.0]
    assert allowed["status"] == "AUTHORIZED_FOR_SINGLE_TRANSLATION"
    assert allowed["proposed_translation_mm"] == pytest.approx([-0.05, 0.0, 0.0])
    assert allowed["executed_translation_mm"] == [0.0, 0.0, 0.0]


def test_positional_repair_applies_tau_e_before_motion_budget() -> None:
    classification = {"classification": "AXIS_TRANSLATIONAL_MISALIGNMENT"}
    base_policy = {
        "policy_valid": True,
        "allow_motion": True,
        "allow_pose_interference_resolution": True,
        "tauE_mm": 0.1,
        "max_translation_mm": 1.0,
    }
    assert decide_repair(classification, [0.11, 0, 0], base_policy)["status"] == "ENGINEERING_TOLERANCE_EXCEEDED"
    assert decide_repair(classification, [0.05, 0, 0], {**base_policy, "max_translation_mm": 0.04})["status"] == "TRANSLATION_BUDGET_EXCEEDED"


def test_declared_numeric_rules_are_unit_bearing() -> None:
    assert RULES == {
        "linear_epsilon_mm": 1e-7,
        "radius_epsilon_mm": 1e-7,
        "angular_epsilon_rad": 1e-7,
        "area_epsilon_mm2": 1e-8,
        "volume_epsilon_mm3": 1e-6,
        "periodic_epsilon_rad": 1e-6,
        "material_probe_offset_mm": 1e-5,
    }


def test_actual_brep_principal_scenarios_enforce_taxonomy(tmp_path: Path) -> None:
    fixtures = tmp_path / "fixtures"
    generated = generate_cylindrical_interface_repair_fixtures(fixtures)
    assert generated["status"] == "PASS"

    expected = {
        "C01": ("EXACT_CYLINDRICAL_CONTACT", "NO_CORRECTION_REQUIRED"),
        "C02": ("AXIS_TRANSLATIONAL_MISALIGNMENT", "CORRECTED_AND_FUSED"),
        "C03": ("DIMENSIONAL_RADIAL_CLEARANCE", "RIGID_POSITION_CORRECTION_NOT_APPLICABLE"),
        "C04": ("DIMENSIONAL_RADIAL_INTERFERENCE", "RIGID_POSITION_CORRECTION_NOT_APPLICABLE"),
        "C05": ("ANGULAR_AXIS_MISALIGNMENT", "UNSUPPORTED_BY_07A_TRANSLATION_ONLY"),
    }
    operations = {}
    for scenario, (classification, status) in expected.items():
        result = run_cylindrical_repair_case(fixtures / scenario, tmp_path / "outputs" / scenario)
        assert result["validation"]["status"] == "PASS", result["validation"]
        operation = result["operation"]
        operations[scenario] = operation
        assert operation["classification"]["classification"] == classification
        assert operation["status"] == status

    assert operations["C01"]["motion"]["executed_translation_mm"] == [0.0, 0.0, 0.0]
    assert operations["C02"]["pre_measurement"]["axis_offset_mm"] == pytest.approx(0.05, abs=1e-7)
    assert operations["C02"]["pre_geometry"]["material_common_volume_mm3"] > RULES["volume_epsilon_mm3"]
    assert operations["C02"]["pre_geometry"]["minimum_surface_distance_mm"] <= RULES["linear_epsilon_mm"]
    assert operations["C02"]["motion"]["execution_count"] == 1
    assert operations["C02"]["motion"]["executed_translation_mm"] == pytest.approx([-0.05, 0.0, 0.0], abs=1e-7)
    assert operations["C02"]["post_measurement"]["axis_offset_mm"] <= RULES["linear_epsilon_mm"]
    assert operations["C02"]["post_geometry"]["actual_common_area_mm2"] > 0.0
    assert operations["C02"]["artifact_verification"]["status"] == "PASS"
    assert {"Axis_Offset_Vector", "Proposed_Translation", "Corrected_Bore_Axis", "Corrected_Shaft_Axis", "Remaining_Side_1", "Remaining_Side_2_EMPTY"} <= set(operations["C02"]["debug"]["semantic_objects"])
    assert operations["C03"]["pre_geometry"]["minimum_surface_distance_mm"] == pytest.approx(0.05, abs=1e-7)
    assert operations["C03"]["motion"]["execution_count"] == 0
    assert "Radial_Clearance_Indicator" in operations["C03"]["debug"]["semantic_objects"]
    assert operations["C04"]["pre_geometry"]["material_common_volume_mm3"] > RULES["volume_epsilon_mm3"]
    assert operations["C05"]["motion"]["execution_count"] == 0


def test_actual_brep_ambiguity_fails_closed_independent_of_traversal(tmp_path: Path) -> None:
    fixtures = tmp_path / "fixtures"
    generate_cylindrical_interface_repair_fixtures(fixtures)
    normal = run_cylindrical_repair_case(fixtures / "AMBIGUOUS", tmp_path / "normal")
    reversed_result = run_cylindrical_repair_case(fixtures / "AMBIGUOUS", tmp_path / "reversed", reverse=True)

    for result in (normal, reversed_result):
        assert result["operation"]["status"] == "UNSUPPORTED_AMBIGUOUS_CYLINDRICAL_INTERFACE"
        assert result["operation"]["candidate_pair_count"] > 1
        assert result["operation"]["motion"]["execution_count"] == 0
        assert result["validation"]["status"] == "PASS"


def test_expected_is_loaded_only_after_actual_operation(tmp_path: Path) -> None:
    fixtures = tmp_path / "fixtures"
    generate_cylindrical_interface_repair_fixtures(fixtures)
    case = fixtures / "C02"
    first = run_cylindrical_repair_case(case, tmp_path / "first")
    expected_path = case / "expected.json"
    altered = json.loads(expected_path.read_text(encoding="utf-8"))
    altered["status"] = "NO_CORRECTION_REQUIRED"
    expected_path.write_text(json.dumps(altered), encoding="utf-8")
    second = run_cylindrical_repair_case(case, tmp_path / "second")

    assert operation_projection(first["operation"]) == operation_projection(second["operation"])
    assert first["validation"]["status"] == "PASS"
    assert second["validation"]["status"] == "FAIL"


def test_suite_publishes_repeatability_and_human_review_index(tmp_path: Path) -> None:
    fixtures = tmp_path / "fixtures"
    outputs = tmp_path / "outputs"
    generate_cylindrical_interface_repair_fixtures(fixtures)
    result = run_cylindrical_repair_suite(fixtures, outputs)

    assert result["status"] == "PASS", result
    assert all(value["status"] == "PASS" for value in result["repeatability"].values())
    assert (outputs / "VIEW_INDEX.md").is_file()
    assert (outputs / "HUMAN_REVIEW" / "README.md").is_file()
    for scenario in ("C01", "C02", "C03", "C04", "C05"):
        assert (outputs / scenario / "operation_debug.FCStd").is_file()


def test_cli_exposes_07a_generate_case_and_suite_commands() -> None:
    environment = os.environ.copy()
    environment["PYTHONPATH"] = str(Path(__file__).resolve().parents[1] / "src")
    result = subprocess.run([sys.executable, "-m", "dmslicer", "--help"], capture_output=True, text=True, check=True, env=environment)
    assert "generate-cylindrical-interface-repair-07a" in result.stdout
    assert "run-cylindrical-interface-repair-case-07a" in result.stdout
    assert "run-cylindrical-interface-repair-suite-07a" in result.stdout


def test_missing_corrected_geometry_artifact_fails_revalidation(tmp_path: Path) -> None:
    fixtures = tmp_path / "fixtures"
    output = tmp_path / "output"
    generate_cylindrical_interface_repair_fixtures(fixtures)
    result = run_cylindrical_repair_case(fixtures / "C02", output)
    assert result["operation"]["artifact_verification"]["status"] == "PASS"

    (output / "actual_common.brep").unlink()
    verification = validate_published_artifacts(result["operation"], output)
    assert verification["status"] == "FAIL"
    assert any(item["kind"] == "missing_artifact" for item in verification["failures"])


def test_validator_applies_unit_specific_inverse_and_roundtrip_postconditions(tmp_path: Path) -> None:
    fixtures = tmp_path / "fixtures"
    generate_cylindrical_interface_repair_fixtures(fixtures)
    result = run_cylindrical_repair_case(fixtures / "C02", tmp_path / "output")
    operation = json.loads(json.dumps(result["operation"]))
    expected = result["expected"]
    operation["inverse_translation_equivalence"]["minimum_distance_mm"] = 5e-7
    operation["artifact_verification"]["corrected_measurement"]["axis_angle_rad"] = 5e-7

    from dmslicer.cylindrical_interface_repair_07a import validate_cylindrical_operation

    validation = validate_cylindrical_operation(operation, expected)
    assert validation["status"] == "FAIL"
    assert {item["kind"] for item in validation["failures"]} >= {"inverse_geometry_equivalence", "artifact_post_axis_angle"}


def test_rotated_c02_control_has_no_world_axis_dependency(tmp_path: Path) -> None:
    fixtures = tmp_path / "fixtures"
    generate_cylindrical_interface_repair_fixtures(fixtures)
    result = run_cylindrical_repair_case(fixtures / "ROTATED_C02", tmp_path / "rotated")
    operation = result["operation"]

    assert result["validation"]["status"] == "PASS", result["validation"]
    assert operation["classification"]["classification"] == "AXIS_TRANSLATIONAL_MISALIGNMENT"
    assert operation["status"] == "CORRECTED_AND_FUSED"
    direction = operation["selected_candidates"]["Side_1"]["axis_direction"]
    translation = operation["motion"]["executed_translation_mm"]
    assert abs(direction[0]) > 0.5 and abs(direction[2]) > 0.5
    assert abs(translation[0]) > 0.01 and abs(translation[2]) > 0.01
    assert sum(a * b for a, b in zip(direction, translation)) == pytest.approx(0.0, abs=1e-7)
    assert operation["post_measurement"]["axis_offset_mm"] <= RULES["linear_epsilon_mm"]
