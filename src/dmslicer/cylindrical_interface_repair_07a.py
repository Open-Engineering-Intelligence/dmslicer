"""07A cylindrical interface classification and authorized pose correction."""

from __future__ import annotations

import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
from typing import Any

from .evidence import read_json, sha256_file, write_json


REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURE_ROOT = REPO_ROOT / "benchmarks" / "cylindrical_interface_repair_07a"
FREECAD_SCRIPT = Path(__file__).with_name("freecad_cylindrical_interface_repair_07a.py")
SCENARIOS = ("C01", "C02", "C03", "C04", "C05", "AMBIGUOUS", "ROTATED_C02")
RULES = {
    "linear_epsilon_mm": 1e-7,
    "radius_epsilon_mm": 1e-7,
    "angular_epsilon_rad": 1e-7,
    "area_epsilon_mm2": 1e-8,
    "volume_epsilon_mm3": 1e-6,
    "periodic_epsilon_rad": 1e-6,
    "material_probe_offset_mm": 1e-5,
}


def _number(value: Any) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(float(value)):
        raise ValueError("expected a finite number")
    return float(value)


def _vector(value: Any) -> list[float]:
    if not isinstance(value, (list, tuple)) or len(value) != 3:
        raise ValueError("expected a finite three-vector")
    try:
        return [_number(component) for component in value]
    except ValueError as error:
        raise ValueError("expected a finite three-vector") from error


def _norm(value: list[float]) -> float:
    return math.sqrt(sum(component * component for component in value))


def _unit(value: Any) -> list[float]:
    vector = _vector(value)
    length = _norm(vector)
    if length <= 0.0:
        raise ValueError("axis direction must have nonzero length")
    return [component / length for component in vector]


def axis_relation(
    axis_point_side_1: Any,
    axis_direction_side_1: Any,
    axis_point_side_2: Any,
    axis_direction_side_2: Any,
) -> dict[str, Any]:
    """Compare two infinite axes without depending on their chosen origins."""
    first_point, second_point = _vector(axis_point_side_1), _vector(axis_point_side_2)
    first_direction, second_direction = _unit(axis_direction_side_1), _unit(axis_direction_side_2)
    dot = sum(a * b for a, b in zip(first_direction, second_direction))
    angle = math.acos(max(0.0, min(1.0, abs(dot))))
    if dot < 0.0:
        second_direction = [-value for value in second_direction]
    delta = [b - a for a, b in zip(first_point, second_point)]
    cross = [
        first_direction[1] * second_direction[2] - first_direction[2] * second_direction[1],
        first_direction[2] * second_direction[0] - first_direction[0] * second_direction[2],
        first_direction[0] * second_direction[1] - first_direction[1] * second_direction[0],
    ]
    cross_norm = _norm(cross)
    if cross_norm > 0.0:
        connector_direction = [value / cross_norm for value in cross]
        signed_distance = sum(value * direction for value, direction in zip(delta, connector_direction))
        offset = [signed_distance * direction for direction in connector_direction]
    else:
        parallel = sum(value * direction for value, direction in zip(delta, first_direction))
        offset = [value - parallel * direction for value, direction in zip(delta, first_direction)]
    return {
        "axis_angle_rad": angle,
        "axis_directions_aligned_for_measurement": [first_direction, second_direction],
        "axis_offset_vector_mm": offset,
        "axis_offset_mm": _norm(offset),
        "definition": "Side_1 bore target axis to Side_2 shaft current axis, perpendicular to Side_1 axis",
    }


def radial_relation(bore_radius_mm: Any, shaft_radius_mm: Any) -> dict[str, Any]:
    bore, shaft = _number(bore_radius_mm), _number(shaft_radius_mm)
    if bore <= 0.0 or shaft <= 0.0:
        raise ValueError("cylinder radii must be positive")
    clearance = bore - shaft
    if abs(clearance) <= RULES["radius_epsilon_mm"]:
        state = "RADIUS_COMPATIBLE"
    elif clearance > 0.0:
        state = "DIMENSIONAL_RADIAL_CLEARANCE"
    else:
        state = "DIMENSIONAL_RADIAL_INTERFERENCE"
    return {"bore_radius_mm": bore, "shaft_radius_mm": shaft, "radial_clearance_mm": clearance, "state": state}


