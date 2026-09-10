"""Limited, evidence-isolated A01/A07 engineering-tolerance pilot."""

from __future__ import annotations

import csv
import json
import math
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from .evidence import read_json, sha256_file, write_json


FREECAD_SCRIPT = Path(__file__).with_name("freecad_contact_tolerance_pilot_05a.py")
FROZEN_OFFSET_RATIOS = (-4, -2, -1.1, -1, -0.9, -0.5, -0.1, 0, 0.1, 0.5, 0.9, 1, 1.1, 2, 4)
TAU_E_MM = 0.1
TAU_K = "NOT_AVAILABLE"
CASES = ("A01", "A07")
LINEAR_EPSILON_MM = 1e-7
AREA_EPSILON_MM2 = 1e-8
VOLUME_EPSILON_MM3 = 1e-6


def engineering_state(offset: float, tau_e: float) -> str:
    """Classify a measured signed offset using the frozen inclusive boundary."""
    if abs(offset) <= 1e-12:
        return "exact"
    if offset > 0:
        return "positive_gap_within_tolerance" if offset <= tau_e + 1e-12 else "positive_gap_beyond_tolerance"
    return "penetration_within_tolerance" if offset >= -tau_e - 1e-12 else "penetration_beyond_tolerance"


def _freecad_executable() -> Path:
    discovered = shutil.which("freecadcmd") or shutil.which("FreeCADCmd.exe")
    for candidate in (Path(discovered) if discovered else None, Path(r"C:\Program Files\FreeCAD 1.1\bin\freecadcmd.exe")):
        if candidate and candidate.is_file():
            return candidate
    raise FileNotFoundError("FreeCADCmd.exe was not found")


def _run_freecad(request: dict[str, Any]) -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="dmslicer_tolerance_05a_") as temporary:
        request_path, response_path = Path(temporary) / "request.json", Path(temporary) / "response.json"
        write_json(request_path, request)
        environment = os.environ.copy()
        environment.update({"DMSLICER_FREECAD_REQUEST": str(request_path), "DMSLICER_FREECAD_RESPONSE": str(response_path), "DMSLICER_FREECAD_SCRIPT": str(FREECAD_SCRIPT)})
        console = "import os; p=os.environ['DMSLICER_FREECAD_SCRIPT']; exec(compile(open(p, encoding='utf-8').read(), p, 'exec'))\n"
        completed = subprocess.run([str(_freecad_executable()), "--safe-mode", "-c"], input=console, env=environment, text=True, capture_output=True, timeout=180, check=False)
        if not response_path.is_file():
            raise RuntimeError(f"FreeCADCmd did not write response: {completed.stderr}")
        response = read_json(response_path)
        if completed.returncode or response.get("status") == "FAILED":
            raise RuntimeError(f"FreeCADCmd tolerance pilot failed: {response}")
        return response


def _nominal(case_id: str) -> dict[str, float]:
    if case_id == "A01":
        raw = (20.0, 20.0, 20.0)
        scale = 100.0 / math.sqrt(sum(v * v for v in raw))
        return {"scale": scale, "a_mm": 20 * scale, "b_mm": 20 * scale, "h_mm": 10 * scale}
    if case_id == "A07":
        raw = (40.0, 40.0, 40.0)
        scale = 100.0 / math.sqrt(sum(v * v for v in raw))
        return {
            "scale": scale,
            "shaft_radius_mm": 10 * scale,
            "shaft_z_min_mm": 0.0,
            "shaft_z_max_mm": 30 * scale,
            "sleeve_outer_radius_mm": 20 * scale,
            "sleeve_z_min_mm": -5 * scale,
            "sleeve_z_max_mm": 35 * scale,
            "bore_cutter_z_min_mm": -10 * scale,
            "bore_cutter_z_max_mm": 50 * scale,
        }
    raise ValueError(f"unsupported pilot case {case_id}")


def _sample_id(case_id: str, ratio: float) -> str:
    token = ("m" if ratio < 0 else "p") + str(abs(ratio)).replace(".", "_")
    return f"{case_id}_delta_{token}tauE"


