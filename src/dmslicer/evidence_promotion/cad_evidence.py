"""Fixture-scoped CAD evidence validation and comparison helpers."""

from __future__ import annotations

import math
import os
import shutil
import subprocess
import tempfile
import hashlib
from pathlib import Path
from typing import Any, Mapping

from jsonschema import Draft202012Validator

from .models import (
    SEMANTIC_DIFFERENT,
    SEMANTIC_EQUIVALENCE_NOT_PROVEN,
    SEMANTIC_EQUIVALENT,
    UI_COMPARISON_NOT_PROVEN,
    UI_DIFFERENT,
    UI_SAME,
    read_json,
    schema_path,
    write_json,
)


_SEMANTIC_FIELDS = ("component_role", "interface_role", "allowed_transform")
_UI_FIELDS = ("shape_color", "transparency", "visibility")
_FREECAD_WORKER = Path(__file__).with_name("freecad_cad_evidence.py")


def _nonfinite_paths(value: Any, path: tuple[str, ...] = ()):
    if isinstance(value, float) and not math.isfinite(value):
        yield ".".join(path) or "artifact"
    elif isinstance(value, Mapping):
        for key, item in value.items():
            yield from _nonfinite_paths(item, (*path, str(key)))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            yield from _nonfinite_paths(item, (*path, str(index)))


def _leaf_errors(error):
    if error.context:
        for child in error.context:
            yield from _leaf_errors(child)
    else:
        yield error


def _error_path(error) -> str:
    parts = [str(part) for part in error.absolute_path]
    if error.validator == "required" and isinstance(error.instance, Mapping):
        missing = [name for name in error.validator_value if name not in error.instance]
        if len(missing) == 1:
            parts.append(missing[0])
    return ".".join(parts) or "artifact"


def validate_cad_artifact(value: Mapping[str, Any]) -> list[str]:
    """Return deterministic public-safe validation findings for one CAD artifact."""
    schema = read_json(schema_path("cad_evidence.schema.json"))
    validator = Draft202012Validator(schema)
    findings = []
    errors = [leaf for error in validator.iter_errors(value) for leaf in _leaf_errors(error)]
    for error in sorted(errors, key=lambda item: list(item.absolute_path)):
        findings.append(f"{_error_path(error)}: {error.message}")
    findings.extend(f"{path}: numeric evidence must be finite" for path in _nonfinite_paths(value))
    return sorted(set(findings))


def within_tolerance(
    measured: float, tolerance: Mapping[str, Any], expected_unit: str
) -> bool:
    """Apply an inclusive, unit-checked tolerance to one finite delta."""
    limit = tolerance.get("value")
    if (
        isinstance(measured, bool)
        or isinstance(limit, bool)
        or not isinstance(measured, (int, float))
        or not isinstance(limit, (int, float))
        or not math.isfinite(float(measured))
        or not math.isfinite(float(limit))
        or float(limit) < 0.0
    ):
        raise ValueError("tolerance inputs must be finite numbers with a nonnegative limit")
    if tolerance.get("unit") != expected_unit:
        raise ValueError("tolerance unit does not match measurement")
    return abs(float(measured)) <= float(limit)


def compare_semantics(
    first: Mapping[str, Any], second: Mapping[str, Any]
) -> dict[str, Any]:
    """Compare only the three explicit semantic fields used by the P2 fixture."""
    if any(
        not isinstance(binding.get(field), str) or not binding.get(field)
        for binding in (first, second)
        for field in _SEMANTIC_FIELDS
    ):
        return {
            "status": SEMANTIC_EQUIVALENCE_NOT_PROVEN,
            "differences": [],
            "reason": "required fixture semantic binding is missing or unsupported",
        }
    differences = sorted(field for field in _SEMANTIC_FIELDS if first[field] != second[field])
    return {
        "status": SEMANTIC_DIFFERENT if differences else SEMANTIC_EQUIVALENT,
        "differences": differences,
    }


def compare_ui_states(
    first: Mapping[str, Any], second: Mapping[str, Any]
) -> dict[str, Any]:
    """Compare saved fixture UI properties without emitting a geometry decision."""
    states = (first.get("state"), second.get("state"))
    if not all(isinstance(state, Mapping) for state in states):
        return {
            "status": UI_COMPARISON_NOT_PROVEN,
            "differences": [],
            "reason": "required saved UI state is unavailable",
        }
    for state in states:
        assert isinstance(state, Mapping)
        for field in _UI_FIELDS:
            value = state.get(field)
            if not isinstance(value, Mapping) or value.get("status") != "SUPPORTED" or "value" not in value:
                return {
                    "status": UI_COMPARISON_NOT_PROVEN,
                    "differences": [],
                    "reason": "required saved UI state is unavailable",
                }
    first_state, second_state = states
    assert isinstance(first_state, Mapping) and isinstance(second_state, Mapping)
    differences = sorted(
        field
        for field in _UI_FIELDS
        if first_state[field]["value"] != second_state[field]["value"]
    )
    return {"status": UI_DIFFERENT if differences else UI_SAME, "differences": differences}


