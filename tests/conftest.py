from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import subprocess

import pytest


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]


def _head() -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=REPOSITORY_ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _base_request() -> dict:
    head = _head()
    return {
        "schema_version": "2.0.0",
        "goal_id": "P2-MVP",
        "run_id": "p2-mvp-test-001",
        "identity": {
            "branch": "feat/evidence-promotion-semantic-snapshot",
            "implementation_commit": head,
            "parent_baseline": head,
            "merge_base": head,
        },
        "source": {
            "staging_root": "outputs/p2-mvp-test-001",
            "allowlist": [
                {
                    "artifact_id": "validator-result",
                    "source_path": "validator-result.json",
                    "public_path": "artifacts/validator-result.json",
                    "kind": "VALIDATOR",
                    "validation_role": "software_validator_result",
                    "retention_role": "STANDARD",
                }
            ],
        },
        "environment": {
            "python_version": "3.12.0",
            "pytest_version": "8.4.2",
            "freecad_version": None,
            "occt_version": None,
        },
        "execution": [
            {
                "command": "py -3.12 -m pytest -q",
                "exit_code": 0,
                "timestamp": "2026-09-10T12:00:00+08:00",
            }
        ],
        "tolerances": [],
        "results": {
            "byte_identity_result": {
                "status": "BYTE_NOT_EVALUATED",
                "evidence_artifact_ids": [],
            },
            "geometry_equivalence_result": {
                "status": "GEOMETRIC_EQUIVALENCE_NOT_PROVEN",
                "evidence_artifact_ids": [],
            },
            "semantic_equivalence_result": {
                "status": "SEMANTIC_EQUIVALENCE_NOT_PROVEN",
                "evidence_artifact_ids": [],
            },
            "ui_state_result": {
                "status": "UI_STATE_NOT_PROVEN",
                "evidence_artifact_ids": [],
            },
            "pytest_result": {
                "status": "NOT_EVALUATED",
                "evidence_artifact_ids": [],
            },
            "validator_result": {
                "status": "PASS",
                "evidence_artifact_ids": ["validator-result"],
            },
            "scientific_experiment_result": {
                "status": "NOT_EVALUATED",
                "evidence_artifact_ids": [],
            },
            "human_inspection_result": {
                "status": "NOT_EVALUATED",
                "evidence_artifact_ids": [],
            },
        },
        "history": {
            "failure_artifact_ids": [],
            "mismatch_artifact_ids": [],
            "rejection_artifact_ids": [],
            "reviewer_finding_artifact_ids": [],
        },
        "custody": {"off_host_copies": [], "publication_authorized": False},
        "geometry_validation": {
            "status": "GEOMETRIC_EQUIVALENCE_NOT_PROVEN",
            "evidence_method": "NOT_EVALUATED_P2_MVP",
            "evidence_artifact_ids": [],
            "sha256_role": "file_and_copy_integrity_only_not_geometry_equivalence",
        },
    }


@pytest.fixture
def valid_request():
    def factory() -> dict:
        return deepcopy(_base_request())

    return factory


@pytest.fixture
def valid_manifest(valid_request):
    def factory() -> dict:
        request = valid_request()
        manifest = {
            **{key: request[key] for key in (
                "schema_version", "goal_id", "run_id", "identity", "environment",
                "execution", "tolerances", "results", "history", "geometry_validation",
            )},
            "source_staging_root": request["source"]["staging_root"],
            "artifacts": [
                {
                    "artifact_id": "validator-result",
                    "kind": "VALIDATOR",
                    "public_path": "artifacts/validator-result.json",
                    "sha256": "0" * 64,
                    "size_bytes": 2,
                    "validation_role": "software_validator_result",
                    "retention_role": "STANDARD",
                    "copy_status": "BYTE_SAME",
                }
            ],
            "local_package_result": {
                "status": "LOCAL_PACKAGE_CREATED",
                "package_path": "evidence/P2-MVP/" + request["identity"]["implementation_commit"] + "/p2-mvp-test-001",
            },
            "preservation_result": {
                "status": "NOT_FULLY_PRESERVED",
                "recoverable_copy_count": 2,
                "recoverable_copy_policy": "LOCAL_TWO_PATHS_NOT_OFF_HOST_REDUNDANCY",
            },
            "publication_result": {
                "status": "PUBLICATION_NOT_AUTHORIZED",
                "off_host_copy_count": 0,
            },
            "policy_result": {"status": "PASS", "findings": []},
        }
        manifest["results"] = deepcopy(manifest["results"])
        manifest["results"]["byte_identity_result"] = {
            "status": "BYTE_SAME",
            "evidence_artifact_ids": ["validator-result"],
        }
        return manifest

    return factory


