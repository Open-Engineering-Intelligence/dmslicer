"""Minimal UI compatibility projection; test-only and FreeCAD-free."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any, Mapping

from dmslicer.geometry_contract.validation import validate_geometry_snapshot


def _records(
    snapshot: Mapping[str, Any], collection: str, id_field: str
) -> list[dict[str, Any]]:
    return sorted(
        (deepcopy(item) for item in snapshot.get(collection, [])),
        key=lambda item: item[id_field],
    )


def _sort_members(view: dict[str, Any]) -> None:
    for relation in view["relations"]:
        relation["region_refs"] = sorted(relation["region_refs"])
        if "tolerance_refs" in relation:
            relation["tolerance_refs"] = sorted(relation["tolerance_refs"])
    for interface in view["interfaces"]:
        interface["region_refs"] = sorted(interface["region_refs"])
        interface["patch_refs"] = sorted(interface["patch_refs"])
    for component in view["interface_components"]:
        component["patch_refs"] = sorted(component["patch_refs"])
    for partition in view["surface_partitions"]:
        partition["patch_refs"] = sorted(partition["patch_refs"])


def _decision_view(decision: Mapping[str, Any] | None) -> dict[str, Any] | None:
    if decision is None:
        return None
    result = {
        key: deepcopy(decision[key])
        for key in (
            "decision_id",
            "status",
            "reason_code",
            "selected_interface_id",
            "selected_patch_ids",
            "target_region_id",
        )
        if key in decision
    }
    if "selected_patch_ids" in result:
        result["selected_patch_ids"] = sorted(result["selected_patch_ids"])
    return result


def build_view_model(
    snapshot: Mapping[str, Any],
    decision: Mapping[str, Any] | None,
    repository_root: Path,
) -> dict[str, Any]:
    """Build a deterministic navigation model from public contract fields."""
    issues = validate_geometry_snapshot(snapshot, repository_root)
    if issues:
        raise ValueError("invalid GeometrySnapshot cannot be displayed as authoritative")

    view = {
        "snapshot_id": snapshot["snapshot_id"],
        "regions": _records(snapshot, "regions", "region_id"),
        "relations": _records(snapshot, "relations", "relation_id"),
        "interfaces": _records(snapshot, "interfaces", "interface_id"),
        "patches": _records(snapshot, "patches", "patch_id"),
        "interface_components": _records(
            snapshot, "interface_components", "component_id"
        ),
        "boundaries": _records(snapshot, "boundaries", "boundary_id"),
        "surface_partitions": _records(
            snapshot, "surface_partitions", "partition_id"
        ),
        "semantic_bindings": _records(
            snapshot, "semantic_bindings", "binding_id"
        ),
        "artifact_links": [
            {
                "artifact_id": artifact["artifact_id"],
                "kind": artifact["kind"],
                "uri": artifact["uri"],
            }
            for artifact in sorted(
                snapshot["artifact_references"], key=lambda item: item["artifact_id"]
            )
        ],
        "provenance_links": [
            {
                "provenance_id": provenance["provenance_id"],
                "goal_id": provenance["goal_id"],
                "evidence_uri": provenance["evidence_uri"],
            }
            for provenance in sorted(
                snapshot["provenance_references"],
                key=lambda item: item["provenance_id"],
            )
        ],
        "decision": _decision_view(decision),
    }
    _sort_members(view)
    return view
