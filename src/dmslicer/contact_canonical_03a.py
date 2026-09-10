"""Host-side fixture, pairwise analysis, validation, and repeatability for A01--A06."""

from __future__ import annotations

import json
import math
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from .evidence import read_json, sha256_file, write_json


FREECAD_SCRIPT = Path(__file__).with_name("freecad_contact_03a.py")
TOLERANCES = {
    "length_unit": "mm",
    "area_unit": "mm2",
    "volume_unit": "mm3",
    "linear_epsilon_mm": 1e-7,
    "area_epsilon_mm2": 1e-8,
    "volume_epsilon_mm3": 1e-6,
    "engineering_tolerance_mm": 0.1,
}


class CanonicalValidationError(RuntimeError):
    """Raised after actual evidence and a failing validation record have been written."""


def _freecad_executable() -> Path:
    discovered = shutil.which("freecadcmd") or shutil.which("FreeCADCmd.exe")
    for candidate in (Path(discovered) if discovered else None, Path(r"C:\Program Files\FreeCAD 1.1\bin\freecadcmd.exe")):
        if candidate and candidate.is_file():
            return candidate
    raise FileNotFoundError("FreeCADCmd.exe was not found")


def _run_freecad(request: dict[str, Any]) -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="dmslicer_contact_03a_") as temporary:
        request_path = Path(temporary) / "request.json"
        response_path = Path(temporary) / "response.json"
        write_json(request_path, request)
        environment = os.environ.copy()
        environment.update({"DMSLICER_FREECAD_REQUEST": str(request_path), "DMSLICER_FREECAD_RESPONSE": str(response_path), "DMSLICER_FREECAD_SCRIPT": str(FREECAD_SCRIPT)})
        console = "import os; p=os.environ['DMSLICER_FREECAD_SCRIPT']; exec(compile(open(p, encoding='utf-8').read(), p, 'exec'))\n"
        completed = subprocess.run([str(_freecad_executable()), "--safe-mode", "-c"], input=console, env=environment, text=True, capture_output=True, timeout=120, check=False)
        if not response_path.is_file():
            raise RuntimeError(f"FreeCADCmd did not write a response: {completed.stderr}")
        response = read_json(response_path)
        if completed.returncode or response.get("status") == "FAILED":
            raise RuntimeError(f"FreeCADCmd contact 03A failed: {response}")
        return response


def _case_definitions() -> dict[str, dict[str, Any]]:
    raw = {
        "A01": {"relation": "full_full", "dimension": "2D", "raw_box": [20, 20, 20], "raw_measure": 400.0, "measure": "area_mm2", "geometry": "equal 20×20×10 prisms with coincident 20×20 end faces"},
        "A02": {"relation": "partial_partial", "dimension": "2D", "raw_box": [28, 20, 20], "raw_measure": 240.0, "measure": "area_mm2", "geometry": "A01 prisms with 8 mm raw x offset"},
        "A03": {"relation": "small_face_contained_in_large_face", "dimension": "2D", "raw_box": [20, 20, 20], "raw_measure": 80.0, "measure": "area_mm2", "geometry": "10×8 end face centered inside 20×20 end face"},
        "A04": {"relation": "point_touch", "dimension": "0D", "raw_box": [60, 60, 30], "raw_measure": 1, "measure": "point_count", "geometry": "r=10 sphere tangent to finite 60×60 plate"},
        "A05": {"relation": "edge_touch", "dimension": "1D", "raw_box": [30, 30, 20], "raw_measure": 20.0, "measure": "length_mm", "geometry": "two prisms sharing only a 20 mm raw edge"},
        "A06": {"relation": "solid_material_interference", "dimension": "3D", "raw_box": [28, 26, 24], "raw_measure": 2688.0, "measure": "volume_mm3", "geometry": "20×20×20 prisms offset by raw (8,6,4)"},
    }
    for definition in raw.values():
        length = math.sqrt(sum(axis * axis for axis in definition["raw_box"]))
        definition["scale"] = 100.0 / length
        power = {"area_mm2": 2, "length_mm": 1, "volume_mm3": 3, "point_count": 0}[definition["measure"]]
        definition["expected_measure"] = definition["raw_measure"] * definition["scale"] ** power
    return raw