def write_request(path: Path, value: dict) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
    return path


def _git(repository: Path, *arguments: str) -> str:
    return subprocess.run(
        ["git", *arguments],
        cwd=repository,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _geometry_snapshot(case_id: str) -> dict:
    count = lambda value: {"value": value, "unit": "count"}
    measure = lambda value, unit: {"value": value, "unit": unit}
    return {
        "schema_version": "1.0.0",
        "artifact_type": "geometry_semantic_snapshot",
        "case_id": case_id,
        "artifact_role": "CLOSING",
        "source_artifact_id": f"p2-fixture/{case_id}/fixture.FCStd",
        "length_unit": "mm",
        "semantic_binding": {
            "component_role": "fixture_body",
            "interface_role": "through_hole_wall",
            "allowed_transform": "IDENTITY",
        },
        "shape": {
            "solid_count": count(1),
            "shell_count": count(1),
            "face_count": count(7),
            "edge_count": count(18),
            "vertex_count": count(12),
            "area": measure(4396.991118, "mm2"),
            "volume": measure(13796.106156, "mm3"),
            "bounding_box": {
                "x_min": measure(0.0, "mm"),
                "y_min": measure(0.0, "mm"),
                "z_min": measure(0.0, "mm"),
                "x_max": measure(40.0, "mm"),
                "y_max": measure(30.0, "mm"),
                "z_max": measure(12.0, "mm"),
            },
            "valid": True,
            "closed": True,
        },
    }


def _ui_snapshot(case_id: str, *, changed: bool) -> dict:
    return {
        "schema_version": "1.0.0",
        "artifact_type": "ui_state_snapshot",
        "case_id": case_id,
        "artifact_role": "CLOSING",
        "source_artifact_id": f"p2-fixture/{case_id}/fixture.FCStd",
        "object_role": "fixture_body",
        "state": {
            "visibility": {"status": "SUPPORTED", "value": not changed},
            "shape_color": {
                "status": "SUPPORTED",
                "value": [0.1, 0.45, 0.9] if changed else [0.82, 0.82, 0.82],
            },
            "transparency": {"status": "SUPPORTED", "value": 60 if changed else 0},
            "display_mode": {"status": "SUPPORTED", "value": "Flat Lines"},
            "camera": {"status": "UNSUPPORTED", "reason": "not fixture-stable"},
        },
    }


def _geometry_comparison() -> dict:
    tolerance = lambda name, value, unit, role: {
        "name": name,
        "value": value,
        "unit": unit,
        "role": role,
        "source": "P2-MVP fixture contract",
    }
    measure = lambda value, unit: {"value": value, "unit": unit}
    return {
        "schema_version": "1.0.0",
        "artifact_type": "geometry_comparison",
        "case_id": "case_a",
        "comparison_role": "UI_ONLY_MUTATION",
        "status": "GEOMETRY_EQUIVALENT",
        "method": "BREP_BOOLEAN_AND_MEASUREMENTS",
        "sha256_role": "file_and_copy_integrity_only_not_geometry_equivalence",
        "tolerances": [
            tolerance("linear", 0.001, "mm", "bounding box and distance"),
            tolerance("area", 0.001, "mm2", "area delta"),
            tolerance("volume", 0.001, "mm3", "volume and Boolean deltas"),
        ],
        "measurements": {
            "area_delta": measure(0.0, "mm2"),
            "volume_delta": measure(0.0, "mm3"),
            "max_bounding_box_delta": measure(0.0, "mm"),
            "minimum_distance": measure(0.0, "mm"),
            "first_minus_second_volume": measure(0.0, "mm3"),
            "second_minus_first_volume": measure(0.0, "mm3"),
        },
        "checks": {
            "valid_closed_single_solids": True,
            "topology_counts": True,
            "area_delta": True,
            "volume_delta": True,
            "bounding_box": True,
            "first_minus_second": True,
            "second_minus_first": True,
        },
        "failed_checks": [],
        "reasons": [],
        "geometry_decision_inputs": [
            "topology",
            "area",
            "volume",
            "bounding_box",
            "bidirectional_boolean_cut",
        ],
    }


def _geometry_difference_comparison() -> dict:
    value = deepcopy(_geometry_comparison())
    value.update(
        {
            "case_id": "case_b",
            "comparison_role": "GEOMETRY_MUTATION",
            "status": "GEOMETRY_DIFFERENT",
            "failed_checks": ["area_delta", "volume_delta", "first_minus_second"],
            "reasons": [
                "AREA_DELTA_EXCEEDS_TOLERANCE",
                "VOLUME_DELTA_EXCEEDS_TOLERANCE",
                "FIRST_MINUS_SECOND_VOLUME_EXCEEDS_TOLERANCE",
            ],
        }
    )
    value["measurements"]["area_delta"]["value"] = 67.858401
    value["measurements"]["volume_delta"]["value"] = 339.292007
    value["measurements"]["first_minus_second_volume"]["value"] = 339.292007
    value["checks"]["area_delta"] = False
    value["checks"]["volume_delta"] = False
    value["checks"]["first_minus_second"] = False
    return value


@pytest.fixture
def repository_root(tmp_path: Path) -> Path:
    repository = tmp_path / "repository"
    repository.mkdir()
    _git(repository, "init", "-q")
    _git(repository, "config", "user.email", "p2-tests@example.invalid")
    _git(repository, "config", "user.name", "P2 Tests")
    (repository / "baseline.txt").write_text("baseline\n", encoding="utf-8")
    _git(repository, "add", "baseline.txt")
    _git(repository, "commit", "-q", "-m", "baseline")
    (repository / "implementation.txt").write_text("implementation\n", encoding="utf-8")
    _git(repository, "add", "implementation.txt")
    _git(repository, "commit", "-q", "-m", "implementation")
    return repository


@pytest.fixture
def valid_cad_request(repository_root: Path, valid_request):
    staging = repository_root / "outputs" / "cad-policy"

    def factory(mutation: str | None = None) -> dict:
        staging.mkdir(parents=True, exist_ok=True)
        values = {
            "case-a-comparison": _geometry_comparison(),
            "original-geometry-snapshot": _geometry_snapshot("original"),
            "ui-geometry-snapshot": _geometry_snapshot("ui_only_changed"),
            "original-ui-snapshot": _ui_snapshot("original", changed=False),
            "ui-changed-snapshot": _ui_snapshot("ui_only_changed", changed=True),
        }
        artifact_kinds = {
            "case-a-comparison": "COMPARISON_JSON",
            "original-geometry-snapshot": "GEOMETRY_SNAPSHOT",
            "ui-geometry-snapshot": "GEOMETRY_SNAPSHOT",
            "original-ui-snapshot": "UI_SNAPSHOT",
            "ui-changed-snapshot": "UI_SNAPSHOT",
        }
        for artifact_id, value in values.items():
            (staging / f"{artifact_id}.json").write_text(
                json.dumps(value, indent=2) + "\n", encoding="utf-8"
            )
        baseline = _git(repository_root, "rev-list", "--max-parents=0", "HEAD")
        implementation = _git(repository_root, "rev-parse", "HEAD")
        request = valid_request()
        request["identity"].update(
            {
                "implementation_commit": implementation,
                "parent_baseline": baseline,
                "merge_base": baseline,
            }
        )
        request["source"]["staging_root"] = "outputs/cad-policy"
        request["source"]["allowlist"] = [
            {
                "artifact_id": artifact_id,
                "source_path": f"{artifact_id}.json",
                "public_path": f"cad/{artifact_id}.json",
                "kind": artifact_kinds[artifact_id],
                "validation_role": "fixture CAD evidence",
                "retention_role": "STANDARD",
            }
            for artifact_id in values
        ]
        request["tolerances"] = deepcopy(values["case-a-comparison"]["tolerances"])
        request["results"]["geometry_equivalence_result"] = {
            "status": "GEOMETRY_EQUIVALENT",
            "evidence_artifact_ids": ["case-a-comparison"],
        }
        request["results"]["semantic_equivalence_result"] = {
            "status": "SEMANTIC_EQUIVALENT",
            "evidence_artifact_ids": [
                "original-geometry-snapshot",
                "ui-geometry-snapshot",
            ],
        }
        request["results"]["ui_state_result"] = {
            "status": "UI_DIFFERENT",
            "evidence_artifact_ids": ["original-ui-snapshot", "ui-changed-snapshot"],
        }
        request["results"]["validator_result"] = {
            "status": "NOT_EVALUATED",
            "evidence_artifact_ids": [],
        }
        request["geometry_validation"] = {
            "status": "GEOMETRY_EQUIVALENT",
            "evidence_method": "BREP_BOOLEAN_AND_MEASUREMENTS",
            "evidence_artifact_ids": ["case-a-comparison"],
            "sha256_role": "file_and_copy_integrity_only_not_geometry_equivalence",
        }
        if mutation == "missing_comparison":
            request["source"]["allowlist"] = [
                item
                for item in request["source"]["allowlist"]
                if item["artifact_id"] != "case-a-comparison"
            ]
        elif mutation == "malformed_snapshot":
            malformed = values["original-geometry-snapshot"]
            del malformed["shape"]["volume"]["unit"]
            (staging / "original-geometry-snapshot.json").write_text(
                json.dumps(malformed, indent=2) + "\n", encoding="utf-8"
            )
        elif mutation == "result_mismatch":
            mismatch = values["case-a-comparison"]
            mismatch["status"] = "GEOMETRY_DIFFERENT"
            mismatch["checks"]["volume_delta"] = False
            mismatch["failed_checks"] = ["volume_delta"]
            mismatch["reasons"] = ["VOLUME_DELTA_EXCEEDS_TOLERANCE"]
            (staging / "case-a-comparison.json").write_text(
                json.dumps(mismatch, indent=2) + "\n", encoding="utf-8"
            )
        elif mutation == "sha_method":
            misuse = values["case-a-comparison"]
            misuse["method"] = "SHA256"
            (staging / "case-a-comparison.json").write_text(
                json.dumps(misuse, indent=2) + "\n", encoding="utf-8"
            )
        return request

    return factory


@pytest.fixture
def valid_cad_request_file(repository_root: Path, valid_cad_request) -> Path:
    request = valid_cad_request()
    comparison = _geometry_difference_comparison()
    comparison_path = repository_root / "outputs/cad-policy/case-b-comparison.json"
    comparison_path.write_text(
        json.dumps(comparison, indent=2) + "\n", encoding="utf-8"
    )
    request["source"]["allowlist"].append(
        {
            "artifact_id": "case-b-comparison",
            "source_path": "case-b-comparison.json",
            "public_path": "cad/case-b-comparison.json",
            "kind": "COMPARISON_JSON",
            "validation_role": "fixture CAD geometry mutation evidence",
            "retention_role": "FAILURE",
        }
    )
    request["results"]["geometry_equivalence_result"] = {
        "status": "GEOMETRY_DIFFERENT",
        "evidence_artifact_ids": ["case-b-comparison"],
    }
    request["geometry_validation"].update(
        {
            "status": "GEOMETRY_DIFFERENT",
            "evidence_artifact_ids": ["case-b-comparison"],
        }
    )
    request["history"]["failure_artifact_ids"] = ["case-b-comparison"]
    return write_request(
        repository_root / "outputs/cad-policy/promotion_request.json",
        request,
    )
