"""CAD evidence comparison helpers."""

from .cad_evidence import (
    TOLERANCE_ARE_UNITS_INCOMPATIBLE,
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

SCHEMA_VERSION = "2.0.0"

__all__ = [
    "TOLERANCE_ARE_UNITS_INCOMPATIBLE",
    "BYTE_DIFFERENT",
    "BYTE_IDENTICAL",
    "SEMANTIC_EQUIVALENT",
    "SEMANTIC_DIFFERENT",
    "SEMANTIC_EQUIVALENCE_NOT_PROVEN",
    "UI_SAME",
    "UI_DIFFERENT",
    "UI_COMPARISON_NOT_PROVEN",
    "compare_byte_identity",
    "compare_semantic_equivalence",
    "compare_ui_state",
    "within_tolerance",
    "ContinuousMeasurement",
    "SCHEMA_VERSION",
]
