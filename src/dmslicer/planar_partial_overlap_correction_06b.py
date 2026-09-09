"""06B: evidence-first correction and partitioning of partial planar interfaces."""

from __future__ import annotations

import argparse
import math
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from .evidence import read_json, sha256_file, write_json


REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURE_ROOT = REPO_ROOT / "benchmarks" / "planar_partial_overlap_correction_06b"
FREECAD_SCRIPT = Path(__file__).with_name("freecad_planar_partial_overlap_correction_06b.py")
RULES = {"linear_epsilon_mm": 1e-7, "area_epsilon_mm2": 1e-8, "volume_epsilon_mm3": 1e-6}
SCENARIOS = {
    "P07": {
        "side_1": [0, 40, 0, 20, 0, 10],
        "side_2": [16, 56, 0, 20, 10.05, 20.05],
        "status": "CORRECTED_PARTIAL_INTERFACE_FUSED",
        "common_area_mm2": 480.0,
        "coverage": {"Side_1": 0.6, "Side_2": 0.6},
        "remaining_area_mm2": {"Side_1": 320.0, "Side_2": 320.0},
    },
    "P08": {
        "side_1": [0, 50, 0, 20, 0, 10],
        "side_2": [20, 30, 0, 20, 10.05, 20.05],
        "status": "CORRECTED_PARTIAL_INTERFACE_FUSED",
        "common_area_mm2": 200.0,
        "coverage": {"Side_1": 0.2, "Side_2": 1.0},
        "remaining_area_mm2": {"Side_1": 800.0, "Side_2": 0.0},
    },
    "P09": {
        "side_1": [0, 40, 0, 20, 0, 10],
        "side_2": [45, 85, 0, 20, 10.05, 20.05],
        "status": "NO_POSITIVE_AREA_INTERFACE",
        "common_area_mm2": 0.0,
    },
}


def _freecad_executable() -> Path:
    discovered = shutil.which("freecadcmd") or shutil.which("FreeCADCmd.exe")
    for candidate in (Path(discovered) if discovered else None, Path(r"C:\Program Files\FreeCAD 1.1\bin\freecadcmd.exe")):
        if candidate and candidate.is_file():
            return candidate
    raise FileNotFoundError("FreeCADCmd.exe was not found")


def _run_freecad(request: dict[str, Any]) -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="dmslicer_partial_06b_") as temporary:
        request_path, response_path = Path(temporary) / "request.json", Path(temporary) / "response.json"
        write_json(request_path, request)
        environment = os.environ.copy()
        environment.update({"DMSLICER_FREECAD_REQUEST": str(request_path), "DMSLICER_FREECAD_RESPONSE": str(response_path), "DMSLICER_FREECAD_SCRIPT": str(FREECAD_SCRIPT)})
        console = "import os; p=os.environ['DMSLICER_FREECAD_SCRIPT']; exec(compile(open(p, encoding='utf-8').read(), p, 'exec'))\n"
        result = subprocess.run([str(_freecad_executable()), "--safe-mode", "-c"], input=console, env=environment, text=True, capture_output=True, timeout=180, check=False)
        if not response_path.is_file():
            raise RuntimeError(f"FreeCADCmd did not write response: {result.stderr}")
        response = read_json(response_path)
        if result.returncode or response.get("status") == "FAILED":
            raise RuntimeError(f"FreeCADCmd 06B failed: {response}")
        return response


def _source_commit() -> str | None:
    result = subprocess.run(["git", "-C", str(REPO_ROOT), "rev-parse", "HEAD"], text=True, capture_output=True, check=False)
    return result.stdout.strip() if result.returncode == 0 else None


