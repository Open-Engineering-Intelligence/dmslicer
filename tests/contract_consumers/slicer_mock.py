"""Minimal SlicerDecision compatibility consumer; test-only and FreeCAD-free."""

from __future__ import annotations

from pathlib import Path
import re
from typing import Any, Mapping

from dmslicer.geometry_contract.ids import decision_id
from dmslicer.geometry_contract.validation import validate_geometry_snapshot


_SNAPSHOT_ID = re.compile(r"snapshot:v0\.1:[0-9a-f]{64}")
_IDENTIFIER = re.compile(r"[A-Za-z][A-Za-z0-9_.-]*:\S+")


def _base(snapshot: Mapping[str, Any], status: str, reason_code: str) -> dict[str, Any]:
    snapshot_identifier = snapshot.get("snapshot_id")
    provenance = sorted(
        identifier
        for item in snapshot.get("provenance_references", [])
        if isinstance(item, Mapping)
        if isinstance(identifier := item.get("provenance_id"), str)
        if _IDENTIFIER.fullmatch(identifier)
    )
    result = {
        "contract": {
            "name": "dmslicer.slicer-decision",
            "version": snapshot.get("contract", {}).get("version", "0.1-rc1"),
        },
        "status": status,
        "reason_code": reason_code,
    }
    if isinstance(snapshot_identifier, str) and _SNAPSHOT_ID.fullmatch(
        snapshot_identifier
    ):
        result["input_snapshot_id"] = snapshot_identifier
    if provenance:
        result["provenance_reference"] = provenance[0]
    result["decision_id"] = decision_id(result)
    return result


def decide(snapshot: Mapping[str, Any], repository_root: Path) -> dict[str, Any]:
    """Return one deterministic pre-slicing decision from public JSON only."""
    if validate_geometry_snapshot(snapshot, repository_root):
        return _base(snapshot, "FAILED", "INVALID_SNAPSHOT")

    relation_by_id = {
        relation["relation_id"]: relation for relation in snapshot["relations"]
    }
    interfaces = sorted(
        snapshot.get("interfaces", []), key=lambda item: item["interface_id"]
    )
    eligible = [
        interface
        for interface in interfaces
        if relation_by_id[interface["relation_ref"]]["confirmation"] == "CONFIRMED"
        and relation_by_id[interface["relation_ref"]]["intersection_dimension"] == 2
    ]
    if not eligible:
        ambiguous = any(
            relation["confirmation"] == "AMBIGUOUS"
            or relation["taxonomy"] == "AMBIGUOUS"
            for relation in snapshot["relations"]
        )
        return _base(
            snapshot,
            "REJECTED" if ambiguous else "UNSUPPORTED",
            "AMBIGUOUS_INTERFACE" if ambiguous else "UNSUPPORTED_STRATEGY",
        )

    active_bindings = [
        binding
        for binding in snapshot.get("semantic_bindings", [])
        if binding["activation"] == "ACTIVE"
    ]
    target_refs = sorted(
        binding["subject_ref"]
        for binding in active_bindings
        if binding["semantic_role"] == "TARGET_REGION"
    )
    bound_interfaces = {
        binding["subject_ref"]
        for binding in active_bindings
        if binding["semantic_role"] == "INTERFACE_SOURCE_BOUNDARY"
    }
    eligible = [
        interface
        for interface in eligible
        if interface["interface_id"] in bound_interfaces
    ]
    if not target_refs or not eligible:
        return _base(snapshot, "REJECTED", "MISSING_SEMANTIC_BINDING")

    selected = eligible[0]
    patches_by_id = {
        patch["patch_id"]: patch for patch in snapshot.get("patches", [])
    }
    selected_patch_ids = sorted(selected["patch_refs"])
    patches = [patches_by_id[identifier] for identifier in selected_patch_ids]
    families = {patch["family"] for patch in patches}
    if "OTHER" in families:
        return _base(snapshot, "UNSUPPORTED", "UNSUPPORTED_GEOMETRY_FAMILY")
    if families != {"PLANE"}:
        return _base(snapshot, "UNSUPPORTED", "UNSUPPORTED_STRATEGY")

    result = {
        "contract": {
            "name": "dmslicer.slicer-decision",
            "version": snapshot["contract"]["version"],
        },
        "input_snapshot_id": snapshot["snapshot_id"],
        "selected_interface_id": selected["interface_id"],
        "selected_patch_ids": selected_patch_ids,
        "target_region_id": target_refs[0],
        "strategy_kind": "PLANAR_INTERFACE_PARTITION",
        "local_frame_ref": patches[0]["frame_ref"],
        "partition_direction": patches[0]["planar_parameters"]["unit_normal"],
        "partition_operation": "SPLIT_COMMON_AND_REMAINING",
        "expected_partition_refs": sorted(
            partition["partition_id"]
            for partition in snapshot.get("surface_partitions", [])
        ),
        "status": "DECIDED",
        "reason_code": "NONE",
        "provenance_reference": sorted(
            item["provenance_id"] for item in snapshot["provenance_references"]
        )[0],
    }
    result["decision_id"] = decision_id(result)
    return result
