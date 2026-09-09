"""Host-side orchestration for the narrow 04A contact partition and union operation."""

import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from .contact_canonical_03a import TOLERANCES
from .evidence import read_json, sha256_file, write_json


FREECAD_SCRIPT = Path(__file__).with_name("freecad_partition_union_04a.py")
CASES = {"A02": Path("benchmarks/contact_canonical_03a/A02/fixture.step"), "A08": Path("benchmarks/contact_canonical_03b/A08/fixture.step")}


def _freecad_executable() -> Path:
    discovered = shutil.which("freecadcmd") or shutil.which("FreeCADCmd.exe")
    for candidate in (Path(discovered) if discovered else None, Path(r"C:\Program Files\FreeCAD 1.1\bin\freecadcmd.exe")):
        if candidate and candidate.is_file():
            return candidate
    raise FileNotFoundError("FreeCADCmd.exe was not found")


def _run_freecad(request: dict[str, Any]) -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="dmslicer_contact_partition_union_04a_") as temporary:
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
            raise RuntimeError(f"FreeCADCmd 04A operation failed: {response}")
        return response


def evaluate_partition_union_validation(facts: dict[str, Any], volume_epsilon_mm3: float) -> dict[str, Any]:
    """Exercise the same FreeCAD-side final status gate used by actual operations."""
    return _run_freecad({"action": "validate", "facts": facts, "volume_epsilon_mm3": volume_epsilon_mm3})["validation"]


def validate_partition_union_facts_file(facts_path: Path, volume_epsilon_mm3: float) -> dict[str, Any]:
    validation = evaluate_partition_union_validation(read_json(Path(facts_path)), volume_epsilon_mm3)
    if validation["status"] != "PASS":
        raise RuntimeError(f"partition/union validation failed: {validation['failures']}")
    return validation


def run_contact_partition_union(step_path: Path, output_dir: Path) -> dict[str, Any]:
    step_path, output_dir = Path(step_path), Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    response = _run_freecad({"case_id": step_path.parent.name, "step_path": str(step_path), "output_dir": str(output_dir), "tolerances": TOLERANCES, "step_hash": sha256_file(step_path)})
    write_json(output_dir / "operation.json", response["operation"])
    write_json(output_dir / "validation.json", response["validation"])
    if response["validation"]["status"] != "PASS":
        raise RuntimeError("04A operation produced validation evidence with status FAIL")
    return response


def run_contact_partition_union_repeatability(step_path: Path, output_dir: Path) -> dict[str, Any]:
    first = run_contact_partition_union(step_path, Path(output_dir) / "run_1")
    second = run_contact_partition_union(step_path, Path(output_dir) / "run_2")
    comparison = {
        "common_patches_match": first["operation"]["common_patches"] == second["operation"]["common_patches"],
        "partitions_match": first["operation"]["partitions"] == second["operation"]["partitions"],
        "union_match": first["operation"]["union"] == second["operation"]["union"],
        "validation_match": first["validation"] == second["validation"],
    }
    report = {"processes": 2, "status": "PASS" if all(comparison.values()) else "FAIL", "comparison": comparison}
    write_json(Path(output_dir) / "repeatability.json", report)
    return report


def run_contact_partition_union_suite(output_root: Path) -> dict[str, Any]:
    output_root = Path(output_root)
    rows = {}
    repository = Path(__file__).resolve().parents[2]
    for case_id, relative_step in CASES.items():
        output = output_root / case_id
        response = run_contact_partition_union(repository / relative_step, output)
        repeatability = run_contact_partition_union_repeatability(repository / relative_step, output / "repeatability")
        rows[case_id] = {"validation": response["validation"]["status"], "repeatability": repeatability["status"], "common_area_mm2": sum(record["area_mm2"] for record in response["operation"]["common_patches"]), "union": response["operation"]["union"]}
    summary = {"status": "PASS" if all(row["validation"] == "PASS" and row["repeatability"] == "PASS" for row in rows.values()) else "FAIL", "cases": rows}
    write_json(output_root / "summary.json", summary)
    (output_root / "VIEW_INDEX.md").write_text("# 04A contact partition and union — view index\n\nOpen each `operation_debug.FCStd`. `Union_Result` is the intended default view. Enable `Originals` to inspect the transparent inputs, or `Partitions` to inspect the actual common face and each side's remaining non-contact face area. A08 is a full small solid sphere plus only the upper half of a larger spherical shell. After fusion, the exposed lower hemisphere of the small sphere is an exterior material boundary, not a residual closed cavity wall; the shell-side inner spherical cap is entirely common and has no remaining patch.\n", encoding="utf-8")
    return summary
