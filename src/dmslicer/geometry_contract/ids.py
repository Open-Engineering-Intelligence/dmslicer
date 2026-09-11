"""Deterministic v0.1 container IDs, not cross-document correspondence."""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping, Sequence

from dmslicer.identity import canonical_digest

_DISPLAY_ONLY_KEYS = {"label", "description", "extensions"}
_SET_LIKE_SCALAR_LISTS = {
    "parent_snapshot_ids",
    "patch_refs",
    "region_refs",
    "selected_patch_ids",
    "source_face_refs",
    "tolerance_refs",
}
_ENTITY_ID_KEYS = (
    "source_document_id",
    "region_id",
    "relation_id",
    "artifact_id",
    "provenance_id",
    "tolerance_id",
    "interface_id",
    "component_id",
    "patch_id",
    "boundary_id",
    "partition_id",
    "binding_id",
)
_COLLECTION_ID_KEYS = {
    "source_documents": "source_document_id",
    "regions": "region_id",
    "relations": "relation_id",
    "artifact_references": "artifact_id",
    "provenance_references": "provenance_id",
    "tolerances": "tolerance_id",
    "interfaces": "interface_id",
    "interface_components": "component_id",
    "patches": "patch_id",
    "boundaries": "boundary_id",
    "surface_partitions": "partition_id",
    "semantic_bindings": "binding_id",
}


def _identifier_for(value: Mapping[str, Any]) -> str | None:
    for key in _ENTITY_ID_KEYS:
        identifier = value.get(key)
        if isinstance(identifier, str):
            return identifier
    return None


def _normalize(value: Any, *, field: str | None = None) -> Any:
    if isinstance(value, Mapping):
        return {
            key: _normalize(item, field=key)
            for key, item in sorted(value.items())
            if key not in _DISPLAY_ONLY_KEYS and key != "snapshot_id"
        }
    if isinstance(value, list):
        normalized = [_normalize(item) for item in value]
        if field in _SET_LIKE_SCALAR_LISTS:
            return sorted(normalized)
        if normalized and all(isinstance(item, Mapping) for item in normalized):
            id_key = _COLLECTION_ID_KEYS.get(field or "")
            identifiers = [
                item.get(id_key) if id_key is not None else _identifier_for(item)
                for item in normalized
            ]
            if all(identifier is not None for identifier in identifiers):
                return [
                    item
                    for _, item in sorted(
                        zip(identifiers, normalized), key=lambda pair: pair[0]
                    )
                ]
        return normalized
    return value


def _contract_id(kind: str, payload: Mapping[str, Any]) -> str:
    return f"{kind}:v0.1:{canonical_digest(payload)}"


def snapshot_id(snapshot_without_id: Mapping[str, Any]) -> str:
    """Identify one publication payload without comparing any CAD geometry."""
    return _contract_id("snapshot", _normalize(deepcopy(snapshot_without_id)))


def relation_id(
    region_ids: Sequence[str], taxonomy: str, confirmation: str
) -> str:
    return _contract_id(
        "relation",
        {
            "region_ids": sorted(region_ids),
            "taxonomy": taxonomy,
            "confirmation": confirmation,
        },
    )


def interface_id(relation_identifier: str) -> str:
    return _contract_id("interface", {"relation_id": relation_identifier})


def component_id(
    interface_identifier: str, patch_ids: Sequence[str]
) -> str:
    return _contract_id(
        "component",
        {
            "interface_id": interface_identifier,
            "patch_ids": sorted(patch_ids),
        },
    )


def partition_id(
    source_geometry_ref: Mapping[str, Any],
    role: str,
    patch_ids: Sequence[str],
) -> str:
    return _contract_id(
        "partition",
        {
            "source_geometry_ref": _normalize(source_geometry_ref),
            "role": role,
            "patch_ids": sorted(patch_ids),
        },
    )


def decision_id(decision_without_id: Mapping[str, Any]) -> str:
    value = deepcopy(decision_without_id)
    value.pop("decision_id", None)
    return _contract_id("decision", _normalize(value))
