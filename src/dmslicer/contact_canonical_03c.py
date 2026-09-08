"""Host-side fixtures, validation, and repeatability for frozen A11--A12."""

from __future__ import annotations

import math
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from .evidence import read_json, sha256_file, write_json


FREECAD_SCRIPT = Path(__file__).with_name("freecad_contact_03c.py")
TOLERANCES = {
    "length_unit": "mm",
    "area_unit": "mm2",
    "linear_epsilon_mm": 1e-7,
    "area_epsilon_mm2": 1e-8,
    "engineering_tolerance_mm": 0.1,
}
VALIDATION_TOLERANCES = {"area_mm2": 0.05, "coverage": 1e-4}


class CanonicalTopologyValidationError(RuntimeError):
    """Raised only after actual evidence and a failed validation are persisted."""


def _freecad_executable() -> Path:
    discovered = shutil.which("freecadcmd") or shutil.which("FreeCADCmd.exe")
    for candidate in (Path(discovered) if discovered else None, Path(r"C:\Program Files\FreeCAD 1.1\bin\freecadcmd.exe")):
        if candidate and candidate.is_file():
            return candidate
    raise FileNotFoundError("FreeCADCmd.exe was not found")


def _run_freecad(request: dict[str, Any]) -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="dmslicer_contact_03c_") as temporary:
        request_path = Path(temporary) / "request.json"
        response_path = Path(temporary) / "response.json"
        write_json(request_path, request)
        environment = os.environ.copy()
        environment.update({
            "DMSLICER_FREECAD_REQUEST": str(request_path),
            "DMSLICER_FREECAD_RESPONSE": str(response_path),
            "DMSLICER_FREECAD_SCRIPT": str(FREECAD_SCRIPT),
        })
        console = "import os; p=os.environ['DMSLICER_FREECAD_SCRIPT']; exec(compile(open(p, encoding='utf-8').read(), p, 'exec'))\n"
        completed = subprocess.run(
            [str(_freecad_executable()), "--safe-mode", "-c"], input=console,
            env=environment, text=True, capture_output=True, timeout=120, check=False,
        )
        if not response_path.is_file():
            raise RuntimeError(f"FreeCADCmd did not write a response: {completed.stderr}")
        response = read_json(response_path)
        if completed.returncode or response.get("status") == "FAILED":
            raise RuntimeError(f"FreeCADCmd contact 03C failed: {response}")
        return response


def _case_definitions() -> dict[str, dict[str, Any]]:
    raw = {
        "A11": {
            "raw_bbox": [60.0, 40.0, 20.0],
            "raw_area": 2.0 * 12.0 * 16.0,
            "plate_area": 60.0 * 40.0,
            "body_b_area": 2.0 * 12.0 * 16.0,
            "geometry": "one connected bridge solid with two 12×16 mm feet, separated by 24 mm clearance, on a 60×40 mm plate",
            "topology": {"component_count": 2, "connectedness": "disconnected", "boundary_component_count": 2, "hole_count": 0},
        },
        "A12": {
            "raw_bbox": [50.0, 50.0, 15.0],
            "raw_area": math.pi * (20.0**2 - 10.0**2),
            "plate_area": 50.0 * 50.0,
            "body_b_area": math.pi * (20.0**2 - 10.0**2),
            "geometry": "r_o=20 mm, r_i=10 mm planar washer bottom coincident with a 50×50 mm plate",
            "topology": {"component_count": 1, "connectedness": "connected", "boundary_component_count": 2, "hole_count": 1},
        },
    }
    for definition in raw.values():
        definition["scale"] = 100.0 / math.sqrt(sum(axis**2 for axis in definition["raw_bbox"]))
        definition["expected_area"] = definition["raw_area"] * definition["scale"]**2
        definition["coverage"] = [
            definition["raw_area"] / definition["plate_area"],
            definition["raw_area"] / definition["body_b_area"],
        ]
    return raw