def classify_cylindrical_error(
    *,
    axis_angle_rad: Any,
    axis_offset_mm: Any,
    radial_clearance_mm: Any,
    axial_overlap_mm: Any,
    actual_common_area_mm2: Any,
) -> dict[str, Any]:
    angle = _number(axis_angle_rad)
    offset = _number(axis_offset_mm)
    clearance = _number(radial_clearance_mm)
    overlap = _number(axial_overlap_mm)
    common_area = _number(actual_common_area_mm2)
    if min(angle, offset, overlap, common_area) < 0.0:
        raise ValueError("measured magnitudes must be nonnegative")
    if overlap <= RULES["linear_epsilon_mm"]:
        return {"classification": "UNSUPPORTED_INSUFFICIENT_AXIAL_OVERLAP", "error_components": []}
    components = []
    if angle > RULES["angular_epsilon_rad"]:
        components.append("ANGULAR")
    if offset > RULES["linear_epsilon_mm"]:
        components.append("POSITIONAL")
    if abs(clearance) > RULES["radius_epsilon_mm"]:
        components.append("DIMENSIONAL")
    if len(components) > 1:
        classification = "COMPOUND_ERROR_UNSUPPORTED"
    elif components == ["ANGULAR"]:
        classification = "ANGULAR_AXIS_MISALIGNMENT"
    elif components == ["POSITIONAL"]:
        classification = "AXIS_TRANSLATIONAL_MISALIGNMENT"
    elif components == ["DIMENSIONAL"]:
        classification = "DIMENSIONAL_RADIAL_CLEARANCE" if clearance > 0.0 else "DIMENSIONAL_RADIAL_INTERFERENCE"
    elif common_area > RULES["area_epsilon_mm2"]:
        classification = "EXACT_CYLINDRICAL_CONTACT"
    else:
        classification = "GEOMETRY_RELATION_MISMATCH"
    return {"classification": classification, "error_components": components}


def _zero_decision(status: str, repairability: str, reason: str) -> dict[str, Any]:
    return {
        "status": status,
        "repairability": repairability,
        "reason": reason,
        "motion_authorized": False,
        "proposed_translation_mm": [0.0, 0.0, 0.0],
        "executed_translation_mm": [0.0, 0.0, 0.0],
        "execution_count": 0,
    }


