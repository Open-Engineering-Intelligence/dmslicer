"""Level-B scale-covariance pilot built on the 05A real B-rep measurement path."""

from __future__ import annotations

import csv
import math
from pathlib import Path
from typing import Any

from .contact_tolerance_pilot_05a import (
    AREA_EPSILON_MM2, CASES, FROZEN_OFFSET_RATIOS, LINEAR_EPSILON_MM,
    TAU_E_MM, VOLUME_EPSILON_MM3, _a07_expected_construction, _nominal,
    _run_freecad, _sample_id, _truth, engineering_state,
)
from .evidence import read_json, sha256_file, write_json

SCALES = (0.01, 1.0, 100.0)
PILOT_LEVEL = "LEVEL_B_SCALE_PILOT"


def scaled_tau_e(scale: float) -> float:
    return TAU_E_MM * scale


def scaled_geometry(case_id: str, scale: float) -> dict[str, float]:
    """Return direct analytic dimensions, uniformly scaled from the 05A nominal."""
    if scale not in SCALES:
        raise ValueError(f"unsupported scale {scale}")
    return {key: value * scale for key, value in _nominal(case_id).items()}


def _scale_token(scale: float) -> str:
    return {0.01: "s0_01", 1.0: "s1", 100.0: "s100"}[scale]


def _expected(case_id: str, ratio: float, geometry: dict[str, float], scale: float) -> dict[str, Any]:
    """Independently evaluate this scale's analytic construction truth."""
    delta = ratio * scaled_tau_e(scale)
    dimension = "2D" if abs(delta) <= 1e-12 else "none" if delta > 0 else "3D"
    expected: dict[str, Any] = {
        "schema_version": 1, "pilot_level": PILOT_LEVEL, "case_id": case_id,
        "ground_truth_mode": "construction_derived", "scale": scale,
        "intended_relation_dimension": "2D", "set_signed_offset_mm": delta,
        "engineering_state": engineering_state(delta, scaled_tau_e(scale)),
        "exact_intersection_dimension": dimension,
    }
    if dimension == "2D":
        expected["contact_area_mm2"] = geometry["a_mm"] * geometry["b_mm"] if case_id == "A01" else 2 * math.pi * geometry["shaft_radius_mm"] * (geometry["shaft_z_max_mm"] - geometry["shaft_z_min_mm"])
    if dimension == "3D":
        expected["material_common_volume_mm3"] = (-delta * geometry["a_mm"] * geometry["b_mm"] if case_id == "A01" else math.pi * (geometry["shaft_radius_mm"] ** 2 - (geometry["shaft_radius_mm"] + delta) ** 2) * (geometry["shaft_z_max_mm"] - geometry["shaft_z_min_mm"]))
    return expected


def generate_contact_scale_covariance_pilot(root: Path, tracked_05a_root: Path) -> dict[str, Any]:
    """Create only scaled STEP inputs; 1x entries remain immutable 05A references."""
    root, tracked_05a_root = Path(root), Path(tracked_05a_root)
    samples: list[dict[str, Any]] = []
    for scale in SCALES:
        for case_id in CASES:
            geometry = scaled_geometry(case_id, scale)
            for ratio in FROZEN_OFFSET_RATIOS:
                base_id = _sample_id(case_id, ratio)
                sample_id = f"{base_id}_{_scale_token(scale)}"
                delta = ratio * scaled_tau_e(scale)
                parameters = {"schema_version": 1, "pilot_level": PILOT_LEVEL, "case_id": case_id, "sample_id": sample_id, "scale": scale, "scale_mode": "co-scaled-tauE", "perturbation_kind": "rigid_pose" if case_id == "A01" else "construction_variant", "delta_over_tauE": ratio, "set_signed_offset_mm": delta, "tauE_mm": scaled_tau_e(scale), "tauK_mm": "NOT_AVAILABLE", "normalization": "05A nominal L=100 mm; all dimensions and tauE co-scaled; perturbation is not renormalized", "geometry": geometry}
                if case_id == "A07":
                    parameters["construction_invariants"] = _a07_expected_construction(geometry)
                    parameters["construction_invariants"]["combined_L_mm"] = 100.0 * scale
                expected = _expected(case_id, ratio, geometry, scale)
                if scale == 1.0:
                    source = tracked_05a_root / base_id / "inputs.step"
                    if not source.is_file():
                        raise FileNotFoundError(source)
                    step = source
                    source_kind = "tracked_05A_reference"
                else:
                    sample = root / sample_id; sample.mkdir(parents=True, exist_ok=True)
                    step = sample / "inputs.step"
                    _run_freecad({"action": "generate", "case_id": case_id, "step_path": str(step), "parameters": parameters})
                    write_json(sample / "parameters.json", parameters); write_json(sample / "expected.json", expected)
                    source_kind = "generated_05B"
                samples.append({"sample_id": sample_id, "case_id": case_id, "scale": scale, "source_kind": source_kind, "step_path": str(step), "step_sha256": sha256_file(step), "parameters": parameters, "expected": expected})
    manifest = {"schema_version": 1, "pilot_level": PILOT_LEVEL, "scale_mode": "co-scaled-tauE", "sample_count": len(samples), "new_input_count": sum(row["source_kind"] == "generated_05B" for row in samples), "tracked_reference_count": sum(row["source_kind"] == "tracked_05A_reference" for row in samples), "samples": samples}
    write_json(root / "manifest.json", manifest)
    return manifest


