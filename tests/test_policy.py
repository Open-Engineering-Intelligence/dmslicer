from __future__ import annotations

from copy import deepcopy
import json
import os
from pathlib import Path
import subprocess

import pytest

from dmslicer.evidence_promotion.policy import portable_relative_path, validate_request


def _git(repository: Path, *arguments: str) -> str:
    return subprocess.run(
        ["git", *arguments],
        cwd=repository,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


@pytest.fixture
def policy_case(tmp_path: Path, valid_request):
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
    (staging / "validator-result.json").write_text(
        json.dumps({"status": "PASS", "scope": "software validation"}) + "\n",
        encoding="utf-8",
    )
    request = valid_request()
    request["identity"].update(
        {
            "implementation_commit": implementation,
            "parent_baseline": baseline,
            "merge_base": baseline,
        }
    )
    return repository, request, staging


def _codes(report: dict) -> set[str]:
    return {finding["code"] for finding in report["findings"]}


@pytest.mark.parametrize(
    "unsafe",
    ["C:/Users/person/result.json", r"C:\Users\person\result.json", "/tmp/result.json", "../result.json", r"..\result.json"],
    ids=[
        "windows-drive-forward-slash",
        "windows-drive-backslash",
        "posix-absolute",
        "posix-traversal",
        "backslash-traversal",
    ],
)
def test_portable_path_parser_rejects_windows_and_posix_escape_forms(unsafe: str) -> None:
    assert portable_relative_path(unsafe) is None


def test_portable_path_parser_normalizes_safe_separators() -> None:
    assert portable_relative_path(r"artifacts\result.json").as_posix() == "artifacts/result.json"


def test_valid_request_passes_every_all_local_policy_checks(policy_case) -> None:
    repository, request, _ = policy_case

    report = validate_request(request, repository)

    assert report["status"] == "PASS"
    assert report["findings"] == []
    assert set(report["checks"]) == {
        "schema", "git", "allowlist", "content", "result_separation", "failure_retention"
    }
    assert set(report["checks"].values()) == {"PASS"}


@pytest.mark.parametrize(
    ("mutation", "expected_code"),
    [
        ("missing_implementation_commit", "SCHEMA_INVALID"),
        ("nonexistent_implementation_commit", "GIT_COMMIT_NOT_FOUND"),
        ("invalid_run_id", "SCHEMA_INVALID"),
        ("missing_tolerance_unit", "SCHEMA_INVALID"),
        ("missing_result_evidence", "EVIDENCE_REFERENCE_MISSING"),
    ],
)
def test_manifest_and_provenance_defects_fail_closed(
    policy_case, mutation: str, expected_code: str
) -> None:
    repository, request, _ = policy_case
    if mutation == "missing_implementation_commit":
        del request["identity"]["implementation_commit"]
    elif mutation == "nonexistent_implementation_commit":
        request["identity"]["implementation_commit"] = "f" * 40
    elif mutation == "invalid_run_id":
        request["run_id"] = "../escape"
    elif mutation == "missing_tolerance_unit":
        request["tolerances"] = [
            {"name": "linear", "value": 1e-7, "role": "comparison", "source": "policy"}
        ]
    else:
        request["results"]["pytest_result"] = {
            "status": "PASS",
            "evidence_artifact_ids": ["not-allowlisted"],
        }

    assert expected_code in _codes(validate_request(request, repository))


def test_non_ancestor_parent_is_rejected(policy_case) -> None:
    repository, request, _ = policy_case
    implementation = request["identity"]["implementation_commit"]
    (repository / "later.txt").write_text("later\n", encoding="utf-8")
    _git(repository, "add", "later.txt")
    _git(repository, "commit", "-q", "-m", "later")
    later = _git(repository, "rev-parse", "HEAD")
    request["identity"]["implementation_commit"] = implementation
    request["identity"]["parent_baseline"] = later

    assert "GIT_ANCESTRY_INVALID" in _codes(validate_request(request, repository))


def test_schema_failure_marks_dependent_checks_not_run(policy_case) -> None:
    repository, request, _ = policy_case
    del request["identity"]["implementation_commit"]

    report = validate_request(request, repository)

    assert report["checks"]["schema"] == "FAIL"
    assert set(report["checks"].values()) == {"FAIL", "NOT_RUN"}


def test_invalid_execution_timestamp_fails_schema_policy(policy_case) -> None:
    repository, request, _ = policy_case
    request["execution"][0]["timestamp"] = "not-a-date"

    assert "SCHEMA_INVALID" in _codes(validate_request(request, repository))


@pytest.mark.parametrize(
    ("mutation", "expected_code"),
    [
        ("missing", "ALLOWLIST_SOURCE_MISSING"),
        ("traversal", "PATH_ESCAPE"),
        ("absolute_source", "PATH_ESCAPE"),
        ("absolute_public", "PUBLIC_PATH_INVALID"),
        ("outside_staging", "STAGING_ROOT_INVALID"),
        ("directory", "BROAD_SELECTION"),
        ("duplicate_public", "PUBLIC_PATH_INVALID"),
        ("reserved_public", "PUBLIC_PATH_INVALID"),
    ],
)
def test_allowlist_and_path_defects_fail_closed(
    policy_case, mutation: str, expected_code: str
) -> None:
    repository, request, staging = policy_case
    artifact = request["source"]["allowlist"][0]
    if mutation == "missing":
        artifact["source_path"] = "missing.json"
    elif mutation == "traversal":
        artifact["source_path"] = "../implementation.txt"
    elif mutation == "absolute_source":
        artifact["source_path"] = str((staging / "validator-result.json").resolve())
    elif mutation == "absolute_public":
        artifact["public_path"] = "C:/Users/person/result.json"
    elif mutation == "outside_staging":
        request["source"]["staging_root"] = "docs"
    elif mutation == "directory":
        artifact["source_path"] = "."
    elif mutation == "duplicate_public":
        duplicate = deepcopy(artifact)
        duplicate["artifact_id"] = "duplicate-result"
        request["source"]["allowlist"].append(duplicate)
    else:
        artifact["public_path"] = "manifest.json"

    assert expected_code in _codes(validate_request(request, repository))


def test_symlink_escape_is_rejected_when_host_supports_symlinks(policy_case, tmp_path: Path) -> None:
    repository, request, staging = policy_case
    outside_directory = tmp_path / "outside"
    outside_directory.mkdir()
    outside = outside_directory / "outside.json"
    outside.write_text('{"status":"FAIL"}\n', encoding="utf-8")
    link = staging / "linked.json"
    try:
        os.symlink(outside, link)
        source_path = "linked.json"
    except OSError:
        junction = staging / "linked-directory"
        completed = subprocess.run(
            ["cmd", "/c", "mklink", "/J", str(junction), str(outside_directory)],
            check=False,
            capture_output=True,
            text=True,
        )
        assert completed.returncode == 0
        source_path = "linked-directory/outside.json"
    request["source"]["allowlist"][0]["source_path"] = source_path

    assert "PATH_ESCAPE" in _codes(validate_request(request, repository))


@pytest.mark.parametrize(
    "sensitive_text",
    [
        r"C:\Users\person\private\result.json",
        "/home/person/private/result.json",
        r"C:\Users\person\.codex\attachments\secret.txt",
        "-----BEGIN PRIVATE KEY-----",
        "ghp_abcdefghijklmnopqrstuvwxyz012345",
        "password = do-not-publish",
    ],
    ids=[
        "windows-home-path",
        "linux-home-path",
        "codex-private-path",
        "private-key-header",
        "github-token",
        "password-assignment",
    ],
)
def test_sensitive_public_content_is_rejected(policy_case, sensitive_text: str) -> None:
    repository, request, staging = policy_case
    (staging / "validator-result.json").write_text(
        json.dumps({"note": sensitive_text}) + "\n", encoding="utf-8"
    )

    assert "SENSITIVE_CONTENT" in _codes(validate_request(request, repository))


def test_ordinary_sha256_integrity_value_is_public_safe(policy_case) -> None:
    repository, request, staging = policy_case
    (staging / "validator-result.json").write_text(
        json.dumps({"sha256": "a" * 64, "role": "byte integrity"}) + "\n",
        encoding="utf-8",
    )

    assert validate_request(request, repository)["status"] == "PASS"


def test_result_evidence_must_match_result_domain(policy_case) -> None:
    repository, request, _ = policy_case
    request["source"]["allowlist"].append(
        {
            "artifact_id": "case-a-ui",
            "source_path": "validator-result.json",
            "public_path": "ui/snapshot.json",
            "kind": "UI_SNAPSHOT",
            "validation_role": "ui snapshot artifact",
            "retention_role": "STANDARD",
        }
    )
    request["results"]["pytest_result"]["evidence_artifact_ids"] = ["case-a-ui"]

    assert "RESULT_EVIDENCE_MISMATCH" in _codes(validate_request(request, repository))


def test_result_evidence_domain_overlap_is_rejected(policy_case) -> None:
    repository, request, _ = policy_case
    request["source"]["allowlist"].append(
        {
            "artifact_id": "shared-junit",
            "source_path": "validator-result.json",
            "public_path": "reports/shared-junit.json",
            "kind": "JUNIT",
            "validation_role": "shared junit evidence",
            "retention_role": "STANDARD",
        }
    )
    request["results"]["pytest_result"] = {
        "status": "PASS",
        "evidence_artifact_ids": ["shared-junit"],
    }
    request["results"]["scientific_experiment_result"] = {
        "status": "PASS",
        "evidence_artifact_ids": ["shared-junit"],
    }

    assert "RESULT_EVIDENCE_DOMAIN_OVERLAP" in _codes(
        validate_request(request, repository)
    )


def test_sha_geometry_predicate_is_rejected(policy_case) -> None:
    repository, request, _ = policy_case
    request["source"]["allowlist"][0]["validation_role"] = (
        "sha256 hash proves geometry equivalence"
    )

    assert "SHA_GEOMETRY_MISUSE" in _codes(validate_request(request, repository))


def test_byte_difference_does_not_set_geometry_failure(policy_case) -> None:
    repository, request, _ = policy_case
    request["results"]["byte_identity_result"]["status"] = "BYTE_DIFFERENT"

    report = validate_request(request, repository)

    assert report["status"] == "PASS"
    assert request["results"]["geometry_equivalence_result"]["status"] == (
        "GEOMETRIC_EQUIVALENCE_NOT_PROVEN"
    )


def _add_retained_history(request: dict, staging: Path) -> None:
    mapping = {
        "failure_artifact_ids": ("failure-1", "FAILURE"),
        "mismatch_artifact_ids": ("mismatch-1", "MISMATCH"),
        "rejection_artifact_ids": ("rejection-1", "REJECTION"),
        "reviewer_finding_artifact_ids": ("review-1", "REVIEWER_FINDING"),
    }
    for history_field, (artifact_id, role) in mapping.items():
        filename = artifact_id + ".json"
        (staging / filename).write_text('{"status":"retained"}\n', encoding="utf-8")
        request["history"][history_field] = [artifact_id]
        request["source"]["allowlist"].append(
            {
                "artifact_id": artifact_id,
                "source_path": filename,
                "public_path": "history/" + filename,
                "kind": "JSON",
                "validation_role": "retained historical evidence",
                "retention_role": role,
            }
        )


def test_all_declared_failure_categories_are_retained(policy_case) -> None:
    repository, request, staging = policy_case
    _add_retained_history(request, staging)

    assert validate_request(request, repository)["status"] == "PASS"


@pytest.mark.parametrize(
    "history_field",
    [
        "failure_artifact_ids",
        "mismatch_artifact_ids",
        "rejection_artifact_ids",
        "reviewer_finding_artifact_ids",
    ],
)
def test_dropped_or_misclassified_failure_evidence_is_rejected(
    policy_case, history_field: str
) -> None:
    repository, request, staging = policy_case
    _add_retained_history(request, staging)
    artifact_id = request["history"][history_field][0]
    artifact = next(
        item for item in request["source"]["allowlist"] if item["artifact_id"] == artifact_id
    )
    artifact["retention_role"] = "STANDARD"

    assert "FAILURE_EVIDENCE_NOT_RETAINED" in _codes(
        validate_request(request, repository)
    )
