from __future__ import annotations

import importlib
import json
import sys
from copy import deepcopy
from pathlib import Path

import pytest

from contract_consumers.slicer_mock import decide


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
EXAMPLE_ROOT = REPOSITORY_ROOT / "contract_examples" / "v0.1"


def _view(snapshot: dict, decision: dict | None = None) -> dict:
    try:
        module = importlib.import_module("contract_consumers.ui_mock")
    except ModuleNotFoundError:
        pytest.fail("FreeCAD-free UI contract mock is not implemented")
    return module.build_view_model(snapshot, decision, REPOSITORY_ROOT)


def _load(group: str, name: str) -> dict:
    return json.loads((EXAMPLE_ROOT / group / name).read_text(encoding="utf-8"))


def test_e0_view_lists_regions_interfaces_and_disjoint_relation() -> None:
    view = _view(_load("geometry", "planar_full.json"))

    assert [item["region_id"] for item in view["regions"]] == [
        "region:e0-a",
        "region:e0-b",
        "region:e0-g",
    ]
    assert len(view["interfaces"]) == 2
    assert any(item["taxonomy"] == "DISJOINT" for item in view["relations"])
    assert {item["semantic_role"] for item in view["semantic_bindings"]} == {
        "GRADIENT_REGION",
        "SOURCE_A",
        "SOURCE_B",
    }


def test_e2_view_keeps_two_components_and_omits_absent_boundaries() -> None:
    view = _view(_load("geometry", "planar_multipatch.json"))

    assert len(view["patches"]) == 2
    assert len(view["interface_components"]) == 2
    assert {tuple(item["patch_refs"]) for item in view["interface_components"]} == {
        ("patch:e2-one",),
        ("patch:e2-two",),
    }
    assert view["boundaries"] == []


def test_ambiguous_relation_is_visible_without_fabricated_interface() -> None:
    view = _view(_load("negative", "ambiguous_relation.json"))

    assert [(item["taxonomy"], item["confirmation"]) for item in view["relations"]] == [
        ("AMBIGUOUS", "AMBIGUOUS")
    ]
    assert view["interfaces"] == []
    assert view["patches"] == []


def test_e1_view_links_artifacts_and_selected_decision() -> None:
    snapshot = _load("geometry", "planar_partial.json")
    decision = decide(snapshot, REPOSITORY_ROOT)

    view = _view(snapshot, decision)

    assert view["decision"] == {
        "decision_id": decision["decision_id"],
        "status": "DECIDED",
        "reason_code": "NONE",
        "selected_interface_id": decision["selected_interface_id"],
        "selected_patch_ids": ["patch:e1-common"],
        "target_region_id": "region:e1-side-1",
    }
    assert view["artifact_links"] == [
        {
            "artifact_id": "artifact:e1-step",
            "kind": "STEP",
            "uri": "benchmarks/planar_partial_overlap_correction_06b/P07/inputs.step",
        }
    ]


def test_collection_reorder_produces_same_view_model() -> None:
    snapshot = _load("geometry", "planar_full.json")
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
        "semantic_bindings",
    ):
        reordered[field].reverse()
    for interface in reordered["interfaces"]:
        interface["region_refs"].reverse()

    assert _view(reordered) == _view(snapshot)


def test_ui_mock_does_not_import_geometry_runners_or_freecad() -> None:
    before = set(sys.modules)

    _view(_load("geometry", "planar_full.json"))

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
