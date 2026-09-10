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
