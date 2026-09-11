from __future__ import annotations

import importlib

import pytest


def _schema_errors(value: dict, schema_name: str):
    try:
        module = importlib.import_module("dmslicer.geometry_contract.schema")
    except ModuleNotFoundError:
        pytest.fail("geometry contract schema loader is not implemented")
    return module.schema_errors(value, schema_name=schema_name)


def _artifact() -> dict:
    return {
        "artifact_id": "artifact:source-step",
        "kind": "STEP",
        "uri": "benchmarks/interface_case01/case01.step",
        "sha256": "0" * 64,
        "hash_semantics": "byte_integrity_only",
    }


def _frame() -> dict:
    return {
        "frame_id": "frame:model",
        "length_unit": "mm",
        "origin": [0.0, 0.0, 0.0],
        "axes": {
            "x": [1.0, 0.0, 0.0],
            "y": [0.0, 1.0, 0.0],
            "z": [0.0, 0.0, 1.0],
        },
    }


def _core_snapshot() -> dict:
    return {
        "contract": {
            "name": "dmslicer.geometry-snapshot",
            "version": "0.1-rc1",
        },
        "snapshot_id": "snapshot:v0.1:" + "1" * 64,
        "source_documents": [
            {
                "source_document_id": "document:case01",
                "artifact_ref": "artifact:source-step",
                "source_length_unit": "mm",
                "internal_length_unit": "mm",
            }
        ],
        "model_frame": _frame(),
        "regions": [
            {
                "region_id": "region:a",
                "source_document_id": "document:case01",
                "validity_state": "VALID",
                "frame_ref": "frame:model",
                "geometry_ref": {
                    "artifact_ref": "artifact:source-step",
                    "locator": {
                        "scheme": "STEP_OCCURRENCE",
                        "value": "CASE01/A",
                    },
                },
            }
        ],
        "relations": [],
        "artifact_references": [_artifact()],
        "provenance_references": [
            {
                "provenance_id": "provenance:case01",
                "goal_id": "02C-CASE01",
                "implementation_commit": "1" * 40,
                "fixture_uri": "benchmarks/interface_case01/case01.step",
                "evidence_uri": "docs/implementation/02b_step_interface_case01.md",
            }
        ],
    }


def _patch(family: str) -> dict:
    patch = {
        "patch_id": f"patch:{family.lower()}",
        "interface_ref": "interface:one",
        "component_ref": "component:one",
        "family": family,
        "frame_ref": "frame:model",
        "area": {"value": 1.0, "unit": "mm2"},
        "geometry_ref": {
            "artifact_ref": "artifact:source-step",
            "locator": {
                "scheme": "STEP_FACE",
                "value": "face:stable-one",
                "provenance_ref": "provenance:case01",
            },
        },
    }
    if family == "PLANE":
        patch["planar_parameters"] = {
            "origin": [0.0, 0.0, 0.0],
            "unit_normal": [0.0, 0.0, 1.0],
            "tangent_u": [1.0, 0.0, 0.0],
            "tangent_v": [0.0, 1.0, 0.0],
        }
    else:
        patch["cylindrical_parameters"] = {
            "axis_origin": [0.0, 0.0, 0.0],
            "axis_direction": [0.0, 0.0, 1.0],
            "radius": {"value": 2.0, "unit": "mm"},
            "axial_interval": {
                "minimum": 0.0,
                "maximum": 4.0,
                "unit": "mm",
            },
            "periodic": True,
            "full_period": False,
        }
    return patch


def test_minimum_root_snapshot_does_not_require_capability_fields() -> None:
    snapshot = _core_snapshot()

    assert _schema_errors(snapshot, "geometry_snapshot") == ()
    for field in (
        "tolerances",
        "interfaces",
        "interface_components",
        "patches",
        "boundaries",
        "surface_partitions",
        "semantic_bindings",
        "parent_snapshot_ids",
    ):
        assert field not in snapshot


@pytest.mark.parametrize("family", ["PLANE", "CYLINDER"])
def test_native_patch_family_accepts_only_its_parameters(family: str) -> None:
    snapshot = _core_snapshot()
    snapshot["patches"] = [_patch(family)]

    assert _schema_errors(snapshot, "geometry_snapshot") == ()

    wrong_field = (
        "cylindrical_parameters" if family == "PLANE" else "planar_parameters"
    )
    snapshot["patches"][0][wrong_field] = {}
    assert _schema_errors(snapshot, "geometry_snapshot")


def test_non_decided_slicer_decision_omits_selection_fields() -> None:
    decision = {
        "contract": {
            "name": "dmslicer.slicer-decision",
            "version": "0.1-rc1",
        },
        "decision_id": "decision:v0.1:" + "2" * 64,
        "input_snapshot_id": "snapshot:v0.1:" + "1" * 64,
        "status": "UNSUPPORTED",
        "reason_code": "UNSUPPORTED_GEOMETRY_FAMILY",
        "provenance_reference": "provenance:case01",
    }

    assert _schema_errors(decision, "slicer_decision") == ()

    decision["selected_interface_id"] = "interface:one"
    assert _schema_errors(decision, "slicer_decision")
