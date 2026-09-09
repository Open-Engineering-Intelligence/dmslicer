"""Evidence-first correction of the limited A01 two-solid planar gap."""

from __future__ import annotations

import argparse
import json
import math
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from .evidence import read_json, sha256_file, write_json

FREECAD_SCRIPT = Path(__file__).with_name("freecad_planar_gap_assembly_correction_06a.py")
REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_NUMERIC_RULES = {
    "linear_epsilon_mm": 1e-7,
    "area_epsilon_mm2": 1e-8,
    "volume_epsilon_mm3": 1e-6,
    "angular_epsilon": 1e-7,
}


def _freecad_executable() -> Path:
    discovered = shutil.which("freecadcmd") or shutil.which("FreeCADCmd.exe")
    for candidate in (
        Path(discovered) if discovered else None,
        Path(r"C:\Program Files\FreeCAD 1.1\bin\freecadcmd.exe"),
    ):
        if candidate and candidate.is_file():
            return candidate
    raise FileNotFoundError("FreeCADCmd.exe was not found")


def _run_freecad(request: dict[str, Any]) -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="dmslicer_planar_gap_06a_") as temporary:
        request_path = Path(temporary) / "request.json"
        response_path = Path(temporary) / "response.json"
        write_json(request_path, request)
        environment = os.environ.copy()
        environment.update(
            {
                "DMSLICER_FREECAD_REQUEST": str(request_path),
                "DMSLICER_FREECAD_RESPONSE": str(response_path),
                "DMSLICER_FREECAD_SCRIPT": str(FREECAD_SCRIPT),
            }
        )
        console = "import os; p=os.environ['DMSLICER_FREECAD_SCRIPT']; exec(compile(open(p, encoding='utf-8').read(), p, 'exec'))\n"
        completed = subprocess.run(
            [str(_freecad_executable()), "--safe-mode", "-c"],
            input=console,
            env=environment,
            text=True,
            capture_output=True,
            timeout=180,
            check=False,
        )
        if not response_path.is_file():
            raise RuntimeError(f"FreeCADCmd did not write response: {completed.stderr}")
        response = read_json(response_path)
        if completed.returncode or response.get("status") == "FAILED":
            raise RuntimeError(f"FreeCADCmd 06A operation failed: {response}")
        return response["operation"]


def load_operation_policy(path: Path) -> dict[str, Any]:
    """Load a policy, defaulting to an explicit no-motion policy on any defect."""
    path = Path(path)
    fallback = {
        "schema_version": 1,
        "allow_motion": False,
        "max_translation_mm": 0.0,
        "tauE_mm": 0.0,
        "policy_source": str(path),
        "policy_valid": False,
    }
    try:
        raw = read_json(path)
    except (OSError, ValueError, json.JSONDecodeError):
        return fallback
    valid = (
        isinstance(raw, dict)
        and type(raw.get("allow_motion")) is bool
        and isinstance(raw.get("max_translation_mm"), (int, float))
        and not isinstance(raw.get("max_translation_mm"), bool)
        and isinstance(raw.get("tauE_mm"), (int, float))
        and not isinstance(raw.get("tauE_mm"), bool)
        and math.isfinite(float(raw["max_translation_mm"]))
        and math.isfinite(float(raw["tauE_mm"]))
        and float(raw["max_translation_mm"]) >= 0.0
        and float(raw["tauE_mm"]) >= 0.0
    )
    if not valid:
        return fallback
    return {
        "schema_version": int(raw.get("schema_version", 1)),
        "allow_motion": raw["allow_motion"],
        "max_translation_mm": float(raw["max_translation_mm"]),
        "tauE_mm": float(raw["tauE_mm"]),
        "policy_source": str(path),
        "policy_valid": True,
    }


