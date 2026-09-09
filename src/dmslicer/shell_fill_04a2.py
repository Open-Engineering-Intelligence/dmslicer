"""Generate and validate the three bounded 04A2 spherical shell-fill operations."""

from __future__ import annotations

import json
import math
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from .contact_canonical_03a import TOLERANCES
from .evidence import read_json, sha256_file, write_json


FREECAD_SCRIPT = Path(__file__).with_name("freecad_shell_fill_04a2.py")
CASE_IDS = ("U01_sphere_full_fill", "U02_sphere_half_fill", "U03_sphere_partial_fill")
RADIUS = {"outer_radius_mm": 30.0, "inner_radius_mm": 20.0, "center_mm": [0.0, 0.0, 0.0], "hemisphere": "z>=0"}


def _definition(case_id: str) -> dict[str, Any]:
    outer, inner = RADIUS["outer_radius_mm"], RADIUS["inner_radius_mm"]
    definitions = {
        "U01_sphere_full_fill": {"side_1": "full spherical shell", "side_2": "full solid core", "common_area_mm2": 4 * math.pi * inner**2, "coverage": [1.0, 1.0], "union_volume_mm3": 4 * math.pi * outer**3 / 3, "union_area_mm2": 4 * math.pi * outer**2, "cavity_state": "none", "remaining_counts": [0, 0]},
        "U02_sphere_half_fill": {"side_1": "upper closed hemispherical shell", "side_2": "upper closed solid hemisphere", "common_area_mm2": 2 * math.pi * inner**2, "coverage": [1.0, 1.0], "union_volume_mm3": 2 * math.pi * outer**3 / 3, "union_area_mm2": 3 * math.pi * outer**2, "cavity_state": "none", "remaining_counts": [0, 0]},
        "U03_sphere_partial_fill": {"side_1": "full spherical shell", "side_2": "upper closed solid hemisphere", "common_area_mm2": 2 * math.pi * inner**2, "coverage": [0.5, 1.0], "union_volume_mm3": 4 * math.pi * outer**3 / 3 - 2 * math.pi * inner**3 / 3, "union_area_mm2": 4 * math.pi * outer**2 + 3 * math.pi * inner**2, "cavity_state": "lower_hemisphere", "remaining_counts": [1, 0]},
    }
    if case_id not in definitions:
        raise ValueError(f"unsupported shell-fill case: {case_id}")
    return definitions[case_id]


def _freecad_executable() -> Path:
    discovered = shutil.which("freecadcmd") or shutil.which("FreeCADCmd.exe")
    for candidate in (Path(discovered) if discovered else None, Path(r"C:\Program Files\FreeCAD 1.1\bin\freecadcmd.exe")):
        if candidate and candidate.is_file():
            return candidate
    raise FileNotFoundError("FreeCADCmd.exe was not found")


def _run_freecad(request: dict[str, Any]) -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="dmslicer_shell_fill_04a2_") as temporary:
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
            raise RuntimeError(f"FreeCADCmd shell-fill operation failed: {response}")
        return response


def generate_shell_fill_cases(root: Path) -> dict[str, Any]:
    root = Path(root)
    generated = []
    for case_id in CASE_IDS:
        case_dir = root / case_id
        case_dir.mkdir(parents=True, exist_ok=True)
        parameters = {"case_id": case_id, **RADIUS, "side_order": {"side_1": "shell", "side_2": "core"}, "construction": {"side_1": _definition(case_id)["side_1"], "side_2": _definition(case_id)["side_2"]}, "angles_deg": {"full_sphere": [-90.0, 90.0, 360.0], "upper_hemisphere": [0.0, 90.0, 360.0]}}
        _run_freecad({"action": "generate", "case_id": case_id, "step_path": str(case_dir / "inputs.step"), "parameters": parameters})
        definition = _definition(case_id)
        expected = {"schema_version": 1, "case_id": case_id, "ground_truth_mode": "analytic_and_constructive_reference", "units": {"length": "mm", "area": "mm2", "volume": "mm3"}, "tolerances": TOLERANCES, **{key: definition[key] for key in ("common_area_mm2", "coverage", "union_volume_mm3", "union_area_mm2", "cavity_state", "remaining_counts")}}
        write_json(case_dir / "parameters.json", parameters)
        write_json(case_dir / "expected.json", expected)
        generated.append({"case_id": case_id, "step": str(case_dir / "inputs.step"), "step_sha256": sha256_file(case_dir / "inputs.step")})
    return {"cases": generated}