def _freecad_executable(*, gui: bool) -> Path:
    names = ("FreeCAD.exe", "freecad") if gui else ("FreeCADCmd.exe", "freecadcmd")
    discovered = next((shutil.which(name) for name in names if shutil.which(name)), None)
    installed = Path(r"C:\Program Files\FreeCAD 1.1\bin") / names[0]
    for candidate in (Path(discovered) if discovered else None, installed):
        if candidate is not None and candidate.is_file():
            return candidate
    raise FileNotFoundError("required FreeCAD executable was not found")


def run_freecad_worker(
    request: Mapping[str, Any], output_root: Path, *, gui: bool
) -> dict[str, Any]:
    """Run the fixture-scoped worker without exposing temporary paths on failure."""
    output_root = Path(output_root).resolve()
    output_root.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="dmslicer_p2_cad_") as temporary:
        request_path = Path(temporary) / "request.json"
        response_path = Path(temporary) / "response.json"
        write_json(request_path, {**request, "output_root": str(output_root)})
        environment = os.environ.copy()
        environment.update(
            {
                "DMSLICER_CAD_REQUEST": str(request_path),
                "DMSLICER_CAD_RESPONSE": str(response_path),
            }
        )
        executable = _freecad_executable(gui=gui)
        if gui:
            command = [str(executable), "--safe-mode", str(_FREECAD_WORKER)]
            completed = subprocess.run(
                command,
                env=environment,
                text=True,
                capture_output=True,
                timeout=120,
                check=False,
            )
        else:
            console = (
                "import os; p=r'%s'; "
                "exec(compile(open(p, encoding='utf-8').read(), p, 'exec'))\n"
                % str(_FREECAD_WORKER)
            )
            completed = subprocess.run(
                [str(executable), "--safe-mode", "-c"],
                input=console,
                env=environment,
                text=True,
                capture_output=True,
                timeout=120,
                check=False,
            )
        if not response_path.is_file():
            raise RuntimeError(
                f"FreeCAD worker failed without a response (exit_code={completed.returncode})"
            )
        response = read_json(response_path)
        if completed.returncode or response.get("status") != "PASS":
            code = response.get("error_code", "WORKER_FAILED")
            raise RuntimeError(f"FreeCAD worker failed ({code})")
        return response


def generate_demo(output_root: Path) -> dict[str, Any]:
    """Generate three immutable fixture variants and their reopened snapshots."""
    output_root = Path(output_root)
    if output_root.exists() and any(output_root.iterdir()):
        raise FileExistsError("demo output root must be absent or empty")
    generated = run_freecad_worker(
        {"operation": "generate_fixture_set"}, output_root, gui=True
    )
    compared = run_freecad_worker(
        {
            "operation": "snapshot_and_compare",
            "comparisons": ["case_a", "case_b", "serialization"],
        },
        output_root,
        gui=False,
    )
    original_root = output_root / "cad" / "original"
    changed_root = output_root / "cad" / "ui_only_changed"
    first_semantic = read_json(
        output_root / "snapshots" / "original" / "geometry_semantic_snapshot.json"
    )["semantic_binding"]
    second_semantic = read_json(
        output_root
        / "snapshots"
        / "ui_only_changed"
        / "geometry_semantic_snapshot.json"
    )["semantic_binding"]
    first_ui = read_json(
        output_root / "snapshots" / "original" / "ui_state_snapshot.json"
    )
    second_ui = read_json(
        output_root / "snapshots" / "ui_only_changed" / "ui_state_snapshot.json"
    )

    def digest(path: Path) -> str:
        value = hashlib.sha256()
        with path.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                value.update(chunk)
        return value.hexdigest()

    comparison = read_json(output_root / "comparisons" / "case_a_ui_only.json")
    case_b_comparison = read_json(
        output_root / "comparisons" / "case_b_geometry_changed.json"
    )
    serialization_comparison = read_json(
        output_root / "comparisons" / "serialization_reopen.json"
    )
    return {
        "status": "PASS",
        "cases": generated["cases"],
        "case_a": {
            "geometry_status": comparison["status"],
            "semantic_status": compare_semantics(first_semantic, second_semantic)["status"],
            "ui_status": compare_ui_states(first_ui, second_ui)["status"],
            "byte_status": (
                "BYTE_SAME"
                if digest(original_root / "fixture.FCStd")
                == digest(changed_root / "fixture.FCStd")
                else "BYTE_DIFFERENT"
            ),
        },
        "case_b": {"geometry_status": case_b_comparison["status"]},
        "serialization": {
            "geometry_status": serialization_comparison["status"],
            "byte_status": (
                "BYTE_SAME"
                if digest(original_root / "fixture.FCStd")
                == digest(output_root / "cad/serialization_reopen/fixture.FCStd")
                else "BYTE_DIFFERENT"
            ),
            "geometry_decision_inputs": serialization_comparison[
                "geometry_decision_inputs"
            ],
        },
        "comparison_worker": compared["status"],
    }
