from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import subprocess

from jsonschema import Draft202012Validator
import pytest

from dmslicer.evidence_promotion.integrity import file_integrity
from dmslicer.evidence_promotion.models import read_json, schema_path
from dmslicer.evidence_promotion.promotion import promote


def _git(repository: Path, *arguments: str) -> str:
    return subprocess.run(
        ["git", *arguments], cwd=repository, check=True, capture_output=True, text=True
    ).stdout.strip()


def _write_json(path: Path, value: dict) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
    return path


@pytest.fixture
def promotion_case(tmp_path: Path, valid_request):
    repository = tmp_path / "repository"
    repository.mkdir()
    _git(repository, "init", "-q")
    _git(repository, "config", "user.email", "p2-tests@example.invalid")
    _git(repository, "config", "user.name", "P2 Tests")
    (repository / "baseline.txt").write_text("baseline\n", encoding="utf-8")
    _git(repository, "add", "baseline.txt")
    _git(repository, "commit", "-q", "-m", "baseline")
    baseline = _git(repository, "rev-parse", "HEAD")
    (repository / "implementation.txt").write_text("implementation\n", encoding="utf-8")
    _git(repository, "add", "implementation.txt")
    _git(repository, "commit", "-q", "-m", "implementation")
    implementation = _git(repository, "rev-parse", "HEAD")

    staging = repository / "outputs" / "p2-mvp-test-001"
    staging.mkdir(parents=True)
    validator = _write_json(
        staging / "validator-result.json",
        {"status": "PASS", "geometry_status": "GEOMETRIC_EQUIVALENCE_NOT_PROVEN"},
    )
    failure = _write_json(
        staging / "retained-failure.json",
        {"status": "FAIL", "reason": "intentional regression evidence"},
    )
    request = valid_request()
    request["identity"].update(
        {
            "implementation_commit": implementation,
            "parent_baseline": baseline,
            "merge_base": baseline,
        }
    )
    request["results"]["byte_identity_result"] = {
        "status": "BYTE_DIFFERENT",
        "evidence_artifact_ids": ["validator-result"],
    }
    request["source"]["allowlist"].append(
        {
            "artifact_id": "retained-failure",
            "source_path": "retained-failure.json",
            "public_path": "history/retained-failure.json",
            "kind": "JSON",
            "validation_role": "negative regression evidence",
            "retention_role": "FAILURE",
        }
    )
    request["history"]["failure_artifact_ids"] = ["retained-failure"]
    request_path = _write_json(staging / "request.json", request)
    return repository, request, request_path, validator, failure


def _destination(repository: Path, request: dict) -> Path:
    return (
        repository
        / "evidence"
        / request["goal_id"]
        / request["identity"]["implementation_commit"]
        / request["run_id"]
    )