def _truth(case_id: str, ratio: float, geometry: dict[str, float]) -> dict[str, Any]:
    delta = ratio * TAU_E_MM
    dimension = "2D" if abs(delta) <= 1e-12 else "none" if delta > 0 else "3D"
    expected: dict[str, Any] = {
        "schema_version": 1, "case_id": case_id, "ground_truth_mode": "construction_derived",
        "intended_relation_dimension": "2D", "set_signed_offset_mm": delta,
        "engineering_state": engineering_state(delta, TAU_E_MM), "exact_intersection_dimension": dimension,
    }
    if dimension == "2D":
        expected["contact_area_mm2"] = geometry["a_mm"] * geometry["b_mm"] if case_id == "A01" else 2 * math.pi * geometry["shaft_radius_mm"] * (geometry["shaft_z_max_mm"] - geometry["shaft_z_min_mm"])
    if dimension == "3D":
        if case_id == "A01": expected["material_common_volume_mm3"] = -delta * geometry["a_mm"] * geometry["b_mm"]
        else: expected["material_common_volume_mm3"] = math.pi * (geometry["shaft_radius_mm"] ** 2 - (geometry["shaft_radius_mm"] + delta) ** 2) * (geometry["shaft_z_max_mm"] - geometry["shaft_z_min_mm"])
    return expected


def generate_contact_tolerance_pilot(root: Path, *, case_ids: tuple[str, ...] = CASES) -> dict[str, Any]:
    """Create separate tracked-style STEP/parameter/independent-truth bundles."""
    root = Path(root); samples = []
    for case_id in case_ids:
        geometry = _nominal(case_id)
        for ratio in FROZEN_OFFSET_RATIOS:
            sample_id = _sample_id(case_id, ratio); sample = root / sample_id; sample.mkdir(parents=True, exist_ok=True)
            delta = ratio * TAU_E_MM
            parameters = {"schema_version": 1, "pilot_level": "LEVEL_B_PILOT", "case_id": case_id, "sample_id": sample_id, "perturbation_kind": "rigid_pose" if case_id == "A01" else "construction_variant", "delta_over_tauE": ratio, "set_signed_offset_mm": delta, "tauE_mm": TAU_E_MM, "normalization": "nominal configuration L=100 mm; perturbation is not renormalized", "geometry": geometry}
            if case_id == "A07":
                parameters["construction_invariants"] = _a07_expected_construction(geometry)
            _run_freecad({"action": "generate", "case_id": case_id, "step_path": str(sample / "inputs.step"), "parameters": parameters})
            write_json(sample / "parameters.json", parameters)
            write_json(sample / "expected.json", _truth(case_id, ratio, geometry))
            samples.append({"case_id": case_id, "sample_id": sample_id, "step_sha256": sha256_file(sample / "inputs.step")})
    return {"schema_version": 1, "pilot_level": "LEVEL_B_PILOT", "samples": samples}


def regenerate_a07_pilot(root: Path) -> dict[str, Any]:
    """Replace only 05A A07 derived inputs and record old/new STEP hashes."""
    root = Path(root)
    previous = {path.parent.name: sha256_file(path) for path in sorted(root.glob("A07_*/inputs.step"))}
    generated = generate_contact_tolerance_pilot(root, case_ids=("A07",))
    replacement = [{"sample_id": sample["sample_id"], "old_step_sha256": previous.get(sample["sample_id"], "NOT_PRESENT"), "new_step_sha256": sample["step_sha256"]} for sample in generated["samples"]]
    report = {"schema_version": 1, "reason": "fix: preserve frozen A07 outer sleeve controls while varying only bore radius", "replaced_a07_samples": replacement, "a01_steps_modified": False, "old_version_commit": "312bc7de1a73424aa6dc6d1c8bc2a2ce4d696443"}
    write_json(root / "A07_REGENERATION_05A_FIX.json", report)
    return report


def _a07_expected_construction(geometry: dict[str, float]) -> dict[str, float]:
    shaft_length = geometry["shaft_z_max_mm"] - geometry["shaft_z_min_mm"]
    sleeve_length = geometry["sleeve_z_max_mm"] - geometry["sleeve_z_min_mm"]
    return {
        "shaft_radius_mm": geometry["shaft_radius_mm"],
        "shaft_z_min_mm": geometry["shaft_z_min_mm"],
        "shaft_z_max_mm": geometry["shaft_z_max_mm"],
        "sleeve_outer_radius_mm": geometry["sleeve_outer_radius_mm"],
        "sleeve_z_min_mm": geometry["sleeve_z_min_mm"],
        "sleeve_z_max_mm": geometry["sleeve_z_max_mm"],
        "sleeve_length_mm": sleeve_length,
        "interface_length_mm": shaft_length,
        "lower_end_clearance_mm": geometry["shaft_z_min_mm"] - geometry["sleeve_z_min_mm"],
        "upper_end_clearance_mm": geometry["sleeve_z_max_mm"] - geometry["shaft_z_max_mm"],
        "combined_L_mm": 100.0,
    }