def run_shell_fill_case(case_dir: Path, output_dir: Path) -> dict[str, Any]:
    case_dir, output_dir = Path(case_dir), Path(output_dir)
    step_path = case_dir / "inputs.step"
    parameters = read_json(case_dir / "parameters.json")
    input_hash = sha256_file(step_path)
    actual = _run_freecad({"action": "analyze", "case_id": parameters["case_id"], "step_path": str(step_path), "output_dir": str(output_dir), "parameters": parameters, "tolerances": TOLERANCES, "step_hash": input_hash})
    operation = actual["operation"]
    operation["input_unchanged"] = sha256_file(step_path) == input_hash
    operation["fused_step_sha256"] = sha256_file(output_dir / "fused.step")
    write_json(output_dir / "operation.json", operation)
    expected = read_json(case_dir / "expected.json")
    validation = _run_freecad({"action": "validate_result", "case_id": parameters["case_id"], "fused_step": str(output_dir / "fused.step"), "debug_path": str(output_dir / "operation_debug.FCStd"), "expected": expected, "parameters": parameters, "actual_checks": actual["checks"]})["validation"]
    write_json(output_dir / "validation.json", validation)
    if validation["status"] != "PASS":
        raise RuntimeError(f"shell-fill validation failed: {validation['failures']}")
    return {"operation": operation, "validation": validation}


def validate_shell_fill_candidate(case_id: str, candidate_kind: str) -> dict[str, Any]:
    expected = {"schema_version": 1, "case_id": case_id, "tolerances": TOLERANCES, **_definition(case_id)}
    return _run_freecad({"action": "validate_candidate", "case_id": case_id, "candidate_kind": candidate_kind, "parameters": {"case_id": case_id, **RADIUS}, "expected": expected})["validation"]


def run_shell_fill_repeatability(case_dir: Path, output_dir: Path) -> dict[str, Any]:
    first = run_shell_fill_case(case_dir, Path(output_dir) / "run_1")
    second = run_shell_fill_case(case_dir, Path(output_dir) / "run_2")
    def geometry_operation(operation: dict[str, Any]) -> dict[str, Any]:
        comparable = dict(operation)
        comparable.pop("fused_step_sha256", None)
        return comparable

    comparison = {
        "operation_geometry_match": geometry_operation(first["operation"]) == geometry_operation(second["operation"]),
        "union_brep_digest_match": first["operation"]["union"]["digest"] == second["operation"]["union"]["digest"],
        "validation_match": first["validation"] == second["validation"],
        "step_file_hashes_recorded": all(run["operation"].get("fused_step_sha256") for run in (first, second)),
    }
    report = {"processes": 2, "status": "PASS" if all(comparison.values()) else "FAIL", "comparison": comparison}
    write_json(Path(output_dir) / "repeatability.json", report)
    return report


def _write_viewer(output_root: Path) -> None:
    (output_root / "view_shell_fill.py").write_text("""# Run in the FreeCAD Python console after opening an operation_debug.FCStd file.\nfor group_name in ('Originals', 'Partitions'):\n    group = App.ActiveDocument.getObject(group_name)\n    group.Visibility = False\n    for obj in group.Group:\n        obj.Visibility = False\nunion = App.ActiveDocument.getObject('Union_Result')\nunion.Visibility = True\nfor obj in union.Group:\n    obj.Visibility = True\nGui.activeDocument().activeView().fitAll()\n""", encoding="utf-8")


def run_shell_fill_suite(fixture_root: Path, output_root: Path) -> dict[str, Any]:
    fixture_root, output_root = Path(fixture_root), Path(output_root)
    rows = {}
    for case_id in CASE_IDS:
        result = run_shell_fill_case(fixture_root / case_id, output_root / case_id)
        repeatability = run_shell_fill_repeatability(fixture_root / case_id, output_root / case_id / "repeatability")
        rows[case_id] = {"validation": result["validation"]["status"], "repeatability": repeatability["status"], "common_area_mm2": result["operation"]["common_area_mm2"], "coverage": result["operation"]["coverage"], "union": result["operation"]["union"]}
    summary = {"schema_version": 1, "status": "PASS" if all(row["validation"] == "PASS" and row["repeatability"] == "PASS" for row in rows.values()) else "FAIL", "cases": rows}
    write_json(output_root / "summary.json", summary)
    (output_root / "VIEW_INDEX.md").write_text("""# 球壳填充 04A2 查看索引

每例打开 `operation_debug.FCStd`。默认意图为仅显示 `Union_Result`；`Originals` 和 `Partitions` 隐藏，避免重叠。若无 GUI 的 FreeCADCmd 未保存显示状态，请在 FreeCAD Python 控制台运行同目录的 `view_shell_fill.py`。

- **U01_sphere_full_fill**：完整球壳＋完整小球，融合结果应为完整实心大球，不保留内腔。
- **U02_sphere_half_fill**：上半球壳＋上半实心球，融合结果应为带完整平面底面的实心大半球，不保留内腔。
- **U03_sphere_partial_fill**：完整球壳＋上半实心球，融合后下半内腔必须保留；查看 `Partitions` 可见球壳侧剩余的下半内球面。

开启 `Originals` 查看两个真实输入；开启 `Partitions` 查看共同曲面和两侧承载面的剩余区域；查看融合结果时关闭前两组。
""", encoding="utf-8")
    _write_viewer(output_root)
    return summary
