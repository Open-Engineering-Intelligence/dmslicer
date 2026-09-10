"""Fixture-scoped CAD evidence validation and comparison helpers."""

from __future__ import annotations

import math
from typing import Any, Mapping

from jsonschema import Draft202012Validator

from .models import (
    SEMANTIC_DIFFERENT,
    SEMANTIC_EQUIVALENCE_NOT_PROVEN,
    SEMANTIC_EQUIVALENT,
    UI_COMPARISON_NOT_PROVEN,
    UI_DIFFERENT,
    UI_SAME,
    read_json,
    schema_path,
)


_SEMANTIC_FIELDS = ("component_role", "interface_role", "allowed_transform")
_UI_FIELDS = ("shape_color", "transparency", "visibility")


def _nonfinite_paths(value: Any, path: tuple[str, ...] = ()):
    if isinstance(value, float) and not math.isfinite(value):
        yield ".".join(path) or "artifact"
    elif isinstance(value, Mapping):
        for key, item in value.items():
            yield from _nonfinite_paths(item, (*path, str(key)))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            yield from _nonfinite_paths(item, (*path, str(index)))


def _leaf_errors(error):
    if error.context:
        for child in error.context:
            yield from _leaf_errors(child)
    else:
        yield error


def _error_path(error) -> str:
    parts = [str(part) for part in error.absolute_path]
    if error.validator == "required" and isinstance(error.instance, Mapping):
        missing = [name for name in error.validator_value if name not in error.instance]
        if len(missing) == 1:
            parts.append(missing[0])
    return ".".join(parts) or "artifact"


def validate_cad_artifact(value: Mapping[str, Any]) -> list[str]:
    """Return deterministic public-safe validation findings for one CAD artifact."""
    schema = read_json(schema_path("cad_evidence.schema.json"))
    validator = Draft202012Validator(schema)
    findings = []
    errors = [leaf for error in validator.iter_errors(value) for leaf in _leaf_errors(error)]
    for error in sorted(errors, key=lambda item: list(item.absolute_path)):
        findings.append(f"{_error_path(error)}: {error.message}")
    findings.extend(f"{path}: numeric evidence must be finite" for path in _nonfinite_paths(value))
    return sorted(set(findings))


def within_tolerance(
    measured: float, tolerance: Mapping[str, Any], expected_unit: str
) -> bool:
    """Apply an inclusive, unit-checked tolerance to one finite delta."""
    limit = tolerance.get("value")
    if (
        isinstance(measured, bool)
        or isinstance(limit, bool)
        or not isinstance(measured, (int, float))
        or not isinstance(limit, (int, float))
        or not math.isfinite(float(measured))
        or not math.isfinite(float(limit))
        or float(limit) < 0.0
    ):
        raise ValueError("tolerance inputs must be finite numbers with a nonnegative limit")
    if tolerance.get("unit") != expected_unit:
        raise ValueError("tolerance unit does not match measurement")
    return abs(float(measured)) <= float(limit)


def compare_semantics(
    first: Mapping[str, Any], second: Mapping[str, Any]
) -> dict[str, Any]:
    """Compare only the three explicit semantic fields used by the P2 fixture."""
    if any(
        not isinstance(binding.get(field), str) or not binding.get(field)
        for binding in (first, second)
        for field in _SEMANTIC_FIELDS
    ):
        return {
            "status": SEMANTIC_EQUIVALENCE_NOT_PROVEN,
            "differences": [],
            "reason": "required fixture semantic binding is missing or unsupported",
        }
    differences = sorted(field for field in _SEMANTIC_FIELDS if first[field] != second[field])
    return {
        "status": SEMANTIC_DIFFERENT if differences else SEMANTIC_EQUIVALENT,
        "differences": differences,
    }


def compare_ui_states(
    first: Mapping[str, Any], second: Mapping[str, Any]
) -> dict[str, Any]:
    """Compare saved fixture UI properties without emitting a geometry decision."""
    states = (first.get("state"), second.get("state"))
    if not all(isinstance(state, Mapping) for state in states):
        return {
            "status": UI_COMPARISON_NOT_PROVEN,
            "differences": [],
            "reason": "required saved UI state is unavailable",
        }
    for state in states:
        assert isinstance(state, Mapping)
        for field in _UI_FIELDS:
            value = state.get(field)
            if not isinstance(value, Mapping) or value.get("status") != "SUPPORTED" or "value" not in value:
                return {
                    "status": UI_COMPARISON_NOT_PROVEN,
                    "differences": [],
                    "reason": "required saved UI state is unavailable",
                }
    first_state, second_state = states
    assert isinstance(first_state, Mapping) and isinstance(second_state, Mapping)
    differences = sorted(
        field
        for field in _UI_FIELDS
        if first_state[field]["value"] != second_state[field]["value"]
    )
    return {"status": UI_DIFFERENT if differences else UI_SAME, "differences": differences}
