from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import subprocess

from jsonschema import Draft202012Validator, ValidationError
import pytest

from dmslicer.evidence_promotion.models import read_json, schema_path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
HISTORICAL_SCHEMA = REPOSITORY_ROOT / "docs/evidence_preservation/evidence_manifest.schema.json"
HISTORICAL_MANIFESTS = REPOSITORY_ROOT / "docs/evidence_preservation/manifests"


def test_stable_evidence_disables_git_line_ending_conversion() -> None:
    completed = subprocess.run(
        ["git", "check-attr", "text", "--", "evidence/P2-MVP/probe.txt"],
        cwd=REPOSITORY_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )

    assert completed.stdout.strip().endswith(": unset")


def _validator(name: str) -> Draft202012Validator:
    schema = read_json(schema_path(name))
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema)


def test_historical_manifests_remain_valid() -> None:
    schema = json.loads(HISTORICAL_SCHEMA.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    validator = Draft202012Validator(schema)
    manifests = sorted(HISTORICAL_MANIFESTS.glob("goal-*.json"))

    assert len(manifests) == 13
    for manifest in manifests:
        validator.validate(json.loads(manifest.read_text(encoding="utf-8")))


def test_valid_mvp_request_requires_unproven_geometry(valid_request) -> None:
    request = valid_request()

    _validator("promotion_request.schema.json").validate(request)

    assert request["results"]["geometry_equivalence_result"] == {
        "status": "GEOMETRIC_EQUIVALENCE_NOT_PROVEN",
        "evidence_artifact_ids": [],
    }
    assert request["geometry_validation"]["evidence_artifact_ids"] == []


def test_valid_generated_manifest_keeps_package_preservation_and_publication_separate(
    valid_manifest,
) -> None:
    manifest = valid_manifest()

    _validator("evidence_manifest.v2.schema.json").validate(manifest)

    assert manifest["local_package_result"]["status"] == "LOCAL_PACKAGE_CREATED"
    assert manifest["preservation_result"]["status"] == "NOT_FULLY_PRESERVED"
    assert manifest["publication_result"]["status"] == "PUBLICATION_NOT_AUTHORIZED"


def test_request_schema_accepts_snapshot_and_cad_artifact_kinds(valid_request) -> None:
    request = valid_request()
    request["source"]["allowlist"].extend(
        [
            {
                "artifact_id": "case-a-geometry",
                "source_path": "validator-result.json",
                "public_path": "cad/case_a_geometry_snapshot.json",
                "kind": "GEOMETRY_SNAPSHOT",
                "validation_role": "geometry snapshot evidence",
                "retention_role": "STANDARD",
            },
            {
                "artifact_id": "case-a-step",
                "source_path": "validator-result.json",
                "public_path": "cad/case_a.step",
                "kind": "STEP",
                "validation_role": "case a step export",
                "retention_role": "STANDARD",
            },
            {
                "artifact_id": "case-a-view-index",
                "source_path": "validator-result.json",
                "public_path": "cad/VIEW_INDEX.md",
                "kind": "VIEW_INDEX",
                "validation_role": "human-view index",
                "retention_role": "STANDARD",
            },
            {
                "artifact_id": "case-a-human",
                "source_path": "validator-result.json",
                "public_path": "cad/HUMAN_REVIEW.md",
                "kind": "HUMAN_REVIEW",
                "validation_role": "human review note",
                "retention_role": "STANDARD",
            },
        ]
    )

    _validator("promotion_request.schema.json").validate(request)


def test_manifest_allows_byte_difference_without_geometry_claim(valid_manifest) -> None:
    manifest = valid_manifest()
    manifest["results"]["byte_identity_result"] = {
        "status": "BYTE_DIFFERENT",
        "evidence_artifact_ids": ["validator-result"],
    }

    _validator("evidence_manifest.v2.schema.json").validate(manifest)

    assert manifest["geometry_validation"]["status"] == "GEOMETRIC_EQUIVALENCE_NOT_PROVEN"


@pytest.mark.parametrize(
    "mutation",
    [
        "missing_implementation_commit",
        "invalid_run_id",
        "missing_tolerance_unit",
        "unknown_property",
        "geometry_pass",
        "geometry_evidence",
        "collapsed_result_status",
    ],
)
def test_request_schema_rejects_incomplete_or_claiming_input(valid_request, mutation: str) -> None:
    request = valid_request()
    if mutation == "missing_implementation_commit":
        del request["identity"]["implementation_commit"]
    elif mutation == "invalid_run_id":
        request["run_id"] = "../escape"
    elif mutation == "missing_tolerance_unit":
        request["tolerances"] = [
            {"name": "linear", "value": 1e-7, "role": "comparison", "source": "policy"}
        ]
    elif mutation == "unknown_property":
        request["geometry_hash_is_truth"] = True
    elif mutation == "geometry_pass":
        request["results"]["geometry_equivalence_result"]["status"] = "GEOMETRY_EQUIVALENT"
    elif mutation == "collapsed_result_status":
        request["results"]["pytest_result"]["status"] = "GEOMETRY_EQUIVALENT"
    else:
        request["geometry_validation"]["evidence_artifact_ids"] = ["validator-result"]

    with pytest.raises(ValidationError):
        _validator("promotion_request.schema.json").validate(request)


def test_deterministic_json_writer_sorts_keys_and_terminates_line(tmp_path: Path) -> None:
    from dmslicer.evidence_promotion.models import write_json

    output = tmp_path / "evidence.json"
    write_json(output, {"z": 1, "a": {"d": 2, "b": 3}})

    assert output.read_text(encoding="utf-8") == (
        '{\n  "a": {\n    "b": 3,\n    "d": 2\n  },\n  "z": 1\n}\n'
    )
