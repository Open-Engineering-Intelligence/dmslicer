"""Transactional creation of stable local evidence packages."""

from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import tempfile
from typing import Any, Callable

from jsonschema import Draft202012Validator

from .integrity import compare_bytes, copy_and_verify
from .models import (
    BYTE_SAME,
    LOCAL_PACKAGE_BLOCKED,
    LOCAL_PACKAGE_CREATED,
    LOCAL_TWO_PATHS_NOT_OFF_HOST_REDUNDANCY,
    NOT_FULLY_PRESERVED,
    PUBLICATION_NOT_AUTHORIZED,
    read_json,
    schema_path,
    write_json,
)
from .policy import PolicyFinding, resolve_allowlisted_files, validate_request


CopyFunction = Callable[[Path, Path], dict[str, Any]]


def _package_relative_path(request: dict[str, Any]) -> Path:
    return (
        Path("evidence")
        / request["goal_id"]
        / request["identity"]["implementation_commit"]
        / request["run_id"]
    )


def _blocked_result(findings: list[dict[str, str]]) -> dict[str, Any]:
    return {
        "schema_version": "2.0.0",
        "status": "FAIL",
        "local_package_status": LOCAL_PACKAGE_BLOCKED,
        "package_path": None,
        "preservation_status": NOT_FULLY_PRESERVED,
        "publication_status": PUBLICATION_NOT_AUTHORIZED,
        "recoverable_copy_count": 1,
        "recoverable_copy_policy": "SOURCE_ONLY_NO_PROMOTED_COPY",
        "findings": findings,
    }


def _safe_failure_parts(request: Any) -> tuple[str, str, str]:
    if isinstance(request, dict):
        goal = request.get("goal_id")
        run = request.get("run_id")
        identity = request.get("identity")
        commit = identity.get("implementation_commit") if isinstance(identity, dict) else None
        if (
            isinstance(goal, str)
            and isinstance(run, str)
            and isinstance(commit, str)
            and goal.replace("-", "").replace("_", "").replace(".", "").isalnum()
            and run.replace("-", "").replace("_", "").replace(".", "").isalnum()
            and len(commit) == 40
            and all(character in "0123456789abcdef" for character in commit)
        ):
            return goal, commit, run
    digest = sha256(
        json.dumps(request, ensure_ascii=True, sort_keys=True, default=str).encode("utf-8")
    ).hexdigest()
    return "UNIDENTIFIED", "NO_VALID_COMMIT", digest


def _retain_failure_report(
    repository_root: Path, request: Any, result: dict[str, Any]
) -> str | None:
    goal, commit, run = _safe_failure_parts(request)
    relative = Path("work") / "evidence-promotion-failures" / goal / commit / run
    report_path = repository_root / relative / "policy_report.json"
    if report_path.exists():
        return relative.as_posix()
    write_json(report_path, result)
    return relative.as_posix()


def _manifest(
    request: dict[str, Any],
    package_path: Path,
    artifacts: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "schema_version": "2.0.0",
        "goal_id": request["goal_id"],
        "run_id": request["run_id"],
        "identity": deepcopy(request["identity"]),
        "source_staging_root": request["source"]["staging_root"],
        "environment": deepcopy(request["environment"]),
        "execution": deepcopy(request["execution"]),
        "tolerances": deepcopy(request["tolerances"]),
        "artifacts": artifacts,
        "history": deepcopy(request["history"]),
        "results": deepcopy(request["results"]),
        "geometry_validation": deepcopy(request["geometry_validation"]),
        "local_package_result": {
            "status": LOCAL_PACKAGE_CREATED,
            "package_path": package_path.as_posix(),
        },
        "preservation_result": {
            "status": NOT_FULLY_PRESERVED,
            "recoverable_copy_count": 2,
            "recoverable_copy_policy": LOCAL_TWO_PATHS_NOT_OFF_HOST_REDUNDANCY,
        },
        "publication_result": {
            "status": PUBLICATION_NOT_AUTHORIZED,
            "off_host_copy_count": 0,
        },
        "policy_result": {"status": "PASS", "findings": []},
    }


