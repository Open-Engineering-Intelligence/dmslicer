"""Build the explicit, custody-only P2 promotion request for Goal 07A."""

from __future__ import annotations

import json
from pathlib import Path


IMPLEMENTATION_COMMIT = "c7db3501cdfc1971ecb2a4f81e1dcd17eddff18b"
IMPLEMENTATION_PARENT = "b42ba9e7b6efc6dd5a9dd9f7b1584b5a89066f8b"
STAGING_ROOT = "work/07a-evidence-closeout-staging"


def _artifact(
    artifact_id: str,
    source_path: str,
    public_path: str,
    kind: str,
    validation_role: str,
    retention_role: str = "STANDARD",
) -> dict[str, str]:
    return {
        "artifact_id": artifact_id,
        "source_path": source_path,
        "public_path": public_path,
        "kind": kind,
        "validation_role": validation_role,
        "retention_role": retention_role,
    }


def _scenario_artifacts(scenario: str, retention_role: str) -> list[dict[str, str]]:
    prefix = scenario.lower().replace("_", "-")
    return [
        _artifact(prefix + "-expected", scenario + "/expected_snapshot.json", "scenarios/" + scenario + "/expected_snapshot.json", "JSON", "historical scenario expectation", retention_role),
        _artifact(prefix + "-operation", scenario + "/operation.json", "scenarios/" + scenario + "/operation.json", "JSON", "historical operation record", retention_role),
        _artifact(prefix + "-validation", scenario + "/validation.json", "scenarios/" + scenario + "/validation.json", "VALIDATOR", "historical validator result", retention_role),
        _artifact(prefix + "-repeatability", scenario + "/repeatability.json", "scenarios/" + scenario + "/repeatability.json", "JSON", "historical repeatability summary", retention_role),
        _artifact(prefix + "-fcstd", scenario + "/operation_debug.FCStd", "human-inspection/" + scenario + "/operation_debug.FCStd", "FCSTD", "human inspection artifact", retention_role),
    ]


def _geometry_artifacts(scenario: str, prefix: str, destination: str) -> list[dict[str, str]]:
    return [
        _artifact(prefix + "-actual-common", scenario + "/actual_common.brep", destination + "/actual_common.brep", "BREP", "historical actual common geometry", "STANDARD"),
        _artifact(prefix + "-corrected-step", scenario + "/corrected_assembly.step", destination + "/corrected_assembly.step", "STEP", "historical corrected assembly geometry", "STANDARD"),
        _artifact(prefix + "-fused-step", scenario + "/fused.step", destination + "/fused.step", "STEP", "historical fused geometry", "STANDARD"),
    ]


def _repeatability_artifacts(scenario: str) -> list[dict[str, str]]:
    prefix = scenario.lower().replace("_", "-")
    source = "repeatability/second_process/" + scenario
    destination = "repeatability/second_process/" + scenario
    return [
        _artifact(prefix + "-repeat-operation", source + "/operation.json", destination + "/operation.json", "JSON", "second-process operation record"),
        _artifact(prefix + "-repeat-validation", source + "/validation.json", destination + "/validation.json", "VALIDATOR", "second-process validator result"),
    ]


