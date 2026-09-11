from __future__ import annotations

import importlib
import json
import sys
from copy import deepcopy
from pathlib import Path

import pytest

from dmslicer.geometry_contract.ids import snapshot_id
from dmslicer.geometry_contract.schema import schema_errors


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
EXAMPLE_ROOT = REPOSITORY_ROOT / "contract_examples" / "v0.1"


def _decide(snapshot: dict) -> dict:
    try:
        module = importlib.import_module("contract_consumers.slicer_mock")
    except ModuleNotFoundError:
        pytest.fail("FreeCAD-free Slicer contract mock is not implemented")
    return module.decide(snapshot, REPOSITORY_ROOT)


def _load(group: str, name: str) -> dict:
    return json.loads((EXAMPLE_ROOT / group / name).read_text(encoding="utf-8"))


def test_e1_produces_schema_valid_planar_partition_decision() -> None:
    snapshot = _load("geometry", "planar_partial.json")

    decision = _decide(snapshot)

    assert schema_errors(decision, schema_name="slicer_decision") == ()
    assert decision["input_snapshot_id"] == snapshot["snapshot_id"]
    assert decision["status"] == "DECIDED"
    assert decision["reason_code"] == "NONE"
    assert decision["strategy_kind"] == "PLANAR_INTERFACE_PARTITION"
    assert decision["partition_operation"] == "SPLIT_COMMON_AND_REMAINING"
    assert decision["target_region_id"] == "region:e1-side-1"
    assert decision["selected_patch_ids"] == ["patch:e1-common"]
    assert decision["expected_partition_refs"] == sorted(
        partition["partition_id"] for partition in snapshot["surface_partitions"]
    )


@pytest.mark.parametrize(
    ("name", "status", "reason"),
    [
        ("ambiguous_relation.json", "REJECTED", "AMBIGUOUS_INTERFACE"),
        (
            "unsupported_family.json",
            "UNSUPPORTED",
            "UNSUPPORTED_GEOMETRY_FAMILY",
        ),
        (
            "missing_semantic_binding.json",
            "REJECTED",
            "MISSING_SEMANTIC_BINDING",
        ),
        ("unresolved_artifact.json", "FAILED", "INVALID_SNAPSHOT"),
    ],
)
def test_negative_examples_fail_closed(name: str, status: str, reason: str) -> None:
    decision = _decide(_load("negative", name))

    assert schema_errors(decision, schema_name="slicer_decision") == ()
    assert decision["status"] == status
    assert decision["reason_code"] == reason
    assert "selected_interface_id" not in decision
    assert "selected_patch_ids" not in decision


def test_collection_reorder_produces_byte_identical_decision() -> None:
    snapshot = _load("geometry", "planar_partial.json")
    reordered = deepcopy(snapshot)
    for field in (
        "source_documents",
        "regions",
        "relations",
        "artifact_references",
        "provenance_references",
        "tolerances",
        "interfaces",
        "interface_components",
        "patches",
        "surface_partitions",
        "semantic_bindings",
    ):
        reordered[field].reverse()
    reordered["interfaces"][0]["region_refs"].reverse()
    assert snapshot_id(reordered) == snapshot["snapshot_id"]

    first = json.dumps(_decide(snapshot), sort_keys=True, separators=(",", ":"))
    second = json.dumps(_decide(reordered), sort_keys=True, separators=(",", ":"))
    assert second == first


def test_slicer_mock_does_not_import_geometry_runners_or_freecad() -> None:
    before = set(sys.modules)

    _decide(_load("geometry", "planar_partial.json"))

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
