from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys

import pytest


SOURCE_ROOT = Path(__file__).resolve().parents[1] / "src"


def _git(repository: Path, *arguments: str) -> str:
    return subprocess.run(
        ["git", *arguments], cwd=repository, check=True, capture_output=True, text=True
    ).stdout.strip()


@pytest.fixture
def cli_case(tmp_path: Path, valid_request):
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
        '{"status":"PASS"}\n', encoding="utf-8"
    )
    request = valid_request()
    request["identity"].update(
        {
            "implementation_commit": implementation,
            "parent_baseline": baseline,
            "merge_base": baseline,
        }
    )
    request_path = staging / "request.json"
    request_path.write_text(json.dumps(request, indent=2) + "\n", encoding="utf-8")
    return repository, request, request_path


def _run(repository: Path, *arguments: str) -> subprocess.CompletedProcess[str]:
    environment = os.environ.copy()
    environment["PYTHONPATH"] = str(SOURCE_ROOT)
    return subprocess.run(
        [sys.executable, "-m", "dmslicer.evidence_promotion", *arguments],
        cwd=repository,
        env=environment,
        check=False,
        capture_output=True,
        text=True,
    )


def test_validate_command_prints_json_and_exits_zero(cli_case) -> None:
    repository, _, request_path = cli_case

    completed = _run(
        repository,
        "validate",
        "--repository-root", ".",
        "--request", str(request_path),
    )

    assert completed.returncode == 0, completed.stderr
    assert completed.stderr == ""
    assert json.loads(completed.stdout)["status"] == "PASS"


def test_validate_command_exits_two_for_policy_failure(cli_case) -> None:
    repository, request, request_path = cli_case
    request["source"]["allowlist"][0]["source_path"] = "missing.json"
    request_path.write_text(json.dumps(request) + "\n", encoding="utf-8")

    completed = _run(
        repository,
        "validate",
        "--repository-root", ".",
        "--request", str(request_path),
    )

    assert completed.returncode == 2
    assert json.loads(completed.stdout)["status"] == "FAIL"


def test_promote_command_succeeds_for_local_package_while_preservation_is_incomplete(
    cli_case,
) -> None:
    repository, _, request_path = cli_case

    completed = _run(
        repository,
        "promote",
        "--repository-root", ".",
        "--request", str(request_path),
    )

    result = json.loads(completed.stdout)
    assert completed.returncode == 0, completed.stderr
    assert result["local_package_status"] == "LOCAL_PACKAGE_CREATED"
    assert result["preservation_status"] == "NOT_FULLY_PRESERVED"
    assert result["publication_status"] == "PUBLICATION_NOT_AUTHORIZED"


def test_malformed_json_does_not_echo_secret_or_traceback(cli_case) -> None:
    repository, _, request_path = cli_case
    secret = "do-not-echo-this-secret"
    request_path.write_text('{"password":"' + secret, encoding="utf-8")

    completed = _run(
        repository,
        "validate",
        "--repository-root", ".",
        "--request", str(request_path),
    )

    combined = completed.stdout + completed.stderr
    assert completed.returncode == 2
    assert json.loads(completed.stdout) == {
        "code": "INVALID_REQUEST_JSON",
        "schema_version": "2.0.0",
        "status": "ERROR",
    }
    assert secret not in combined
    assert "Traceback" not in combined
