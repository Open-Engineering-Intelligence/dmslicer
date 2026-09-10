"""Shared deterministic evidence representations."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
SCHEMA_DIRECTORY = REPOSITORY_ROOT / "docs" / "evidence_preservation" / "schemas"

BYTE_SAME = "BYTE_SAME"
BYTE_DIFFERENT = "BYTE_DIFFERENT"
BYTE_NOT_EVALUATED = "BYTE_NOT_EVALUATED"
GEOMETRIC_EQUIVALENCE_NOT_PROVEN = "GEOMETRIC_EQUIVALENCE_NOT_PROVEN"
GEOMETRY_EQUIVALENT = "GEOMETRY_EQUIVALENT"
GEOMETRY_DIFFERENT = "GEOMETRY_DIFFERENT"
SEMANTIC_EQUIVALENCE_NOT_PROVEN = "SEMANTIC_EQUIVALENCE_NOT_PROVEN"
SEMANTIC_EQUIVALENT = "SEMANTIC_EQUIVALENT"
SEMANTIC_DIFFERENT = "SEMANTIC_DIFFERENT"
UI_STATE_NOT_PROVEN = "UI_STATE_NOT_PROVEN"
UI_COMPARISON_NOT_PROVEN = "UI_COMPARISON_NOT_PROVEN"
UI_SAME = "UI_SAME"
UI_DIFFERENT = "UI_DIFFERENT"
LOCAL_PACKAGE_CREATED = "LOCAL_PACKAGE_CREATED"
LOCAL_PACKAGE_BLOCKED = "LOCAL_PACKAGE_BLOCKED"
NOT_FULLY_PRESERVED = "NOT_FULLY_PRESERVED"
FULLY_PRESERVED = "FULLY_PRESERVED"
PUBLICATION_NOT_AUTHORIZED = "PUBLICATION_NOT_AUTHORIZED"
PUBLICATION_BLOCKED_OFF_HOST_COPY = "PUBLICATION_BLOCKED_OFF_HOST_COPY"
LOCAL_TWO_PATHS_NOT_OFF_HOST_REDUNDANCY = "LOCAL_TWO_PATHS_NOT_OFF_HOST_REDUNDANCY"


def write_json(path: Path, value: Mapping[str, Any]) -> None:
    """Write stable, readable JSON suitable for evidence artifacts."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def schema_path(name: str) -> Path:
    path = SCHEMA_DIRECTORY / name
    if not path.is_file():
        raise FileNotFoundError(f"Evidence schema does not exist: {name}")
    return path
