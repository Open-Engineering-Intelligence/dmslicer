from __future__ import annotations

import importlib
from copy import deepcopy

import pytest

from ._samples import connected_snapshot


def _ids():
    try:
        return importlib.import_module("dmslicer.geometry_contract.ids")
    except ModuleNotFoundError:
        pytest.fail("geometry contract identity functions are not implemented")


def test_container_ids_have_hand_checked_digests() -> None:
    ids = _ids()

    assert ids.relation_id(
        ["region:b", "region:a"], "PARTIAL_FACE_OVERLAP", "CONFIRMED"
    ) == (
        "relation:v0.1:"
        "6db68a270d3813e3ec0a50ba5e7b77d868231b8bda1987865eaae98e73fd4682"
    )
    assert ids.interface_id("relation:sample") == (
        "interface:v0.1:"
        "6fecdb2af7b54d94415bb24a2751f88a6d8282578436ca15dac619aaf26d224e"
    )
    assert ids.component_id("interface:sample", ["patch:b", "patch:a"]) == (
        "component:v0.1:"
        "ce4087913efa663fdc8317e6d566adcdd3d02654096599365d5574feb07bcd84"
    )


def test_snapshot_identity_ignores_collection_order_but_not_geometry_facts() -> None:
    ids = _ids()
    first = connected_snapshot(ids)
    reordered = deepcopy(first)
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
        reordered[field] = list(reversed(reordered[field]))
    reordered["interfaces"][0]["region_refs"].reverse()

    assert ids.snapshot_id(reordered) == first["snapshot_id"]

    changed = deepcopy(first)
    changed["patches"][0]["area"]["value"] = 481.0
    assert ids.snapshot_id(changed) != first["snapshot_id"]


def test_display_only_metadata_does_not_change_snapshot_identity() -> None:
    ids = _ids()
    snapshot = connected_snapshot(ids)
    decorated = deepcopy(snapshot)
    decorated["label"] = "Human label"
    decorated["description"] = "Display-only explanation"
    decorated["extensions"] = {"viewer.example": {"color": "red"}}

    assert ids.snapshot_id(decorated) == snapshot["snapshot_id"]