def decide_repair(classification: dict[str, Any], axis_offset_vector_mm: Any, policy: dict[str, Any]) -> dict[str, Any]:
    kind = classification.get("classification")
    if kind == "EXACT_CYLINDRICAL_CONTACT":
        return _zero_decision("NO_CORRECTION_REQUIRED", "NO_CORRECTION_REQUIRED", "actual cylindrical contact already exists")
    if kind in {"DIMENSIONAL_RADIAL_CLEARANCE", "DIMENSIONAL_RADIAL_INTERFERENCE"}:
        return _zero_decision("RIGID_POSITION_CORRECTION_NOT_APPLICABLE", "RIGID_POSITION_CORRECTION_NOT_APPLICABLE", "radius mismatch is dimensional")
    if kind == "ANGULAR_AXIS_MISALIGNMENT":
        return _zero_decision("UNSUPPORTED_BY_07A_TRANSLATION_ONLY", "UNSUPPORTED_BY_07A_TRANSLATION_ONLY", "rotation is outside 07A")
    if kind != "AXIS_TRANSLATIONAL_MISALIGNMENT":
        return _zero_decision(kind or "UNSUPPORTED", kind or "UNSUPPORTED", "classification is not translation-repairable")
    offset = _vector(axis_offset_vector_mm)
    norm = _norm(offset)
    proposed = [-value for value in offset]
    valid = (
        isinstance(policy, dict)
        and policy.get("policy_valid") is True
        and type(policy.get("allow_motion")) is bool
        and type(policy.get("allow_pose_interference_resolution")) is bool
    )
    try:
        tau_e = _number(policy.get("tauE_mm")) if valid else 0.0
        budget = _number(policy.get("max_translation_mm")) if valid else 0.0
        valid = valid and tau_e >= 0.0 and budget >= 0.0
    except ValueError:
        valid = False
        tau_e = budget = 0.0
    if not valid or policy.get("allow_motion") is not True or policy.get("allow_pose_interference_resolution") is not True:
        return _zero_decision("MOTION_NOT_AUTHORIZED", "RIGID_TRANSLATION_REPAIRABLE", "explicit motion and pose-interference authorization are required")
    if norm > tau_e + RULES["linear_epsilon_mm"]:
        return _zero_decision("ENGINEERING_TOLERANCE_EXCEEDED", "RIGID_TRANSLATION_REPAIRABLE", "axis offset exceeds tauE_mm")
    if norm > budget + RULES["linear_epsilon_mm"]:
        return _zero_decision("TRANSLATION_BUDGET_EXCEEDED", "RIGID_TRANSLATION_REPAIRABLE", "axis offset exceeds max_translation_mm")
    return {
        "status": "AUTHORIZED_FOR_SINGLE_TRANSLATION",
        "repairability": "RIGID_TRANSLATION_REPAIRABLE",
        "reason": "positional error explicitly authorized within tolerance and budget",
        "motion_authorized": True,
        "proposed_translation_mm": proposed,
        "executed_translation_mm": [0.0, 0.0, 0.0],
        "execution_count": 0,
    }


def _freecad_executable() -> Path:
    discovered = shutil.which("FreeCADCmd") or shutil.which("freecadcmd")
    candidates = [Path(discovered)] if discovered else []
    candidates.append(Path(r"C:\Program Files\FreeCAD 1.1\bin\FreeCADCmd.exe"))
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    raise FileNotFoundError("FreeCADCmd is required for 07A")


def _run_freecad(request: dict[str, Any]) -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="dmslicer-07a-") as temporary:
        request_path = Path(temporary) / "request.json"
        response_path = Path(temporary) / "response.json"
        request_path.write_text(json.dumps(request, ensure_ascii=False), encoding="utf-8")
        environment = os.environ.copy()
        environment.update({
            "DMSLICER_FREECAD_REQUEST": str(request_path),
            "DMSLICER_FREECAD_RESPONSE": str(response_path),
            "DMSLICER_FREECAD_SCRIPT": str(FREECAD_SCRIPT),
        })
        console = "import os; p=os.environ['DMSLICER_FREECAD_SCRIPT']; exec(compile(open(p, encoding='utf-8').read(), p, 'exec'))\n"
        result = subprocess.run(
            [str(_freecad_executable()), "--safe-mode", "-c"],
            input=console,
            env=environment,
            capture_output=True,
            text=True,
            timeout=180,
        )
        if result.returncode != 0 or not response_path.is_file():
            raise RuntimeError(f"FreeCADCmd 07A failed ({result.returncode}): {result.stdout}\n{result.stderr}")
        response = json.loads(response_path.read_text(encoding="utf-8"))
        if response.get("status") != "ok":
            raise RuntimeError(f"FreeCADCmd 07A failed: {response}")
        return response["result"]


def _policy(allow: bool = False) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "policy_valid": True,
        "allow_motion": allow,
        "allow_pose_interference_resolution": allow,
        "tauE_mm": 0.1,
        "max_translation_mm": 0.1,
    }