def _finite(value: Any) -> bool:
    return isinstance(value, (int, float)) and math.isfinite(value)


def validate_scale_actual(actual: dict[str, Any], expected: dict[str, Any]) -> dict[str, Any]:
    """Keep classification, native-absolute, and normalized evidence distinct."""
    classification_failures: list[dict[str, Any]] = []
    scale = actual.get("scale")
    if not _finite(scale) or scale not in SCALES:
        classification_failures.append({"kind": "scale", "actual": scale})
        scale = 1.0
    geometry = actual.get("geometry_state") if isinstance(actual.get("geometry_state"), dict) else {}
    for key in ("case_id", "engineering_state"):
        if actual.get(key) != expected.get(key): classification_failures.append({"kind": key, "expected": expected.get(key), "actual": actual.get(key)})
    if geometry.get("exact_intersection_dimension") != expected.get("exact_intersection_dimension"):
        classification_failures.append({"kind": "exact_intersection_dimension", "expected": expected.get("exact_intersection_dimension"), "actual": geometry.get("exact_intersection_dimension")})
    measured, set_delta = actual.get("measured_signed_offset_mm"), expected.get("set_signed_offset_mm")
    if not _finite(measured) or not _finite(set_delta) or abs(measured - set_delta) > LINEAR_EPSILON_MM:
        classification_failures.append({"kind": "measured_signed_offset_mm", "expected": set_delta, "actual": measured})
    native_failures: list[dict[str, Any]] = []
    native_metrics = {"area": {"status": "NOT_APPLICABLE"}, "volume": {"status": "NOT_APPLICABLE"}}
    if "contact_area_mm2" in expected:
        value = geometry.get("positive_common_area_mm2")
        if not _finite(value) or abs(value - expected["contact_area_mm2"]) > AREA_EPSILON_MM2:
            native_failures.append({"kind": "positive_common_area_mm2", "actual": value, "expected": expected["contact_area_mm2"], "tolerance_mm2": AREA_EPSILON_MM2})
        native_metrics["area"] = {"status": "FAIL" if native_failures else "PASS"}
    elif "material_common_volume_mm3" in expected:
        value = geometry.get("material_common_volume_mm3")
        if not _finite(value) or abs(value - expected["material_common_volume_mm3"]) > VOLUME_EPSILON_MM3:
            native_failures.append({"kind": "material_common_volume_mm3", "actual": value, "expected": expected["material_common_volume_mm3"], "tolerance_mm3": VOLUME_EPSILON_MM3})
        native_metrics["volume"] = {"status": "FAIL" if native_failures else "PASS"}
    elif expected.get("exact_intersection_dimension") == "none":
        volume = geometry.get("material_common_volume_mm3")
        if not _finite(volume) or abs(volume) > VOLUME_EPSILON_MM3 or geometry.get("positive_common_area_mm2") is not None:
            native_failures.append({"kind": "gap_no_intersection", "actual": geometry, "tolerance_mm3": VOLUME_EPSILON_MM3})
        native_metrics["volume"] = {"status": "FAIL" if native_failures else "PASS", "definition": "zero intersection for positive gap"}
    normalized_failures: list[dict[str, Any]] = []
    normalized_metrics = {"area": {"status": "NOT_APPLICABLE"}, "volume": {"status": "NOT_APPLICABLE"}}
    normalized_expected = expected.get("normalized_reference", expected)
    if "contact_area_mm2" in normalized_expected:
        value = geometry.get("positive_common_area_mm2")
        if not _finite(value) or abs(value / scale ** 2 - normalized_expected["contact_area_mm2"]) > AREA_EPSILON_MM2:
            normalized_failures.append({"kind": "positive_common_area_mm2", "actual": value, "expected": normalized_expected["contact_area_mm2"]})
        normalized_metrics["area"] = {"status": "FAIL" if normalized_failures else "PASS"}
    elif "material_common_volume_mm3" in normalized_expected:
        value = geometry.get("material_common_volume_mm3")
        if not _finite(value) or abs(value / scale ** 3 - normalized_expected["material_common_volume_mm3"]) > VOLUME_EPSILON_MM3:
            normalized_failures.append({"kind": "material_common_volume_mm3", "actual": value, "expected": normalized_expected["material_common_volume_mm3"]})
        normalized_metrics["volume"] = {"status": "FAIL" if normalized_failures else "PASS"}
    elif normalized_expected["exact_intersection_dimension"] == "none" and (not _finite(geometry.get("material_common_volume_mm3")) or abs(geometry["material_common_volume_mm3"]) > VOLUME_EPSILON_MM3 * scale ** 3):
        normalized_failures.append({"kind": "gap_no_intersection", "actual": geometry})
    if normalized_expected["exact_intersection_dimension"] == "none":
        normalized_metrics["volume"] = {"status": "FAIL" if normalized_failures else "PASS", "definition": "zero intersection for positive gap"}
    classification = {"status": "PASS" if not classification_failures else "FAIL", "failures": classification_failures}
    native = {"status": "PASS" if not native_failures else "FAIL", "failures": native_failures, "metrics": native_metrics, "definition": "same-scale expected; fixed 05A absolute limits"}
    normalized = {"status": "PASS" if not normalized_failures else "FAIL", "failures": normalized_failures, "metrics": normalized_metrics, "definition": "length/s, area/s^2, volume/s^3 against independent 1x expected"}
    primary = "PASS" if classification["status"] == "PASS" and normalized["status"] == "PASS" else "METHOD_MISMATCH"
    return {"schema_version": 1, "classification_validation": classification, "native_absolute_validation": native, "scale_normalized_validation": normalized, "native_validation": native, "normalized_validation": normalized, "primary_scale_covariance_verdict": primary, "status": primary}


