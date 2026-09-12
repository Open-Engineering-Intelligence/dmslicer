"""Deterministic contract projection. No geometry evaluation or HTML generation.

Snapshot validity means the public contract validator accepted the publication,
not that this consumer checked CAD geometry. Decision validity below means public
schema validity only. Overlay consistency is a separate, viewer-local result.

The baseline schema constrains decision_id syntax but does not require consumers
to recompute it. The baseline does not require local_frame_ref to equal a patch's
frame. Neither is an overlay rejection rule here; strategies and vectors remain
producer-supplied facts. Entity reference checks never select or repair anything.
"""

from __future__ import annotations

from copy import deepcopy
import math
from pathlib import Path, PurePosixPath
from typing import Any, Mapping, TypeAlias

from dmslicer.geometry_contract.schema import schema_errors
from dmslicer.geometry_contract.validation import validate_geometry_snapshot


ViewerModel: TypeAlias = dict[str, Any]

_ENTITY_IDS = {
    "regions": "region_id",
    "relations": "relation_id",
    "interfaces": "interface_id",
    "patches": "patch_id",
    "interface_components": "component_id",
    "boundaries": "boundary_id",
    "surface_partitions": "partition_id",
    "semantic_bindings": "binding_id",
}
_METADATA_IDS = {
    "source_documents": "source_document_id",
    "tolerances": "tolerance_id",
}
_REFERENCE_IDS = {
    "artifact_references": "artifact_id",
    "provenance_references": "provenance_id",
}
_MEMBERS = {
    "relations": ("region_refs", "tolerance_refs"),
    "interfaces": ("region_refs", "patch_refs"),
    "patches": ("source_face_refs",),
    "interface_components": ("patch_refs",),
    "surface_partitions": ("patch_refs",),
}
_SELECTION_FIELDS = (
    "selected_interface_id", "selected_patch_ids", "target_region_id",
    "strategy_kind", "local_frame_ref", "partition_direction",
    "partition_operation", "expected_partition_refs",
)


def _issue(code: str, path: str, message: str) -> dict[str, str]:
    return {"code": code, "path": path, "message": message}


def _report(status: str, issues: list[dict[str, str]]) -> dict[str, Any]:
    return {
        "status": status,
        "issues": sorted(issues, key=lambda i: (i["path"], i["code"], i["message"])),
    }


def _json_issues(value: Any, path: str = "$") -> list[dict[str, str]]:
    """Reject non-JSON values before projection, without coercing input facts."""
    if value is None or isinstance(value, (str, bool, int)):
        return []
    if isinstance(value, float) and math.isfinite(value):
        return []
    if isinstance(value, Mapping):
        result = []
        for key, item in value.items():
            if not isinstance(key, str):
                result.append(_issue("NON_JSON_VALUE", path, "Object keys must be strings"))
            else:
                result.extend(_json_issues(item, f"{path}.{key}"))
        return result
    if isinstance(value, list):
        return [issue for index, item in enumerate(value)
                for issue in _json_issues(item, f"{path}.{index}")]
    return [_issue("NON_JSON_VALUE", path, "Value must be finite JSON data")]


def _presence(snapshot: Any) -> dict[str, str]:
    fields = (*_ENTITY_IDS, *_METADATA_IDS, *_REFERENCE_IDS, "parent_snapshot_ids")
    source = snapshot if isinstance(snapshot, Mapping) else {}
    return {
        field: (
            "ABSENT" if field not in source else
            "INVALID_TYPE" if not isinstance(source[field], list) else
            "PRESENT" if source[field] else "EMPTY"
        )
        for field in fields
    }


def _records(snapshot: Mapping[str, Any], collection: str, id_key: str) -> list[dict]:
    records = sorted(deepcopy(snapshot.get(collection, [])), key=lambda r: r[id_key])
    for record in records:
        for field in _MEMBERS.get(collection, ()):
            if field in record:
                record[field] = sorted(record[field])
    return records


def _resolution(root: Path, uri: str) -> str:
    """Filesystem metadata only; href construction/rechecking belongs to render.

    Percent-encoded paths are deliberately not decoded. A renderer must not give
    a raw URI a second interpretation different from this containment check.
    """
    if any(c in uri for c in "\\:%?#") or any(ord(c) < 32 or ord(c) == 127 for c in uri):
        return "UNSAFE"
    pure = PurePosixPath(uri)
    if pure.is_absolute() or not pure.parts or ".." in pure.parts:
        return "UNSAFE"
    if any(part.endswith((".", " ")) for part in pure.parts):
        return "UNSAFE"
    try:
        resolved_root = root.resolve()
        candidate = (resolved_root / Path(*pure.parts)).resolve()
        if not candidate.is_relative_to(resolved_root):
            return "UNSAFE"
        return "RESOLVED" if candidate.is_file() else "MISSING"
    except (OSError, ValueError, RuntimeError):
        return "UNAVAILABLE"


