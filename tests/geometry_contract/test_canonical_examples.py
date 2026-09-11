from __future__ import annotations

import json
from pathlib import Path

import pytest

from dmslicer.geometry_contract.validation import validate_geometry_snapshot

from ._samples import REPOSITORY_ROOT


EXAMPLE_ROOT = REPOSITORY_ROOT / "contract_examples" / "v0.1" / "geometry"


def _load(name: str) -> dict:
    path = EXAMPLE_ROOT / name
    if not path.is_file():
        pytest.fail(f"canonical example is missing: {path.relative_to(REPOSITORY_ROOT)}")
    return json.loads(path.read_text(encoding="utf-8"))


def test_e0_planar_full_records_two_full_interfaces_and_disjoint_sources() -> None:
    snapshot = _load("planar_full.json")

    assert validate_geometry_snapshot(snapshot, REPOSITORY_ROOT) == ()
    assert len(snapshot["regions"]) == 3
    assert sorted(relation["taxonomy"] for relation in snapshot["relations"]) == [
        "DISJOINT",
        "FULL_FACE_OVERLAP",
        "FULL_FACE_OVERLAP",
    ]
    assert len(snapshot["interfaces"]) == 2
    assert sorted([patch["area"] for patch in snapshot["patches"]], key=str) == [
        {"value": 400.0, "unit": "mm2"},
        {"value": 400.0, "unit": "mm2"},
    ]
    assert {binding["semantic_role"] for binding in snapshot["semantic_bindings"]} == {
        "GRADIENT_REGION",
        "SOURCE_A",
        "SOURCE_B",
    }


def test_e1_planar_partial_records_common_and_both_remaining_partitions() -> None:
    snapshot = _load("planar_partial.json")

    assert validate_geometry_snapshot(snapshot, REPOSITORY_ROOT) == ()
    assert [patch["area"]["value"] for patch in snapshot["patches"]] == [480.0]
    areas = sorted(
        (partition["role"], partition["area"]["value"])
        for partition in snapshot["surface_partitions"]
    )
    assert areas == [
        ("COMMON", 480.0),
        ("REMAINING", 320.0),
        ("REMAINING", 320.0),
    ]
    assert any(
        binding["semantic_role"] == "TARGET_REGION"
        and binding["activation"] == "ACTIVE"
        for binding in snapshot["semantic_bindings"]
    )


def test_e2_planar_multipatch_keeps_equal_area_patches_in_two_components() -> None:
    snapshot = _load("planar_multipatch.json")

    assert validate_geometry_snapshot(snapshot, REPOSITORY_ROOT) == ()
    assert sorted(patch["area"]["value"] for patch in snapshot["patches"]) == [
        192.0,
        192.0,
    ]
    assert len(snapshot["interface_components"]) == 2
    assert {
        tuple(component["patch_refs"])
        for component in snapshot["interface_components"]
    } == {(snapshot["patches"][0]["patch_id"],), (snapshot["patches"][1]["patch_id"],)}
    assert "boundaries" not in snapshot


def test_g1_examples_reference_only_tracked_repository_artifacts() -> None:
    for name in ("planar_full.json", "planar_partial.json", "planar_multipatch.json"):
        snapshot = _load(name)
        for artifact in snapshot["artifact_references"]:
            assert not artifact["uri"].startswith("outputs/")
            assert (REPOSITORY_ROOT / artifact["uri"]).is_file()