def generate_partial_overlap_fixtures(root: Path) -> dict[str, Any]:
    """Create independent tracked-style STEP, policy, construction, and truth bundles."""
    root = Path(root)
    rows = []
    for scenario_id, definition in SCENARIOS.items():
        case = root / scenario_id
        case.mkdir(parents=True, exist_ok=True)
        step = case / "inputs.step"
        _run_freecad({"action": "generate", "step_path": str(step), "side_1": definition["side_1"], "side_2": definition["side_2"]})
        policy = {"schema_version": 1, "policy_valid": True, "allow_motion": True, "max_translation_mm": 0.1, "tauE_mm": 0.1}
        expected = {"schema_version": 1, "scenario_id": scenario_id, "status": definition["status"], "common_area_mm2": definition["common_area_mm2"], "numeric_rules": RULES}
        if "coverage" in definition:
            expected.update({"coverage": definition["coverage"], "remaining_area_mm2": definition["remaining_area_mm2"]})
        write_json(case / "parameters.json", {"schema_version": 1, "scenario_id": scenario_id, "construction": {"Side_1": definition["side_1"], "Side_2": definition["side_2"]}, "units": "mm"})
        write_json(case / "policy.json", policy)
        write_json(case / "expected.json", expected)
        rows.append({"scenario_id": scenario_id, "step_sha256": sha256_file(step), "status": definition["status"]})
    manifest = {"schema_version": 1, "operation": "PLANAR_PARTIAL_OVERLAP_CORRECTION_06B", "numeric_rules": RULES, "scenarios": rows}
    write_json(root / "manifest.json", manifest)
    return manifest


def _finite(value: Any) -> bool:
    return type(value) in {int, float} and math.isfinite(float(value))


def _number(failures: list[dict[str, Any]], value: Any, field: str, *, nonnegative: bool = False, positive: bool = False) -> float | None:
    if not _finite(value):
        failures.append({"kind": "invalid_numeric", "field": field, "actual": value})
        return None
    result = float(value)
    if (nonnegative and result < 0) or (positive and result <= 0):
        failures.append({"kind": "numeric_constraint", "field": field, "actual": value})
    return result


def _vector(failures: list[dict[str, Any]], value: Any, field: str) -> list[float] | None:
    if not isinstance(value, list) or len(value) != 3:
        failures.append({"kind": "invalid_vector", "field": field, "actual": value})
        return None
    values = [_number(failures, item, f"{field}.{index}") for index, item in enumerate(value)]
    return values if all(item is not None for item in values) else None


