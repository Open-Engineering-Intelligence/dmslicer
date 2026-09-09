"""Bounded 04B cylindrical sleeve/core partition and union operations."""

from __future__ import annotations

import math
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from .contact_canonical_03a import TOLERANCES
from .evidence import read_json, sha256_file, write_json


FREECAD_SCRIPT = Path(__file__).with_name("freecad_cylinder_partition_union_04b.py")
CASE_IDS = ("U04_cylinder_full_fill", "U05_cylinder_short_core", "U06_cylinder_unequal_overlap")
PARAMETERS = {"outer_radius_mm": 30.0, "inner_radius_mm": 20.0, "sleeve_z_mm": [0.0, 40.0], "axis": "z", "angle_deg": 360.0}


def _definition(case_id: str) -> dict[str, Any]:
    definitions = {
        "U04_cylinder_full_fill": {"core_z_mm": [0.0, 40.0], "common_area_mm2": 1600 * math.pi, "coverage": [1.0, 1.0], "remaining_counts": [0, 0], "union_volume_mm3": 36000 * math.pi},
        "U05_cylinder_short_core": {"core_z_mm": [0.0, 20.0], "common_area_mm2": 800 * math.pi, "coverage": [0.5, 1.0], "remaining_counts": [1, 0], "union_volume_mm3": 28000 * math.pi},
        "U06_cylinder_unequal_overlap": {"core_z_mm": [-80.0, 20.0], "common_area_mm2": 800 * math.pi, "coverage": [0.5, 0.2], "remaining_counts": [1, 1], "union_volume_mm3": 60000 * math.pi},
    }
    if case_id not in definitions:
        raise ValueError(f"unsupported cylinder case: {case_id}")
    return definitions[case_id]


def _freecad_executable() -> Path:
    discovered = shutil.which("freecadcmd") or shutil.which("FreeCADCmd.exe")
    for candidate in (Path(discovered) if discovered else None, Path(r"C:\Program Files\FreeCAD 1.1\bin\freecadcmd.exe")):
        if candidate and candidate.is_file():
            return candidate
    raise FileNotFoundError("FreeCADCmd.exe was not found")


def _run_freecad(request: dict[str, Any]) -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="dmslicer_cylinder_04b_") as temporary:
        request_path, response_path = Path(temporary) / "request.json", Path(temporary) / "response.json"
        write_json(request_path, request)
        environment = os.environ.copy()
        environment.update({"DMSLICER_FREECAD_REQUEST": str(request_path), "DMSLICER_FREECAD_RESPONSE": str(response_path), "DMSLICER_FREECAD_SCRIPT": str(FREECAD_SCRIPT)})
        console = "import os; p=os.environ['DMSLICER_FREECAD_SCRIPT']; exec(compile(open(p, encoding='utf-8').read(), p, 'exec'))\n"
        completed = subprocess.run([str(_freecad_executable()), "--safe-mode", "-c"], input=console, env=environment, text=True, capture_output=True, timeout=180, check=False)
        if not response_path.is_file():
            raise RuntimeError(f"FreeCADCmd did not write a response: {completed.stderr}")
        response = read_json(response_path)
        if completed.returncode or response.get("status") == "FAILED":
            raise RuntimeError(f"FreeCADCmd cylinder operation failed: {response}")
        return response


def generate_cylinder_fit_cases(root: Path) -> dict[str, Any]:
    root = Path(root); generated = []
    for case_id in CASE_IDS:
        case = root / case_id; case.mkdir(parents=True, exist_ok=True)
        definition = _definition(case_id)
        parameters = {"case_id": case_id, **PARAMETERS, "core_z_mm": definition["core_z_mm"], "side_order": {"side_1": "sleeve", "side_2": "core"}, "construction": {"side_1": "outer cylinder minus through inner cylinder", "side_2": "solid coaxial core"}}
        _run_freecad({"action": "generate", "case_id": case_id, "step_path": str(case / "inputs.step"), "parameters": parameters})
        write_json(case / "parameters.json", parameters)
        write_json(case / "expected.json", {"schema_version": 1, "case_id": case_id, "ground_truth_mode": "analytic_and_independent_axial_reference", "units": {"length": "mm", "area": "mm2", "volume": "mm3"}, "tolerances": TOLERANCES, **definition})
        generated.append({"case_id": case_id, "step": str(case / "inputs.step"), "step_sha256": sha256_file(case / "inputs.step")})
    return {"cases": generated}