def generate_contact_canonical_interface_topology(root: Path) -> dict[str, Any]:
    root = Path(root)
    generated = []
    for case_id, definition in _case_definitions().items():
        case_dir = root / case_id
        step_path = case_dir / "fixture.step"
        _run_freecad({"action": "generate", "case_id": case_id, "step_path": str(step_path), "scale": definition["scale"]})
        expected = {
            "schema_version": 1,
            "case_id": case_id,
            "geometry": definition["geometry"],
            "relation": "exact",
            "dimension": "2D",
            "units": {"length": "mm", "area": "mm2"},
            "tolerances": TOLERANCES,
            "validation_tolerances": VALIDATION_TOLERANCES,
            "measures": {"area_mm2": definition["expected_area"]},
            "coverage": definition["coverage"],
            "support_surface_family": "plane",
            "patch_topology": {**definition["topology"], "first_betti_number": definition["topology"]["hole_count"], "annular_or_multiply_connected": definition["topology"]["hole_count"] > 0},
            "provenance_scope": "actual_brep_direct_common",
            "ground_truth_mode": "analytic",
        }
        parameters = {
            "case_id": case_id,
            "raw_bounding_box_mm": definition["raw_bbox"],
            "scale": definition["scale"],
            "normalization": "combined bounding-box diagonal L=100 mm",
            "geometry": definition["geometry"],
            "analytic_area_formula": "2*a_f*b_f" if case_id == "A11" else "pi*(r_o^2-r_i^2)",
        }
        write_json(case_dir / "expected.json", expected)
        write_json(case_dir / "parameters.json", parameters)
        generated.append({"case_id": case_id, "step": str(step_path), "step_sha256": sha256_file(step_path)})
    return {"cases": generated}


def _validate(actual: dict[str, Any], expected: dict[str, Any]) -> dict[str, Any]:
    relation, failures = actual["relation"], []
    for field in ("relation", "dimension", "support_surface_family"):
        if relation.get(field) != expected.get(field):
            failures.append({"kind": field, "expected": expected.get(field), "actual": relation.get(field)})
    area = relation.get("area_mm2")
    area_tolerance = expected["validation_tolerances"]["area_mm2"]
    if area is None or abs(area - expected["measures"]["area_mm2"]) > area_tolerance:
        failures.append({"kind": "area_mm2", "expected": expected["measures"]["area_mm2"], "actual": area, "tolerance": area_tolerance})
    for key, value in zip(("coverage_a", "coverage_b"), expected["coverage"]):
        if abs(relation.get(key, -1.0) - value) > expected["validation_tolerances"]["coverage"]:
            failures.append({"kind": key, "expected": value, "actual": relation.get(key)})
    for key, value in expected["patch_topology"].items():
        if relation.get(key) != value:
            failures.append({"kind": key, "expected": value, "actual": relation.get(key)})
    if not relation.get("patches") or not relation.get("components"):
        failures.append({"kind": "provenance_scope", "expected": expected["provenance_scope"], "actual": "not_applicable"})
    return {"schema_version": 1, "status": "PASS" if not failures else "FAIL", "failures": failures}


def analyze_contact_canonical_interface_topology(step_path: Path, output_dir: Path, *, reverse_raw_order: bool = False) -> dict[str, Any]:
    step_path, output_dir = Path(step_path), Path(output_dir)
    response = _run_freecad({
        "action": "analyze", "case_id": step_path.parent.name, "step_path": str(step_path),
        "debug_path": str(output_dir / "debug.FCStd"), "tolerances": TOLERANCES,
        "reverse_raw_order": reverse_raw_order,
    })
    actual = {key: value for key, value in response.items() if key != "status"}
    actual["step_sha256"] = sha256_file(step_path)
    write_json(output_dir / "actual.json", actual)
    validation = _validate(actual, read_json(step_path.with_name("expected.json")))
    write_json(output_dir / "validation.json", validation)
    actual["validation"] = validation
    write_json(output_dir / "actual.json", actual)
    if validation["status"] != "PASS":
        raise CanonicalTopologyValidationError("expected truth disagrees with completed actual B-rep evidence")
    return actual