def generate_cylindrical_interface_repair_fixtures(root: Path) -> dict[str, Any]:
    """Create 07A bundles, reusing tracked 05A A07 inputs where they express the state."""
    root = Path(root)
    reused = {
        "C01": "A07_delta_p0tauE",
        "C03": "A07_delta_p0_5tauE",
        "C04": "A07_delta_m0_5tauE",
    }
    expected = {
        "C01": {"classification": "EXACT_CYLINDRICAL_CONTACT", "status": "NO_CORRECTION_REQUIRED", "axis_offset_mm": 0.0, "radial_clearance_mm": 0.0},
        "C02": {"classification": "AXIS_TRANSLATIONAL_MISALIGNMENT", "status": "CORRECTED_AND_FUSED", "axis_offset_mm": 0.05, "radial_clearance_mm": 0.0},
        "C03": {"classification": "DIMENSIONAL_RADIAL_CLEARANCE", "status": "RIGID_POSITION_CORRECTION_NOT_APPLICABLE", "axis_offset_mm": 0.0, "radial_clearance_mm": 0.05},
        "C04": {"classification": "DIMENSIONAL_RADIAL_INTERFERENCE", "status": "RIGID_POSITION_CORRECTION_NOT_APPLICABLE", "axis_offset_mm": 0.0, "radial_clearance_mm": -0.05},
        "C05": {"classification": "ANGULAR_AXIS_MISALIGNMENT", "status": "UNSUPPORTED_BY_07A_TRANSLATION_ONLY", "axis_offset_mm": 0.0, "axis_angle_rad": 0.001, "radial_clearance_mm": 0.0},
        "AMBIGUOUS": {"classification": "UNSUPPORTED_AMBIGUOUS_CYLINDRICAL_INTERFACE", "status": "UNSUPPORTED_AMBIGUOUS_CYLINDRICAL_INTERFACE"},
        "ROTATED_C02": {"classification": "AXIS_TRANSLATIONAL_MISALIGNMENT", "status": "CORRECTED_AND_FUSED", "axis_offset_mm": 0.05, "radial_clearance_mm": 0.0},
    }
    rows = []
    for scenario in SCENARIOS:
        case = root / scenario
        case.mkdir(parents=True, exist_ok=True)
        step = case / "inputs.step"
        if scenario in reused:
            source = REPO_ROOT / "benchmarks" / "contact_tolerance_pilot_05a" / reused[scenario] / "inputs.step"
            shutil.copy2(source, step)
            source_record = {"mode": "reused_05a_tracked_step", "path": str(source.relative_to(REPO_ROOT)).replace("\\", "/"), "sha256": sha256_file(source)}
        else:
            generation = _run_freecad({"action": "generate", "scenario_id": scenario, "step_path": str(step)})
            if generation.get("valid_closed") != [True, True]:
                raise RuntimeError(f"invalid generated 07A fixture: {scenario}")
            source_record = {"mode": "07a_independent_generation", "geometry": "A07 dimensions; actual STEP is analysis input", "control": "proper_rotation" if scenario == "ROTATED_C02" else None}
        write_json(case / "policy.json", _policy(scenario in {"C02", "ROTATED_C02"}))
        write_json(case / "expected.json", {"schema_version": 1, "scenario_id": scenario, "numeric_rules": RULES, **expected[scenario]})
        write_json(case / "generation_manifest.json", {"schema_version": 1, "scenario_id": scenario, "source": source_record, "input_sha256": sha256_file(step), "hash_semantics": "byte_integrity_only"})
        rows.append({"scenario_id": scenario, "step_sha256": sha256_file(step)})
    manifest = {"schema_version": 1, "operation": "CYLINDRICAL_INTERFACE_REPAIR_07A", "numeric_rules": RULES, "scenarios": rows}
    write_json(root / "manifest.json", manifest)
    return {"status": "PASS", **manifest}


