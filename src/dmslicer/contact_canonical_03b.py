"""Host-side fixture, validation, and repeatability for frozen A07--A09 cases."""

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


FREECAD_SCRIPT = Path(__file__).with_name("freecad_contact_03b.py")
TOLERANCES = {"length_unit": "mm", "area_unit": "mm2", "volume_unit": "mm3", "linear_epsilon_mm": 1e-7, "area_epsilon_mm2": 1e-8, "volume_epsilon_mm3": 1e-6, "engineering_tolerance_mm": 0.1}


class CanonicalAnalyticValidationError(RuntimeError):
    """Raised after actual evidence and a failed independent validation are written."""


def _freecad_executable() -> Path:
    discovered = shutil.which("freecadcmd") or shutil.which("FreeCADCmd.exe")
    for candidate in (Path(discovered) if discovered else None, Path(r"C:\\Program Files\\FreeCAD 1.1\\bin\\freecadcmd.exe")):
        if candidate and candidate.is_file():
            return candidate
    raise FileNotFoundError("FreeCADCmd.exe was not found")


def _run_freecad(request: dict[str, Any]) -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="dmslicer_contact_03b_") as temporary:
        request_path, response_path = Path(temporary) / "request.json", Path(temporary) / "response.json"
        write_json(request_path, request)
        environment = os.environ.copy()
        environment.update({"DMSLICER_FREECAD_REQUEST": str(request_path), "DMSLICER_FREECAD_RESPONSE": str(response_path), "DMSLICER_FREECAD_SCRIPT": str(FREECAD_SCRIPT)})
        console = "import os; p=os.environ['DMSLICER_FREECAD_SCRIPT']; exec(compile(open(p, encoding='utf-8').read(), p, 'exec'))\n"
        completed = subprocess.run([str(_freecad_executable()), "--safe-mode", "-c"], input=console, env=environment, text=True, capture_output=True, timeout=120, check=False)
        if not response_path.is_file():
            raise RuntimeError(f"FreeCADCmd did not write a response: {completed.stderr}")
        response = read_json(response_path)
        if completed.returncode or response.get("status") == "FAILED":
            raise RuntimeError(f"FreeCADCmd contact 03B failed: {response}")
        return response


def _case_definitions() -> dict[str, dict[str, Any]]:
    alpha = math.pi / 2
    beta = math.pi / 4
    return {
        "A07": {"relation": "exact", "surface_family": "cylinder", "raw_bbox": [40.0, 40.0, 40.0], "raw_area": 2 * math.pi * 10 * 30, "geometry": "r=10 mm shaft and r=10 mm bore over l=30 mm with end clearance", "topology": {"boundary_component_count": 2, "hole_count": 1}},
        "A08": {"relation": "solid_cavity_wall_touch", "surface_family": "sphere", "raw_bbox": [30.0, 30.0, 25.0], "raw_area": 2 * math.pi * 10**2 * (1 - math.cos(alpha)), "geometry": "r=10 mm sphere against a concave upper-hemisphere cavity cap (alpha=90 deg)", "topology": {"boundary_component_count": 1, "hole_count": 0}},
        "A09": {"relation": "exact", "surface_family": "cone", "raw_bbox": [54.0, 54.0, 17.0], "raw_area": math.pi * (10 + 20) * ((20 - 10) / math.sin(beta)), "geometry": "r0=10 mm, r1=20 mm, beta=45 deg matching conical frustum and a z=-5..12 mm seat", "topology": {"boundary_component_count": 2, "hole_count": 1}},
    }


def generate_contact_canonical_analytic(root: Path) -> dict[str, Any]:
    root = Path(root)
    generated = []
    for case_id, definition in _case_definitions().items():
        case_dir = root / case_id
        scale = 100.0 / math.sqrt(sum(axis**2 for axis in definition["raw_bbox"]))
        step_path = case_dir / "fixture.step"
        _run_freecad({"action": "generate", "case_id": case_id, "step_path": str(step_path), "scale": scale})
        expected = {"schema_version": 1, "case_id": case_id, "geometry": definition["geometry"], "relation": definition["relation"], "dimension": "2D", "units": {"length": "mm", "area": "mm2", "volume": "mm3"}, "tolerances": TOLERANCES, "measures": {"area_mm2": definition["raw_area"] * scale**2}, "coverage": {"A07": [1.0, 0.75], "A08": [0.5, 1.0], "A09": [1.0, 100.0 / 153.0]}[case_id], "support_surface_family": definition["surface_family"], "patch_topology": {"component_count": 1, "connectedness": "connected", "boundary_component_count": definition["topology"]["boundary_component_count"], "hole_count": definition["topology"]["hole_count"]}, "provenance_scope": "actual_brep_direct_common", "ground_truth_mode": "analytic"}
        write_json(case_dir / "expected.json", expected)
        write_json(case_dir / "parameters.json", {"case_id": case_id, "raw_bounding_box_mm": definition["raw_bbox"], "scale": scale, "normalization": "combined bounding-box diagonal L=100 mm", "geometry": definition["geometry"], "analytic_area_formula": {"A07": "2*pi*r*l", "A08": "2*pi*r^2*(1-cos(alpha))", "A09": "pi*(r0+r1)*(r1-r0)/sin(beta)"}[case_id]})
        generated.append({"case_id": case_id, "step": str(step_path), "step_sha256": sha256_file(step_path)})
    return {"cases": generated}


