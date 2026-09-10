"""Fail-closed policy checks for local evidence promotion."""

from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path
import re
import subprocess
from typing import Any, Mapping

from jsonschema import Draft202012Validator

from .models import read_json, schema_path


_GENERATED_PACKAGE_PATHS = {"manifest.json", "copy_inventory.json", "policy_report.json"}
_TEXT_KINDS = {"JUNIT", "VALIDATOR", "JSON", "TEXT", "VIEW_INDEX", "HUMAN_REVIEW"}
_EXPECTED_HISTORY_ROLES = {
    "failure_artifact_ids": "FAILURE",
    "mismatch_artifact_ids": "MISMATCH",
    "rejection_artifact_ids": "REJECTION",
    "reviewer_finding_artifact_ids": "REVIEWER_FINDING",
}
_SAFE_SHA_ROLE = "file_and_copy_integrity_only_not_geometry_equivalence"
_SENSITIVE_PATTERNS = (
    re.compile(r"(?i)\b[A-Z]:[\\/]+"),
    re.compile(r"(?i)/(?:home|users|tmp)/[^\s\"']+"),
    re.compile(r"(?i)(?:^|[\\/])\.codex(?:[\\/])"),
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    re.compile(r"\bgh[pousr]_[A-Za-z0-9]{10,}\b"),
    re.compile(r"(?i)\b(?:password|secret|api[_-]?key)\s*[:=]\s*[^\s,}\]]+"),
)


@dataclass(frozen=True)
class PolicyFinding:
    code: str
    message: str
    artifact_id: str | None = None

    def as_dict(self) -> dict[str, str]:
        value = {"code": self.code, "message": self.message}
        if self.artifact_id is not None:
            value["artifact_id"] = self.artifact_id
        return value


@dataclass(frozen=True)
class ResolvedArtifact:
    artifact_id: str
    source_path: Path
    public_path: Path
    kind: str
    validation_role: str
    retention_role: str


class PolicyValidationError(ValueError):
    def __init__(self, findings: list[PolicyFinding]):
        super().__init__("Evidence promotion request failed policy validation")
        self.findings = findings


def _schema_findings(request: Mapping[str, Any]) -> list[PolicyFinding]:
    schema = read_json(schema_path("promotion_request.schema.json"))
    validator = Draft202012Validator(schema)
    findings = []
    for error in sorted(validator.iter_errors(request), key=lambda item: list(item.absolute_path)):
        field = ".".join(str(value) for value in error.absolute_path) or "request"
        findings.append(
            PolicyFinding("SCHEMA_INVALID", f"Request schema validation failed at {field}")
        )
    return findings


def _git(repository_root: Path, *arguments: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *arguments],
        cwd=repository_root,
        check=False,
        capture_output=True,
        text=True,
    )


def _git_findings(request: Mapping[str, Any], repository_root: Path) -> list[PolicyFinding]:
    identity = request["identity"]
    commits = {
        "implementation_commit": identity["implementation_commit"],
        "parent_baseline": identity["parent_baseline"],
        "merge_base": identity["merge_base"],
    }
    exists: dict[str, bool] = {}
    findings = []
    for role, commit in commits.items():
        exists[role] = _git(repository_root, "cat-file", "-e", f"{commit}^{{commit}}").returncode == 0
        if not exists[role]:
            findings.append(
                PolicyFinding("GIT_COMMIT_NOT_FOUND", f"Declared {role} is not a local Git commit")
            )
    if not all(exists.values()):
        return findings

    implementation = commits["implementation_commit"]
    for role in ("parent_baseline", "merge_base"):
        candidate = commits[role]
        if _git(repository_root, "merge-base", "--is-ancestor", candidate, implementation).returncode != 0:
            findings.append(
                PolicyFinding(
                    "GIT_ANCESTRY_INVALID",
                    f"Declared {role} is not an ancestor of implementation_commit",
                )
            )
    actual_merge_base = _git(
        repository_root,
        "merge-base",
        commits["parent_baseline"],
        implementation,
    )
    if actual_merge_base.returncode != 0 or actual_merge_base.stdout.strip() != commits["merge_base"]:
        findings.append(
            PolicyFinding("GIT_ANCESTRY_INVALID", "Declared merge_base does not match Git ancestry")
        )
    return findings