def _all_strings(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for nested in value.values():
            yield from _all_strings(nested)
    elif isinstance(value, list):
        for nested in value:
            yield from _all_strings(nested)


def test_local_package_can_succeed_without_full_preservation(promotion_case) -> None:
    repository, request, request_path, validator, failure = promotion_case

    result = promote(request_path, repository)

    destination = _destination(repository, request)
    assert result == {
        "schema_version": "2.0.0",
        "status": "PASS",
        "local_package_status": "LOCAL_PACKAGE_CREATED",
        "package_path": destination.relative_to(repository).as_posix(),
        "preservation_status": "NOT_FULLY_PRESERVED",
        "publication_status": "PUBLICATION_NOT_AUTHORIZED",
        "recoverable_copy_count": 2,
        "recoverable_copy_policy": "LOCAL_TWO_PATHS_NOT_OFF_HOST_REDUNDANCY",
        "findings": [],
    }
    assert (destination / "artifacts/validator-result.json").read_bytes() == validator.read_bytes()
    assert (destination / "history/retained-failure.json").read_bytes() == failure.read_bytes()
    assert {path.name for path in destination.iterdir()} >= {
        "manifest.json", "copy_inventory.json", "policy_report.json", "artifacts", "history"
    }


def test_generated_manifest_is_schema_valid_and_keeps_results_separate(promotion_case) -> None:
    repository, request, request_path, _, _ = promotion_case
    promote(request_path, repository)
    destination = _destination(repository, request)
    manifest = read_json(destination / "manifest.json")
    schema = read_json(schema_path("evidence_manifest.v2.schema.json"))

    Draft202012Validator(schema).validate(manifest)

    assert set(manifest["results"]) == {
        "byte_identity_result", "geometry_equivalence_result",
        "semantic_equivalence_result", "ui_state_result", "pytest_result",
        "validator_result", "scientific_experiment_result", "human_inspection_result",
    }
    assert manifest["results"]["byte_identity_result"]["status"] == "BYTE_DIFFERENT"
    assert manifest["results"]["geometry_equivalence_result"]["status"] == (
        "GEOMETRIC_EQUIVALENCE_NOT_PROVEN"
    )
    assert manifest["local_package_result"]["status"] == "LOCAL_PACKAGE_CREATED"
    assert manifest["preservation_result"]["status"] == "NOT_FULLY_PRESERVED"
    assert manifest["publication_result"]["status"] == "PUBLICATION_NOT_AUTHORIZED"
    assert not any(Path(value).is_absolute() for value in _all_strings(manifest))


def test_copy_inventory_recounts_each_allowlisted_file(promotion_case) -> None:
    repository, request, request_path, validator, failure = promotion_case
    promote(request_path, repository)
    inventory = read_json(_destination(repository, request) / "copy_inventory.json")

    assert inventory["artifact_count"] == 2
    assert [item["artifact_id"] for item in inventory["artifacts"]] == [
        "retained-failure", "validator-result"
    ]
    by_id = {item["artifact_id"]: item for item in inventory["artifacts"]}
    assert by_id["validator-result"]["sha256"] == file_integrity(validator)["sha256"]
    assert by_id["retained-failure"]["size_bytes"] == file_integrity(failure)["size_bytes"]
    assert set(item["copy_status"] for item in inventory["artifacts"]) == {"BYTE_SAME"}


def test_second_promotion_refuses_overwrite_without_changing_package(promotion_case) -> None:
    repository, request, request_path, _, _ = promotion_case
    first = promote(request_path, repository)
    destination = _destination(repository, request)
    before = {
        path.relative_to(destination).as_posix(): path.read_bytes()
        for path in destination.rglob("*") if path.is_file()
    }

    second = promote(request_path, repository)

    after = {
        path.relative_to(destination).as_posix(): path.read_bytes()
        for path in destination.rglob("*") if path.is_file()
    }
    assert first["local_package_status"] == "LOCAL_PACKAGE_CREATED"
    assert second["local_package_status"] == "LOCAL_PACKAGE_BLOCKED"
    assert {finding["code"] for finding in second["findings"]} == {"DESTINATION_EXISTS"}
    assert after == before


def test_missing_allowlisted_file_installs_no_package(promotion_case) -> None:
    repository, request, _, _, _ = promotion_case
    request["run_id"] = "p2-mvp-missing-001"
    request["source"]["allowlist"][0]["source_path"] = "missing.json"
    request_path = _write_json(
        repository / "outputs/p2-mvp-test-001/missing-request.json", request
    )

    result = promote(request_path, repository)

    assert result["local_package_status"] == "LOCAL_PACKAGE_BLOCKED"
    assert "ALLOWLIST_SOURCE_MISSING" in {item["code"] for item in result["findings"]}
    assert not _destination(repository, request).exists()


def test_copy_corruption_retains_failure_report_and_source_evidence(promotion_case) -> None:
    repository, request, request_path, _, failure = promotion_case
    original_failure = failure.read_bytes()

    def corrupt_copy(source: Path, destination: Path) -> dict:
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(b"corrupt")
        return {
            "status": "BYTE_DIFFERENT",
            "source": file_integrity(source),
            "destination": file_integrity(destination),
            "sha256_role": "file_and_copy_integrity_only_not_geometry_equivalence",
        }

    result = promote(request_path, repository, copy_function=corrupt_copy)

    failure_report = (
        repository / "work/evidence-promotion-failures" / request["goal_id"]
        / request["identity"]["implementation_commit"] / request["run_id"]
        / "policy_report.json"
    )
    assert result["local_package_status"] == "LOCAL_PACKAGE_BLOCKED"
    assert {item["code"] for item in result["findings"]} == {"COPY_VERIFY_FAILED"}
    assert not _destination(repository, request).exists()
    assert failure.read_bytes() == original_failure
    assert read_json(failure_report)["status"] == "FAIL"