def build_request(*, run_id: str, timestamp: str, python_version: str, pytest_version: str, freecad_version: str | None, occt_version: str | None) -> dict:
    allowlist = [
        _artifact("view-index", "VIEW_INDEX.md", "human-inspection/VIEW_INDEX.md", "VIEW_INDEX", "human inspection navigation"),
        _artifact("summary", "summary.json", "records/summary.json", "JSON", "historical scenario summary"),
        _artifact("human-review-readme", "HUMAN_REVIEW/README.md", "human-inspection/HUMAN_REVIEW_README.md", "HUMAN_REVIEW", "human inspection index"),
    ]
    for scenario, retention_role in (("C01", "STANDARD"), ("C02", "STANDARD"), ("C03", "REJECTION"), ("C04", "REJECTION"), ("C05", "REJECTION"), ("AMBIGUOUS", "REJECTION"), ("ROTATED_C02", "STANDARD")):
        allowlist.extend(_scenario_artifacts(scenario, retention_role))
    allowlist.extend(_geometry_artifacts("C02", "c02", "scenarios/C02"))
    allowlist.extend(_geometry_artifacts("ROTATED_C02", "rotated-c02", "scenarios/ROTATED_C02"))
    for scenario in ("C01", "C02", "C03", "C04", "C05", "AMBIGUOUS", "ROTATED_C02"):
        allowlist.extend(_repeatability_artifacts(scenario))
    allowlist.extend(_geometry_artifacts("repeatability/second_process/C02", "c02-repeat", "repeatability/second_process/C02"))
    allowlist.extend(_geometry_artifacts("repeatability/second_process/ROTATED_C02", "rotated-c02-repeat", "repeatability/second_process/ROTATED_C02"))
    return {
        "schema_version": "2.0.0",
        "goal_id": "07A",
        "run_id": run_id,
        "identity": {"branch": "chore/07a-evidence-closeout", "implementation_commit": IMPLEMENTATION_COMMIT, "parent_baseline": IMPLEMENTATION_PARENT, "merge_base": IMPLEMENTATION_PARENT},
        "source": {"staging_root": STAGING_ROOT, "allowlist": allowlist},
        "environment": {"python_version": python_version, "pytest_version": pytest_version, "freecad_version": freecad_version, "occt_version": occt_version},
        "execution": [{"command": "custody-only historical 07A evidence promotion; no geometry benchmark rerun", "exit_code": 0, "timestamp": timestamp}],
        "tolerances": [
            {"name": "linear_epsilon", "value": 1e-7, "unit": "mm", "role": "historical geometric validation", "source": "07A operation records"},
            {"name": "area_epsilon", "value": 1e-8, "unit": "mm2", "role": "historical geometric validation", "source": "07A operation records"},
            {"name": "volume_epsilon", "value": 1e-6, "unit": "mm3", "role": "historical geometric validation", "source": "07A operation records"},
            {"name": "angular_epsilon", "value": 1e-7, "unit": "rad", "role": "historical geometric validation", "source": "07A operation records"},
            {"name": "periodic_epsilon", "value": 1e-6, "unit": "rad", "role": "historical geometric validation", "source": "07A operation records"},
            {"name": "radius_epsilon", "value": 1e-7, "unit": "mm", "role": "historical geometric validation", "source": "07A operation records"},
            {"name": "material_probe_offset", "value": 1e-5, "unit": "mm", "role": "historical geometric validation", "source": "07A operation records"},
        ],
        "results": {
            "byte_identity_result": {"status": "BYTE_NOT_EVALUATED", "evidence_artifact_ids": []},
            "geometry_equivalence_result": {"status": "GEOMETRIC_EQUIVALENCE_NOT_PROVEN", "evidence_artifact_ids": []},
            "semantic_equivalence_result": {"status": "SEMANTIC_EQUIVALENCE_NOT_PROVEN", "evidence_artifact_ids": []},
            "ui_state_result": {"status": "UI_STATE_NOT_PROVEN", "evidence_artifact_ids": []},
            "pytest_result": {"status": "NOT_EVALUATED", "evidence_artifact_ids": []},
            "validator_result": {"status": "NOT_EVALUATED", "evidence_artifact_ids": []},
            "scientific_experiment_result": {"status": "NOT_EVALUATED", "evidence_artifact_ids": []},
            "human_inspection_result": {"status": "NOT_EVALUATED", "evidence_artifact_ids": []},
        },
        "history": {"failure_artifact_ids": [], "mismatch_artifact_ids": [], "rejection_artifact_ids": ["c03-operation", "c04-operation", "c05-operation", "ambiguous-operation"], "reviewer_finding_artifact_ids": []},
        "custody": {"off_host_copies": [], "publication_authorized": False},
        "geometry_validation": {"status": "GEOMETRIC_EQUIVALENCE_NOT_PROVEN", "evidence_method": "NOT_EVALUATED_P2_MVP", "evidence_artifact_ids": [], "sha256_role": "file_and_copy_integrity_only_not_geometry_equivalence"},
    }


def write_request(path: Path, **kwargs: object) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(build_request(**kwargs), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path