def _overlay_checks(snapshot: Mapping[str, Any], decision: Mapping[str, Any]) -> list[dict[str, str]]:
    """Only the approved Snapshot association and entity membership checks."""
    issues = []
    if "input_snapshot_id" in decision and decision["input_snapshot_id"] != snapshot["snapshot_id"]:
        issues.append(_issue("SNAPSHOT_MISMATCH", "input_snapshot_id", "Decision references another Snapshot"))
    indexes = {
        collection: {item[id_key]: item for item in snapshot.get(collection, [])}
        for collection, id_key in {**_ENTITY_IDS, **_REFERENCE_IDS}.items()
    }

    def require(collection: str, identifier: str, field: str) -> None:
        if identifier not in indexes[collection]:
            issues.append(_issue("UNRESOLVED_REFERENCE", field, f"Reference not found in {collection}: {identifier}"))

    if "provenance_reference" in decision:
        require("provenance_references", decision["provenance_reference"], "provenance_reference")
    if decision["status"] != "DECIDED":
        return issues

    require("interfaces", decision["selected_interface_id"], "selected_interface_id")
    require("regions", decision["target_region_id"], "target_region_id")
    interface = indexes["interfaces"].get(decision["selected_interface_id"])
    for identifier in decision["selected_patch_ids"]:
        require("patches", identifier, "selected_patch_ids")
        patch = indexes["patches"].get(identifier)
        if interface is not None and patch is not None:
            if identifier not in interface["patch_refs"] or patch["interface_ref"] != interface["interface_id"]:
                issues.append(_issue("MEMBERSHIP_MISMATCH", "selected_patch_ids", f"Patch does not belong to selected interface: {identifier}"))
    for identifier in decision["expected_partition_refs"]:
        require("surface_partitions", identifier, "expected_partition_refs")
    return issues


def _add_decision(view: ViewerModel, snapshot: Any, decision: Any) -> None:
    if decision is None:
        return
    issues = _json_issues(decision)
    if not issues:
        issues = [_issue(i.code, i.path, i.message)
                  for i in schema_errors(decision, schema_name="slicer_decision")]
    view["validation"]["decision"] = _report("INVALID" if issues else "VALID", issues)
    overlay = {"state": "DISABLED"}
    view["decision_overlay"] = overlay
    if issues:
        overlay["disabled_reason"] = "INVALID_DECISION"
        return

    for field in ("contract", "decision_id", "input_snapshot_id", "status", "reason_code", "provenance_reference"):
        if field in decision:
            overlay[field] = deepcopy(decision[field])
    if view["validation"]["snapshot"]["status"] != "VALID":
        overlay["disabled_reason"] = "INVALID_SNAPSHOT"
        return

    issues = _overlay_checks(snapshot, decision)
    view["validation"]["overlay"] = _report("INCOMPATIBLE" if issues else "COMPATIBLE", issues)
    if issues:
        overlay["disabled_reason"] = "OVERLAY_INCONSISTENT"
    elif decision["status"] != "DECIDED":
        overlay["disabled_reason"] = "NOT_DECIDED"
    else:
        selection = {field: deepcopy(decision[field]) for field in _SELECTION_FIELDS}
        for field in ("selected_patch_ids", "expected_partition_refs"):
            selection[field] = sorted(selection[field])
        overlay.update(state="ENABLED", selection=selection, execution_state="NOT_EXECUTED")


def build_viewer_model(
    snapshot: Mapping[str, Any],
    decision: Mapping[str, Any] | None = None,
    *,
    repository_root: Path,
) -> ViewerModel:
    """Return a detached JSON model, including diagnostics for invalid input.

    Determinism assumes identical inputs, repository root and filesystem state.
    Resolution statuses are observations, not promises that a link remains safe
    or available. No absolute local paths or HTML are included in the model.
    """
    root = Path(repository_root)
    issues = _json_issues(snapshot)
    snapshot_status = "INVALID" if issues else "VALID"
    if not issues:
        try:
            issues = [_issue(i.code, i.path, i.message)
                      for i in validate_geometry_snapshot(snapshot, root)]
            snapshot_status = "INVALID" if issues else "VALID"
        except (OSError, ValueError, RuntimeError) as error:
            # Invalid paths, inaccessible files or symlink loops can prevent the
            # public validator from completing. Do not publish unchecked facts
            # or misreport an operational failure as a contract verdict.
            snapshot_status = "UNAVAILABLE"
            issues = [_issue(
                "VALIDATION_UNAVAILABLE", "$",
                f"Public Snapshot validation could not complete ({type(error).__name__})",
            )]
    view: ViewerModel = {
        "metadata": {"view_kind": "CONTRACT TOPOLOGY / NON-GEOMETRIC VIEW"},
        "validation": {
            "snapshot": _report(snapshot_status, issues),
            "decision": _report("NOT_PROVIDED", []),
            "overlay": _report("NOT_EVALUATED", []),
        },
        "collection_presence": _presence(snapshot),
        **{collection: [] for collection in _ENTITY_IDS},
        "artifact_links": [],
        "provenance_links": [],
        "decision_overlay": {"state": "NOT_PROVIDED"},
    }
    if not issues:
        for field in ("contract", "snapshot_id", "model_frame", "label", "description", "extensions"):
            if field in snapshot:
                view["metadata"][field] = deepcopy(snapshot[field])
        if "parent_snapshot_ids" in snapshot:
            view["metadata"]["parent_snapshot_ids"] = sorted(snapshot["parent_snapshot_ids"])
        for collection, id_key in _METADATA_IDS.items():
            if collection in snapshot:
                view["metadata"][collection] = _records(snapshot, collection, id_key)
        for collection, id_key in _ENTITY_IDS.items():
            view[collection] = _records(snapshot, collection, id_key)
        for artifact in _records(snapshot, "artifact_references", "artifact_id"):
            view["artifact_links"].append({**artifact, "resolution": _resolution(root, artifact["uri"])})
        for provenance in _records(snapshot, "provenance_references", "provenance_id"):
            view["provenance_links"].append({
                **provenance,
                "resolution": {field: _resolution(root, provenance[field])
                               for field in ("fixture_uri", "evidence_uri")},
            })
    _add_decision(view, snapshot, decision)
    return view
