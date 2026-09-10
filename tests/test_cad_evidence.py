from __future__ import annotations

from copy import deepcopy

import pytest

from dmslicer.evidence_promotion.cad_evidence import (
    compare_semantics,
    compare_ui_states,
    within_tolerance,
)


def _tolerance(value: float, unit: str) -> dict[str, object]:
    return {
        "value": value,
        "unit": unit,
        "role": "fixture comparison",
        "source": "P2 fixture policy",
    }


def _binding() -> dict[str, str]:
    return {
        "component_role": "fixture_body",
        "interface_role": "through_hole_wall",
        "allowed_transform": "IDENTITY",
    }


def _ui_snapshot(
    *, visibility: bool = True, color: list[float] | None = None, transparency: int = 0
) -> dict[str, object]:
    return {
        "schema_version": "1.0.0",
        "artifact_type": "ui_state_snapshot",
        "case_id": "fixture",
        "artifact_role": "OPENING",
        "source_artifact_id": "fixture-fcstd",
        "object_role": "fixture_body",
        "state": {
            "visibility": {"status": "SUPPORTED", "value": visibility},
            "shape_color": {
                "status": "SUPPORTED",
                "value": color if color is not None else [0.8, 0.8, 0.8],
            },
            "transparency": {"status": "SUPPORTED", "value": transparency},
            "display_mode": {"status": "UNSUPPORTED", "reason": "not required"},
            "camera": {"status": "UNSUPPORTED", "reason": "not required"},
        },
    }


@pytest.mark.parametrize(
    ("delta", "expected"),
    [(0.000999, True), (0.001, True), (0.001001, False)],
)
def test_tolerance_boundary_is_inclusive(delta: float, expected: bool) -> None:
    assert within_tolerance(delta, _tolerance(0.001, "mm"), "mm") is expected


@pytest.mark.parametrize("invalid", [True, False, float("nan"), float("inf")])
def test_tolerance_rejects_boolean_and_nonfinite_measurements(invalid: object) -> None:
    with pytest.raises(ValueError, match="finite"):
        within_tolerance(invalid, _tolerance(0.001, "mm"), "mm")


def test_tolerance_rejects_wrong_unit() -> None:
    with pytest.raises(ValueError, match="unit"):
        within_tolerance(0.0005, _tolerance(0.001, "mm3"), "mm")


def test_semantics_support_only_the_fixture_binding() -> None:
    binding = _binding()

    assert compare_semantics(binding, dict(binding)) == {
        "status": "SEMANTIC_EQUIVALENT",
        "differences": [],
    }

    changed = dict(binding)
    changed["interface_role"] = "outer_wall"
    assert compare_semantics(binding, changed) == {
        "status": "SEMANTIC_DIFFERENT",
        "differences": ["interface_role"],
    }


def test_missing_fixture_semantics_fail_closed() -> None:
    missing = _binding()
    del missing["interface_role"]

    assert compare_semantics(_binding(), missing) == {
        "status": "SEMANTIC_EQUIVALENCE_NOT_PROVEN",
        "differences": [],
        "reason": "required fixture semantic binding is missing or unsupported",
    }


def test_ui_difference_is_reported_only_in_ui_domain() -> None:
    first = _ui_snapshot()
    second = _ui_snapshot(
        visibility=False,
        color=[0.2, 0.4, 0.8],
        transparency=60,
    )

    result = compare_ui_states(first, second)

    assert result == {
        "status": "UI_DIFFERENT",
        "differences": ["shape_color", "transparency", "visibility"],
    }
    assert "geometry" not in result


def test_equal_supported_ui_state_is_ui_same() -> None:
    snapshot = _ui_snapshot()

    assert compare_ui_states(snapshot, deepcopy(snapshot)) == {
        "status": "UI_SAME",
        "differences": [],
    }


def test_missing_required_saved_ui_state_is_not_proven() -> None:
    unsupported = _ui_snapshot()
    unsupported["state"]["shape_color"] = {  # type: ignore[index]
        "status": "UNSUPPORTED",
        "reason": "GUI state was not available after reopen",
    }

    assert compare_ui_states(_ui_snapshot(), unsupported) == {
        "status": "UI_COMPARISON_NOT_PROVEN",
        "differences": [],
        "reason": "required saved UI state is unavailable",
    }