def decide_correction(offset_mm: float, policy: dict[str, Any], numeric_rules: dict[str, float]) -> dict[str, Any]:
    """Decide before mutation whether the measured positive gap may be closed."""
    epsilon = float(numeric_rules["linear_epsilon_mm"])
    offset = float(offset_mm)
    decision = {"executed_translation_norm_mm": 0.0, "motion_authorized": False}
    if offset < -epsilon:
        return {**decision, "status": "PENETRATION_OUT_OF_SCOPE", "reason": "negative signed offset is not auto-separated"}
    if abs(offset) <= epsilon:
        return {**decision, "status": "ALREADY_CONTACT", "reason": "interface is already within the numerical zero rule"}
    if policy.get("policy_valid") is False:
        return {**decision, "status": "MOTION_NOT_AUTHORIZED", "reason": "operation policy is missing or invalid"}
    if offset > float(policy.get("tauE_mm", 0.0)) + epsilon:
        return {**decision, "status": "ENGINEERING_TOLERANCE_EXCEEDED", "reason": "measured gap exceeds tauE_mm"}
    if policy.get("allow_motion") is not True:
        return {**decision, "status": "MOTION_NOT_AUTHORIZED", "reason": "operation policy does not explicitly authorize motion"}
    if offset > float(policy.get("max_translation_mm", 0.0)) + epsilon:
        return {**decision, "status": "TRANSLATION_BUDGET_EXCEEDED", "reason": "required translation exceeds max_translation_mm"}
    return {
        **decision,
        "status": "CORRECTED_AND_FUSED",
        "reason": "positive gap is authorized and within both engineering tolerance and motion budget",
        "motion_authorized": True,
        "executed_translation_norm_mm": offset,
    }


def _close(actual: float, expected: float, epsilon: float) -> bool:
    return math.isfinite(float(actual)) and abs(float(actual) - float(expected)) <= epsilon


def validate_operation_evidence(evidence: dict[str, Any], expected: str | dict[str, Any]) -> dict[str, Any]:
    """Independently validate saved operation facts; expected never drives geometry."""
    expected_status = expected if isinstance(expected, str) else expected.get("status")
    rules = {**DEFAULT_NUMERIC_RULES, **(expected.get("numeric_rules", {}) if isinstance(expected, dict) else {})}
    linear = float(rules["linear_epsilon_mm"])
    area_epsilon = float(rules["area_epsilon_mm2"])
    volume_epsilon = float(rules["volume_epsilon_mm3"])
    failures: list[dict[str, Any]] = []
    if evidence.get("status") != expected_status:
        failures.append({"kind": "status", "expected": expected_status, "actual": evidence.get("status")})
    decision = evidence.get("decision", {})
    vector = decision.get("executed_translation_mm", [0.0, 0.0, 0.0])
    norm = decision.get("executed_translation_norm_mm")
    if not isinstance(vector, list) or len(vector) != 3 or not all(isinstance(v, (int, float)) for v in vector):
        failures.append({"kind": "translation_vector", "actual": vector})
        vector_norm = math.inf
    else:
        vector_norm = math.sqrt(sum(float(v) ** 2 for v in vector))
    if not isinstance(norm, (int, float)) or not _close(norm, vector_norm, linear):
        failures.append({"kind": "translation_norm", "reported": norm, "actual": vector_norm})
    policy = evidence.get("policy", {})
    if isinstance(norm, (int, float)) and float(norm) > float(policy.get("max_translation_mm", 0.0)) + linear:
        failures.append({"kind": "translation_budget", "budget": policy.get("max_translation_mm"), "actual": norm})
    pre = evidence.get("pre_measurement", {})
    offset = pre.get("measured_signed_offset_mm")
    normal = pre.get("reference_direction")
    if evidence.get("status") == "CORRECTED_AND_FUSED":
        if not isinstance(offset, (int, float)) or not isinstance(normal, list) or len(normal) != 3:
            failures.append({"kind": "motion_basis", "pre_measurement": pre})
        else:
            expected_vector = [-float(offset) * float(component) for component in normal]
            if any(not _close(vector[i], expected_vector[i], linear) for i in range(3)):
                failures.append({"kind": "translation_direction", "expected": expected_vector, "actual": vector})
    elif evidence.get("status") not in {"ALREADY_CONTACT", "POSTCHECK_FAILED"} and isinstance(norm, (int, float)) and float(norm) > linear:
        failures.append({"kind": "rejected_motion_executed", "actual": norm})

    if evidence.get("status") in {"CORRECTED_AND_FUSED", "ALREADY_CONTACT"}:
        post = evidence.get("post_measurement", {})
        if not isinstance(post.get("measured_signed_offset_mm"), (int, float)) or abs(float(post["measured_signed_offset_mm"])) > linear:
            failures.append({"kind": "residual_offset", "actual": post.get("measured_signed_offset_mm")})
        patch = evidence.get("contact_patch", {})
        if patch.get("dimension") != "2D" or float(patch.get("area_mm2", 0.0)) <= area_epsilon:
            failures.append({"kind": "contact_patch", "actual": patch})
        else:
            for key in ("side_1_area_mm2", "side_2_area_mm2"):
                if not _close(patch.get("area_mm2", math.inf), patch.get(key, -math.inf), area_epsilon):
                    failures.append({"kind": "full_coverage", "field": key, "actual": patch})
            if float(patch.get("fused_boundary_overlap_area_mm2", math.inf)) > area_epsilon:
                failures.append({"kind": "internal_interface_retained", "actual": patch.get("fused_boundary_overlap_area_mm2")})
        fuse = evidence.get("fuse", {})
        if not (fuse.get("executed") is True and fuse.get("solid_count") == 1 and fuse.get("valid") is True and fuse.get("closed") is True):
            failures.append({"kind": "fuse", "actual": fuse})
        if not isinstance(fuse.get("volume_conservation_error_mm3"), (int, float)) or float(fuse["volume_conservation_error_mm3"]) > volume_epsilon:
            failures.append({"kind": "volume_conservation", "actual": fuse.get("volume_conservation_error_mm3")})
        invariants = evidence.get("invariants", {})
        required = (
            "input_step_hash_unchanged",
            "input_manifest_hash_match",
            "original_shapes_unchanged",
            "side_1_unchanged",
            "side_2_inverse_transform_match",
            "side_2_volume_unchanged",
            "rotation_is_identity",
            "scale_is_one",
        )
        for key in required:
            if invariants.get(key) is not True:
                failures.append({"kind": "invariant", "field": key, "actual": invariants.get(key)})
        reimport = evidence.get("reimport", {})
        assembly = reimport.get("corrected_assembly", {})
        fused = reimport.get("fused", {})
        if assembly.get("role_binding") != {"Side_1": "Side_1", "Side_2": "Side_2"} or abs(float(assembly.get("residual_offset_mm", math.inf))) > linear or assembly.get("contact_dimension") != "2D":
            failures.append({"kind": "corrected_step_reimport", "actual": assembly})
        if not (fused.get("solid_count") == 1 and fused.get("valid") is True and fused.get("closed") is True):
            failures.append({"kind": "fused_step_reimport", "actual": fused})
    else:
        if evidence.get("fuse", {}).get("executed") is True:
            failures.append({"kind": "rejected_fuse_executed"})
    return {"schema_version": 1, "status": "PASS" if not failures else "FAIL", "expected_status": expected_status, "failures": failures}


