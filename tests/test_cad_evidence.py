from __future__ import annotations

from pathlib import Path
import sys


ROOT_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from dmslicer.evidence_promotion import (  # noqa: E402
    BYTE_DIFFERENT,
    BYTE_IDENTICAL,
    SEMANTIC_EQUIVALENT,
    SEMANTIC_DIFFERENT,
    SEMANTIC_EQUIVALENCE_NOT_PROVEN,
    UI_SAME,
    UI_DIFFERENT,
    UI_COMPARISON_NOT_PROVEN,
    compare_byte_identity,
    compare_semantic_equivalence,
    compare_ui_state,
    within_tolerance,
    ContinuousMeasurement,
)


def test_byte_identity_identical():
    assert compare_byte_identity(b"fixture", b"fixture") == BYTE_IDENTICAL


def test_byte_identity_different():
    assert compare_byte_identity(b"fixture-a", b"fixture-b") == BYTE_DIFFERENT


def test_semantic_equivalence_supports_current_fixture_roles():
    left = {
        "component_role": "fixture_body",
        "interface_role": "through_hole_wall",
        "transform": "IDENTITY",
        "regions": [{"id": "G", "faces": ["G:x_min"]}],
    }
    right = {
        "component_role": "fixture_body",
        "interface_role": "through_hole_wall",
        "transform": "IDENTITY",
        "regions": [{"id": "G", "faces": ["G:x_min"]}],
    }

    assert compare_semantic_equivalence(left, right) == SEMANTIC_EQUIVALENT


def test_semantic_equivalence_not_proven_for_unsupported_roles():
    left = {
        "component_role": "legacy_body",
        "interface_role": "through_hole_wall",
        "transform": "IDENTITY",
    }
    right = {
        "component_role": "legacy_body",
        "interface_role": "through_hole_wall",
        "transform": "IDENTITY",
    }

    assert compare_semantic_equivalence(left, right) == SEMANTIC_EQUIVALENCE_NOT_PROVEN


def test_semantic_equivalence_not_proven_for_non_identity_transform():
    left = {
        "component_role": "fixture_body",
        "interface_role": "through_hole_wall",
        "transform": "ROTATE_Z_90",
    }
    right = left

    assert compare_semantic_equivalence(left, right) == SEMANTIC_EQUIVALENCE_NOT_PROVEN


def test_ui_state_same_and_different():
    base = {"visibility": True, "color": [0.1, 0.2, 0.3], "transparency": 0.0}
    equal = {"visibility": True, "color": [0.1, 0.2, 0.3], "transparency": 0.0}
    changed = {"visibility": False, "color": [0.1, 0.2, 0.3], "transparency": 0.2}

    assert compare_ui_state(base, equal) == UI_SAME
    assert compare_ui_state(base, changed) == UI_DIFFERENT


def test_ui_state_not_proven_when_missing_fields():
    base = {"visibility": True}

    assert compare_ui_state(base, base) == UI_COMPARISON_NOT_PROVEN


def test_tolerance_helper_inside_boundary_and_outside():
    expected = ContinuousMeasurement(5.0, "mm2")
    assert within_tolerance(ContinuousMeasurement(4.9, "mm2"), expected, ContinuousMeasurement(0.1, "mm2"))
    assert within_tolerance(ContinuousMeasurement(4.95, "mm2"), expected, ContinuousMeasurement(0.05, "mm2"))
    assert within_tolerance(ContinuousMeasurement(5.0, "mm2"), expected, ContinuousMeasurement(0.0, "mm2"))
    assert not within_tolerance(
        ContinuousMeasurement(4.899, "mm2"), expected, ContinuousMeasurement(0.1, "mm2")
    )