def _is_relative_input(path: Path) -> bool:
    return not path.is_absolute() and not path.drive and ".." not in path.parts


def _contains_symlink(path: Path, stop: Path) -> bool:
    cursor = path
    while True:
        attributes = getattr(os.lstat(cursor), "st_file_attributes", 0)
        if cursor.is_symlink() or bool(attributes & 0x400):
            return True
        if cursor == stop:
            return False
        if stop not in cursor.parents:
            return True
        cursor = cursor.parent


def _resolve_artifacts(
    request: Mapping[str, Any], repository_root: Path
) -> tuple[list[ResolvedArtifact], list[PolicyFinding]]:
    findings: list[PolicyFinding] = []
    resolved: list[ResolvedArtifact] = []
    repository_root = repository_root.resolve(strict=True)
    staging_input = Path(request["source"]["staging_root"])
    if (
        not _is_relative_input(staging_input)
        or not staging_input.parts
        or staging_input.parts[0].lower() not in {"outputs", "work"}
    ):
        return [], [
            PolicyFinding(
                "STAGING_ROOT_INVALID",
                "Staging root must be repository-relative beneath outputs/ or work/",
            )
        ]
    try:
        staging_root = (repository_root / staging_input).resolve(strict=True)
        staging_root.relative_to(repository_root)
    except (FileNotFoundError, ValueError):
        return [], [PolicyFinding("STAGING_ROOT_INVALID", "Staging root is missing or escapes the repository")]

    seen_ids: set[str] = set()
    seen_public: set[str] = set()
    for artifact in request["source"]["allowlist"]:
        artifact_id = artifact["artifact_id"]
        source_input = Path(artifact["source_path"])
        public_input = Path(artifact["public_path"])
        if artifact_id in seen_ids:
            findings.append(PolicyFinding("PUBLIC_PATH_INVALID", "Artifact IDs must be unique", artifact_id))
        seen_ids.add(artifact_id)

        if not _is_relative_input(public_input) or public_input == Path("."):
            findings.append(
                PolicyFinding("PUBLIC_PATH_INVALID", "Public path must be a safe relative file path", artifact_id)
            )
        public_key = public_input.as_posix().lower()
        if public_key in _GENERATED_PACKAGE_PATHS or public_key in seen_public:
            findings.append(
                PolicyFinding("PUBLIC_PATH_INVALID", "Public path is reserved or duplicated", artifact_id)
            )
        seen_public.add(public_key)

        if not _is_relative_input(source_input):
            findings.append(
                PolicyFinding("PATH_ESCAPE", "Allowlisted source must be relative to the staging root", artifact_id)
            )
            continue
        source_candidate = staging_root / source_input
        try:
            if _contains_symlink(source_candidate, staging_root):
                findings.append(
                    PolicyFinding("PATH_ESCAPE", "Allowlisted source uses a symlink or reparse point", artifact_id)
                )
                continue
            source_path = source_candidate.resolve(strict=True)
            source_path.relative_to(staging_root)
        except FileNotFoundError:
            findings.append(
                PolicyFinding("ALLOWLIST_SOURCE_MISSING", "Allowlisted source file does not exist", artifact_id)
            )
            continue
        except (OSError, ValueError):
            findings.append(
                PolicyFinding("PATH_ESCAPE", "Allowlisted source escapes the staging root", artifact_id)
            )
            continue
        if not source_path.is_file():
            findings.append(
                PolicyFinding("BROAD_SELECTION", "Allowlist entries must name individual regular files", artifact_id)
            )
            continue
        resolved.append(
            ResolvedArtifact(
                artifact_id=artifact_id,
                source_path=source_path,
                public_path=public_input,
                kind=artifact["kind"],
                validation_role=artifact["validation_role"],
                retention_role=artifact["retention_role"],
            )
        )
    return resolved, findings


