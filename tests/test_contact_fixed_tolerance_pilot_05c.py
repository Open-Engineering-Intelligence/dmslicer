import copy

import pytest

from dmslicer.contact_fixed_tolerance_pilot_05c import (
    FIXED_TAU_E_MM,
    SCALES,
    a07_construction_domain,
    expected_truth,
    fixed_tau_e,
    generate_contact_fixed_tolerance_manifest,
    materialize_fixed_inputs,
    normalized_reference,
    validate_fixed_actual,
)
from dmslicer.evidence import write_json


def test_fixed_tau_e_does_not_scale() -> None:
    assert SCALES == (0.01, 1.0, 100.0)
    assert [fixed_tau_e(scale) for scale in SCALES] == [FIXED_TAU_E_MM] * 3


def test_a07_domain_rejects_non_positive_and_outer_radius_bore() -> None:
    assert a07_construction_domain(0.01, -4.0)["status"] == "OUT_OF_CONSTRUCTION_DOMAIN"
    assert a07_construction_domain(0.01, 4.0)["status"] == "OUT_OF_CONSTRUCTION_DOMAIN"
    assert a07_construction_domain(0.01, -1.0)["status"] == "CONSTRUCTIBLE"


def test_a01_large_negative_delta_uses_interval_intersection_volume() -> None:
    truth = expected_truth("A01", 0.01, -4.0)
    geometry = truth["geometry"]
    assert truth["exact_intersection_dimension"] == "3D"
    assert truth["material_common_volume_mm3"] == pytest.approx(geometry["a_mm"] * geometry["b_mm"] * (2 * geometry["h_mm"] - 0.4))


def test_normalized_reference_uses_delta_over_scale_not_same_q() -> None:
    reference = normalized_reference("A01", 0.01, 1.0)
    assert reference["set_signed_offset_mm"] == 10.0
    assert reference["exact_intersection_dimension"] == "none"


def test_normalized_auxiliary_validation_accepts_current_delta_over_scale_reference() -> None:
    expected = expected_truth("A01", 0.01, -1.0)
    actual = {"case_id": "A01", "scale": 0.01, "measured_signed_offset_mm": -0.1, "engineering_state": "penetration_within_tolerance", "geometry_state": {"exact_intersection_dimension": "3D", "positive_common_area_mm2": None, "material_common_volume_mm3": expected["material_common_volume_mm3"]}, "direct_fuse": {"solid_count": 1, "valid": True, "closed": True, "one_valid_connected_solid": True}}
    result = validate_fixed_actual(actual, {**expected, "normalized_reference": normalized_reference("A01", 0.01, -1.0)})
    assert result["native_absolute_validation"]["status"] == "PASS"
    assert result["normalized_validation"]["status"] == "PASS"


def test_manifest_has_all_planned_rows_and_keeps_domain_exclusions(tmp_path) -> None:
    manifest = generate_contact_fixed_tolerance_manifest(tmp_path, tmp_path / "tracked")
    assert manifest["planned_count"] == 90
    assert len({row["sample_id"] for row in manifest["samples"]}) == 90
    assert manifest["domain_excluded_count"] == 4
    assert manifest["constructible_count"] == 86


def test_expected_mutation_cannot_change_actual_and_missing_values_cannot_pass() -> None:
    actual = {"case_id": "A01", "scale": 1.0, "measured_signed_offset_mm": 0.0, "engineering_state": "exact", "geometry_state": {"exact_intersection_dimension": "2D", "positive_common_area_mm2": 1.0, "material_common_volume_mm3": 0.0}, "direct_fuse": {"solid_count": 1, "valid": True, "closed": True, "one_valid_connected_solid": True}}
    expected = {"case_id": "A01", "scale": 1.0, "set_signed_offset_mm": 0.0, "engineering_state": "exact", "exact_intersection_dimension": "2D", "contact_area_mm2": 2.0}
    before = copy.deepcopy(actual)
    assert validate_fixed_actual(actual, expected)["status"] == "METHOD_MISMATCH"
    assert actual == before
    assert validate_fixed_actual({}, expected)["status"] == "METHOD_MISMATCH"


def test_materialize_preserves_an_existing_generated_step(tmp_path, monkeypatch) -> None:
    step = tmp_path / "inputs.step"
    step.write_text("already-generated", encoding="utf-8")
    manifest = {"samples": [{"sample_id": "sample", "case_id": "A01", "planned_status": "CONSTRUCTIBLE", "source_kind": "generated_05C", "step_path": str(step), "parameters": {}, "expected": {}}]}
    manifest_path = tmp_path / "manifest.json"
    write_json(manifest_path, manifest)
    monkeypatch.setattr("dmslicer.contact_fixed_tolerance_pilot_05c._run_freecad", lambda request: (_ for _ in ()).throw(AssertionError("must not regenerate")))
    assert materialize_fixed_inputs(manifest_path)["generated_input_count"] == 0