def validate_cylindrical_operation(operation: dict[str, Any], expected: dict[str, Any]) -> dict[str, Any]:
    """Validate saved facts after measurement; expected is never sent to FreeCAD analysis."""
    failures = []
    classification = operation.get("classification", {}).get("classification")
    if classification != expected.get("classification"):
        failures.append({"kind": "classification", "expected": expected.get("classification"), "actual": classification})
    if operation.get("status") != expected.get("status"):
        failures.append({"kind": "status", "expected": expected.get("status"), "actual": operation.get("status")})
    measurement = operation.get("pre_measurement", {})
    for field, epsilon in (("axis_offset_mm", RULES["linear_epsilon_mm"]), ("radial_clearance_mm", RULES["radius_epsilon_mm"]), ("axis_angle_rad", RULES["angular_epsilon_rad"])):
        if field in expected:
            actual = measurement.get(field)
            if not isinstance(actual, (int, float)) or isinstance(actual, bool) or not math.isfinite(float(actual)) or abs(float(actual) - float(expected[field])) > epsilon:
                failures.append({"kind": field, "expected": expected[field], "actual": actual, "tolerance": epsilon})
    motion = operation.get("motion", {})
    rejected = operation.get("status") != "CORRECTED_AND_FUSED"
    if rejected and (motion.get("execution_count") != 0 or motion.get("executed_translation_mm") != [0.0, 0.0, 0.0]):
        failures.append({"kind": "rejected_motion"})
    if operation.get("status") == "CORRECTED_AND_FUSED":
        if motion.get("execution_count") != 1:
            failures.append({"kind": "single_execution"})
        proposed, executed = motion.get("proposed_translation_mm"), motion.get("executed_translation_mm")
        if proposed != executed:
            failures.append({"kind": "proposed_executed_parity"})
        pre_vector = measurement.get("axis_offset_vector_mm")
        if not isinstance(pre_vector, list) or not isinstance(proposed, list) or len(pre_vector) != 3 or len(proposed) != 3 or any(abs(float(a) + float(b)) > RULES["linear_epsilon_mm"] for a, b in zip(pre_vector, proposed)):
            failures.append({"kind": "translation_not_negative_axis_offset"})
        if operation.get("pre_geometry", {}).get("material_common_volume_mm3", 0.0) <= RULES["volume_epsilon_mm3"]:
            failures.append({"kind": "missing_pose_interference"})
        if operation.get("post_measurement", {}).get("axis_offset_mm", math.inf) > RULES["linear_epsilon_mm"]:
            failures.append({"kind": "post_axis_residual"})
        if operation.get("post_geometry", {}).get("actual_common_area_mm2", 0.0) <= RULES["area_epsilon_mm2"]:
            failures.append({"kind": "post_actual_common"})
        if operation.get("post_geometry", {}).get("material_common_volume_mm3", math.inf) > RULES["volume_epsilon_mm3"]:
            failures.append({"kind": "post_material_interference"})
        inverse = operation.get("inverse_translation_equivalence", {})
        if (
            inverse.get("actual_minus_original_mm3", math.inf) > RULES["volume_epsilon_mm3"]
            or inverse.get("original_minus_actual_mm3", math.inf) > RULES["volume_epsilon_mm3"]
            or inverse.get("minimum_distance_mm", math.inf) > RULES["linear_epsilon_mm"]
        ):
            failures.append({"kind": "inverse_geometry_equivalence"})
        artifact = operation.get("artifact_verification", {})
        if artifact.get("status") != "PASS":
            failures.append({"kind": "artifact_geometry_revalidation"})
        artifact_measurement = artifact.get("corrected_measurement", {})
        if artifact_measurement.get("axis_angle_rad", math.inf) > RULES["angular_epsilon_rad"]:
            failures.append({"kind": "artifact_post_axis_angle"})
        if abs(artifact_measurement.get("radial_clearance_mm", math.inf)) > RULES["radius_epsilon_mm"]:
            failures.append({"kind": "artifact_post_radius"})
        if artifact_measurement.get("axial_overlap_mm", 0.0) <= RULES["linear_epsilon_mm"]:
            failures.append({"kind": "artifact_post_axial_overlap"})
    debug = operation.get("debug", {})
    if debug.get("reopened") is not True:
        failures.append({"kind": "human_inspection_reopen"})
    return {"schema_version": 1, "status": "PASS" if not failures else "FAIL", "failures": failures}


