from __future__ import annotations

import importlib
from copy import deepcopy

import pytest

from ._samples import REPOSITORY_ROOT, connected_snapshot, core_snapshot


def _api():
    try:
        ids = importlib.import_module("dmslicer.geometry_contract.ids")
        validation = importlib.import_module("dmslicer.geometry_contract.validation")
    except ModuleNotFoundError:
        pytest.fail("geometry contract semantic validation is not implemented")
    return ids, validation


def _codes(issues) -> set[str]:
    return {issue.code for issue in issues}


def test_shared_step_artifact_with_distinct_occurrence_locators_is_valid() -> None:
    ids, validation = _api()
    snapshot = core_snapshot()
    snapshot["regions"].append(
        {
            **deepcopy(snapshot["regions"][0]),
            "region_id": "region:c",
            "geometry_ref": {
                "artifact_ref": "artifact:source-step",
                "locator": {
                    "scheme": "STEP_OCCURRENCE",
                    "value": "CASE01/C",
                },
            },
        }
    )
    snapshot["snapshot_id"] = ids.snapshot_id(snapshot)

    assert validation.validate_geometry_snapshot(snapshot, REPOSITORY_ROOT) == ()
    assert len(snapshot["artifact_references"]) == 1


@pytest.mark.parametrize(
    ("scheme", "value"),
    [
        ("STEP_FACE", "Face3"),
        ("CAD_OBJECT", "Shape17"),
        ("STEP_FACE", "3"),
        ("CAD_OBJECT", "id(140707123456)"),
        ("CAD_OBJECT", "runtime:0xABCDEF"),
    ],
)
def test_unstable_face_or_object_locator_fails_closed(scheme: str, value: str) -> None:
    ids, validation = _api()
    snapshot = core_snapshot()
    snapshot["regions"][0]["geometry_ref"]["locator"] = {
        "scheme": scheme,
        "value": value,
        "provenance_ref": "provenance:case01",
    }
    snapshot["snapshot_id"] = ids.snapshot_id(snapshot)

    assert "UNSTABLE_LOCATOR" in _codes(
        validation.validate_geometry_snapshot(snapshot, REPOSITORY_ROOT)
    )


@pytest.mark.parametrize(
    "locator",
    [
        {
            "scheme": "STEP_FACE",
            "value": "face:v1:stable-source",
            "provenance_ref": "provenance:case01",
        },
        {
            "scheme": "CAD_OBJECT",
            "value": "cad-object:PersistentBodyLabel",
            "provenance_ref": "provenance:case01",
        },
    ],
)
def test_provenance_backed_face_or_object_locator_is_valid(locator: dict) -> None:
    ids, validation = _api()
    snapshot = core_snapshot()
    snapshot["regions"][0]["geometry_ref"]["locator"] = locator
    snapshot["snapshot_id"] = ids.snapshot_id(snapshot)

    assert validation.validate_geometry_snapshot(snapshot, REPOSITORY_ROOT) == ()


def test_unresolved_artifact_is_reported_without_geometry_inference() -> None:
    ids, validation = _api()
    snapshot = core_snapshot()
    snapshot["artifact_references"][0]["uri"] = "outputs/missing/source.step"
    snapshot["snapshot_id"] = ids.snapshot_id(snapshot)

    assert "UNRESOLVED_ARTIFACT" in _codes(
        validation.validate_geometry_snapshot(snapshot, REPOSITORY_ROOT)
    )


def test_confirmed_two_dimensional_relation_is_required_for_interface() -> None:
    ids, validation = _api()
    snapshot = connected_snapshot(ids)
    snapshot["relations"][0]["confirmation"] = "AMBIGUOUS"
    snapshot["snapshot_id"] = ids.snapshot_id(snapshot)

    assert "INVALID_INTERFACE_CONFIRMATION" in _codes(
        validation.validate_geometry_snapshot(snapshot, REPOSITORY_ROOT)
    )


def test_patch_component_membership_must_agree_in_both_directions() -> None:
    ids, validation = _api()
    snapshot = connected_snapshot(ids)
    snapshot["interface_components"][0]["patch_refs"] = ["patch:v1:other"]
    snapshot["snapshot_id"] = ids.snapshot_id(snapshot)

    codes = _codes(validation.validate_geometry_snapshot(snapshot, REPOSITORY_ROOT))
    assert "UNRESOLVED_REFERENCE" in codes
    assert "MEMBERSHIP_MISMATCH" in codes


def test_duplicate_ids_and_placeholder_values_are_rejected() -> None:
    ids, validation = _api()
    snapshot = connected_snapshot(ids)
    snapshot["semantic_bindings"].append(deepcopy(snapshot["semantic_bindings"][0]))
    snapshot["semantic_bindings"][1]["semantic_role"] = "N/A"
    snapshot["snapshot_id"] = ids.snapshot_id(snapshot)

    codes = _codes(validation.validate_geometry_snapshot(snapshot, REPOSITORY_ROOT))
    assert "DUPLICATE_ID" in codes
    assert "PLACEHOLDER_VALUE" in codes


def test_wrong_declared_snapshot_identity_is_rejected() -> None:
    ids, validation = _api()
    snapshot = connected_snapshot(ids)
    snapshot["snapshot_id"] = "snapshot:v0.1:" + "f" * 64

    assert "IDENTITY_MISMATCH" in _codes(
        validation.validate_geometry_snapshot(snapshot, REPOSITORY_ROOT)
    )
