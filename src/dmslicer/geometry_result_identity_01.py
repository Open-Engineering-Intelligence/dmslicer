"""Explicit publication of P07 operation results to existing snapshot identities."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path, PurePosixPath
from typing import Any, Mapping
import shutil

from .evidence import read_json, write_json
from .geometry_contract.ids import snapshot_id


SUCCESS_STATUS = "CORRECTED_PARTIAL_INTERFACE_FUSED"
_REQUIRED_ENTITY_COUNT = 5


def load_publication_map(path: Path) -> dict[str, Any]:
    value = read_json(Path(path))
    if value.get("schema_version") != 1 or value.get("scenario_id") != "P07":
        raise ValueError("P07 identity publication map is invalid")
    if not isinstance(value.get("backend_results"), list) or not isinstance(value.get("entity_bindings"), list):
        raise ValueError("P07 identity publication map is incomplete")
    return value


def _safe_relative(uri: str) -> Path:
    pure = PurePosixPath(uri)
    if not uri or "\\" in uri or pure.is_absolute() or ".." in pure.parts:
        raise ValueError(f"non-portable artifact URI: {uri}")
    return Path(*pure.parts)


def _result_index(operation: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    rows = operation.get("result_bindings")
    if not isinstance(rows, list):
        raise ValueError("operation has no result_bindings")
    index: dict[str, Mapping[str, Any]] = {}
    for row in rows:
        if not isinstance(row, Mapping) or not isinstance(row.get("result_ref"), str):
            raise ValueError("invalid result binding")
        result_ref = row["result_ref"]
        if result_ref in index:
            raise ValueError(f"duplicate result_ref: {result_ref}")
        index[result_ref] = row
    return index


def validate_result_bindings(
    operation: Mapping[str, Any],
    publication_map: Mapping[str, Any],
    source_root: Path,
    operation_root: Path,
) -> None:
    if operation.get("scenario_id") != "P07" or operation.get("status") != SUCCESS_STATUS:
        raise ValueError("operation is not a successful P07 result")
    expected_rows = publication_map.get("backend_results")
    if not isinstance(expected_rows, list):
        raise ValueError("publication map has no backend_results")
    index = _result_index(operation)
    expected = {row.get("result_ref"): row for row in expected_rows if isinstance(row, Mapping)}
    if None in expected or set(index) != set(expected):
        raise ValueError("operation result refs do not match the explicit P07 publication map")
    for result_ref, expected_row in expected.items():
        actual = index[result_ref]
        for key in ("role", "source_role"):
            if key in expected_row and actual.get(key) != expected_row[key]:
                raise ValueError(f"result binding mismatch for {result_ref}: {key}")
        expected_artifact = expected_row.get("artifact")
        actual_artifact = actual.get("artifact")
        if actual_artifact != expected_artifact or not isinstance(actual_artifact, Mapping):
            raise ValueError(f"result binding mismatch for {result_ref}: artifact")
        target_root = source_root if actual_artifact["kind"] == "STEP" else operation_root
        if not (target_root / _safe_relative(str(actual_artifact["uri"]))).is_file():
            raise ValueError(f"missing artifact for {result_ref}")
    entity_rows = publication_map.get("entity_bindings")
    if not isinstance(entity_rows, list) or len(entity_rows) != _REQUIRED_ENTITY_COUNT:
        raise ValueError("publication map must declare exactly five entity bindings")
    entity_ids = [row.get("entity_id") for row in entity_rows if isinstance(row, Mapping)]
    mapped_refs = [row.get("result_ref") for row in entity_rows if isinstance(row, Mapping)]
    if len(entity_ids) != _REQUIRED_ENTITY_COUNT or len(set(entity_ids)) != _REQUIRED_ENTITY_COUNT:
        raise ValueError("duplicate or invalid entity binding")
    if len(mapped_refs) != _REQUIRED_ENTITY_COUNT or set(mapped_refs) != set(expected):
        raise ValueError("entity bindings must cover every explicit result ref")


def _artifact_id(result_ref: str) -> str:
    return "artifact:p07-result-" + result_ref.split("result:", 1)[1].replace(":", "-")


def _snapshot_entity_ids(snapshot: Mapping[str, Any]) -> set[str]:
    ids = {row["region_id"] for row in snapshot.get("regions", [])}
    ids.update(row["partition_id"] for row in snapshot.get("surface_partitions", []))
    return ids


def publish_identity_bound_snapshot(
    snapshot: Mapping[str, Any],
    operation: Mapping[str, Any],
    publication_map: Mapping[str, Any],
    *,
    source_root: Path,
    operation_root: Path,
    repository_root: Path,
    evidence_root: Path,
    implementation_commit: str,
) -> dict[str, Any]:
    validate_result_bindings(operation, publication_map, source_root, operation_root)
    entity_rows = publication_map["entity_bindings"]
    if {row["entity_id"] for row in entity_rows} - _snapshot_entity_ids(snapshot):
        raise ValueError("publication map references an entity absent from the source snapshot")
    result_rows = _result_index(operation)
    published = deepcopy(dict(snapshot))
    evidence_root = Path(evidence_root)
    repository_root = Path(repository_root)
    artifacts_dir = evidence_root / "artifacts"
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    binding_by_entity = {row["entity_id"]: row["result_ref"] for row in entity_rows}
    output_artifacts: dict[str, str] = {}
    for result_ref, binding in result_rows.items():
        artifact = binding["artifact"]
        if artifact["kind"] != "BREP":
            continue
        source = Path(operation_root) / _safe_relative(artifact["uri"])
        destination = artifacts_dir / Path(artifact["uri"]).name
        shutil.copyfile(source, destination)
        uri = destination.relative_to(repository_root).as_posix()
        artifact_id = _artifact_id(result_ref)
        output_artifacts[result_ref] = artifact_id
        published["artifact_references"].append(
            {"artifact_id": artifact_id, "kind": "BREP", "uri": uri}
        )
    partitions = {row["partition_id"]: row for row in published["surface_partitions"]}
    for entity_id, result_ref in binding_by_entity.items():
        if entity_id not in partitions:
            continue
        artifact_id = output_artifacts.get(result_ref)
        if artifact_id is None:
            raise ValueError(f"partition binding lacks a BREP artifact: {entity_id}")
        partitions[entity_id]["geometry_ref"] = {
            "artifact_ref": artifact_id,
            "locator": {"scheme": "BREP_ROOT", "value": "$"},
        }
    original_snapshot_id = snapshot["snapshot_id"]
    published["parent_snapshot_ids"] = [original_snapshot_id]
    evidence_uri = (evidence_root / "operation.json").relative_to(repository_root).as_posix()
    published["provenance_references"].append(
        {
            "provenance_id": "provenance:p07-result-identity-01",
            "goal_id": "GEOMETRY-RESULT-IDENTITY-01",
            "implementation_commit": implementation_commit,
            "fixture_uri": "benchmarks/planar_partial_overlap_correction_06b/P07/inputs.step",
            "evidence_uri": evidence_uri,
        }
    )
    published["snapshot_id"] = snapshot_id(published)
    write_json(evidence_root / "operation.json", dict(operation))
    write_json(
        evidence_root / "identity_bindings.json",
        {
            "source_snapshot_id": original_snapshot_id,
            "published_snapshot_id": published["snapshot_id"],
            "entity_bindings": entity_rows,
        },
    )
    write_json(evidence_root / "geometry_snapshot.json", published)
    write_json(
        evidence_root / "manifest.json",
        {
            "goal_id": "GEOMETRY-RESULT-IDENTITY-01",
            "run_id": evidence_root.name,
            "implementation_commit": implementation_commit,
            "fixture": "benchmarks/planar_partial_overlap_correction_06b/P07/inputs.step",
            "operation": "operation.json",
            "identity_bindings": "identity_bindings.json",
            "geometry_snapshot": "geometry_snapshot.json",
            "status": "PASS",
        },
    )
    return published
