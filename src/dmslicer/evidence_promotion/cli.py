"""Command-line interface for P2 MVP validation and local promotion."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Sequence

from .cad_evidence import generate_demo, write_demo_promotion_request
from .models import LOCAL_PACKAGE_CREATED, read_json
from .policy import validate_request
from .promotion import promote


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m dmslicer.evidence_promotion",
        description="Validate or locally promote an explicit DM-Slicer evidence allowlist.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    for command in ("validate", "promote"):
        command_parser = subparsers.add_parser(command)
        command_parser.add_argument("--repository-root", required=True)
        command_parser.add_argument("--request", required=True)
    demo_parser = subparsers.add_parser("demo")
    demo_parser.add_argument("--output-root", required=True)
    return parser


def _emit(value: dict) -> None:
    sys.stdout.write(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n")


def _input_error(code: str) -> int:
    _emit({"code": code, "schema_version": "2.0.0", "status": "ERROR"})
    return 2


def main(argv: Sequence[str] | None = None) -> int:
    arguments = _parser().parse_args(argv)
    if arguments.command == "demo":
        repository_root = Path.cwd().resolve()
        output_root = Path(arguments.output_root).resolve()
        try:
            relative = output_root.relative_to(repository_root)
        except ValueError:
            return _input_error("DEMO_OUTPUT_ROOT_INVALID")
        if not relative.parts or relative.parts[0].lower() not in {"outputs", "work"}:
            return _input_error("DEMO_OUTPUT_ROOT_INVALID")
        try:
            result = generate_demo(output_root)
            request_path = write_demo_promotion_request(
                output_root, repository_root, result
            )
        except (OSError, RuntimeError):
            return _input_error("DEMO_EXECUTION_FAILED")
        result["promotion_request"] = request_path.relative_to(repository_root).as_posix()
        _emit(result)
        return 0

    try:
        repository_root = Path(arguments.repository_root).resolve(strict=True)
        request_path = Path(arguments.request)
        request = read_json(request_path)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return _input_error("INVALID_REQUEST_JSON")
    except OSError:
        return _input_error("REQUEST_UNAVAILABLE")

    if arguments.command == "validate":
        result = validate_request(request, repository_root)
        _emit(result)
        return 0 if result["status"] == "PASS" else 2

    result = promote(request_path, repository_root)
    _emit(result)
    return 0 if result["local_package_status"] == LOCAL_PACKAGE_CREATED else 2
