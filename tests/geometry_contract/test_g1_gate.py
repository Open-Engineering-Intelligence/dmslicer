from __future__ import annotations

import json
import sys
from copy import deepcopy
from pathlib import Path
from typing import Any

from contract_consumers.slicer_mock import decide
from contract_consumers.ui_mock import build_view_model
from dmslicer.geometry_contract.validation import validate_geometry_snapshot


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
EXAMPLE_ROOT = REPOSITORY_ROOT / "contract_examples" / "v0.1"
G1_POSITIVE = (
    "planar_full.json",
    "planar_partial.json",
    "planar_multipatch.json",
)
G1_NEGATIVE = {
    "ambiguous_relation.json": ("REJECTED", "AMBIGUOUS_INTERFACE"),
    "unsupported_family.json": (
        "UNSUPPORTED",
        "UNSUPPORTED_GEOMETRY_FAMILY",
    ),
    "missing_semantic_binding.json": (
        "REJECTED",
        "MISSING_SEMANTIC_BINDING",
    ),
    "unresolved_artifact.json": ("FAILED", "INVALID_SNAPSHOT"),
}
_SET_LIKE_COLLECTIONS = (
    "source_documents",
    "regions",
    "relations",
    "artifact_references",
    "provenance_references",
    "tolerances",
    "interfaces",
    "interface_components",
    "patches",
    "boundaries",
    "surface_partitions",
    "semantic_bindings",
)
_PRIVATE_OPERATION_KEYS = {
    "operation",
    "command",
    "validator",
    "validator_details",
    "diagnostics",
    "execution_environment",
}


def _load(group: str, name: str) -> dict[str, Any]:
    path = EXAMPLE_ROOT / group / name
    return json.loads(path.read_text(encoding="utf-8"))


def _walk_keys(value: Any) -> set[str]:
    if isinstance(value, dict):
        return set(value).union(*(_walk_keys(item) for item in value.values()))
    if isinstance(value, list):
        return set().union(*(_walk_keys(item) for item in value))
    return set()


def _reordered(snapshot: dict[str, Any]) -> dict[str, Any]:
    result = deepcopy(snapshot)
    for field in _SET_LIKE_COLLECTIONS:
        if field in result:
            result[field].reverse()
    for relation in result.get("relations", []):
        relation["region_refs"].reverse()
        if "tolerance_refs" in relation:
            relation["tolerance_refs"].reverse()
    for interface in result.get("interfaces", []):
        interface["region_refs"].reverse()
        interface["patch_refs"].reverse()
    for component in result.get("interface_components", []):
        component["patch_refs"].reverse()
    for partition in result.get("surface_partitions", []):
        partition["patch_refs"].reverse()
    return result


def test_g1_parallel_development_start_gate() -> None:
    before = set(sys.modules)

    for name in G1_POSITIVE:
        snapshot = _load("geometry", name)
        assert validate_geometry_snapshot(snapshot, REPOSITORY_ROOT) == ()
        assert not (_walk_keys(snapshot) & _PRIVATE_OPERATION_KEYS)
        reordered = _reordered(snapshot)
        assert validate_geometry_snapshot(reordered, REPOSITORY_ROOT) == ()
        assert build_view_model(reordered, None, REPOSITORY_ROOT) == build_view_model(
            snapshot, None, REPOSITORY_ROOT
        )

    partial = _load("geometry", "planar_partial.json")
    assert decide(_reordered(partial), REPOSITORY_ROOT) == decide(
        partial, REPOSITORY_ROOT
    )

    for name, expected in G1_NEGATIVE.items():
        snapshot = _load("negative", name)
        decision = decide(snapshot, REPOSITORY_ROOT)
        assert (decision["status"], decision["reason_code"]) == expected

    loaded = set(sys.modules) - before
    forbidden = {
        "FreeCAD",
        "Part",
        "dmslicer.runner",
        "dmslicer.planar_partial_overlap_correction_06b",
        "dmslicer.planar_multipatch_interface_correction_06c",
        "dmslicer.cylindrical_interface_repair_07a",
    }
    assert loaded.isdisjoint(forbidden)