def generate_contact_canonical(root: Path) -> dict[str, Any]:
    root = Path(root)
    generated = []
    for case_id, definition in _case_definitions().items():
        case_dir = root / case_id
        step_path = case_dir / "fixture.step"
        _run_freecad({"action": "generate", "case_id": case_id, "step_path": str(step_path), "scale": definition["scale"], "parameters": {"raw_geometry": definition["geometry"], "normalization": "L=100 mm"}})
        expected = {
            "schema_version": 1,
            "case_id": case_id,
            "geometry": definition["geometry"],
            "relation": definition["relation"],
            "dimension": definition["dimension"],
            "units": {"length": "mm", "area": "mm2", "volume": "mm3"},
            "tolerances": TOLERANCES,
            "measures": {definition["measure"]: definition["expected_measure"]},
            "ground_truth_mode": "analytic",
        }
        if case_id in {"A01", "A02", "A03"}:
            expected["coverage"] = {"A01": [1.0, 1.0], "A02": [0.6, 0.6], "A03": [0.2, 1.0]}[case_id]
            expected["provenance_scope"] = "actual_brep_direct_common"
        write_json(case_dir / "expected.json", expected)
        write_json(case_dir / "parameters.json", {"case_id": case_id, "raw_bounding_box_mm": definition["raw_box"], "scale": definition["scale"], "normalization": "combined bounding-box diagonal L=100 mm"})
        generated.append({"case_id": case_id, "step": str(step_path), "step_sha256": sha256_file(step_path)})
    return {"cases": generated}


def _validate(actual: dict[str, Any], expected: dict[str, Any]) -> dict[str, Any]:
    failures = []
    relation = actual["relation"]
    for field in ("relation", "dimension"):
        if relation.get(field) != expected.get(field):
            failures.append({"kind": field, "expected": expected.get(field), "actual": relation.get(field)})
    for key, expected_value in expected["measures"].items():
        actual_value = relation.get(key)
        tolerance = TOLERANCES["area_epsilon_mm2"] if key == "area_mm2" else TOLERANCES["volume_epsilon_mm3"] if key == "volume_mm3" else TOLERANCES["linear_epsilon_mm"] if key == "length_mm" else 0
        if actual_value is None or abs(actual_value - expected_value) > tolerance:
            failures.append({"kind": key, "expected": expected_value, "actual": actual_value, "tolerance": tolerance})
    if "coverage" in expected:
        for key, expected_value in zip(("coverage_a", "coverage_b"), expected["coverage"]):
            if abs(relation.get(key, -1) - expected_value) > 1e-7:
                failures.append({"kind": key, "expected": expected_value, "actual": relation.get(key)})
    if "provenance_scope" in expected:
        actual_scope = "actual_brep_direct_common" if relation.get("patches") else "not_applicable"
        if actual_scope != expected["provenance_scope"]:
            failures.append({"kind": "provenance_scope", "expected": expected["provenance_scope"], "actual": actual_scope})
    return {"schema_version": 1, "status": "PASS" if not failures else "FAIL", "failures": failures}


def analyze_contact_canonical(step_path: Path, output_dir: Path) -> dict[str, Any]:
    step_path, output_dir = Path(step_path), Path(output_dir)
    expected_path = step_path.with_name("expected.json")
    case_id = step_path.parent.name
    response = _run_freecad({"action": "analyze", "case_id": case_id, "step_path": str(step_path), "debug_path": str(output_dir / "debug.FCStd"), "tolerances": TOLERANCES})
    actual = {key: value for key, value in response.items() if key != "status"}
    actual["step_sha256"] = sha256_file(step_path)
    write_json(output_dir / "actual.json", actual)
    expected = read_json(expected_path)
    validation = _validate(actual, expected)
    write_json(output_dir / "validation.json", validation)
    actual["validation"] = validation
    write_json(output_dir / "actual.json", actual)
    if validation["status"] != "PASS":
        raise CanonicalValidationError("expected truth disagrees with completed actual B-rep evidence")
    return actual