def _normalized_reference(row: dict[str, Any]) -> dict[str, Any]:
    return _expected(row["case_id"], row["parameters"]["delta_over_tauE"], _nominal(row["case_id"]), 1.0)


def _error_row(row: dict[str, Any], actual: dict[str, Any]) -> dict[str, Any]:
    scale, expected, geometry = row["scale"], row["expected"], actual["geometry_state"]
    reference = _normalized_reference(row)
    result = {"sample_id": row["sample_id"], "case_id": row["case_id"], "scale": scale, "q": row["parameters"]["delta_over_tauE"], "set_delta_mm": expected["set_signed_offset_mm"], "measured_delta_mm": actual.get("measured_signed_offset_mm"), "raw_delta_error_mm": None, "normalized_delta_error_mm": None, "raw_area_error_mm2": None, "normalized_area_error_mm2": None, "raw_volume_error_mm3": None, "normalized_volume_error_mm3": None}
    if _finite(result["measured_delta_mm"]):
        result["raw_delta_error_mm"] = result["measured_delta_mm"] - result["set_delta_mm"]
        result["normalized_delta_error_mm"] = result["raw_delta_error_mm"] / scale
    if "contact_area_mm2" in expected and _finite(geometry.get("positive_common_area_mm2")):
        result["raw_area_error_mm2"] = geometry["positive_common_area_mm2"] - expected["contact_area_mm2"]
        result["normalized_area_error_mm2"] = geometry["positive_common_area_mm2"] / scale ** 2 - reference["contact_area_mm2"]
    if "material_common_volume_mm3" in expected and _finite(geometry.get("material_common_volume_mm3")):
        result["raw_volume_error_mm3"] = geometry["material_common_volume_mm3"] - expected["material_common_volume_mm3"]
        result["normalized_volume_error_mm3"] = geometry["material_common_volume_mm3"] / scale ** 3 - reference["material_common_volume_mm3"]
    return result


