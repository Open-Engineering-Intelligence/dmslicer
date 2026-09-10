"""Pure-Python CAD evidence comparison core for P2-MVP."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

import hashlib
import json


class _ComparableStr(str):
    """Small helper to keep stable comparison semantics in enums."""


BYTE_IDENTICAL = _ComparableStr("BYTE_IDENTICAL")
BYTE_DIFFERENT = _ComparableStr("BYTE_DIFFERENT")
TOLERANCE_ARE_UNITS_INCOMPATIBLE = _ComparableStr("TOLERANCE_ARE_UNITS_INCOMPATIBLE")

SEMANTIC_EQUIVALENT = _ComparableStr("SEMANTIC_EQUIVALENT")
SEMANTIC_DIFFERENT = _ComparableStr("SEMANTIC_DIFFERENT")
SEMANTIC_EQUIVALENCE_NOT_PROVEN = _ComparableStr("SEMANTIC_EQUIVALENCE_NOT_PROVEN")

UI_SAME = _ComparableStr("UI_SAME")
UI_DIFFERENT = _ComparableStr("UI_DIFFERENT")
UI_COMPARISON_NOT_PROVEN = _ComparableStr("UI_COMPARISON_NOT_PROVEN")

GEOMETRY_UNKNOWN = _ComparableStr("UNKNOWN")
GEOMETRY_UNSUPPORTED = _ComparableStr("UNSUPPORTED")
GEOMETRY_NOT_PROVEN = _ComparableStr("NOT_PROVEN")


_SUPPORTED_COMPONENT_ROLE = "fixture_body"
_SUPPORTED_INTERFACE_ROLE = "through_hole_wall"
_SUPPORTED_TRANSFORM = "IDENTITY"


def _read_bytes(source: bytes | str | Path) -> bytes:
    if isinstance(source, bytes):
        return source
    path = Path(source)
    return path.read_bytes()


def compare_byte_identity(left: bytes | str | Path, right: bytes | str | Path) -> str:
    """Pure byte identity check that intentionally returns only byte outcomes."""
    return (
        BYTE_IDENTICAL
        if hashlib.sha256(_read_bytes(left)).hexdigest()
        == hashlib.sha256(_read_bytes(right)).hexdigest()
        else BYTE_DIFFERENT
    )


@dataclass(frozen=True)
class ContinuousMeasurement:
    value: float
    unit: str


def _as_measurement(value: float | ContinuousMeasurement) -> ContinuousMeasurement:
    if isinstance(value, ContinuousMeasurement):
        return value
    if not isinstance(value, (float, int)):
        raise TypeError("measurement must be a float, int, or ContinuousMeasurement")
    return ContinuousMeasurement(float(value), "unitless")


def _normalize_snapshot(snapshot: Mapping[str, Any]) -> Any:
    if isinstance(snapshot, Mapping):
        normalized = {}
        for key in sorted(snapshot):
            normalized[key] = _normalize_snapshot(snapshot[key])
        return normalized
    if isinstance(snapshot, (list, tuple)):
        normalized_items = [_normalize_snapshot(item) for item in snapshot]
        # Keep existing order in list containers, but make dict-like items deterministic
        return [
            item if not isinstance(item, dict) else _sort_dict_repr(item) for item in normalized_items
        ]
    return snapshot


def _sort_dict_repr(item: dict[str, Any]) -> dict[str, Any]:
    return {
        key: _normalize_snapshot(value) for key, value in sorted(item.items(), key=lambda kv: kv[0])
    }


def compare_semantic_equivalence(
    left: Mapping[str, Any],
    right: Mapping[str, Any],
    *,
    allowed_transform: str = _SUPPORTED_TRANSFORM,
) -> str:
    """Compare minimal semantic snapshot payload.

    This MVP only supports fixture body vs through-hole-wall fixtures and identity
    transforms. Any unsupported role or transform is intentionally returned as
    NOT_PROVEN.
    """

    if not isinstance(left, Mapping) or not isinstance(right, Mapping):
        raise TypeError("semantic snapshots must be mappings")

    left_component_role = left.get("component_role")
    right_component_role = right.get("component_role")
    left_interface_role = left.get("interface_role")
    right_interface_role = right.get("interface_role")

    if (
        left_component_role != _SUPPORTED_COMPONENT_ROLE
        or right_component_role != _SUPPORTED_COMPONENT_ROLE
        or left_interface_role != _SUPPORTED_INTERFACE_ROLE
        or right_interface_role != _SUPPORTED_INTERFACE_ROLE
    ):
        return SEMANTIC_EQUIVALENCE_NOT_PROVEN

    left_transform = left.get("transform", _SUPPORTED_TRANSFORM)
    right_transform = right.get("transform", _SUPPORTED_TRANSFORM)
    if isinstance(left_transform, Mapping):
        left_transform = left_transform.get("type", _SUPPORTED_TRANSFORM)
    if isinstance(right_transform, Mapping):
        right_transform = right_transform.get("type", _SUPPORTED_TRANSFORM)

    if (
        allowed_transform != _SUPPORTED_TRANSFORM
        or left_transform != _SUPPORTED_TRANSFORM
        or right_transform != _SUPPORTED_TRANSFORM
    ):
        return SEMANTIC_EQUIVALENCE_NOT_PROVEN

    compare_fields = ("component_role", "interface_role", "regions", "interface_pairs", "source_boundaries")
    left_signature = {
        field: _normalize_snapshot(left[field]) if field in left else None for field in compare_fields
    }
    right_signature = {
        field: _normalize_snapshot(right[field]) if field in right else None for field in compare_fields
    }

    return SEMANTIC_EQUIVALENT if left_signature == right_signature else SEMANTIC_DIFFERENT


def _normalize_float(value: Any) -> float:
    if isinstance(value, bool):
        raise TypeError("color/transparency value must be numeric, not bool")
    if isinstance(value, (int, float)):
        return float(value)
    raise TypeError(f"invalid scalar value: {type(value)!r}")


def _normalize_color(color: Any) -> tuple[float, ...]:
    if isinstance(color, Mapping):
        candidates = [color.get(axis) for axis in ("r", "g", "b", "a")]
        candidates = [value for value in candidates if value is not None]
        if len(candidates) == 0:
            return ()
        return tuple(_normalize_float(value) for value in candidates)
    if isinstance(color, (list, tuple)) and 0 < len(color) <= 4:
        return tuple(_normalize_float(value) for value in color)
    if isinstance(color, str):
        normalized = color.lstrip("#")
        if len(normalized) in {6, 8} and all(c in "0123456789abcdefABCDEF" for c in normalized):
            chunks = [normalized[i : i + 2] for i in range(0, len(normalized), 2)]
            return tuple(int(chunk, 16) / 255.0 for chunk in chunks)
    raise TypeError("unsupported color representation")


def compare_ui_state(left: Mapping[str, Any], right: Mapping[str, Any]) -> str:
    """Compare only visibility, color, and transparency for this MVP."""

    if not isinstance(left, Mapping) or not isinstance(right, Mapping):
        raise TypeError("ui state snapshots must be mappings")

    if (
        "visibility" not in left
        or "visibility" not in right
        or "color" not in left
        or "color" not in right
        or "transparency" not in left
        or "transparency" not in right
    ):
        return UI_COMPARISON_NOT_PROVEN

    if left.get("visibility") != right.get("visibility"):
        return UI_DIFFERENT

    if _normalize_color(left["color"]) != _normalize_color(right["color"]):
        return UI_DIFFERENT

    try:
        left_trans = _normalize_float(left["transparency"])
        right_trans = _normalize_float(right["transparency"])
    except TypeError:
        return UI_COMPARISON_NOT_PROVEN

    return UI_SAME if left_trans == right_trans else UI_DIFFERENT


def within_tolerance(
    actual: float | ContinuousMeasurement,
    expected: float | ContinuousMeasurement,
    tolerance: float | ContinuousMeasurement,
) -> bool:
    """Compare two real measurements with explicit value+unit semantics.

    Units must match; tolerance comparison is strict and symmetric.
    """

    actual_measurement = _as_measurement(actual)
    expected_measurement = _as_measurement(expected)
    tolerance_measurement = _as_measurement(tolerance)

    if actual_measurement.unit != expected_measurement.unit:
        raise ValueError(f"measurement units differ: {actual_measurement.unit} vs {expected_measurement.unit}")
    if tolerance_measurement.value < 0:
        raise ValueError("tolerance must be non-negative")
    if tolerance_measurement.unit != expected_measurement.unit:
        raise ValueError(
            f"tolerance unit mismatch: {tolerance_measurement.unit} != {expected_measurement.unit}"
        )

    delta = abs(actual_measurement.value - expected_measurement.value)
    return delta <= tolerance_measurement.value


def _manifest_to_json_lines(manifest: Mapping[str, Any]) -> str:
    """Utility helper for stable manifest serialization in tests or diagnostics."""
    return json.dumps(manifest, indent=2, sort_keys=True, ensure_ascii=False)

