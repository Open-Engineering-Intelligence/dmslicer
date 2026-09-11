"""Fail-closed policy checks for local evidence promotion."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import json
import os
from pathlib import Path, PurePosixPath
import re
import subprocess
from typing import Any, Mapping

from jsonschema import Draft202012Validator

from .cad_evidence import compare_semantics, compare_ui_states, validate_cad_artifact
from .models import read_json, schema_path


_GENERATED_PACKAGE_PATHS = {"manifest.json", "copy_inventory.json", "policy_report.json"}
_TEXT_KINDS = {"JUNIT", "VALIDATOR", "JSON", "TEXT", "VIEW_INDEX", "HUMAN_REVIEW"}
_RESULT_DOMAIN_ARTIFACT_KINDS = {
    "geometry_equivalence_result": {
        "FCSTD",
        "STEP",
        "BREP",
        "GEOMETRY_SNAPSHOT",
        "TOPOLOGY_SNAPSHOT",
        "COMPARISON_JSON",
    },
    "semantic_equivalence_result": {
        "GEOMETRY_SNAPSHOT",
        "TOPOLOGY_SNAPSHOT",
        "COMPARISON_JSON",
    },
    "ui_state_result": {"UI_SNAPSHOT", "COMPARISON_JSON"},
    "pytest_result": {"JUNIT", "JSON", "TEXT"},
    "validator_result": {"VALIDATOR"},
    "scientific_experiment_result": {"JSON", "TEXT", "OTHER", "JUNIT"},
    "human_inspection_result": {"HUMAN_REVIEW"},
}
_EXPECTED_HISTORY_ROLES = {
    "failure_artifact_ids": "FAILURE",
    "mismatch_artifact_ids": "MISMATCH",
    "rejection_artifact_ids": "REJECTION",
    "reviewer_finding_artifact_ids": "REVIEWER_FINDING",
}
_SAFE_SHA_ROLE = "file_and_copy_integrity_only_not_geometry_equivalence"
_CAD_KIND_ARTIFACT_TYPES = {
    "GEOMETRY_SNAPSHOT": "geometry_semantic_snapshot",
    "TOPOLOGY_SNAPSHOT": "topology_snapshot",
    "UI_SNAPSHOT": "ui_state_snapshot",
    "COMPARISON_JSON": "geometry_comparison",
}
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
    execution = request.get("execution")
    if isinstance(execution, list):
        for index, record in enumerate(execution):
            if not isinstance(record, Mapping):
                continue
            timestamp = record.get("timestamp")
            if not isinstance(timestamp, str):
                continue
            try:
                parsed = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
                valid_timestamp = "T" in timestamp and parsed.tzinfo is not None
            except ValueError:
                valid_timestamp = False
            if not valid_timestamp:
                findings.append(
                    PolicyFinding(
                        "SCHEMA_INVALID",
                        f"Request schema validation failed at execution.{index}.timestamp",
                    )
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


def portable_relative_path(value: str) -> Path | None:
    """Parse a repository-relative path consistently on Windows and POSIX hosts."""
    normalized = value.replace("\\", "/")
    if normalized == ".":
        return Path(".")
    if not normalized:
        return None
    if re.match(r"^[A-Za-z]:", normalized):
        return None
    pure = PurePosixPath(normalized)
    if pure.is_absolute() or not pure.parts:
        return None
    if ".." in pure.parts:
        return None
    return Path(*pure.parts)


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
    staging_input = portable_relative_path(request["source"]["staging_root"])
    if (
        staging_input is None
        or staging_input == Path(".")
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
        source_input = portable_relative_path(artifact["source_path"])
        public_input = portable_relative_path(artifact["public_path"])
        if artifact_id in seen_ids:
            findings.append(PolicyFinding("PUBLIC_PATH_INVALID", "Artifact IDs must be unique", artifact_id))
        seen_ids.add(artifact_id)

        if public_input is None or public_input == Path("."):
            findings.append(
                PolicyFinding("PUBLIC_PATH_INVALID", "Public path must be a safe relative file path", artifact_id)
            )
            public_key = ""
        else:
            public_key = public_input.as_posix().lower()
        if public_key in _GENERATED_PACKAGE_PATHS or public_key in seen_public:
            findings.append(
                PolicyFinding("PUBLIC_PATH_INVALID", "Public path is reserved or duplicated", artifact_id)
            )
        seen_public.add(public_key)

        if source_input is None:
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
    by_domain: dict[str, set[str]] = {}
    for domain, result in request["results"].items():
        artifact_ids = result["evidence_artifact_ids"]
        by_domain[domain] = set(artifact_ids)
        for artifact_id in artifact_ids:
            if artifact_id not in artifact_by_id:
                findings.append(
                    PolicyFinding(
                        "EVIDENCE_REFERENCE_MISSING",
                        "Result references an artifact outside the allowlist",
                        artifact_id,
                    )
                )
                continue
            allowed_kinds = _RESULT_DOMAIN_ARTIFACT_KINDS.get(domain)
            if allowed_kinds is None:
                continue
            kind = artifact_by_id[artifact_id]["kind"]
            if kind not in allowed_kinds:
                findings.append(
                    PolicyFinding(
                        "RESULT_EVIDENCE_MISMATCH",
                        f"{domain} may only reference {sorted(allowed_kinds)} artifacts",
                        artifact_id,
                    )
                )

    for artifact_id in artifact_by_id:
        referenced_domains = [
            domain
            for domain, evidence_ids in by_domain.items()
            if artifact_id in evidence_ids and domain in _RESULT_DOMAIN_ARTIFACT_KINDS
        ]
        if len(referenced_domains) > 1:
            findings.append(
                PolicyFinding(
                    "RESULT_EVIDENCE_DOMAIN_OVERLAP",
                    "One evidence artifact is used in multiple result domains",
                    artifact_id,
                )
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


def _comparison_consistency_findings(
    artifact_id: str,
    comparison: Mapping[str, Any],
    request_tolerances: list[Mapping[str, Any]],
) -> list[PolicyFinding]:
    """Recompute the fixture comparison decision from measurements and tolerances."""
    findings: list[PolicyFinding] = []
    comparison_tolerances = {
        item["name"]: (item["value"], item["unit"])
        for item in comparison["tolerances"]
    }
    declared_tolerances = {
        item["name"]: (item["value"], item["unit"])
        for item in request_tolerances
    }
    if comparison_tolerances != declared_tolerances:
        findings.append(
            PolicyFinding(
                "CAD_COMPARISON_INCONSISTENT",
                "Comparison tolerances do not match the promotion request",
                artifact_id,
            )
        )
    expected_units = {"linear": "mm", "area": "mm2", "volume": "mm3"}
    if (
        set(comparison_tolerances) != set(expected_units)
        or any(
            comparison_tolerances[name][1] != unit
            for name, unit in expected_units.items()
            if name in comparison_tolerances
        )
    ):
        findings.append(
            PolicyFinding(
                "CAD_COMPARISON_INCONSISTENT",
                "Comparison tolerance names and units are not the fixture contract",
                artifact_id,
            )
        )

    measurement_checks = {
        "area_delta": ("area_delta", "area"),
        "volume_delta": ("volume_delta", "volume"),
        "bounding_box": ("max_bounding_box_delta", "linear"),
        "first_minus_second": ("first_minus_second_volume", "volume"),
        "second_minus_first": ("second_minus_first_volume", "volume"),
    }
    checks = comparison["checks"]
    measurements = comparison["measurements"]
    for check_name, (measurement_name, tolerance_name) in measurement_checks.items():
        measurement = measurements[measurement_name]
        declared_check = checks[check_name]
        if "value" not in measurement or tolerance_name not in comparison_tolerances:
            expected_check: bool | None = None
        else:
            expected_check = (
                abs(float(measurement["value"]))
                <= float(comparison_tolerances[tolerance_name][0])
            )
        if expected_check is not None and declared_check is not expected_check:
            findings.append(
                PolicyFinding(
                    "CAD_COMPARISON_INCONSISTENT",
                    f"{check_name} does not match its measurement and tolerance",
                    artifact_id,
                )
            )

    boolean_checks = {
        name: value for name, value in checks.items() if isinstance(value, bool)
    }
    unavailable_checks = [
        name for name, value in checks.items() if isinstance(value, Mapping)
    ]
    expected_failed = sorted(
        name for name, value in boolean_checks.items() if value is False
    )
    if unavailable_checks:
        expected_status = "GEOMETRIC_EQUIVALENCE_NOT_PROVEN"
    elif expected_failed:
        expected_status = "GEOMETRY_DIFFERENT"
    else:
        expected_status = "GEOMETRY_EQUIVALENT"
    reasons = comparison["reasons"]
    reason_text = " ".join(reasons).lower()
    reason_tokens = {
        "valid_closed_single_solids": ("valid", "closed", "solid"),
        "topology_counts": ("topology",),
        "area_delta": ("area",),
        "volume_delta": ("volume",),
        "bounding_box": ("bounding", "bbox"),
        "first_minus_second": ("boolean", "first", "cut"),
        "second_minus_first": ("boolean", "second", "cut"),
    }
    uncovered_failures = [
        name
        for name in expected_failed
        if not any(token in reason_text for token in reason_tokens[name])
    ]
    if (
        comparison["status"] != expected_status
        or sorted(comparison["failed_checks"]) != expected_failed
        or (expected_status == "GEOMETRY_EQUIVALENT" and reasons)
        or (expected_status != "GEOMETRY_EQUIVALENT" and not reasons)
        or uncovered_failures
        or any(token in reason_text for token in ("sha", "hash", "digest", "byte"))
    ):
        findings.append(
            PolicyFinding(
                "CAD_COMPARISON_INCONSISTENT",
                "Comparison status, failed checks, and reasons are not mutually consistent",
                artifact_id,
            )
        )
    return findings


def _cad_evidence_findings(
    request: Mapping[str, Any], artifacts: list[ResolvedArtifact]
) -> list[PolicyFinding]:
    """Validate only the fixture-scoped CAD claims admitted by the P2 schema."""
    results = request["results"]
    domain_results = {
        "geometry": results["geometry_equivalence_result"],
        "semantic": results["semantic_equivalence_result"],
        "ui": results["ui_state_result"],
    }
    proven = {
        domain: result
        for domain, result in domain_results.items()
        if result["evidence_artifact_ids"]
    }
    allowlisted_ids = {
        artifact["artifact_id"] for artifact in request["source"]["allowlist"]
    }
    resolved_by_id = {artifact.artifact_id: artifact for artifact in artifacts}
    referenced_ids = {
        artifact_id
        for result in proven.values()
        for artifact_id in result["evidence_artifact_ids"]
    }
    referenced_ids.update(request["geometry_validation"]["evidence_artifact_ids"])
    cad_artifact_ids = {
        artifact.artifact_id
        for artifact in artifacts
        if artifact.kind in _CAD_KIND_ARTIFACT_TYPES
    }
    findings: list[PolicyFinding] = []
    values: dict[str, dict[str, Any]] = {}
    for artifact_id in sorted(referenced_ids | cad_artifact_ids):
        if artifact_id not in allowlisted_ids or artifact_id not in resolved_by_id:
            findings.append(
                PolicyFinding(
                    "CAD_EVIDENCE_REFERENCE_MISSING",
                    "CAD result references unavailable allowlisted evidence",
                    artifact_id,
                )
            )
            continue
        try:
            value = read_json(resolved_by_id[artifact_id].source_path)
        except (OSError, ValueError, json.JSONDecodeError):
            findings.append(
                PolicyFinding(
                    "CAD_EVIDENCE_SCHEMA_INVALID",
                    "CAD evidence is not a valid JSON artifact",
                    artifact_id,
                )
            )
            continue
        strings = list(_all_strings(value))
        artifact_claims_hash_geometry = any(
            text != _SAFE_SHA_ROLE
            and any(token in text.lower() for token in ("sha", "hash", "digest"))
            and "geometr" in text.lower()
            and any(
                token in text.lower()
                for token in ("equival", "predicate", "proof", "proves")
            )
            for text in strings
        )
        schema_errors = validate_cad_artifact(value)
        if schema_errors:
            findings.append(
                PolicyFinding(
                    "CAD_EVIDENCE_SCHEMA_INVALID",
                    "CAD evidence does not satisfy the fixture evidence schema",
                    artifact_id,
                )
            )
            method = str(value.get("method", "")).lower()
            if any(token in method for token in ("sha", "hash", "digest")) or artifact_claims_hash_geometry:
                findings.append(
                    PolicyFinding(
                        "SHA_GEOMETRY_MISUSE",
                        "A hash or digest is presented as a geometry comparison method",
                        artifact_id,
                    )
                )
            continue
        artifact = resolved_by_id[artifact_id]
        expected_artifact_type = _CAD_KIND_ARTIFACT_TYPES.get(artifact.kind)
        if (
            expected_artifact_type is not None
            and value.get("artifact_type") != expected_artifact_type
        ):
            findings.append(
                PolicyFinding(
                    "CAD_EVIDENCE_KIND_MISMATCH",
                    f"{artifact.kind} requires artifact_type={expected_artifact_type}",
                    artifact_id,
                )
            )
            continue
        if artifact_claims_hash_geometry:
            findings.append(
                PolicyFinding(
                    "SHA_GEOMETRY_MISUSE",
                    "A hash or digest is presented as geometry evidence",
                    artifact_id,
                )
            )
        values[artifact_id] = value
        if value.get("artifact_type") == "geometry_comparison":
            findings.extend(
                _comparison_consistency_findings(
                    artifact_id, value, request["tolerances"]
                )
            )

    geometry = proven.get("geometry")
    if geometry is not None:
        comparisons = [
            values[artifact_id]
            for artifact_id in geometry["evidence_artifact_ids"]
            if artifact_id in values
            and values[artifact_id].get("artifact_type") == "geometry_comparison"
        ]
        validation = request["geometry_validation"]
        if (
            not comparisons
            or comparisons[0]["status"] != geometry["status"]
            or validation["status"] != geometry["status"]
            or comparisons[0]["method"] != validation["evidence_method"]
            or not set(validation["evidence_artifact_ids"]).issubset(
                set(geometry["evidence_artifact_ids"])
            )
        ):
            findings.append(
                PolicyFinding(
                    "CAD_RESULT_MISMATCH",
                    "Geometry result does not match its B-rep comparison evidence",
                )
            )

    semantic = proven.get("semantic")
    if semantic is not None:
        snapshots = [
            values[artifact_id]
            for artifact_id in semantic["evidence_artifact_ids"]
            if artifact_id in values
            and values[artifact_id].get("artifact_type")
            == "geometry_semantic_snapshot"
        ]
        status = (
            compare_semantics(
                snapshots[0]["semantic_binding"], snapshots[1]["semantic_binding"]
            )["status"]
            if len(snapshots) == 2
            else None
        )
        if status != semantic["status"]:
            findings.append(
                PolicyFinding(
                    "CAD_RESULT_MISMATCH",
                    "Semantic result does not match its two fixture snapshots",
                )
            )

    ui = proven.get("ui")
    if ui is not None:
        snapshots = [
            values[artifact_id]
            for artifact_id in ui["evidence_artifact_ids"]
            if artifact_id in values
            and values[artifact_id].get("artifact_type") == "ui_state_snapshot"
        ]
        status = compare_ui_states(snapshots[0], snapshots[1])["status"] if len(snapshots) == 2 else None
        if status != ui["status"]:
            findings.append(
                PolicyFinding(
                    "CAD_RESULT_MISMATCH",
                    "UI result does not match its two saved-state snapshots",
                )
            )
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
            "result_separation": (
                _result_findings(request) + _cad_evidence_findings(request, resolved)
            ),
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