def _validate(actual: dict[str, Any], expected: dict[str, Any]) -> dict[str, Any]:
    relation, failures = actual["relation"], []
    for field in ("relation", "dimension", "support_surface_family"):
        if relation.get(field) != expected.get(field):
            failures.append({"kind": field, "expected": expected.get(field), "actual": relation.get(field)})
    area = relation.get("area_mm2")
    if area is None or abs(area - expected["measures"]["area_mm2"]) > TOLERANCES["area_epsilon_mm2"]:
        failures.append({"kind": "area_mm2", "expected": expected["measures"]["area_mm2"], "actual": area, "tolerance": TOLERANCES["area_epsilon_mm2"]})
    for key, value in zip(("coverage_a", "coverage_b"), expected["coverage"]):
        if abs(relation.get(key, -1) - value) > 1e-7:
            failures.append({"kind": key, "expected": value, "actual": relation.get(key)})
    for key, value in expected["patch_topology"].items():
        if relation.get(key) != value:
            failures.append({"kind": key, "expected": value, "actual": relation.get(key)})
    if not relation.get("patches"):
        failures.append({"kind": "provenance_scope", "expected": expected["provenance_scope"], "actual": "not_applicable"})
    return {"schema_version": 1, "status": "PASS" if not failures else "FAIL", "failures": failures}


def analyze_contact_canonical_analytic(step_path: Path, output_dir: Path) -> dict[str, Any]:
    step_path, output_dir = Path(step_path), Path(output_dir)
    response = _run_freecad({"action": "analyze", "case_id": step_path.parent.name, "step_path": str(step_path), "debug_path": str(output_dir / "debug.FCStd"), "tolerances": TOLERANCES})
    actual = {key: value for key, value in response.items() if key != "status"}
    actual["step_sha256"] = sha256_file(step_path)
    write_json(output_dir / "actual.json", actual)
    validation = _validate(actual, read_json(step_path.with_name("expected.json")))
    write_json(output_dir / "validation.json", validation)
    actual["validation"] = validation
    write_json(output_dir / "actual.json", actual)
    if validation["status"] != "PASS":
        raise CanonicalAnalyticValidationError("expected truth disagrees with completed actual B-rep evidence")
    return actual


def run_contact_canonical_analytic_repeatability(step_path: Path, output_dir: Path) -> dict[str, Any]:
    first = analyze_contact_canonical_analytic(step_path, Path(output_dir) / "run_1")
    second = analyze_contact_canonical_analytic(step_path, Path(output_dir) / "run_2")
    fields = ("raw_common_face_count", "patch_count", "component_count", "boundary_component_count", "hole_count")
    comparison = {"relation_match": (first["relation"]["relation"], first["relation"]["dimension"]) == (second["relation"]["relation"], second["relation"]["dimension"]), "relation_measure_match": first["relation"].get("area_mm2") == second["relation"].get("area_mm2"), "coverage_match": (first["relation"].get("coverage_a"), first["relation"].get("coverage_b")) == (second["relation"].get("coverage_a"), second["relation"].get("coverage_b")), "component_information_match": {field: first["relation"].get(field) for field in fields} == {field: second["relation"].get(field) for field in fields}, "provenance_linkage_match": first["relation"].get("patches", []) == second["relation"].get("patches", []), "geometry_digest_match": first["relation"]["evidence"]["geometry_digest"] == second["relation"]["evidence"]["geometry_digest"]}
    report = {"schema_version": 1, "processes": 2, "status": "PASS" if all(comparison.values()) else "FAIL", "comparison": comparison}
    write_json(Path(output_dir) / "repeatability.json", report)
    return report


def run_contact_canonical_analytic_suite(fixture_root: Path, output_root: Path) -> dict[str, Any]:
    fixture_root, output_root = Path(fixture_root), Path(output_root)
    rows = {}
    for case_id in _case_definitions():
        step_path, case_output = fixture_root / case_id / "fixture.step", output_root / case_id
        actual = analyze_contact_canonical_analytic(step_path, case_output)
        repeatability = run_contact_canonical_analytic_repeatability(step_path, case_output / "repeatability")
        expected = read_json(step_path.with_name("expected.json"))
        rows[case_id] = {"relation": actual["relation"]["relation"], "dimension": actual["relation"]["dimension"], "expected_measure": expected["measures"], "actual_measure": {"area_mm2": actual["relation"]["area_mm2"]}, "absolute_error": abs(actual["relation"]["area_mm2"] - expected["measures"]["area_mm2"]), "coverage": [actual["relation"]["coverage_a"], actual["relation"]["coverage_b"]], "raw_common_face_count": actual["relation"]["raw_common_face_count"], "patch_count": actual["relation"]["patch_count"], "component_count": actual["relation"]["component_count"], "validation": actual["validation"]["status"], "repeatability": repeatability["status"], "debug_fcstd": str(case_output / "debug.FCStd")}
    summary = {"schema_version": 1, "status": "PASS" if all(row["validation"] == "PASS" and row["repeatability"] == "PASS" for row in rows.values()) else "FAIL", "cases": rows}
    write_json(output_root / "summary.json", summary)
    index = ["# Contact Canonical 03B — view index", "", "Each `debug.FCStd` contains the two STEP-reimported solids and the actual direct-common result.  The result is not reconstructed from expected data.", "", "- **A07** — cylindrical shaft/bore: hide `Body_2` to inspect the full internal cylindrical band.", "- **A08** — spherical cavity-wall cap: hide `Body_2` to inspect the upper hemispherical contact cap.", "- **A09** — conical frustum/seat: hide `Body_2` to inspect the full internal conical band.", "", "For every case, select `Actual_Result` and inspect Relation, Dimension, Area, Coverage, SourceFaceLinkage, SurfaceFamily, raw/contract patch counts, component count, and GeometryDigest."]
    (output_root / "VIEW_INDEX.md").write_text("\n".join(index) + "\n", encoding="utf-8")
    return summary
