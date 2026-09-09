from pathlib import Path

import pytest

from dmslicer.contact_tolerance_pilot_05a import (
    FROZEN_OFFSET_RATIOS,
    engineering_state,
    generate_contact_tolerance_pilot,
    run_contact_tolerance_pilot_case,
    validate_tolerance_actual,
)


def _actual(state: str) -> dict:
    return {
        "schema_version": 1,
        "case_id": "A01",
        "set_signed_offset_mm": 0.0,
        "measured_signed_offset_mm": 0.0,
        "engineering_state": state,
        "geometry_state": {"exact_intersection_dimension": "2D"},
        "direct_fuse": {"solid_count": 1, "valid": True, "closed": True, "one_valid_connected_solid": True},
    }


def _expected(state: str) -> dict:
    return {
        "schema_version": 1,
        "case_id": "A01",
        "set_signed_offset_mm": 0.0,
        "engineering_state": state,
        "exact_intersection_dimension": "2D",
    }


def test_generator_writes_two_cases_with_the_frozen_15_offsets(tmp_path: Path) -> None:
    generated = generate_contact_tolerance_pilot(tmp_path)

    assert len(generated["samples"]) == 30
    assert {row["case_id"] for row in generated["samples"]} == {"A01", "A07"}
    assert FROZEN_OFFSET_RATIOS == (-4, -2, -1.1, -1, -0.9, -0.5, -0.1, 0, 0.1, 0.5, 0.9, 1, 1.1, 2, 4)
    for row in generated["samples"]:
        sample = tmp_path / row["sample_id"]
        assert (sample / "inputs.step").is_file()
        assert (sample / "parameters.json").is_file()
        assert (sample / "expected.json").is_file()


def test_engineering_state_uses_inclusive_tolerance_boundaries() -> None:
    assert engineering_state(0.0, 0.1) == "exact"
    assert engineering_state(0.1, 0.1) == "positive_gap_within_tolerance"
    assert engineering_state(-0.1, 0.1) == "penetration_within_tolerance"
    assert engineering_state(0.1000001, 0.1) == "positive_gap_beyond_tolerance"
    assert engineering_state(-0.1000001, 0.1) == "penetration_beyond_tolerance"


def test_validation_detects_mutated_expected_truth() -> None:
    assert validate_tolerance_actual(_actual("exact"), _expected("exact"))["status"] == "PASS"
    assert validate_tolerance_actual(_actual("exact"), _expected("positive_gap_within_tolerance"))["status"] == "FAIL"


def test_validation_rejects_missing_actual_fields() -> None:
    assert validate_tolerance_actual({}, _expected("exact"))["status"] == "FAIL"


def test_validation_detects_a_mutated_actual_measurement() -> None:
    actual = _actual("exact")
    actual["measured_signed_offset_mm"] = 0.2
    actual["tauE_mm"] = 0.1
    assert validate_tolerance_actual(actual, _expected("exact"))["status"] == "FAIL"


def test_validation_detects_mutated_actual_engineering_state() -> None:
    actual = _actual("positive_gap_within_tolerance")
    assert validate_tolerance_actual(actual, _expected("exact"))["status"] == "FAIL"


def test_validation_detects_mutated_direct_fuse_solid_count() -> None:
    actual = _actual("exact")
    actual["direct_fuse"]["solid_count"] = 2
    assert validate_tolerance_actual(actual, _expected("exact"))["status"] == "FAIL"


def test_actual_measurement_uses_the_reimported_a01_gap_not_truth(tmp_path: Path) -> None:
    fixtures = tmp_path / "fixtures"
    generate_contact_tolerance_pilot(fixtures)
    case = fixtures / "A01_delta_p0_5tauE"
    result = run_contact_tolerance_pilot_case(case, tmp_path / "actual")

    assert result["actual"]["analysis_input"] == "reimported_step"
    assert result["actual"]["measured_signed_offset_mm"] == pytest.approx(0.05, abs=1e-9)
    assert result["actual"]["geometry_state"]["exact_intersection_dimension"] == "none"