def validate_a07_construction(actual: dict[str, Any], expected: dict[str, float]) -> dict[str, Any]:
    """Accept A07 only if imported STEP preserves every fixed construction control."""
    failures = []
    for key, expected_value in expected.items():
        value = actual.get(key)
        if not isinstance(value, (int, float)) or not math.isfinite(value) or abs(value - expected_value) > LINEAR_EPSILON_MM:
            failures.append({"kind": key, "expected": expected_value, "actual": value, "tolerance": LINEAR_EPSILON_MM})
    return {"schema_version": 1, "status": "PASS" if not failures else "FAIL", "failures": failures}


def validate_a07_nominal_equivalence(pilot_actual: dict[str, Any], frozen_actual: dict[str, Any]) -> dict[str, Any]:
    """Compare the nominal pilot and frozen A07 only from imported STEP evidence."""
    failures = []
    for key in ("shaft_radius_mm", "shaft_z_min_mm", "shaft_z_max_mm", "sleeve_outer_radius_mm", "sleeve_z_min_mm", "sleeve_z_max_mm", "interface_length_mm", "lower_end_clearance_mm", "upper_end_clearance_mm", "combined_L_mm", "shaft_material_volume_mm3", "sleeve_material_volume_mm3"):
        pilot_value = pilot_actual.get("construction", {}).get(key)
        frozen_value = frozen_actual.get("construction", {}).get(key)
        tolerance = VOLUME_EPSILON_MM3 if key.endswith("volume_mm3") else LINEAR_EPSILON_MM
        if not isinstance(pilot_value, (int, float)) or not isinstance(frozen_value, (int, float)) or not math.isfinite(pilot_value) or not math.isfinite(frozen_value) or abs(pilot_value - frozen_value) > tolerance:
            failures.append({"kind": key, "pilot": pilot_value, "frozen": frozen_value, "tolerance": tolerance})
    for key, tolerance in (("positive_common_area_mm2", AREA_EPSILON_MM2), ("material_common_volume_mm3", VOLUME_EPSILON_MM3)):
        pilot_value = pilot_actual.get("geometry_state", {}).get(key)
        frozen_value = frozen_actual.get("geometry_state", {}).get(key)
        if not isinstance(pilot_value, (int, float)) or not isinstance(frozen_value, (int, float)) or not math.isfinite(pilot_value) or not math.isfinite(frozen_value) or abs(pilot_value - frozen_value) > tolerance:
            failures.append({"kind": key, "pilot": pilot_value, "frozen": frozen_value, "tolerance": tolerance})
    return {"schema_version": 1, "status": "PASS" if not failures else "FAIL", "failures": failures}


