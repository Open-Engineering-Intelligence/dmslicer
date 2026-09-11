from __future__ import annotations

from pathlib import Path
import json

import pytest
import jsonschema


ROOT_DIR = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT_DIR / "docs" / "evidence_preservation" / "schemas" / "cad_evidence.schema.json"


def _load_schema():
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def test_cad_evidence_schema_accepts_expected_structure():
    schema = _load_schema()
    validator = jsonschema.Draft202012Validator(schema)

    manifest = {
        "schema_version": 1,
        "goal_id": "p2_cad_evidence_mvp",
        "run_id": "run_001",
        "geometry_semantic_snapshot": {
            "component_role": "fixture_body",
            "interface_role": "through_hole_wall",
            "source_regions": ["A", "G", "B"],
            "source_faces": ["A:x_max", "G:x_min", "G:x_max", "B:x_min"],
        },
        "topology_snapshot": {
            "solid_volume": {"value": 4000.0, "unit": "mm3"},
            "solid_area": {"value": 1200.0, "unit": "mm2"},
            "component_count": 3,
        },
        "ui_state_snapshot": {
            "visibility": True,
            "color": [1.0, 0.0, 0.0],
            "transparency": 0.0,
        },
        "geometry_comparison": {
            "byte_identity": "BYTE_IDENTICAL",
            "byte_identity_input": {
                "input_sha256_left": "0" * 64,
                "input_sha256_right": "0" * 64,
            },
            "semantic_comparison": "SEMANTIC_EQUIVALENT",
            "topology_comparison": "TOPOLOGY_COMPARISON_NOT_PROVEN",
            "ui_comparison": "UI_SAME",
        },
    }

    validator.validate(manifest)


def test_cad_evidence_schema_rejects_missing_measurement_unit():
    schema = _load_schema()
    validator = jsonschema.Draft202012Validator(schema)

    invalid_manifest = {
        "schema_version": 1,
        "topology_snapshot": {
            "solid_volume": {"value": 1.0}
        },
    }

    with pytest.raises(jsonschema.ValidationError):
        validator.validate(invalid_manifest)


def test_cad_evidence_schema_supports_unknown_and_not_proven_states():
    schema = _load_schema()
    validator = jsonschema.Draft202012Validator(schema)

    manifest = {
        "schema_version": 1,
        "geometry_comparison": {
            "byte_identity": "UNKNOWN",
            "byte_identity_input": {
                "input_sha256_left": "1" * 64,
                "input_sha256_right": "2" * 64,
            },
            "semantic_comparison": "NOT_PROVEN",
            "topology_comparison": "UNSUPPORTED",
            "ui_comparison": "UI_COMPARISON_NOT_PROVEN",
        },
    }

    validator.validate(manifest)


def test_cad_evidence_schema_rejects_sha_as_geometry_predicate():
    schema = _load_schema()
    validator = jsonschema.Draft202012Validator(schema)

    invalid_manifest = {
        "schema_version": 1,
        "topology_snapshot": {
            "solids_sha256": "abc",
            "solid_volume": {"value": 1.0, "unit": "mm3"},
        },
    }

    with pytest.raises(jsonschema.ValidationError):
        validator.validate(invalid_manifest)


def test_cad_evidence_schema_accepts_policy_consumed_artifact_envelopes(
    valid_cad_request, repository_root: Path
) -> None:
    schema = _load_schema()
    validator = jsonschema.Draft202012Validator(schema)
    request = valid_cad_request()
    staging_root = repository_root / request["source"]["staging_root"]

    for artifact in request["source"]["allowlist"]:
        value = json.loads(
            (staging_root / artifact["source_path"]).read_text(encoding="utf-8")
        )
        validator.validate(value)