def promote(
    request_path: Path,
    repository_root: Path,
    *,
    copy_function: CopyFunction = copy_and_verify,
) -> dict[str, Any]:
    repository_root = Path(repository_root).resolve(strict=True)
    request = read_json(Path(request_path))
    policy_report = validate_request(request, repository_root)
    if policy_report["status"] != "PASS":
        result = _blocked_result(deepcopy(policy_report["findings"]))
        _retain_failure_report(repository_root, request, result)
        return result

    package_relative = _package_relative_path(request)
    destination = repository_root / package_relative
    if destination.exists():
        findings = [
            PolicyFinding(
                "DESTINATION_EXISTS",
                "Stable evidence destination already exists and will not be overwritten",
            ).as_dict()
        ]
        result = _blocked_result(findings)
        _retain_failure_report(repository_root, request, result)
        return result

    artifacts = sorted(
        resolve_allowlisted_files(request, repository_root),
        key=lambda artifact: artifact.artifact_id,
    )
    staging_parent = repository_root / "work" / "evidence-promotion-staging"
    staging_parent.mkdir(parents=True, exist_ok=True)
    try:
        with tempfile.TemporaryDirectory(
            prefix=f"{request['run_id']}-", dir=staging_parent
        ) as temporary_directory:
            candidate = Path(temporary_directory)
            inventory_artifacts = []
            manifest_artifacts = []
            for artifact in artifacts:
                copied_path = candidate / artifact.public_path
                copy_function(artifact.source_path, copied_path)
                comparison = compare_bytes(artifact.source_path, copied_path)
                if comparison["status"] != BYTE_SAME:
                    raise OSError(f"byte verification failed for {artifact.artifact_id}")
                integrity = comparison["source"]
                record = {
                    "artifact_id": artifact.artifact_id,
                    "kind": artifact.kind,
                    "public_path": artifact.public_path.as_posix(),
                    "sha256": integrity["sha256"],
                    "size_bytes": integrity["size_bytes"],
                    "validation_role": artifact.validation_role,
                    "retention_role": artifact.retention_role,
                    "copy_status": BYTE_SAME,
                }
                manifest_artifacts.append(record)
                inventory_artifacts.append(
                    {
                        "artifact_id": artifact.artifact_id,
                        "source_logical_path": (
                            Path(request["source"]["staging_root"])
                            / next(
                                item["source_path"]
                                for item in request["source"]["allowlist"]
                                if item["artifact_id"] == artifact.artifact_id
                            )
                        ).as_posix(),
                        "public_path": artifact.public_path.as_posix(),
                        "sha256": integrity["sha256"],
                        "size_bytes": integrity["size_bytes"],
                        "copy_status": BYTE_SAME,
                    }
                )

            copy_inventory = {
                "schema_version": "2.0.0",
                "sha256_role": "file_and_copy_integrity_only_not_geometry_equivalence",
                "artifact_count": len(inventory_artifacts),
                "artifacts": inventory_artifacts,
            }
            manifest = _manifest(request, package_relative, manifest_artifacts)
            manifest_schema = read_json(schema_path("evidence_manifest.v2.schema.json"))
            errors = sorted(
                Draft202012Validator(manifest_schema).iter_errors(manifest),
                key=lambda error: list(error.absolute_path),
            )
            if errors:
                raise ValueError("generated manifest failed evidence_manifest.v2 schema")
            write_json(candidate / "copy_inventory.json", copy_inventory)
            write_json(candidate / "policy_report.json", policy_report)
            write_json(candidate / "manifest.json", manifest)
            destination.parent.mkdir(parents=True, exist_ok=True)
            candidate.rename(destination)
    except Exception:
        findings = [
            PolicyFinding(
                "COPY_VERIFY_FAILED",
                "Candidate package failed copy or generated-manifest verification",
            ).as_dict()
        ]
        result = _blocked_result(findings)
        _retain_failure_report(repository_root, request, result)
        return result

    return {
        "schema_version": "2.0.0",
        "status": "PASS",
        "local_package_status": LOCAL_PACKAGE_CREATED,
        "package_path": package_relative.as_posix(),
        "preservation_status": NOT_FULLY_PRESERVED,
        "publication_status": PUBLICATION_NOT_AUTHORIZED,
        "recoverable_copy_count": 2,
        "recoverable_copy_policy": LOCAL_TWO_PATHS_NOT_OFF_HOST_REDUNDANCY,
        "findings": [],
    }