def validate_published_artifacts(operation: dict[str, Any], output_dir: Path) -> dict[str, Any]:
    output = Path(output_dir)
    artifacts = operation.get("artifacts", {})
    required = ("corrected_assembly.step", "fused.step", "actual_common.brep")
    failures = []
    for name in required:
        record = artifacts.get(name)
        path = output / name
        if not isinstance(record, dict) or not path.is_file():
            failures.append({"kind": "missing_artifact", "artifact": name})
        elif sha256_file(path) != record.get("sha256"):
            failures.append({"kind": "byte_integrity", "artifact": name})
    if failures:
        return {"schema_version": 1, "status": "FAIL", "failures": failures}
    actual = _run_freecad({
        "action": "verify_artifacts",
        "numeric_rules": RULES,
        "corrected_step": str(output / "corrected_assembly.step"),
        "fused_step": str(output / "fused.step"),
        "common_brep": str(output / "actual_common.brep"),
    })
    return {"schema_version": 1, **actual}


def run_cylindrical_repair_case(case_dir: Path, output_dir: Path, *, reverse: bool = False) -> dict[str, Any]:
    case, output = Path(case_dir), Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    step = case / "inputs.step"
    generation = read_json(case / "generation_manifest.json")
    actual_hash = sha256_file(step)
    if actual_hash != generation.get("input_sha256"):
        raise ValueError("07A input byte-integrity check failed")
    policy = read_json(case / "policy.json")
    operation = _run_freecad({
        "action": "analyze",
        "scenario_id": case.name,
        "step_path": str(step),
        "input_step_sha256": actual_hash,
        "output_dir": str(output),
        "numeric_rules": RULES,
        "policy": policy,
        "reverse": reverse,
    })
    if operation.get("status") in {"CORRECTED_AND_FUSED", "POSTCHECK_FAILED"} and all((output / name).is_file() for name in ("corrected_assembly.step", "fused.step", "actual_common.brep")):
        operation["artifacts"] = {
            name: {"path": name, "sha256": sha256_file(output / name), "hash_semantics": "byte_integrity_only"}
            for name in ("corrected_assembly.step", "fused.step", "actual_common.brep")
        }
        operation["artifact_verification"] = validate_published_artifacts(operation, output)
    write_json(output / "operation.json", operation)
    expected = read_json(case / "expected.json")
    validation = validate_cylindrical_operation(operation, expected)
    write_json(output / "validation.json", validation)
    write_json(output / "expected_snapshot.json", expected)
    return {"operation": operation, "validation": validation, "expected": expected}


def operation_projection(operation: dict[str, Any]) -> dict[str, Any]:
    """Project actual geometry decisions without expected or byte-identity fields."""
    return {
        key: value
        for key, value in operation.items()
        if key not in {"input_step_sha256", "debug", "artifacts"}
    }


def _repeatability(first: dict[str, Any], second: dict[str, Any]) -> dict[str, Any]:
    failures = []

    def compare(left: Any, right: Any, path: str) -> None:
        if isinstance(left, bool) or isinstance(right, bool):
            if left is not right:
                failures.append({"kind": "value", "field": path, "first": left, "second": right})
        elif isinstance(left, (int, float)) and isinstance(right, (int, float)):
            epsilon = RULES["angular_epsilon_rad"] if path.endswith("_rad") else RULES["volume_epsilon_mm3"] if path.endswith("_mm3") else RULES["area_epsilon_mm2"] if path.endswith("_mm2") else RULES["linear_epsilon_mm"]
            if not math.isfinite(float(left)) or not math.isfinite(float(right)) or abs(float(left) - float(right)) > epsilon:
                failures.append({"kind": "numeric", "field": path, "first": left, "second": right, "tolerance": epsilon})
        elif isinstance(left, dict) and isinstance(right, dict):
            if set(left) != set(right):
                failures.append({"kind": "fields", "field": path})
            for key in sorted(set(left) & set(right)):
                compare(left[key], right[key], f"{path}.{key}" if path else key)
        elif isinstance(left, list) and isinstance(right, list):
            if len(left) != len(right):
                failures.append({"kind": "length", "field": path})
            for index, (left_item, right_item) in enumerate(zip(left, right)):
                compare(left_item, right_item, f"{path}.{index}")
        elif left != right:
            failures.append({"kind": "value", "field": path, "first": left, "second": right})

    compare(operation_projection(first), operation_projection(second), "")
    return {"schema_version": 1, "status": "PASS" if not failures else "FAIL", "comparison": "tolerance_aware_actual_geometry_and_provenance", "failures": failures}