def validate_tolerance_actual(actual: dict[str, Any], expected: dict[str, Any]) -> dict[str, Any]:
    """Compare saved actual evidence to independent truth only after measurement."""
    failures: list[dict[str, Any]] = []
    for field in ("case_id", "engineering_state"):
        if actual.get(field) != expected.get(field): failures.append({"kind": field, "expected": expected.get(field), "actual": actual.get(field)})
    actual_dimension = actual.get("geometry_state", {}).get("exact_intersection_dimension")
    if actual_dimension != expected.get("exact_intersection_dimension"):
        failures.append({"kind": "exact_intersection_dimension", "expected": expected.get("exact_intersection_dimension"), "actual": actual_dimension})
    direct_fuse = actual.get("direct_fuse")
    if not isinstance(direct_fuse, dict):
        failures.append({"kind": "direct_fuse", "actual": direct_fuse})
    else:
        connected = direct_fuse.get("one_valid_connected_solid")
        consistent = isinstance(direct_fuse.get("solid_count"), int) and connected == (direct_fuse["solid_count"] == 1 and direct_fuse.get("valid") is True and direct_fuse.get("closed") is True)
        if not consistent: failures.append({"kind": "direct_fuse_consistency", "actual": direct_fuse})
    measured = actual.get("measured_signed_offset_mm")
    expected_offset = expected.get("set_signed_offset_mm")
    if not isinstance(measured, (int, float)) or not isinstance(expected_offset, (int, float)) or abs(measured - expected_offset) > 1e-7:
        failures.append({"kind": "measured_signed_offset_mm", "expected": expected_offset, "actual": measured, "tolerance": 1e-7})
    geometry_state = actual.get("geometry_state")
    if not isinstance(geometry_state, dict):
        failures.append({"kind": "geometry_state", "actual": geometry_state})
    elif "contact_area_mm2" in expected:
        value = geometry_state.get("positive_common_area_mm2")
        if not isinstance(value, (int, float)) or not math.isfinite(value) or abs(value - expected["contact_area_mm2"]) > AREA_EPSILON_MM2:
            failures.append({"kind": "positive_common_area_mm2", "expected": expected["contact_area_mm2"], "actual": value, "tolerance": AREA_EPSILON_MM2})
    elif "material_common_volume_mm3" in expected:
        value = geometry_state.get("material_common_volume_mm3")
        if not isinstance(value, (int, float)) or not math.isfinite(value) or abs(value - expected["material_common_volume_mm3"]) > VOLUME_EPSILON_MM3:
            failures.append({"kind": "material_common_volume_mm3", "expected": expected["material_common_volume_mm3"], "actual": value, "tolerance": VOLUME_EPSILON_MM3})
    elif expected.get("exact_intersection_dimension") == "none":
        value = geometry_state.get("material_common_volume_mm3")
        if not isinstance(value, (int, float)) or not math.isfinite(value) or abs(value) > VOLUME_EPSILON_MM3 or geometry_state.get("positive_common_area_mm2") is not None:
            failures.append({"kind": "gap_no_intersection", "actual": geometry_state, "tolerance": VOLUME_EPSILON_MM3})
    return {"schema_version": 1, "status": "PASS" if not failures else "FAIL", "failures": failures}


def run_contact_tolerance_pilot_case(case_dir: Path, output_dir: Path, *, debug_path: Path | None = None) -> dict[str, Any]:
    """Measure one STEP without loading its parameter or expected-truth records."""
    case_dir, output_dir = Path(case_dir), Path(output_dir); output_dir.mkdir(parents=True, exist_ok=True)
    case_id = case_dir.name.split("_delta_", 1)[0]
    step = case_dir / "inputs.step"
    actual = _run_freecad({"action": "analyze", "case_id": case_id, "step_path": str(step), "tauE_mm": TAU_E_MM, "debug_path": str(debug_path) if debug_path else None})
    actual.pop("status", None); actual["input_step_sha256"] = sha256_file(step)
    write_json(output_dir / "actual.json", actual)
    parameters = read_json(case_dir / "parameters.json")
    expected = read_json(case_dir / "expected.json")
    geometry_validation = validate_tolerance_actual(actual, expected)
    construction_validation = {"schema_version": 1, "status": "NOT_APPLICABLE", "failures": []}
    if parameters["case_id"] == "A07":
        construction_validation = validate_a07_construction(actual.get("construction", {}), parameters["construction_invariants"])
    validation = {"schema_version": 1, "status": "PASS" if geometry_validation["status"] == "PASS" and construction_validation["status"] in {"PASS", "NOT_APPLICABLE"} else "FAIL", "construction_validation": construction_validation, "geometry_measurement_validation": geometry_validation, "engineering_classification_validation": {"status": "PASS" if not any(item["kind"] in {"engineering_state", "measured_signed_offset_mm", "exact_intersection_dimension"} for item in geometry_validation["failures"]) else "FAIL"}, "direct_fuse_outcome": actual["direct_fuse"], "failures": geometry_validation["failures"] + construction_validation["failures"]}
    write_json(output_dir / "validation.json", validation)
    return {"actual": actual, "validation": validation}


def _flat_row(sample_id: str, result: dict[str, Any], parameters: dict[str, Any]) -> dict[str, Any]:
    actual, validation = result["actual"], result["validation"]
    geometry, fuse = actual["geometry_state"], actual["direct_fuse"]
    return {"sample_id": sample_id, "base_case": actual["case_id"], "perturbation_kind": parameters["perturbation_kind"], "set_delta_mm": parameters["set_signed_offset_mm"], "measured_delta_mm": actual["measured_signed_offset_mm"], "tauE_mm": actual["tauE_mm"], "tauK_mm": actual["tauK_mm"], "L_mm": actual["L_mm"], "tauE_over_L": actual["tauE_over_L"], "exact_dimension": geometry["exact_intersection_dimension"], "engineering_state": actual["engineering_state"], "direct_fuse_executed": fuse["executed"], "direct_fuse_one_solid": fuse["one_valid_connected_solid"], "solid_count": fuse["solid_count"], "validation": validation["status"], "failure_or_rejection_reason": "; ".join(f["kind"] for f in validation["failures"]) or fuse.get("reason", "")}


