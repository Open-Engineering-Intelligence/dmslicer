"""Semantic and repository-reference validation for GeometrySnapshot v0.1."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any, Iterable, Mapping

from .ids import component_id, interface_id, partition_id, relation_id, snapshot_id
from .schema import schema_errors


@dataclass(frozen=True)
class ValidationIssue:
    code: str
    path: str
    message: str


_COLLECTION_IDS = {
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
_PLACEHOLDERS = {"N/A", "NOT APPLICABLE", "NOT_APPLICABLE"}
_ORDINAL_LOCATOR = re.compile(r"^(?:Face|Shape)\d+$", re.IGNORECASE)
_RUNTIME_LOCATOR = re.compile(
    r"^(?:\d+|id\(.*\)|runtime:|handle:|0x[0-9a-f]+)", re.IGNORECASE
)


def _issue(code: str, path: str, message: str) -> ValidationIssue:
    return ValidationIssue(code=code, path=path, message=message)


def _index(
    snapshot: Mapping[str, Any], issues: list[ValidationIssue]
) -> dict[str, dict[str, Mapping[str, Any]]]:
    indexes: dict[str, dict[str, Mapping[str, Any]]] = {}
    all_ids: dict[str, str] = {}
    for collection, id_field in _COLLECTION_IDS.items():
        records = snapshot.get(collection, [])
        current: dict[str, Mapping[str, Any]] = {}
        for position, record in enumerate(records):
            identifier = record[id_field]
            path = f"{collection}.{position}.{id_field}"
            if identifier in current or identifier in all_ids:
                issues.append(
                    _issue("DUPLICATE_ID", path, f"duplicate identifier: {identifier}")
                )
            current[identifier] = record
            all_ids[identifier] = path
        indexes[collection] = current
    return indexes


def _portable_artifact_path(repository_root: Path, uri: str) -> Path | None:
    if "\\" in uri or re.match(r"^[A-Za-z]:", uri):
        return None
    pure = PurePosixPath(uri)
    if pure.is_absolute() or not pure.parts or ".." in pure.parts:
        return None
    root = repository_root.resolve()
    candidate = (root / Path(*pure.parts)).resolve()
    try:
        candidate.relative_to(root)
    except ValueError:
        return None
    return candidate


def _geometry_references(snapshot: Mapping[str, Any]) -> Iterable[tuple[str, Mapping[str, Any]]]:
    for collection in ("regions", "patches", "boundaries"):
        for position, record in enumerate(snapshot.get(collection, [])):
            yield f"{collection}.{position}.geometry_ref", record["geometry_ref"]
    for position, record in enumerate(snapshot.get("surface_partitions", [])):
        yield f"surface_partitions.{position}.source_geometry_ref", record[
            "source_geometry_ref"
        ]
        geometry_ref = record.get("geometry_ref")
        if geometry_ref is not None:
            yield f"surface_partitions.{position}.geometry_ref", geometry_ref


def _reference_issue(
    indexes: Mapping[str, Mapping[str, Any]],
    collection: str,
    identifier: str,
    path: str,
    issues: list[ValidationIssue],
) -> None:
    if identifier not in indexes[collection]:
        issues.append(
            _issue(
                "UNRESOLVED_REFERENCE",
                path,
                f"reference does not resolve in {collection}: {identifier}",
            )
        )


def _check_placeholders(
    value: Any, path: str, issues: list[ValidationIssue]
) -> None:
    if isinstance(value, Mapping):
        for key, item in value.items():
            _check_placeholders(item, f"{path}.{key}" if path else key, issues)
    elif isinstance(value, list):
        for position, item in enumerate(value):
            _check_placeholders(item, f"{path}.{position}", issues)
    elif isinstance(value, str) and value.strip().upper() in _PLACEHOLDERS:
        issues.append(
            _issue("PLACEHOLDER_VALUE", path or "$", "placeholder values are forbidden")
        )


def _validate_artifacts(
    indexes: Mapping[str, Mapping[str, Any]],
    repository_root: Path,
    issues: list[ValidationIssue],
) -> None:
    for identifier, artifact in indexes["artifact_references"].items():
        uri = artifact["uri"]
        path = _portable_artifact_path(repository_root, uri)
        if path is None:
            issues.append(
                _issue(
                    "NON_PORTABLE_ARTIFACT_URI",
                    f"artifact_references.{identifier}.uri",
                    "artifact URI must stay within the repository",
                )
            )
        elif not path.is_file():
            issues.append(
                _issue(
                    "UNRESOLVED_ARTIFACT",
                    f"artifact_references.{identifier}.uri",
                    f"artifact does not exist: {uri}",
                )
            )


def _validate_locators(
    snapshot: Mapping[str, Any],
    indexes: Mapping[str, Mapping[str, Any]],
    issues: list[ValidationIssue],
) -> None:
    for path, geometry_ref in _geometry_references(snapshot):
        _reference_issue(
            indexes,
            "artifact_references",
            geometry_ref["artifact_ref"],
            f"{path}.artifact_ref",
            issues,
        )
        locator = geometry_ref["locator"]
        scheme = locator["scheme"]
        value = locator["value"]
        provenance_ref = locator.get("provenance_ref")
        if provenance_ref is not None:
            _reference_issue(
                indexes,
                "provenance_references",
                provenance_ref,
                f"{path}.locator.provenance_ref",
                issues,
            )
        unstable = _ORDINAL_LOCATOR.fullmatch(value) or _RUNTIME_LOCATOR.match(value)
        if scheme == "STEP_FACE":
            unstable = unstable or not value.startswith("face:") or provenance_ref is None
        elif scheme == "CAD_OBJECT":
            unstable = (
                unstable
                or not value.startswith("cad-object:")
                or provenance_ref is None
            )
        elif scheme == "BREP_ROOT":
            unstable = value != "$"
        if unstable:
            issues.append(
                _issue(
                    "UNSTABLE_LOCATOR",
                    f"{path}.locator.value",
                    "locator is not backed by stable provenance or a persistent label",
                )
            )


def _validate_references(
    snapshot: Mapping[str, Any],
    indexes: Mapping[str, Mapping[str, Any]],
    issues: list[ValidationIssue],
) -> None:
    frame_id = snapshot["model_frame"]["frame_id"]
    for position, document in enumerate(snapshot["source_documents"]):
        _reference_issue(
            indexes,
            "artifact_references",
            document["artifact_ref"],
            f"source_documents.{position}.artifact_ref",
            issues,
        )
    for position, region in enumerate(snapshot["regions"]):
        _reference_issue(
            indexes,
            "source_documents",
            region["source_document_id"],
            f"regions.{position}.source_document_id",
            issues,
        )
        if region["frame_ref"] != frame_id:
            issues.append(
                _issue(
                    "UNRESOLVED_REFERENCE",
                    f"regions.{position}.frame_ref",
                    "region frame does not resolve to model_frame",
                )
            )
    for position, relation in enumerate(snapshot["relations"]):
        for region_ref in relation["region_refs"]:
            _reference_issue(
                indexes,
                "regions",
                region_ref,
                f"relations.{position}.region_refs",
                issues,
            )
        for tolerance_ref in relation.get("tolerance_refs", []):
            _reference_issue(
                indexes,
                "tolerances",
                tolerance_ref,
                f"relations.{position}.tolerance_refs",
                issues,
            )
    for position, interface in enumerate(snapshot.get("interfaces", [])):
        _reference_issue(indexes, "relations", interface["relation_ref"], f"interfaces.{position}.relation_ref", issues)
        for region_ref in interface["region_refs"]:
            _reference_issue(indexes, "regions", region_ref, f"interfaces.{position}.region_refs", issues)
        for patch_ref in interface["patch_refs"]:
            _reference_issue(indexes, "patches", patch_ref, f"interfaces.{position}.patch_refs", issues)
    for position, component in enumerate(snapshot.get("interface_components", [])):
        _reference_issue(indexes, "interfaces", component["interface_ref"], f"interface_components.{position}.interface_ref", issues)
        for patch_ref in component["patch_refs"]:
            _reference_issue(indexes, "patches", patch_ref, f"interface_components.{position}.patch_refs", issues)
    for position, patch in enumerate(snapshot.get("patches", [])):
        _reference_issue(indexes, "interfaces", patch["interface_ref"], f"patches.{position}.interface_ref", issues)
        _reference_issue(indexes, "interface_components", patch["component_ref"], f"patches.{position}.component_ref", issues)
        if patch["frame_ref"] != frame_id:
            issues.append(_issue("UNRESOLVED_REFERENCE", f"patches.{position}.frame_ref", "patch frame does not resolve to model_frame"))
    for position, boundary in enumerate(snapshot.get("boundaries", [])):
        _reference_issue(indexes, "patches", boundary["patch_ref"], f"boundaries.{position}.patch_ref", issues)
    for position, partition in enumerate(snapshot.get("surface_partitions", [])):
        for patch_ref in partition["patch_refs"]:
            _reference_issue(indexes, "patches", patch_ref, f"surface_partitions.{position}.patch_refs", issues)
    subject_ids = set().union(
        indexes["regions"], indexes["interfaces"], indexes["patches"]
    )
    for position, binding in enumerate(snapshot.get("semantic_bindings", [])):
        if binding["subject_ref"] not in subject_ids:
            issues.append(_issue("INVALID_SEMANTIC_BINDING", f"semantic_bindings.{position}.subject_ref", "semantic subject does not resolve"))


def _validate_membership_and_ids(
    snapshot: Mapping[str, Any],
    indexes: Mapping[str, Mapping[str, Any]],
    issues: list[ValidationIssue],
) -> None:
    for relation in snapshot["relations"]:
        expected = relation_id(
            relation["region_refs"], relation["taxonomy"], relation["confirmation"]
        )
        if relation["relation_id"] != expected:
            issues.append(_issue("IDENTITY_MISMATCH", f"relations.{relation['relation_id']}", "relation_id does not match semantic members"))
    for interface in snapshot.get("interfaces", []):
        relation = indexes["relations"].get(interface["relation_ref"])
        if relation is not None:
            if relation["confirmation"] != "CONFIRMED" or relation["intersection_dimension"] != 2:
                issues.append(_issue("INVALID_INTERFACE_CONFIRMATION", f"interfaces.{interface['interface_id']}", "only confirmed two-dimensional relations create interfaces"))
            if set(interface["region_refs"]) != set(relation["region_refs"]):
                issues.append(_issue("MEMBERSHIP_MISMATCH", f"interfaces.{interface['interface_id']}.region_refs", "interface regions differ from its relation"))
        if interface["interface_id"] != interface_id(interface["relation_ref"]):
            issues.append(_issue("IDENTITY_MISMATCH", f"interfaces.{interface['interface_id']}", "interface_id does not match relation"))
        actual_patches = {
            patch_id_value
            for patch_id_value, patch in indexes["patches"].items()
            if patch["interface_ref"] == interface["interface_id"]
        }
        if set(interface["patch_refs"]) != actual_patches:
            issues.append(_issue("MEMBERSHIP_MISMATCH", f"interfaces.{interface['interface_id']}.patch_refs", "interface patch membership is inconsistent"))
    for component in snapshot.get("interface_components", []):
        actual_patches = {
            patch_id_value
            for patch_id_value, patch in indexes["patches"].items()
            if patch["component_ref"] == component["component_id"]
        }
        if set(component["patch_refs"]) != actual_patches:
            issues.append(_issue("MEMBERSHIP_MISMATCH", f"interface_components.{component['component_id']}.patch_refs", "component patch membership is inconsistent"))
        if component["component_id"] != component_id(component["interface_ref"], component["patch_refs"]):
            issues.append(_issue("IDENTITY_MISMATCH", f"interface_components.{component['component_id']}", "component_id does not match members"))
    for partition in snapshot.get("surface_partitions", []):
        expected = partition_id(
            partition["source_geometry_ref"], partition["role"], partition["patch_refs"]
        )
        if partition["partition_id"] != expected:
            issues.append(_issue("IDENTITY_MISMATCH", f"surface_partitions.{partition['partition_id']}", "partition_id does not match members"))
    if snapshot["snapshot_id"] != snapshot_id(snapshot):
        issues.append(_issue("IDENTITY_MISMATCH", "snapshot_id", "snapshot_id does not match semantic content"))


def validate_geometry_snapshot(
    snapshot: Mapping[str, Any], repository_root: Path
) -> tuple[ValidationIssue, ...]:
    shape_issues = schema_errors(snapshot, schema_name="geometry_snapshot")
    if shape_issues:
        return tuple(
            ValidationIssue(issue.code, issue.path, issue.message)
            for issue in shape_issues
        )

    issues: list[ValidationIssue] = []
    indexes = _index(snapshot, issues)
    _check_placeholders(snapshot, "", issues)
    _validate_artifacts(indexes, Path(repository_root), issues)
    _validate_locators(snapshot, indexes, issues)
    _validate_references(snapshot, indexes, issues)
    _validate_membership_and_ids(snapshot, indexes, issues)
    return tuple(sorted(issues, key=lambda item: (item.path, item.code, item.message)))