def _revalidate_construction(row: dict[str, Any], actual: dict[str, Any]) -> dict[str, Any]:
    if row["case_id"] != "A07":
        return {"status": "NOT_APPLICABLE", "failures": []}
    failures = []
    for key, expected_value in row["parameters"]["construction_invariants"].items():
        value = actual.get("construction", {}).get(key)
        if not _finite(value) or abs(value - expected_value) > LINEAR_EPSILON_MM * row["scale"]:
            failures.append({"kind": key, "expected": expected_value, "actual": value})
    return {"status": "PASS" if not failures else "FAIL", "failures": failures}


def revalidate_contact_scale_covariance_pilot(manifest_path: Path, source_output_root: Path, output_root: Path) -> dict[str, Any]:
    """Re-evaluate saved paired actual evidence without calling FreeCAD or changing it."""
    manifest, source_output_root, output_root = read_json(Path(manifest_path)), Path(source_output_root), Path(output_root)
    output_root.mkdir(parents=True, exist_ok=True)
    rows, errors, repeatability, missing = [], [], [], []
    for row in manifest["samples"]:
        sample_id = row["sample_id"]
        first_path = source_output_root / "batch_1" / "samples" / sample_id / "actual.json"
        second_path = source_output_root / "batch_2" / "samples" / sample_id / "actual.json"
        original_validation_path = source_output_root / "batch_1" / "samples" / sample_id / "validation.json"
        absent = [str(path) for path in (first_path, second_path, original_validation_path) if not path.is_file()]
        if absent:
            missing.append({"sample_id": sample_id, "missing_paths": absent})
            continue
        first, second = read_json(first_path), read_json(second_path)
        evidence_failures = []
        for label, actual in (("batch_1", first), ("batch_2", second)):
            if actual.get("input_step_sha256") != row["step_sha256"]:
                evidence_failures.append({"kind": "input_step_sha256", "batch": label, "expected": row["step_sha256"], "actual": actual.get("input_step_sha256")})
        expected = {**row["expected"], "normalized_reference": _normalized_reference(row)}
        validation = validate_scale_actual(first, expected)
        construction = _revalidate_construction(row, first)
        validation["construction_validation"] = construction
        validation["evidence_validation"] = {"status": "PASS" if not evidence_failures else "FAIL", "failures": evidence_failures}
        if construction["status"] == "FAIL" or evidence_failures:
            validation["primary_scale_covariance_verdict"] = "METHOD_MISMATCH"
            validation["status"] = "METHOD_MISMATCH"
        output_dir = output_root / "samples" / sample_id
        output_dir.mkdir(parents=True, exist_ok=True)
        write_json(output_dir / "validation.json", validation)
        geometry, fuse = first["geometry_state"], first["direct_fuse"]
        rows.append({"sample_id": sample_id, "case_id": row["case_id"], "scale": row["scale"], "q": row["parameters"]["delta_over_tauE"], "classification_status": validation["classification_validation"]["status"], "native_absolute_status": validation["native_absolute_validation"]["status"], "scale_normalized_status": validation["scale_normalized_validation"]["status"], "construction_status": construction["status"], "evidence_status": validation["evidence_validation"]["status"], "primary_scale_covariance_verdict": validation["primary_scale_covariance_verdict"], "measured_delta_mm": first.get("measured_signed_offset_mm"), "common_area_mm2": geometry.get("positive_common_area_mm2"), "common_volume_mm3": geometry.get("material_common_volume_mm3"), "direct_fuse_solid_count": fuse.get("solid_count")})
        errors.append(_error_row(row, first))
        repeatability.append({"sample_id": sample_id, "two_independent_measurements_match": first == second, "input_hash_match": first.get("input_step_sha256") == second.get("input_step_sha256") == row["step_sha256"], "original_validation_reused": True})
    for name, content in (("revalidation_results.csv", rows), ("revalidation_errors.csv", errors), ("reused_repeatability.csv", repeatability), ("missing_samples.csv", missing)):
        if content:
            with (output_root / name).open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=list(content[0])); writer.writeheader(); writer.writerows(content)
    native_count = sum(item["native_absolute_status"] != "PASS" for item in rows)
    normalized_count = sum(item["scale_normalized_status"] != "PASS" for item in rows)
    classification_count = sum(item["classification_status"] != "PASS" for item in rows)
    construction_count = sum(item["construction_status"] == "FAIL" for item in rows)
    evidence_count = sum(item["evidence_status"] != "PASS" for item in rows)
    primary = "INCOMPLETE" if missing or len(rows) != manifest.get("sample_count", len(manifest["samples"])) else ("PASS" if not normalized_count and not classification_count and not construction_count and not evidence_count else "METHOD_MISMATCH")
    summary = {"schema_version": 2, "pilot_level": PILOT_LEVEL, "revalidation_mode": "saved_actual_only_no_freecad", "sample_denominator": manifest.get("sample_count", len(manifest["samples"])), "complete_sample_count": len(rows), "missing_actual_count": len(missing), "native_absolute_mismatch_count": native_count, "scale_normalized_mismatch_count": normalized_count, "classification_mismatch_count": classification_count, "construction_mismatch_count": construction_count, "evidence_mismatch_count": evidence_count, "two_independent_measurements": {"definition": "saved batch_1 and batch_2 actual records generated by separate FreeCADCmd invocations per sample", "matching_pairs": sum(item["two_independent_measurements_match"] for item in repeatability), "pair_count": len(repeatability)}, "primary_scale_covariance_verdict": primary, "method_mismatch_count": normalized_count, "method_mismatch_definition": "legacy-compatible count for the primary scale-normalized criterion only", "applicability": {"native_absolute": "same-scale area or volume when applicable; otherwise gap zero-intersection", "scale_normalized": "same metric after prescribed dimensional normalization", "classification": "state, exact dimension, and signed offset", "construction": "A07 only; NOT_APPLICABLE for A01"}, "samples": rows, "missing_samples": missing}
    write_json(output_root / "summary.json", summary)
    return summary