def run_cylindrical_repair_suite(fixture_root: Path, output_root: Path) -> dict[str, Any]:
    fixtures, outputs = Path(fixture_root), Path(output_root)
    rows, repeatability = {}, {}
    for scenario in SCENARIOS:
        first = run_cylindrical_repair_case(fixtures / scenario, outputs / scenario)
        second = run_cylindrical_repair_case(fixtures / scenario, outputs / "repeatability" / "second_process" / scenario)
        comparison = _repeatability(first["operation"], second["operation"])
        repeatability[scenario] = comparison
        write_json(outputs / scenario / "repeatability.json", comparison)
        rows[scenario] = {
            "classification": first["operation"]["classification"]["classification"],
            "status": first["operation"]["status"],
            "validation": first["validation"]["status"],
        }
    status = "PASS" if all(row["validation"] == "PASS" for row in rows.values()) and all(item["status"] == "PASS" for item in repeatability.values()) else "FAIL"
    summary = {"schema_version": 1, "status": status, "cases": rows, "repeatability": repeatability}
    write_json(outputs / "summary.json", summary)
    view = """# 07A Cylindrical Interface Repair — View Index

STEP/B-rep operations and JSON validation are authoritative. FCStd files are human-inspection aids only.

1. **C01 — exact cylindrical contact**: open `C01/operation_debug.FCStd`; inspect `01_Originals`, `02_Selected_Interface`, then `05_Common_Patches`. Confirm `NO_CORRECTION_REQUIRED` and a full cylindrical common band.
2. **C02 — axis translational misalignment**: open `C02/operation_debug.FCStd`; inspect originals and axes, `03_Precommit_Preview`, `04_Corrected_Assembly`, `05_Common_Patches`, then `09_Fused_Result`. The arrow is `DISPLAY_ONLY / NOT_EXECUTED`; the corrected shaft is the sole executed translation.
3. **C03 — dimensional radial clearance**: open `C03/operation_debug.FCStd`; confirm coaxial axes, different radii, and zero executed motion.
4. **C04 — dimensional radial interference**: open `C04/operation_debug.FCStd`; inspect `10_Rejection_Evidence` for actual material common and confirm zero executed motion.
5. **C05 — angular axis misalignment**: open `C05/operation_debug.FCStd`; inspect the nonparallel axes and confirm translation-only rejection.

Control: `AMBIGUOUS/operation_debug.FCStd` shows all role-valid candidates without selecting one. A likely failure is any corrected/fused success artifact or nonzero motion for C03/C04/C05/AMBIGUOUS.

Orientation control: `ROTATED_C02/operation_debug.FCStd` applies the same C02 geometry under a proper world rotation and translation; its measured correction must remain perpendicular to the rotated axis.
"""
    outputs.mkdir(parents=True, exist_ok=True)
    (outputs / "VIEW_INDEX.md").write_text(view, encoding="utf-8")
    human = outputs / "HUMAN_REVIEW"
    human.mkdir(parents=True, exist_ok=True)
    (human / "README.md").write_text("# HUMAN_REVIEW\n\nUse `../VIEW_INDEX.md`; this directory is an index only and is not validator input or geometry truth.\n", encoding="utf-8")
    return summary