def _resolve(root: Path, value: str) -> Path:
    candidate = Path(value)
    return candidate if candidate.is_absolute() else root / candidate


def run_planar_gap_case(
    manifest_path: Path,
    scenario_id: str,
    output_root: Path,
    *,
    repo_root: Path | None = None,
    traversal_order: str = "normal",
    step_override: Path | None = None,
    create_view: bool = False,
) -> dict[str, Any]:
    """Run one scenario in a fresh FreeCADCmd process and publish atomically."""
    root = Path(repo_root) if repo_root else REPO_ROOT
    manifest = read_json(Path(manifest_path))
    rows = [row for row in manifest["scenarios"] if row["scenario_id"] == scenario_id]
    if len(rows) != 1:
        raise ValueError(f"manifest must contain exactly one {scenario_id} row")
    row = rows[0]
    step_path = Path(step_override) if step_override else _resolve(root, row["input"]["step_path"])
    policy_path = _resolve(root, row["policy_path"])
    expected_path = _resolve(root, row["expected_path"])
    policy = load_operation_policy(policy_path)
    input_hash_before = sha256_file(step_path)
    output_root = Path(output_root)
    output_root.mkdir(parents=True, exist_ok=True)
    staged = Path(tempfile.mkdtemp(prefix=f".{scenario_id}-staged-", dir=output_root))
    try:
        operation = _run_freecad(
            {
                "action": "correct",
                "step_path": str(step_path),
                "output_dir": str(staged),
                "policy": policy,
                "numeric_rules": {**DEFAULT_NUMERIC_RULES, **manifest.get("numeric_rules", {})},
                "traversal_order": traversal_order,
                "create_view": bool(create_view),
                "scenario_id": scenario_id,
            }
        )
        input_hash_after = sha256_file(step_path)
        operation["input_step_sha256"] = input_hash_before
        operation["manifest_input_step_sha256"] = row["input"]["step_sha256"]
        operation["invariants"]["input_step_hash_unchanged"] = input_hash_before == input_hash_after
        operation["invariants"]["input_manifest_hash_match"] = input_hash_before == row["input"]["step_sha256"]
        operation["policy"] = policy
        expected = read_json(expected_path)
        validation = validate_operation_evidence(operation, expected)
        write_json(staged / "operation.json", operation)
        write_json(staged / "validation.json", validation)
        write_json(staged / "expected_snapshot.json", expected)
        target = output_root / scenario_id
        publish_target = target
        failed_attempt = operation.get("status") == "POSTCHECK_FAILED" or validation["status"] == "FAIL"
        if target.exists() and failed_attempt:
            publish_target = output_root / f"{scenario_id}_failed_attempt"
            suffix = 2
            while publish_target.exists():
                publish_target = output_root / f"{scenario_id}_failed_attempt_{suffix}"
                suffix += 1
        elif target.exists():
            shutil.rmtree(target)
        staged.replace(publish_target)
        target = publish_target
        for value in operation.get("artifacts", {}).values():
            if isinstance(value, str):
                operation["artifacts"] = {k: str(target / Path(v).name) if isinstance(v, str) else v for k, v in operation["artifacts"].items()}
                break
        write_json(target / "operation.json", operation)
        checkpoint = {
            "schema_version": 1,
            "source_version": "06A",
            "source_files_sha256": {
                "runner": sha256_file(Path(__file__)),
                "freecad_script": sha256_file(FREECAD_SCRIPT),
            },
            "completed_scenario": scenario_id,
            "input_step_sha256": input_hash_before,
            "operation_status": operation["status"],
            "validation_status": validation["status"],
            "completed_steps": ["measure", "policy_decision", "geometry_operation", "evidence_write", "independent_validation"],
            "valid_result": validation["status"] == "PASS",
        }
        write_json(output_root / "checkpoint.json", checkpoint)
        return {"manifest_row": row, "operation": operation, "expected": expected, "validation": validation}
    except Exception as error:
        # The staged directory intentionally remains diagnostic-only; an existing
        # published scenario is untouched until the complete replacement is ready.
        write_json(staged / "runner_failure.json", {"error_type": type(error).__name__, "message": str(error)})
        raise


