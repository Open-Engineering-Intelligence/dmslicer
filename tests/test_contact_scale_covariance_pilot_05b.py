from dmslicer.contact_scale_covariance_pilot_05b import (
    SCALES,
    scaled_geometry,
    scaled_tau_e,
    validate_scale_actual,
)


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
