from __future__ import annotations

from copy import deepcopy
import math

from dmslicer.evidence_promotion.cad_evidence import validate_cad_artifact


def _measured(value: float | int, unit: str) -> dict[str, object]:
    return {"value": value, "unit": unit}


def geometry_snapshot_literal() -> dict[str, object]:
    return {
        "schema_version": "1.0.0",
        "artifact_type": "geometry_semantic_snapshot",
        "case_id": "original",
        "artifact_role": "OPENING",
        "source_artifact_id": "original-fcstd",
        "length_unit": "mm",
        "semantic_binding": {
            "component_role": "fixture_body",
            "interface_role": "through_hole_wall",
            "allowed_transform": "IDENTITY",
        },
        "shape": {
            "solid_count": _measured(1, "count"),
            "shell_count": _measured(1, "count"),
            "face_count": _measured(7, "count"),
            "edge_count": _measured(18, "count"),
            "vertex_count": _measured(12, "count"),
            "area": _measured(4396.991118, "mm2"),
            "volume": _measured(13796.106156, "mm3"),
            "bounding_box": {
                "x_min": _measured(0.0, "mm"),
                "y_min": _measured(0.0, "mm"),
                "z_min": _measured(0.0, "mm"),
                "x_max": _measured(40.0, "mm"),
                "y_max": _measured(30.0, "mm"),
                "z_max": _measured(12.0, "mm"),
            },
            "valid": True,
            "closed": True,
        },
    }


def topology_snapshot_literal() -> dict[str, object]:
    return {
        "schema_version": "1.0.0",
        "artifact_type": "topology_snapshot",
        "case_id": "original",
        "artifact_role": "OPENING",
        "source_artifact_id": "original-fcstd",
        "topology": {
            "solid_count": _measured(1, "count"),
            "shell_count": _measured(1, "count"),
            "face_count": _measured(7, "count"),
            "edge_count": _measured(18, "count"),
            "vertex_count": _measured(12, "count"),
            "connected_solid_count": _measured(1, "count"),
            "valid": True,
            "closed": True,
            "through_hole": {
                "status": "PROVEN",
                "count": _measured(1, "count"),
                "selection": "unique cylindrical wall at declared fixture radius",
            },
            "manifold": {
                "status": "UNKNOWN",
                "reason": "not required for the P2 fixture claim",
            },
        },
    }


def ui_snapshot_literal() -> dict[str, object]:
    return {
        "schema_version": "1.0.0",
        "artifact_type": "ui_state_snapshot",
        "case_id": "original",
        "artifact_role": "OPENING",
        "source_artifact_id": "original-fcstd",
        "object_role": "fixture_body",
        "state": {
            "visibility": {"status": "SUPPORTED", "value": True},
            "shape_color": {"status": "SUPPORTED", "value": [0.8, 0.8, 0.8]},
            "transparency": {"status": "SUPPORTED", "value": 0},
            "display_mode": {
                "status": "UNSUPPORTED",
                "reason": "not stable in the local headless reopen path",
            },
            "camera": {
                "status": "UNSUPPORTED",
                "reason": "not stable in the local headless reopen path",
            },
        },
    }


def geometry_comparison_literal(status: str = "GEOMETRY_EQUIVALENT") -> dict[str, object]:
    return {
        "schema_version": "1.0.0",
        "artifact_type": "geometry_comparison",
        "case_id": "case_a_ui_only",
        "comparison_role": "UI_ONLY_MUTATION",
        "status": status,
        "method": "BREP_BOOLEAN_AND_MEASUREMENTS",
        "sha256_role": "file_and_copy_integrity_only_not_geometry_equivalence",
        "tolerances": [
            {
                "name": "linear",
                "value": 0.001,
                "unit": "mm",
                "role": "bounding_box_comparison",
                "source": "P2 fixture policy",
            },
            {
                "name": "area",
                "value": 0.001,
                "unit": "mm2",
                "role": "surface_area_comparison",
                "source": "P2 fixture policy",
            },
            {
                "name": "volume",
                "value": 0.001,
                "unit": "mm3",
                "role": "volume_and_boolean_comparison",
                "source": "P2 fixture policy",
            },
        ],
        "measurements": {
            "area_delta": _measured(0.0, "mm2"),
            "volume_delta": _measured(0.0, "mm3"),
            "max_bounding_box_delta": _measured(0.0, "mm"),
            "minimum_distance": _measured(0.0, "mm"),
            "first_minus_second_volume": _measured(0.0, "mm3"),
            "second_minus_first_volume": _measured(0.0, "mm3"),
        },
        "checks": {
            "valid_closed_single_solids": True,
            "topology_counts": True,
            "area_delta": True,
            "volume_delta": True,
            "bounding_box": True,
            "first_minus_second": True,
            "second_minus_first": True,
        },
        "failed_checks": [],
        "reasons": [],
        "geometry_decision_inputs": [
            "topology",
            "area",
            "volume",
            "bounding_box",
            "bidirectional_boolean_cut",
        ],
    }


def test_all_four_cad_artifact_types_validate() -> None:
    for value in (
        geometry_snapshot_literal(),
        topology_snapshot_literal(),
        ui_snapshot_literal(),
        geometry_comparison_literal(),
    ):
        assert validate_cad_artifact(value) == []


def test_geometry_snapshot_requires_unit_bearing_actual_measurements() -> None:
    snapshot = geometry_snapshot_literal()
    del snapshot["shape"]["volume"]["unit"]  # type: ignore[index]

    assert any("shape.volume.unit" in error for error in validate_cad_artifact(snapshot))


def test_snapshot_types_remain_separate() -> None:
    geometry = geometry_snapshot_literal()
    geometry["artifact_type"] = "ui_state_snapshot"

    assert validate_cad_artifact(geometry)


def test_geometry_comparison_forbids_sha_as_method() -> None:
    comparison = geometry_comparison_literal()
    comparison["method"] = "SHA256_EQUALITY"

    assert any("method" in error for error in validate_cad_artifact(comparison))


def test_nonfinite_measurement_is_rejected_before_serialization() -> None:
    snapshot = deepcopy(geometry_snapshot_literal())
    snapshot["shape"]["volume"]["value"] = math.nan  # type: ignore[index]

    assert any("finite" in error for error in validate_cad_artifact(snapshot))
