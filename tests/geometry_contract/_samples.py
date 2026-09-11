from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]


def core_snapshot() -> dict[str, Any]:
    return {
        "contract": {
            "name": "dmslicer.geometry-snapshot",
            "version": "0.1-rc1",
        },
        "snapshot_id": "snapshot:v0.1:" + "0" * 64,
        "source_documents": [
            {
                "source_document_id": "document:case01",
                "artifact_ref": "artifact:source-step",
                "source_length_unit": "mm",
                "internal_length_unit": "mm",
            }
        ],
        "model_frame": {
            "frame_id": "frame:model",
            "length_unit": "mm",
            "origin": [0.0, 0.0, 0.0],
            "axes": {
                "x": [1.0, 0.0, 0.0],
                "y": [0.0, 1.0, 0.0],
                "z": [0.0, 0.0, 1.0],
            },
        },
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
            },
            {
                "region_id": "region:b",
                "source_document_id": "document:case01",
                "validity_state": "VALID",
                "frame_ref": "frame:model",
                "geometry_ref": {
                    "artifact_ref": "artifact:source-step",
                    "locator": {
                        "scheme": "STEP_OCCURRENCE",
                        "value": "CASE01/B",
                    },
                },
            },
        ],
        "relations": [],
        "artifact_references": [
            {
                "artifact_id": "artifact:source-step",
                "kind": "STEP",
                "uri": "benchmarks/interface_case01/case01.step",
            }
        ],
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


def connected_snapshot(ids_module) -> dict[str, Any]:
    snapshot = core_snapshot()
    relation_identifier = ids_module.relation_id(
        ["region:a", "region:b"], "PARTIAL_FACE_OVERLAP", "CONFIRMED"
    )
    interface_identifier = ids_module.interface_id(relation_identifier)
    patch_identifier = "patch:v1:stable-common"
    component_identifier = ids_module.component_id(
        interface_identifier, [patch_identifier]
    )
    source_geometry_ref = {
        "artifact_ref": "artifact:source-step",
        "locator": {
            "scheme": "STEP_FACE",
            "value": "face:v1:stable-source",
            "provenance_ref": "provenance:case01",
        },
    }
    partition_identifier = ids_module.partition_id(
        source_geometry_ref, "COMMON", [patch_identifier]
    )
    snapshot.update(
        {
            "relations": [
                {
                    "relation_id": relation_identifier,
                    "region_refs": ["region:a", "region:b"],
                    "taxonomy": "PARTIAL_FACE_OVERLAP",
                    "confirmation": "CONFIRMED",
                    "intersection_dimension": 2,
                    "tolerance_refs": ["tolerance:area"],
                }
            ],
            "tolerances": [
                {
                    "tolerance_id": "tolerance:area",
                    "role": "interface_area_acceptance",
                    "value": 1e-6,
                    "unit": "mm2",
                    "source": "06B",
                }
            ],
            "interfaces": [
                {
                    "interface_id": interface_identifier,
                    "relation_ref": relation_identifier,
                    "region_refs": ["region:a", "region:b"],
                    "patch_refs": [patch_identifier],
                }
            ],
            "interface_components": [
                {
                    "component_id": component_identifier,
                    "interface_ref": interface_identifier,
                    "patch_refs": [patch_identifier],
                }
            ],
            "patches": [
                {
                    "patch_id": patch_identifier,
                    "interface_ref": interface_identifier,
                    "component_ref": component_identifier,
                    "family": "PLANE",
                    "frame_ref": "frame:model",
                    "area": {"value": 480.0, "unit": "mm2"},
                    "geometry_ref": deepcopy(source_geometry_ref),
                    "planar_parameters": {
                        "origin": [0.0, 0.0, 0.0],
                        "unit_normal": [0.0, 0.0, 1.0],
                        "tangent_u": [1.0, 0.0, 0.0],
                        "tangent_v": [0.0, 1.0, 0.0],
                    },
                }
            ],
            "surface_partitions": [
                {
                    "partition_id": partition_identifier,
                    "source_geometry_ref": deepcopy(source_geometry_ref),
                    "role": "COMMON",
                    "patch_refs": [patch_identifier],
                    "geometry_ref": deepcopy(source_geometry_ref),
                    "area": {"value": 480.0, "unit": "mm2"},
                }
            ],
            "semantic_bindings": [
                {
                    "binding_id": "binding:target",
                    "subject_ref": "region:a",
                    "semantic_role": "TARGET_REGION",
                    "activation": "ACTIVE",
                },
                {
                    "binding_id": "binding:interface",
                    "subject_ref": interface_identifier,
                    "semantic_role": "INTERFACE_SOURCE_BOUNDARY",
                    "activation": "ACTIVE",
                },
            ],
        }
    )
    snapshot["snapshot_id"] = ids_module.snapshot_id(snapshot)
    return snapshot