def _sensitive_content_findings(artifacts: list[ResolvedArtifact]) -> list[PolicyFinding]:
    findings = []
    for artifact in artifacts:
        if artifact.kind not in _TEXT_KINDS:
            continue
        try:
            content = artifact.source_path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            findings.append(
                PolicyFinding("SENSITIVE_CONTENT", "Declared public text is not valid UTF-8", artifact.artifact_id)
            )
            continue
        if any(pattern.search(content) for pattern in _SENSITIVE_PATTERNS):
            findings.append(
                PolicyFinding("SENSITIVE_CONTENT", "Selected public content contains a sensitive value or path", artifact.artifact_id)
            )
    return findings


def _all_strings(value: Any):
    if isinstance(value, str):
        yield value
    elif isinstance(value, Mapping):
        for nested in value.values():
            yield from _all_strings(nested)
    elif isinstance(value, list):
        for nested in value:
            yield from _all_strings(nested)


def _result_findings(request: Mapping[str, Any]) -> list[PolicyFinding]:
    findings = []
    artifact_by_id = {
        artifact["artifact_id"]: artifact for artifact in request["source"]["allowlist"]
    }
    for result in request["results"].values():
        for artifact_id in result["evidence_artifact_ids"]:
            if artifact_id not in artifact_by_id:
                findings.append(
                    PolicyFinding("EVIDENCE_REFERENCE_MISSING", "Result references an artifact outside the allowlist", artifact_id)
                )
    for value in _all_strings(request):
        lowered = value.lower()
        if value == _SAFE_SHA_ROLE:
            continue
        mentions_hash = any(token in lowered for token in ("sha", "hash", "digest"))
        mentions_geometry_proof = "geometr" in lowered and any(
            token in lowered for token in ("equival", "predicate", "proof", "proves")
        )
        if mentions_hash and mentions_geometry_proof:
            findings.append(
                PolicyFinding("SHA_GEOMETRY_MISUSE", "A hash or digest is presented as geometry evidence")
            )
            break
    return findings


def _retention_findings(request: Mapping[str, Any]) -> list[PolicyFinding]:
    artifacts = {
        artifact["artifact_id"]: artifact for artifact in request["source"]["allowlist"]
    }
    findings = []
    for history_field, expected_role in _EXPECTED_HISTORY_ROLES.items():
        for artifact_id in request["history"][history_field]:
            artifact = artifacts.get(artifact_id)
            if artifact is None or artifact["retention_role"] != expected_role:
                findings.append(
                    PolicyFinding(
                        "FAILURE_EVIDENCE_NOT_RETAINED",
                        "Declared failure or review evidence is absent or misclassified",
                        artifact_id,
                    )
                )
    return findings


def _report(
    findings_by_check: dict[str, list[PolicyFinding]],
    *,
    not_run: set[str] | None = None,
) -> dict[str, Any]:
    not_run = not_run or set()
    findings = sorted(
        (finding for values in findings_by_check.values() for finding in values),
        key=lambda item: (item.code, item.artifact_id or "", item.message),
    )
    return {
        "schema_version": "2.0.0",
        "status": "PASS" if not findings else "FAIL",
        "checks": {
            name: (
                "NOT_RUN"
                if name in not_run
                else "PASS" if not values else "FAIL"
            )
            for name, values in findings_by_check.items()
        },
        "findings": [finding.as_dict() for finding in findings],
    }


def validate_request(request: Mapping[str, Any], repository_root: Path) -> dict[str, Any]:
    schema_findings = _schema_findings(request)
    if schema_findings:
        dependent = {
            "git", "allowlist", "content", "result_separation", "failure_retention"
        }
        return _report(
            {
                "schema": schema_findings,
                "git": [],
                "allowlist": [],
                "content": [],
                "result_separation": [],
                "failure_retention": [],
            },
            not_run=dependent,
        )
    resolved, path_findings = _resolve_artifacts(request, Path(repository_root))
    return _report(
        {
            "schema": [],
            "git": _git_findings(request, Path(repository_root)),
            "allowlist": path_findings,
            "content": _sensitive_content_findings(resolved),
            "result_separation": _result_findings(request),
            "failure_retention": _retention_findings(request),
        }
    )


def resolve_allowlisted_files(
    request: Mapping[str, Any], repository_root: Path
) -> list[ResolvedArtifact]:
    resolved, findings = _resolve_artifacts(request, Path(repository_root))
    if findings:
        raise PolicyValidationError(findings)
    return resolved
