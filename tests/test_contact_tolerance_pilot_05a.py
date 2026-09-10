from pathlib import Path
import shutil

import pytest

from dmslicer.contact_tolerance_pilot_05a import (
    FROZEN_OFFSET_RATIOS,
    validate_a07_construction,
    validate_a07_nominal_equivalence,
    engineering_state,
    generate_contact_tolerance_pilot,
    regenerate_a07_pilot,
    run_contact_tolerance_pilot_case,
    validate_tolerance_actual,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
ROLE_FIXTURES = REPO_ROOT / "tests" / "data" / "contact_fixed_tolerance_05c"
TRACKED_05A = REPO_ROOT / "benchmarks" / "contact_tolerance_pilot_05a"


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


def test_a07_regeneration_preserves_all_tracked_a01_steps(tmp_path: Path) -> None:
    generate_contact_tolerance_pilot(tmp_path)
    a01_hashes = {path.parent.name: path.read_bytes() for path in tmp_path.glob("A01_*/inputs.step")}

    report = regenerate_a07_pilot(tmp_path)

    assert len(report["replaced_a07_samples"]) == 15
    assert {path.parent.name: path.read_bytes() for path in tmp_path.glob("A01_*/inputs.step")} == a01_hashes


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


def test_a01_role_constrained_measurement_uses_tracked_penetration_interface(tmp_path: Path) -> None:
    result = run_contact_tolerance_pilot_case(ROLE_FIXTURES / "A01_delta_m2tauE_s0_01", tmp_path / "actual")
    assert result["actual"]["measured_signed_offset_mm"] == pytest.approx(-0.2, abs=1e-9)
    assert result["actual"]["engineering_state"] == "penetration_beyond_tolerance"
    assert result["actual"]["geometry_state"]["exact_intersection_dimension"] == "3D"
    assert result["actual"]["measurement"]["role_binding"] == {"Side_1": "Side_1", "Side_2": "Side_2"}


def test_a01_role_constrained_measurement_uses_archived_minus_four_interface(tmp_path: Path) -> None:
    result = run_contact_tolerance_pilot_case(ROLE_FIXTURES / "A01_delta_m4tauE_s0_01", tmp_path / "actual")

    assert result["actual"]["measured_signed_offset_mm"] == pytest.approx(-0.4, abs=1e-9)
    assert result["actual"]["engineering_state"] == "penetration_beyond_tolerance"
    assert result["actual"]["measurement"]["role_binding"] == {"Side_1": "Side_1", "Side_2": "Side_2"}


@pytest.mark.parametrize(("sample_id", "expected_offset", "expected_state"), [
    ("A01_delta_m1tauE", -0.1, "penetration_within_tolerance"),
    ("A01_delta_p0tauE", 0.0, "exact"),
    ("A01_delta_p0_5tauE", 0.05, "positive_gap_within_tolerance"),
])
def test_a01_role_fixture_controls_use_reimported_geometry(tmp_path: Path, sample_id: str, expected_offset: float, expected_state: str) -> None:
    result = run_contact_tolerance_pilot_case(TRACKED_05A / sample_id, tmp_path / "actual")

    assert result["actual"]["measured_signed_offset_mm"] == pytest.approx(expected_offset, abs=1e-9)
    assert result["actual"]["engineering_state"] == expected_state


@pytest.mark.parametrize(("replacement", "reason"), [
    ("Missing_1", "A01 role Side_1 is missing or duplicated"),
    # FreeCAD's STEP importer disambiguates the two duplicate labels; the
    # resulting imported convention is still explicitly rejected as Side_2
    # missing rather than being position-guessed.
    ("Side_1", "A01 role Side_2 is missing or duplicated"),
])
def test_a01_rejects_missing_or_duplicate_roles_on_the_production_step_path(tmp_path: Path, replacement: str, reason: str) -> None:
    """Exercise the normal STEP import/analyze path, not an isolated role helper."""
    source = ROLE_FIXTURES / "A01_delta_m2tauE_s0_01"
    # The runner derives the base case from the bundle name, as do real bundles.
    case = tmp_path / "A01_delta_role_malformed"
    shutil.copytree(source, case)
    step = case / "inputs.step"
    text = step.read_text(encoding="utf-8")
    if replacement == "Missing_1":
        text = text.replace("Side_1", replacement)
    else:
        text = text.replace("Side_2", replacement)
    step.write_text(text, encoding="utf-8", newline="\n")

    result = run_contact_tolerance_pilot_case(case, tmp_path / "actual")

    assert result["actual"]["engineering_state"] == "UNSUPPORTED"
    assert result["actual"]["measurement"]["reason"] == reason
    assert result["actual"]["direct_fuse"]["executed"] is False


def test_a01_measurement_is_independent_of_its_parent_directory(tmp_path: Path) -> None:
    source = ROLE_FIXTURES / "A01_delta_m2tauE_s0_01"
    relocated = tmp_path / "arbitrary" / "nested" / source.name
    relocated.parent.mkdir(parents=True)
    shutil.copytree(source, relocated)

    result = run_contact_tolerance_pilot_case(relocated, tmp_path / "actual")

    assert result["actual"]["measured_signed_offset_mm"] == pytest.approx(-0.2, abs=1e-9)


def test_gap_view_exports_real_inputs_without_gui_view_provider(tmp_path: Path) -> None:
    fixtures = tmp_path / "fixtures"
    generate_contact_tolerance_pilot(fixtures)
    debug = tmp_path / "views" / "gap.FCStd"
    run_contact_tolerance_pilot_case(fixtures / "A01_delta_p0_5tauE", tmp_path / "actual", debug_path=debug)
    assert debug.is_file()


def _a07_construction() -> dict:
    return {
        "shaft_radius_mm": 14.433756729740644,
        "shaft_z_min_mm": 0.0,
        "shaft_z_max_mm": 43.30127018922193,
        "sleeve_outer_radius_mm": 28.867513459481287,
        "sleeve_z_min_mm": -7.216878364870322,
        "sleeve_z_max_mm": 50.51814855409225,
        "sleeve_length_mm": 57.73502691896257,
        "interface_length_mm": 43.30127018922193,
        "lower_end_clearance_mm": 7.216878364870322,
        "upper_end_clearance_mm": 7.216878364870322,
        "combined_L_mm": 100.0,
    }


def test_a07_construction_rejects_legacy_75_mm_nominal_geometry() -> None:
    actual = _a07_construction()
    actual["combined_L_mm"] = 75.0
    assert validate_a07_construction(actual, _a07_construction())["status"] == "FAIL"


def test_a07_construction_rejects_outer_radius_drift() -> None:
    actual = _a07_construction()
    actual["sleeve_outer_radius_mm"] += 0.4
    assert validate_a07_construction(actual, _a07_construction())["status"] == "FAIL"


def test_a07_nominal_equivalence_rejects_material_volume_difference() -> None:
    frozen = {"construction": {**_a07_construction(), "shaft_material_volume_mm3": 10.0, "sleeve_material_volume_mm3": 20.0}, "geometry_state": {"positive_common_area_mm2": 30.0, "material_common_volume_mm3": 0.0}}
    pilot = {"construction": {**_a07_construction(), "shaft_material_volume_mm3": 10.0, "sleeve_material_volume_mm3": 21.0}, "geometry_state": {"positive_common_area_mm2": 30.0, "material_common_volume_mm3": 0.0}}
    assert validate_a07_nominal_equivalence(pilot, frozen)["status"] == "FAIL"


def test_validator_rejects_changed_actual_contact_area_and_common_volume() -> None:
    exact_actual = _actual("exact")
    exact_actual["geometry_state"].update({"positive_common_area_mm2": 99.0, "material_common_volume_mm3": 0.0})
    exact_expected = {**_expected("exact"), "contact_area_mm2": 100.0}
    assert validate_tolerance_actual(exact_actual, exact_expected)["status"] == "FAIL"

    penetration_actual = _actual("penetration_within_tolerance")
    penetration_actual["measured_signed_offset_mm"] = -0.05
    penetration_actual["geometry_state"].update({"exact_intersection_dimension": "3D", "material_common_volume_mm3": 4.0, "positive_common_area_mm2": None})
    penetration_expected = {"case_id": "A01", "set_signed_offset_mm": -0.05, "engineering_state": "penetration_within_tolerance", "exact_intersection_dimension": "3D", "material_common_volume_mm3": 5.0}
    assert validate_tolerance_actual(penetration_actual, penetration_expected)["status"] == "FAIL"


def test_validator_rejects_missing_applicable_measurement() -> None:
    actual = _actual("exact")
    actual["geometry_state"].update({"positive_common_area_mm2": None, "material_common_volume_mm3": 0.0})
    expected = {**_expected("exact"), "contact_area_mm2": 100.0}
    assert validate_tolerance_actual(actual, expected)["status"] == "FAIL"