def _run_one(row: dict[str, Any], output_root: Path, batch: int, *, view: bool) -> dict[str, Any]:
    actual_dir = output_root / f"batch_{batch}" / "samples" / row["sample_id"]
    actual_dir.mkdir(parents=True, exist_ok=True)
    debug_path = output_root / "views" / f"{row['sample_id']}.FCStd" if view else None
    actual = _run_freecad({"action": "analyze", "case_id": row["case_id"], "step_path": row["step_path"], "tauE_mm": row["parameters"]["tauE_mm"], "debug_path": str(debug_path) if debug_path else None})
    actual.pop("status", None)
    actual["scale"] = row["scale"]
    actual["pilot_level"] = PILOT_LEVEL
    actual["input_step_sha256"] = sha256_file(Path(row["step_path"]))
    write_json(actual_dir / "actual.json", actual)
    expected = {**row["expected"], "normalized_reference": _normalized_reference(row)}
    validation = validate_scale_actual(actual, expected)
    validation["construction_validation"] = {"status": "NOT_APPLICABLE", "failures": []}
    if row["case_id"] == "A07":
        measured = actual.get("construction", {})
        failed = []
        for key, expected_value in row["parameters"]["construction_invariants"].items():
            value = measured.get(key)
            if not _finite(value) or abs(value - expected_value) > LINEAR_EPSILON_MM * row["scale"]:
                failed.append({"kind": key, "expected": expected_value, "actual": value})
        validation["construction_validation"] = {"status": "PASS" if not failed else "FAIL", "failures": failed}
        if failed: validation["status"] = "METHOD_MISMATCH"
    write_json(actual_dir / "validation.json", validation)
    return {"actual": actual, "validation": validation, "errors": _error_row(row, actual)}