def run_planar_gap_suite(manifest_path: Path, output_root: Path) -> dict[str, Any]:
    results = {}
    for scenario_id in ("P01", "P02", "P03", "P04", "P05", "P06"):
        results[scenario_id] = run_planar_gap_case(
            manifest_path,
            scenario_id,
            output_root,
            create_view=scenario_id in {"P01", "P02"},
        )
    summary = {
        "schema_version": 1,
        "status": "PASS" if all(result["validation"]["status"] == "PASS" for result in results.values()) else "FAIL",
        "scenarios": {key: {"operation_status": value["operation"]["status"], "validation_status": value["validation"]["status"]} for key, value in results.items()},
    }
    write_json(Path(output_root) / "summary.json", summary)
    (Path(output_root) / "VIEW_INDEX.md").write_text(
        "# 06A 平面间隙装配校正查看索引\n\n"
        "- `P01/operation_debug.FCStd`：成功代表。默认只显示 `Actual_Fused_Result`；"
        "可分别打开 Originals、Corrected_Assembly 和 Contact_Patch。\n"
        "- `P02/rejected_operation.FCStd`：拒绝代表。只显示两件原始实体，记录拒绝原因与零执行位移。\n\n"
        "视图仅呈现实际运算几何，不放大间隙或改变实体。\n",
        encoding="utf-8",
    )
    return summary


def _main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("run", "case"))
    parser.add_argument("manifest", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--scenario", default="P01")
    parser.add_argument("--view", action="store_true")
    args = parser.parse_args()
    if args.action == "run":
        run_planar_gap_suite(args.manifest, args.output)
    else:
        run_planar_gap_case(args.manifest, args.scenario, args.output, create_view=args.view)


if __name__ == "__main__":
    _main()