def run_contact_tolerance_pilot_repeatability(fixture_root: Path, output_root: Path) -> dict[str, Any]:
    """Repeat the same immutable STEP inputs in two separate FreeCADCmd processes."""
    fixture_root, output_root = Path(fixture_root), Path(output_root)
    comparisons = []
    for case_dir in sorted(path for path in fixture_root.iterdir() if path.is_dir()):
        first = run_contact_tolerance_pilot_case(case_dir, output_root / "run_1" / case_dir.name)
        second = run_contact_tolerance_pilot_case(case_dir, output_root / "run_2" / case_dir.name)
        comparisons.append({"sample_id": case_dir.name, "actual_match": first["actual"] == second["actual"], "validation_match": first["validation"] == second["validation"], "input_hash_match": first["actual"]["input_step_sha256"] == second["actual"]["input_step_sha256"]})
    report = {"schema_version": 1, "processes": 2, "status": "PASS" if all(all(row[key] for key in ("actual_match", "validation_match", "input_hash_match")) for row in comparisons) else "FAIL", "samples": comparisons}
    write_json(output_root / "repeatability.json", report)
    return report


def run_contact_tolerance_pilot_suite(fixture_root: Path, output_root: Path) -> dict[str, Any]:
    fixture_root, output_root = Path(fixture_root), Path(output_root); output_root.mkdir(parents=True, exist_ok=True)
    rows = []
    for case_dir in sorted(p for p in fixture_root.iterdir() if p.is_dir()):
        parameters = read_json(case_dir / "parameters.json")
        ratio = parameters["delta_over_tauE"]
        debug = output_root / "views" / f"{case_dir.name}.FCStd" if ratio in (-0.5, 0, 0.5) else None
        result = run_contact_tolerance_pilot_case(case_dir, output_root / "samples" / case_dir.name, debug_path=debug)
        rows.append(_flat_row(case_dir.name, result, parameters))
    fieldnames = list(rows[0])
    with (output_root / "results.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames); writer.writeheader(); writer.writerows(rows)
    mismatches = [row for row in rows if row["validation"] != "PASS"]
    pilot_nominal = read_json(output_root / "samples" / "A07_delta_p0tauE" / "actual.json")
    frozen_nominal = _run_freecad({"action": "analyze", "case_id": "A07", "step_path": str(Path("benchmarks/contact_canonical_03b/A07/fixture.step")), "tauE_mm": TAU_E_MM, "debug_path": None})
    frozen_nominal.pop("status", None)
    nominal_equivalence = validate_a07_nominal_equivalence(pilot_nominal, frozen_nominal)
    summary = {"schema_version": 1, "pilot_level": "LEVEL_B_PILOT", "sample_count": len(rows), "method_mismatch_count": len(mismatches), "boundary_samples": [row for row in rows if abs(abs(row["set_delta_mm"]) - TAU_E_MM) <= 1e-12], "a07_frozen_nominal_equivalence": nominal_equivalence, "samples": rows, "status": "PASS" if not mismatches and nominal_equivalence["status"] == "PASS" else "METHOD_MISMATCH"}
    write_json(output_root / "summary.json", summary)
    (output_root / "VIEW_INDEX.md").write_text("# 05A 工程容差小样本查看索引\n\n六个 FCStd 仅显示真实输入、实际交集和直接融合结果。它们不移动运算几何，也不会为间隙或三维穿透伪造接触面。\n", encoding="utf-8")
    (output_root / "CONCLUSION.md").write_text(f"# 05A 实验结论\n\n已采样 A01/A07 共 {len(rows)} 个样本；METHOD_MISMATCH={len(mismatches)}。在离零最近的非零采样点 ±0.1 观察到状态变化；零与该点之间未进一步采样。名义几何接触的变化点是 δ=0，工程容差边界是 ±τE。结果仅覆盖固定 15 点，不外推连续区间；旋转、切向扰动、多尺度及其他 cases 未执行。\n", encoding="utf-8")
    repeatability = run_contact_tolerance_pilot_repeatability(fixture_root, output_root / "repeatability")
    summary["repeatability"] = repeatability["status"]
    write_json(output_root / "summary.json", summary)
    return summary