def run_contact_scale_covariance_pilot(manifest_path: Path, output_root: Path) -> dict[str, Any]:
    """Run the finite 90-sample pilot twice in distinct FreeCADCmd processes."""
    manifest, output_root = read_json(Path(manifest_path)), Path(output_root)
    output_root.mkdir(parents=True, exist_ok=True)
    rows, repeatability, errors = [], [], []
    for row in manifest["samples"]:
        is_view = row["scale"] in (0.01, 100.0) and row["parameters"]["delta_over_tauE"] == 0.5
        first = _run_one(row, output_root, 1, view=is_view)
        second = _run_one(row, output_root, 2, view=False)
        actual_match = first["actual"] == second["actual"]
        validation_match = first["validation"] == second["validation"]
        repeatability.append({"sample_id": row["sample_id"], "batch_1_batch_2_actual_match": actual_match, "validation_match": validation_match, "input_hash_match": first["actual"]["input_step_sha256"] == second["actual"]["input_step_sha256"]})
        actual, validation = first["actual"], first["validation"]
        geometry, fuse = actual["geometry_state"], actual["direct_fuse"]
        rows.append({"sample_id": row["sample_id"], "case_id": row["case_id"], "scale": row["scale"], "q": row["parameters"]["delta_over_tauE"], "tauE_mm": actual["tauE_mm"], "L_mm": actual["L_mm"], "tauE_over_L": actual["tauE_over_L"], "measured_delta_mm": actual.get("measured_signed_offset_mm"), "exact_dimension": geometry["exact_intersection_dimension"], "engineering_state": actual["engineering_state"], "common_area_mm2": geometry.get("positive_common_area_mm2"), "common_volume_mm3": geometry["material_common_volume_mm3"], "direct_fuse_solid_count": fuse["solid_count"], "direct_fuse_volume_error_mm3": fuse.get("volume_conservation_error_mm3"), "native_status": validation["native_validation"]["status"], "normalized_status": validation["normalized_validation"]["status"], "construction_status": validation["construction_validation"]["status"], "status": validation["status"]})
        errors.append(first["errors"])
    for name, content in (("results.csv", rows), ("raw_and_normalized_errors.csv", errors), ("repeatability.csv", repeatability)):
        with (output_root / name).open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(content[0])); writer.writeheader(); writer.writerows(content)
    failed = [row for row in rows if row["status"] != "PASS"]
    summary = {"schema_version": 1, "pilot_level": PILOT_LEVEL, "sample_count": len(rows), "method_mismatch_count": len(failed), "invalid_count": 0, "timeout_count": 0, "unsupported_count": sum(row["engineering_state"] == "UNSUPPORTED" for row in rows), "repeatability": {"processes": 2, "status": "PASS" if all(all(item[key] for key in ("batch_1_batch_2_actual_match", "validation_match", "input_hash_match")) for item in repeatability) else "FAIL"}, "status": "PASS" if not failed else "METHOD_MISMATCH", "samples": rows}
    write_json(output_root / "summary.json", summary)
    (output_root / "VIEW_INDEX.md").write_text("# 05B 代表视图索引\n\n四个 FCStd 为 A01/A07 在 0.01×、100×和 q=+0.5 的真实输入；正间隙仍显示两个输入实体。对象属性记录实测 delta、tauE、L、工程状态和直接 Fuse solid 数。1× 场景引用 05A。\n", encoding="utf-8")
    (output_root / "CONCLUSION.md").write_text(f"# 05B co-scaled-τE 结论\n\n本实验仅覆盖 A01/A07 的 90 个离散 `LEVEL_B_SCALE_PILOT` 条件；不外推连续区间、其他 CAD 软件或内核版本。METHOD_MISMATCH={len(failed)}，两进程复现={summary['repeatability']['status']}。固定内核与算法阈值未随尺度调整。\n", encoding="utf-8")
    return summary