def validate_partial_overlap_evidence(operation: dict[str, Any], expected: dict[str, Any]) -> dict[str, Any]:
    """Validate actual partition, pose, and fuse evidence without generating geometry."""
    failures: list[dict[str, Any]] = []
    status = operation.get("status")
    if status != expected.get("status"):
        failures.append({"kind": "status", "expected": expected.get("status"), "actual": status})
    epsilon, linear = RULES["area_epsilon_mm2"], RULES["linear_epsilon_mm"]
    decision = operation.get("decision", {})
    pose = operation.get("pose_invariants", {})
    policy = operation.get("policy", {})
    pre = operation.get("pre_measurement", {})
    offset = _number(failures, pre.get("measured_signed_offset_mm"), "pre_measurement.measured_signed_offset_mm")
    normal = _vector(failures, pre.get("reference_direction"), "pre_measurement.reference_direction")
    if normal is not None and abs(math.sqrt(sum(item * item for item in normal)) - 1.0) > linear:
        failures.append({"kind": "normal", "field": "pre_measurement.reference_direction"})
    translation = _vector(failures, decision.get("executed_translation_mm"), "decision.executed_translation_mm")
    translation_norm = _number(failures, decision.get("executed_translation_norm_mm"), "decision.executed_translation_norm_mm", nonnegative=True)
    if translation is not None and translation_norm is not None and abs(math.sqrt(sum(item * item for item in translation)) - translation_norm) > linear:
        failures.append({"kind": "translation_norm", "field": "decision.executed_translation_norm_mm"})
    tangent_norm = _number(failures, pose.get("tangential_translation_norm_mm"), "pose_invariants.tangential_translation_norm_mm", nonnegative=True)
    if tangent_norm is None or tangent_norm > linear:
        failures.append({"kind": "tangential_translation", "actual": pose.get("tangential_translation_norm_mm")})
    if pose.get("tangential_projection_relation_preserved") is not True:
        failures.append({"kind": "tangential_projection_relation"})
    prospective = operation.get("prospective_interface", {})
    area = prospective.get("common_area_mm2")
    if not _finite(area) or float(area) < 0:
        failures.append({"kind": "prospective_common", "actual": area})
    if status == "NO_POSITIVE_AREA_INTERFACE":
        if not _finite(area) or float(area) > epsilon:
            failures.append({"kind": "no_positive_area_gate", "actual": area})
        if float(decision.get("executed_translation_norm_mm", math.inf)) > RULES["linear_epsilon_mm"]:
            failures.append({"kind": "rejected_motion"})
        if operation.get("fuse", {}).get("executed") is not False:
            failures.append({"kind": "rejected_fuse"})
    elif status == "CORRECTED_PARTIAL_INTERFACE_FUSED":
        for key, nonnegative in (("tauE_mm", True), ("max_translation_mm", True)):
            _number(failures, policy.get(key), f"policy.{key}", nonnegative=nonnegative)
        if policy.get("policy_valid") is not True:
            failures.append({"kind": "authorization", "field": "policy.policy_valid"})
        if policy.get("allow_motion") is not True:
            failures.append({"kind": "authorization", "field": "policy.allow_motion"})
        if decision.get("motion_authorized") is not True:
            failures.append({"kind": "authorization", "field": "decision.motion_authorized"})
        tau = _number(failures, policy.get("tauE_mm"), "policy.tauE_mm", nonnegative=True)
        budget = _number(failures, policy.get("max_translation_mm"), "policy.max_translation_mm", nonnegative=True)
        if offset is None or offset <= linear:
            failures.append({"kind": "positive_gap", "field": "pre_measurement.measured_signed_offset_mm", "actual": offset})
        if offset is not None and tau is not None and offset > tau + linear:
            failures.append({"kind": "policy_constraint", "field": "policy.tauE_mm", "actual": offset})
        if translation_norm is None or (budget is not None and translation_norm > budget + linear):
            failures.append({"kind": "translation_budget", "field": "decision.executed_translation_norm_mm"})
        if normal is not None and translation is not None and offset is not None:
            expected_vector = [-offset * item for item in normal]
            if any(abs(actual - expected_value) > linear for actual, expected_value in zip(translation, expected_vector)):
                failures.append({"kind": "translation_direction", "field": "decision.executed_translation_mm"})
        post = _number(failures, operation.get("post_measurement", {}).get("measured_signed_offset_mm"), "post_measurement.measured_signed_offset_mm")
        if post is not None and abs(post) > linear:
            failures.append({"kind": "post_contact", "field": "post_measurement.measured_signed_offset_mm"})
        partition = operation.get("partition", {})
        common = partition.get("common_area_mm2")
        if not _finite(common) or float(common) <= epsilon:
            failures.append({"kind": "common_area", "actual": common})
        if expected.get("common_area_mm2") is not None and (not _finite(common) or abs(float(common) - float(expected["common_area_mm2"])) > epsilon):
            failures.append({"kind": "expected_common_area", "actual": common})
        for side in ("Side_1", "Side_2"):
            coverage = partition.get("coverage", {}).get(side)
            remaining = partition.get("remaining_area_mm2", {}).get(side)
            carrier = partition.get("carrier_area_mm2", {}).get(side)
            if not _finite(coverage) or not 0 <= float(coverage) <= 1:
                failures.append({"kind": "coverage", "field": f"partition.coverage.{side}", "actual": coverage})
            if not _finite(remaining) or float(remaining) < 0:
                failures.append({"kind": "remaining", "field": f"partition.remaining_area_mm2.{side}", "actual": remaining})
            if not _finite(carrier) or float(carrier) <= epsilon or not _finite(common) or not _finite(remaining) or abs(float(carrier) - float(common) - float(remaining)) > epsilon:
                failures.append({"kind": "area_conservation", "field": side, "carrier": carrier, "common": common, "remaining": remaining})
            if side in expected.get("coverage", {}) and (not _finite(coverage) or abs(float(coverage) - float(expected["coverage"][side])) > 1e-7):
                failures.append({"kind": "expected_coverage", "field": side, "actual": coverage})
        if partition.get("area_conserved") is not True:
            failures.append({"kind": "area_conservation"})
        if partition.get("spatial_coverage") is not True:
            failures.append({"kind": "spatial_coverage"})
        fuse = operation.get("fuse", {})
        if not (fuse.get("executed") is True and fuse.get("solid_count") == 1 and fuse.get("valid") is True and fuse.get("closed") is True):
            failures.append({"kind": "fuse"})
        if not _finite(fuse.get("volume_conservation_error_mm3")) or float(fuse.get("volume_conservation_error_mm3", math.inf)) > RULES["volume_epsilon_mm3"]:
            failures.append({"kind": "volume_conservation"})
        if not _finite(fuse.get("boundary_overlap_area_mm2")) or float(fuse.get("boundary_overlap_area_mm2", math.inf)) > epsilon:
            failures.append({"kind": "interface_boundary"})
        reimport = operation.get("reimport", {}).get("corrected_assembly", {})
        residual = _number(failures, reimport.get("residual_offset_mm"), "reimport.corrected_assembly.residual_offset_mm")
        if residual is not None and abs(residual) > linear:
            failures.append({"kind": "reimport_residual", "field": "reimport.corrected_assembly.residual_offset_mm"})
    return {"schema_version": 1, "status": "PASS" if not failures else "FAIL", "expected_status": expected.get("status"), "failures": failures}


