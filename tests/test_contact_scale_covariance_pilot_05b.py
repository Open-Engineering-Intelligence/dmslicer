from dmslicer.contact_scale_covariance_pilot_05b import (
    SCALES,
    scaled_geometry,
    scaled_tau_e,
    validate_scale_actual,
    revalidate_contact_scale_covariance_pilot,
)
from dmslicer.evidence import write_json
import copy


def test_scale_rules_keep_tau_e_and_a07_controls_covariant() -> None:
    assert SCALES == (0.01, 1.0, 100.0)
    assert scaled_tau_e(0.01) == 0.001
    geometry = scaled_geometry("A07", 100.0)
    assert geometry["shaft_radius_mm"] == 1443.3756729740644
    assert geometry["sleeve_outer_radius_mm"] == 2886.7513459481287
    assert geometry["sleeve_z_min_mm"] == -721.6878364870322
    assert geometry["sleeve_z_max_mm"] == 5051.814855409225


def test_scale_validation_normalizes_area_by_square_scale() -> None:
    actual = {"case_id": "A01", "scale": 0.01, "measured_signed_offset_mm": 0.0,
              "engineering_state": "exact", "geometry_state": {"exact_intersection_dimension": "2D", "positive_common_area_mm2": 1.0, "material_common_volume_mm3": 0.0},
              "direct_fuse": {"solid_count": 1, "valid": True, "closed": True, "one_valid_connected_solid": True}}
    expected = {"case_id": "A01", "set_signed_offset_mm": 0.0, "engineering_state": "exact", "exact_intersection_dimension": "2D", "contact_area_mm2": 10000.0}
    assert validate_scale_actual(actual, expected)["normalized_validation"]["status"] == "PASS"


def _actual(*, scale: float, area: float | None = None, volume: float | None = None) -> dict:
    return {"case_id": "A01", "scale": scale, "measured_signed_offset_mm": 0.0,
            "engineering_state": "exact", "geometry_state": {"exact_intersection_dimension": "2D", "positive_common_area_mm2": area, "material_common_volume_mm3": volume},
            "direct_fuse": {"solid_count": 1, "valid": True, "closed": True, "one_valid_connected_solid": True}}


def _area_expected(*, scale: float, area: float, normalized_area: float | None = None) -> dict:
    return {"case_id": "A01", "set_signed_offset_mm": 0.0, "engineering_state": "exact", "exact_intersection_dimension": "2D", "contact_area_mm2": area,
            "normalized_reference": {"exact_intersection_dimension": "2D", "contact_area_mm2": normalized_area if normalized_area is not None else area}}


def test_small_scale_keeps_native_absolute_pass_separate_from_normalized_failure() -> None:
    result = validate_scale_actual(_actual(scale=0.01, area=1.00000000005), _area_expected(scale=0.01, area=1.0, normalized_area=10000.0))
    assert result["native_absolute_validation"]["status"] == "PASS"
    assert result["scale_normalized_validation"]["status"] == "FAIL"


def test_large_scale_keeps_native_absolute_failure_separate_from_normalized_pass() -> None:
    result = validate_scale_actual(_actual(scale=100.0, area=100000000.00002), _area_expected(scale=100.0, area=100000000.0, normalized_area=10000.0))
    assert result["native_absolute_validation"]["status"] == "FAIL"
    assert result["scale_normalized_validation"]["status"] == "PASS"


def test_scale_validation_uses_cubed_scale_for_volume() -> None:
    actual = {**_actual(scale=0.01, area=None, volume=0.00000100000000002), "geometry_state": {"exact_intersection_dimension": "3D", "positive_common_area_mm2": None, "material_common_volume_mm3": 0.00000100000000002}}
    expected = {"case_id": "A01", "set_signed_offset_mm": 0.0, "engineering_state": "exact", "exact_intersection_dimension": "3D", "material_common_volume_mm3": 0.000001, "normalized_reference": {"exact_intersection_dimension": "3D", "material_common_volume_mm3": 1.0}}
    assert validate_scale_actual(actual, expected)["scale_normalized_validation"]["status"] == "PASS"


def test_scale_validation_rejects_missing_nan_and_non_applicable_metrics() -> None:
    missing = validate_scale_actual(_actual(scale=1.0, area=None), _area_expected(scale=1.0, area=1.0))
    assert missing["native_absolute_validation"]["status"] == "FAIL"
    nan_actual = _actual(scale=1.0, area=float("nan"))
    assert validate_scale_actual(nan_actual, _area_expected(scale=1.0, area=1.0))["scale_normalized_validation"]["status"] == "FAIL"
    assert missing["native_absolute_validation"]["metrics"]["volume"]["status"] == "NOT_APPLICABLE"


def test_expected_mutation_never_changes_actual_evidence() -> None:
    actual = _actual(scale=1.0, area=1.0)
    before = copy.deepcopy(actual)
    expected = _area_expected(scale=1.0, area=2.0)
    assert validate_scale_actual(actual, expected)["native_absolute_validation"]["status"] == "FAIL"
    assert actual == before


def test_revalidation_reports_missing_actual_as_incomplete(tmp_path) -> None:
    manifest = {"samples": [{"sample_id": "missing", "case_id": "A01", "scale": 1.0, "step_sha256": "sha256", "parameters": {"delta_over_tauE": 0.0}, "expected": _area_expected(scale=1.0, area=1.0)}]}
    write_json(tmp_path / "manifest.json", manifest)
    summary = revalidate_contact_scale_covariance_pilot(tmp_path / "manifest.json", tmp_path / "source", tmp_path / "out")
    assert summary["complete_sample_count"] == 0
    assert summary["missing_actual_count"] == 1
    assert summary["primary_scale_covariance_verdict"] == "INCOMPLETE"