def run_cylinder_fit_case(case_dir: Path, output_dir: Path) -> dict[str, Any]:
    case_dir, output_dir = Path(case_dir), Path(output_dir)
    parameters = read_json(case_dir / "parameters.json"); step = case_dir / "inputs.step"; input_hash = sha256_file(step)
    actual = _run_freecad({"action": "analyze", "case_id": parameters["case_id"], "step_path": str(step), "output_dir": str(output_dir), "parameters": parameters, "tolerances": TOLERANCES, "step_hash": input_hash})
    operation = actual["operation"]; operation["input_unchanged"] = sha256_file(step) == input_hash; operation["fused_step_sha256"] = sha256_file(output_dir / "fused.step")
    write_json(output_dir / "operation.json", operation)
    validation = _run_freecad({"action": "validate", "case_id": parameters["case_id"], "fused_step": str(output_dir / "fused.step"), "debug_path": str(output_dir / "operation_debug.FCStd"), "parameters": parameters, "expected": read_json(case_dir / "expected.json"), "actual_checks": actual["checks"]})["validation"]
    write_json(output_dir / "validation.json", validation)
    if validation["status"] != "PASS":
        raise RuntimeError(f"cylinder validation failed: {validation['failures']}")
    return {"operation": operation, "validation": validation}


def validate_cylinder_candidate(case_id: str, candidate_kind: str) -> dict[str, Any]:
    definition = _definition(case_id)
    params = {"case_id": case_id, **PARAMETERS, "core_z_mm": definition["core_z_mm"]}
    expected = {"case_id": case_id, "tolerances": TOLERANCES, **definition}
    return _run_freecad({"action": "validate_candidate", "case_id": case_id, "candidate_kind": candidate_kind, "parameters": params, "expected": expected})["validation"]


def run_cylinder_fit_repeatability(case_dir: Path, output_dir: Path) -> dict[str, Any]:
    first = run_cylinder_fit_case(case_dir, Path(output_dir) / "run_1")
    second = run_cylinder_fit_case(case_dir, Path(output_dir) / "run_2")
    comparable = lambda operation: {key: value for key, value in operation.items() if key != "fused_step_sha256"}
    report = {"processes": 2, "comparison": {"operation_geometry_match": comparable(first["operation"]) == comparable(second["operation"]), "union_brep_digest_match": first["operation"]["union"]["digest"] == second["operation"]["union"]["digest"], "validation_match": first["validation"] == second["validation"]}, "status": "PASS"}
    report["status"] = "PASS" if all(report["comparison"].values()) else "FAIL"; write_json(Path(output_dir) / "repeatability.json", report); return report


def run_cylinder_fit_suite(fixture_root: Path, output_root: Path) -> dict[str, Any]:
    fixture_root, output_root = Path(fixture_root), Path(output_root); rows = {}
    for case_id in CASE_IDS:
        result = run_cylinder_fit_case(fixture_root / case_id, output_root / case_id)
        repeat = run_cylinder_fit_repeatability(fixture_root / case_id, output_root / case_id / "repeatability")
        rows[case_id] = {"validation": result["validation"]["status"], "repeatability": repeat["status"], "common_area_mm2": result["operation"]["common_area_mm2"], "coverage": result["operation"]["coverage"], "union": result["operation"]["union"]}
    summary = {"schema_version": 1, "status": "PASS" if all(row["validation"] == row["repeatability"] == "PASS" for row in rows.values()) else "FAIL", "cases": rows}; write_json(output_root / "summary.json", summary)
    (output_root / "VIEW_INDEX.md").write_text("# 圆柱套筒贴合与融合 04B 查看索引\n\n每例打开 `operation_debug.FCStd`。默认仅显示 `Union_Result`；`Originals` 与 `Partitions` 可单独显示。U05/U06 顶部均为与外界连通的盲孔，不是封闭内腔。U06 还保留 z=-80--0 的伸出细轴。\n", encoding="utf-8")
    return summary