def run_partial_overlap_case(fixture_root: Path, scenario_id: str, output_root: Path, *, create_view: bool = False, traversal_order: str = "normal") -> dict[str, Any]:
    fixture_root, output_root = Path(fixture_root), Path(output_root)
    case = fixture_root / scenario_id
    step, policy_path, expected_path = case / "inputs.step", case / "policy.json", case / "expected.json"
    policy, expected = read_json(policy_path), read_json(expected_path)
    output_root.mkdir(parents=True, exist_ok=True)
    staged = Path(tempfile.mkdtemp(prefix=f".{scenario_id}-06b-", dir=output_root))
    operation = _run_freecad({"action": "analyze", "scenario_id": scenario_id, "step_path": str(step), "policy": policy, "rules": RULES, "output_dir": str(staged), "create_view": create_view, "traversal_order": traversal_order})["operation"]
    operation["input_step_sha256"] = sha256_file(step)
    operation["policy"] = policy
    operation["validator_version"] = "06B"
    operation["validator_source_commit"] = _source_commit()
    validation = validate_partial_overlap_evidence(operation, expected)
    write_json(staged / "operation.json", operation)
    write_json(staged / "validation.json", validation)
    write_json(staged / "expected_snapshot.json", expected)
    target = output_root / scenario_id
    if target.exists() and validation["status"] == "PASS":
        shutil.rmtree(target)
    if target.exists():
        target = output_root / f"{scenario_id}_failed_validation"
    staged.replace(target)
    return {"operation": operation, "validation": validation, "expected": expected}


def run_partial_overlap_suite(fixture_root: Path, output_root: Path) -> dict[str, Any]:
    results = {scenario: run_partial_overlap_case(fixture_root, scenario, output_root, create_view=True) for scenario in ("P07", "P08", "P09")}
    repeatability = {}
    for scenario in ("P07", "P08", "P09"):
        first = results[scenario]["operation"]
        second = run_partial_overlap_case(fixture_root, scenario, output_root / "repeatability", traversal_order="reverse")["operation"]
        keys = ("status", "pre_measurement", "decision", "prospective_interface", "partition", "fuse", "pose_invariants")
        repeatability[scenario] = {"processes": 2, "status": "PASS" if all(first.get(key) == second.get(key) for key in keys) else "FAIL"}
    summary = {"schema_version": 1, "status": "PASS" if all(item["validation"]["status"] == "PASS" for item in results.values()) and all(item["status"] == "PASS" for item in repeatability.values()) else "FAIL", "scenarios": {key: value["operation"]["status"] for key, value in results.items()}, "repeatability": repeatability}
    write_json(Path(output_root) / "summary.json", summary)
    (Path(output_root) / "VIEW_INDEX.md").write_text("# 06B 平面部分覆盖校正\n\nP07/P08 默认显示融合实体，可打开 Common 与双方 Remaining。P08 的 Side_2_Remaining 标记为 EMPTY。P09 默认显示真实原件；Preview_Candidate 仅为 DISPLAY_ONLY，未执行。\n", encoding="utf-8")
    return summary


def _main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("generate", "run", "case"))
    parser.add_argument("root", type=Path)
    parser.add_argument("--scenario", default="P07")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.action == "generate":
        generate_partial_overlap_fixtures(args.root)
    elif args.action == "run":
        report = run_partial_overlap_suite(args.root, args.output)
        if report["status"] != "PASS":
            raise SystemExit(1)
    else:
        report = run_partial_overlap_case(args.root, args.scenario, args.output)
        if report["validation"]["status"] != "PASS":
            raise SystemExit(1)


if __name__ == "__main__":
    _main()