def compare_topology_relations(first_relation: dict[str, Any], second_relation: dict[str, Any]) -> dict[str, bool]:
    """Compare semantic evidence after the adapter has normalized raw ordering."""
    return {
        "relation_match": (first_relation["relation"], first_relation["dimension"]) == (second_relation["relation"], second_relation["dimension"]),
        "area_coverage_match": (first_relation["area_mm2"], first_relation["coverage_a"], first_relation["coverage_b"]) == (second_relation["area_mm2"], second_relation["coverage_a"], second_relation["coverage_b"]),
        "component_membership_match": first_relation["components"] == second_relation["components"],
        "boundary_topology_match": {key: first_relation[key] for key in ("boundary_component_count", "first_betti_number", "hole_count")} == {key: second_relation[key] for key in ("boundary_component_count", "first_betti_number", "hole_count")},
        "provenance_linkage_match": first_relation["patches"] == second_relation["patches"],
        "geometry_digest_match": first_relation["evidence"]["geometry_digest"] == second_relation["evidence"]["geometry_digest"],
    }


def run_contact_canonical_interface_topology_repeatability(step_path: Path, output_dir: Path) -> dict[str, Any]:
    first = analyze_contact_canonical_interface_topology(step_path, Path(output_dir) / "run_1")
    second = analyze_contact_canonical_interface_topology(step_path, Path(output_dir) / "run_2")
    first_relation, second_relation = first["relation"], second["relation"]
    comparison = compare_topology_relations(first_relation, second_relation)
    report = {"schema_version": 1, "processes": 2, "status": "PASS" if all(comparison.values()) else "FAIL", "comparison": comparison}
    write_json(Path(output_dir) / "repeatability.json", report)
    return report


def run_contact_canonical_interface_topology_suite(fixture_root: Path, output_root: Path) -> dict[str, Any]:
    fixture_root, output_root = Path(fixture_root), Path(output_root)
    rows = {}
    for case_id in _case_definitions():
        step_path, case_output = fixture_root / case_id / "fixture.step", output_root / case_id
        actual = analyze_contact_canonical_interface_topology(step_path, case_output)
        repeatability = run_contact_canonical_interface_topology_repeatability(step_path, case_output / "repeatability")
        expected = read_json(step_path.with_name("expected.json"))
        relation = actual["relation"]
        rows[case_id] = {
            "relation": relation["relation"], "dimension": relation["dimension"],
            "expected_measure": expected["measures"], "actual_measure": {"area_mm2": relation["area_mm2"]},
            "absolute_error": abs(relation["area_mm2"] - expected["measures"]["area_mm2"]),
            "raw_common_face_count": relation["raw_common_face_count"], "patch_count": relation["patch_count"],
            "component_count": relation["component_count"], "boundary_component_count": relation["boundary_component_count"], "hole_count": relation["hole_count"],
            "validation": actual["validation"]["status"], "repeatability": repeatability["status"], "debug_fcstd": str(case_output / "debug.FCStd"),
        }
    summary = {"schema_version": 1, "status": "PASS" if all(row["validation"] == "PASS" and row["repeatability"] == "PASS" for row in rows.values()) else "FAIL", "cases": rows}
    write_json(output_root / "summary.json", summary)
    index = [
        "# Contact Canonical 03C — view index", "",
        "Each `debug.FCStd` contains the two STEP-reimported bodies. `Actual_Result`, `Component_1`, and where applicable `Component_2` are produced from actual direct-common B-rep evidence, not from expected truth.", "",
        "- **A11** — hide `Body_2` to see two separated rectangles on `Body_1`; select `Component_1` and `Component_2` independently to inspect their area and full source-face linkage.",
        "- **A12** — hide either body to inspect the annular `Component_1`; the orange boundary objects show outer boundary and hole boundary, and the central hole is deliberately not filled.",
        "",
        "Select `Actual_Result` or a component and inspect Relation, Dimension, Area, SourceFaceLinkage, RawCommonFaces, PatchCount, ComponentCount, BoundaryComponentCount, HoleCount, and GeometryDigest.",
    ]
    (output_root / "VIEW_INDEX.md").write_text("\n".join(index) + "\n", encoding="utf-8")
    return summary
