"""Load and apply the GeometrySnapshot and SlicerDecision JSON schemas."""

from __future__ import annotations

import json
from dataclasses import dataclass
from importlib.resources import files
from typing import Any, Literal, Mapping

from jsonschema import Draft202012Validator

GEOMETRY_CONTRACT_NAME = "dmslicer.geometry-snapshot"
GEOMETRY_RC_VERSION = "0.1-rc1"
GEOMETRY_RELEASE_VERSION = "0.1.0"
CURRENT_GEOMETRY_VERSION = GEOMETRY_RC_VERSION
SLICER_CONTRACT_NAME = "dmslicer.slicer-decision"

SchemaName = Literal["geometry_snapshot", "slicer_decision"]
_SCHEMA_FILES: dict[SchemaName, str] = {
    "geometry_snapshot": "geometry_snapshot.v0.1.schema.json",
    "slicer_decision": "slicer_decision.v0.1.schema.json",
}


@dataclass(frozen=True)
class SchemaIssue:
    code: str
    path: str
    message: str


def load_schema(name: SchemaName) -> Mapping[str, Any]:
    try:
        filename = _SCHEMA_FILES[name]
    except KeyError as error:
        raise ValueError(f"unknown contract schema: {name}") from error
    resource = files("dmslicer.geometry_contract.schemas").joinpath(filename)
    return json.loads(resource.read_text(encoding="utf-8"))


def schema_errors(
    value: Mapping[str, Any], *, schema_name: SchemaName
) -> tuple[SchemaIssue, ...]:
    validator = Draft202012Validator(load_schema(schema_name))
    errors = sorted(
        validator.iter_errors(value),
        key=lambda error: tuple(str(component) for component in error.absolute_path),
    )
    return tuple(
        SchemaIssue(
            code="SCHEMA_INVALID",
            path=".".join(str(component) for component in error.absolute_path) or "$",
            message=error.message,
        )
        for error in errors
    )