def run_contact_canonical_repeatability(step_path: Path, output_dir: Path) -> dict[str, Any]:
    first = analyze_contact_canonical(step_path, Path(output_dir) / "run_1")
    second = analyze_contact_canonical(step_path, Path(output_dir) / "run_2")
    first_relation, second_relation = first["relation"], second["relation"]
    comparison = {
        "relation_match": (first_relation["relation"], first_relation["dimension"]) == (second_relation["relation"], second_relation["dimension"]),
        "relation_measure_match": {key: first_relation.get(key) for key in ("area_mm2", "length_mm", "volume_mm3", "point_count")} == {key: second_relation.get(key) for key in ("area_mm2", "length_mm", "volume_mm3", "point_count")},
        "coverage_match": (first_relation.get("coverage_a"), first_relation.get("coverage_b")) == (second_relation.get("coverage_a"), second_relation.get("coverage_b")),
        "provenance_linkage_match": first_relation.get("patches", []) == second_relation.get("patches", []),
        "geometry_digest_match": first_relation["evidence"]["geometry_digest"] == second_relation["evidence"]["geometry_digest"],
    }
    report = {"schema_version": 1, "processes": 2, "status": "PASS" if all(comparison.values()) else "FAIL", "comparison": comparison}
    write_json(Path(output_dir) / "repeatability.json", report)
    return report


def run_contact_canonical_suite(fixture_root: Path, output_root: Path) -> dict[str, Any]:
    """Publish a durable acceptance bundle from the six tracked STEP fixtures."""
    fixture_root, output_root = Path(fixture_root), Path(output_root)
    rows = {}
    for case_id in _case_definitions():
        step_path = fixture_root / case_id / "fixture.step"
        case_output = output_root / case_id
        actual = analyze_contact_canonical(step_path, case_output)
        repeatability = run_contact_canonical_repeatability(step_path, case_output / "repeatability")
        expected = read_json(step_path.with_name("expected.json"))
        measure_name, expected_measure = next(iter(expected["measures"].items()))
        actual_measure = actual["relation"].get(measure_name)
        rows[case_id] = {
            "relation": actual["relation"]["relation"],
            "dimension": actual["relation"]["dimension"],
            "expected_measure": {measure_name: expected_measure},
            "actual_measure": {measure_name: actual_measure},
            "absolute_error": abs(actual_measure - expected_measure),
            "coverage": [actual["relation"].get("coverage_a", "not_applicable"), actual["relation"].get("coverage_b", "not_applicable")],
            "provenance_scope": "actual_brep_direct_common" if actual["relation"].get("patches") else "not_applicable",
            "validation": actual["validation"]["status"],
            "repeatability": repeatability["status"],
            "debug_fcstd": str(case_output / "debug.FCStd"),
        }
    summary = {"schema_version": 1, "status": "PASS" if all(row["validation"] == "PASS" and row["repeatability"] == "PASS" for row in rows.values()) else "FAIL", "cases": rows}
    write_json(output_root / "summary.json", summary)
    index = ["# Contact Canonical 03A — view index", "", "Open each `debug.FCStd` in FreeCAD. `Body_1` and `Body_2` are the STEP-reimported solids; `Actual_Result` is the B-rep result produced by this analysis.", ""]
    for case_id, row in rows.items():
        index.append(f"- **{case_id}** — {row['relation']} ({row['dimension']}): `{case_id}/debug.FCStd`")
    (output_root / "VIEW_INDEX.md").write_text("\n".join(index) + "\n", encoding="utf-8")
    return summary
