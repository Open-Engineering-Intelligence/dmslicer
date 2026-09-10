"""Finite fixed-absolute-tolerance experiment, reusing the 05A B-rep path."""

from __future__ import annotations

import argparse
import csv
import math
from pathlib import Path
from typing import Any

from .contact_scale_covariance_pilot_05b import SCALES, scaled_geometry
from .contact_tolerance_pilot_05a import (
    AREA_EPSILON_MM2,
    CASES,
    FROZEN_OFFSET_RATIOS,
    LINEAR_EPSILON_MM,
    TAU_E_MM,
    VOLUME_EPSILON_MM3,
    _a07_expected_construction,
    _run_freecad,
    _sample_id,
    engineering_state,
)
from .evidence import read_json, sha256_file, write_json

FIXED_TAU_E_MM = TAU_E_MM
PILOT_LEVEL = "LEVEL_B_FIXED_ABSOLUTE_TOLERANCE_PILOT"


def fixed_tau_e(scale: float) -> float:
    if scale not in SCALES:
        raise ValueError(f"unsupported scale {scale}")
    return FIXED_TAU_E_MM


def _scale_token(scale: float) -> str:
    return {0.01: "s0_01", 1.0: "s1", 100.0: "s100"}[scale]


def _sample_id_at_scale(case_id: str, q: float, scale: float) -> str:
    return f"{_sample_id(case_id, q)}_{_scale_token(scale)}"


def a07_construction_domain(scale: float, q: float) -> dict[str, Any]:
    geometry, delta = scaled_geometry("A07", scale), q * fixed_tau_e(scale)
    bore, outer = geometry["shaft_radius_mm"] + delta, geometry["sleeve_outer_radius_mm"]
    if 0 < bore < outer:
        return {"status": "CONSTRUCTIBLE", "bore_radius_mm": bore, "outer_radius_mm": outer, "inequality": f"0 < {bore} < {outer}"}
    return {"status": "OUT_OF_CONSTRUCTION_DOMAIN", "bore_radius_mm": bore, "outer_radius_mm": outer, "inequality": f"0 < {bore} < {outer}", "reason": "A07 requires 0 < bore_radius_mm < sleeve_outer_radius_mm"}


def _a01_truth(geometry: dict[str, float], delta: float) -> tuple[str, float]:
    h = geometry["h_mm"]
    thickness = max(0.0, min(h, 2 * h + delta) - max(0.0, h + delta))
    if abs(delta) <= LINEAR_EPSILON_MM:
        return "2D", 0.0
    return ("3D", geometry["a_mm"] * geometry["b_mm"] * thickness) if thickness > LINEAR_EPSILON_MM else ("none", 0.0)


def expected_truth(case_id: str, scale: float, q: float) -> dict[str, Any]:
    """Independent current-geometry truth; never read by the actual measurement stage."""
    geometry, delta = scaled_geometry(case_id, scale), q * fixed_tau_e(scale)
    if case_id == "A01":
        dimension, volume = _a01_truth(geometry, delta)
    elif case_id == "A07":
        domain = a07_construction_domain(scale, q)
        if domain["status"] != "CONSTRUCTIBLE":
            return {"case_id": case_id, "scale": scale, "q": q, "geometry": geometry, "construction_status": domain["status"], "construction": domain}
        dimension = "2D" if abs(delta) <= LINEAR_EPSILON_MM else "3D" if delta < 0 else "none"
        volume = math.pi * (geometry["shaft_radius_mm"] ** 2 - (geometry["shaft_radius_mm"] + delta) ** 2) * (geometry["shaft_z_max_mm"] - geometry["shaft_z_min_mm"]) if dimension == "3D" else 0.0
    else:
        raise ValueError(case_id)
    result: dict[str, Any] = {"schema_version": 1, "pilot_level": PILOT_LEVEL, "case_id": case_id, "scale": scale, "q": q, "geometry": geometry, "ground_truth_mode": "construction_derived", "intended_relation_dimension": "2D", "set_signed_offset_mm": delta, "engineering_state": engineering_state(delta, FIXED_TAU_E_MM), "exact_intersection_dimension": dimension, "construction_status": "CONSTRUCTIBLE"}
    if dimension == "2D":
        result["contact_area_mm2"] = geometry["a_mm"] * geometry["b_mm"] if case_id == "A01" else 2 * math.pi * geometry["shaft_radius_mm"] * (geometry["shaft_z_max_mm"] - geometry["shaft_z_min_mm"])
    elif dimension == "3D":
        result["material_common_volume_mm3"] = volume
    return result


def normalized_reference(case_id: str, scale: float, q: float) -> dict[str, Any]:
    """Reference the 1x geometry at delta/s, not the old same-q 05B reference."""
    return expected_truth(case_id, 1.0, q / scale)


def generate_contact_fixed_tolerance_manifest(root: Path, tracked_05a_root: Path) -> dict[str, Any]:
    root, tracked_05a_root = Path(root), Path(tracked_05a_root)
    samples: list[dict[str, Any]] = []
    for scale in SCALES:
        for case_id in CASES:
            for q in FROZEN_OFFSET_RATIOS:
                sample_id, truth = _sample_id_at_scale(case_id, q, scale), expected_truth(case_id, scale, q)
                domain = truth.get("construction", {"status": "CONSTRUCTIBLE"})
                parameters = {"schema_version": 1, "pilot_level": PILOT_LEVEL, "case_id": case_id, "sample_id": sample_id, "scale": scale, "scale_mode": "fixed-absolute-tauE", "perturbation_kind": "rigid_pose" if case_id == "A01" else "construction_variant", "delta_over_tauE": q, "set_signed_offset_mm": q * FIXED_TAU_E_MM, "tauE_mm": FIXED_TAU_E_MM, "tauK_mm": "NOT_AVAILABLE", "geometry": scaled_geometry(case_id, scale), "construction_domain": domain}
                if case_id == "A07" and domain["status"] == "CONSTRUCTIBLE":
                    parameters["construction_invariants"] = _a07_expected_construction(parameters["geometry"])
                    parameters["construction_invariants"]["combined_L_mm"] = 100.0 * scale
                source = tracked_05a_root / _sample_id(case_id, q) / "inputs.step" if scale == 1.0 else root / "inputs" / sample_id / "inputs.step"
                samples.append({"sample_id": sample_id, "case_id": case_id, "scale": scale, "source_kind": "tracked_05A_reference" if scale == 1.0 else "generated_05C", "planned_status": domain["status"], "step_path": str(source), "parameters": parameters, "expected": truth})
    manifest = {"schema_version": 1, "pilot_level": PILOT_LEVEL, "scale_mode": "fixed-absolute-tauE", "planned_count": len(samples), "constructible_count": sum(row["planned_status"] == "CONSTRUCTIBLE" for row in samples), "domain_excluded_count": sum(row["planned_status"] == "OUT_OF_CONSTRUCTION_DOMAIN" for row in samples), "samples": samples}
    if len({row["sample_id"] for row in samples}) != len(samples) or len(samples) != 90:
        raise RuntimeError("05C manifest must contain 90 unique planned samples")
    root.mkdir(parents=True, exist_ok=True)
    write_json(root / "manifest.json", manifest)
    return manifest


def materialize_fixed_inputs(manifest_path: Path) -> dict[str, Any]:
    manifest = read_json(Path(manifest_path))
    generated, reused = 0, 0
    for row in manifest["samples"]:
        if row["planned_status"] != "CONSTRUCTIBLE":
            continue
        step = Path(row["step_path"])
        if row["source_kind"] == "tracked_05A_reference":
            if not step.is_file():
                raise FileNotFoundError(f"missing tracked 05A STEP: {step}")
            reused += 1
        else:
            if not step.is_file():
                step.parent.mkdir(parents=True, exist_ok=True)
                _run_freecad({"action": "generate", "case_id": row["case_id"], "step_path": str(step), "parameters": row["parameters"]})
                write_json(step.parent / "parameters.json", row["parameters"])
                write_json(step.parent / "expected.json", row["expected"])
                generated += 1
        row["step_sha256"] = sha256_file(step)
    write_json(Path(manifest_path), manifest)
    return {"generated_input_count": generated, "reused_tracked_input_count": reused}


def _finite(value: Any) -> bool:
    return isinstance(value, (int, float)) and math.isfinite(value)


def validate_fixed_actual(actual: dict[str, Any], expected: dict[str, Any]) -> dict[str, Any]:
    """Validate saved measurements after they have been written, retaining real mismatches."""
    failures: list[dict[str, Any]] = []
    geometry = actual.get("geometry_state") if isinstance(actual.get("geometry_state"), dict) else {}
    for key in ("case_id", "engineering_state"):
        if actual.get(key) != expected.get(key): failures.append({"kind": key, "expected": expected.get(key), "actual": actual.get(key)})
    if geometry.get("exact_intersection_dimension") != expected.get("exact_intersection_dimension"):
        failures.append({"kind": "exact_intersection_dimension", "expected": expected.get("exact_intersection_dimension"), "actual": geometry.get("exact_intersection_dimension")})
    measured, set_delta = actual.get("measured_signed_offset_mm"), expected.get("set_signed_offset_mm")
    if not _finite(measured) or not _finite(set_delta) or abs(measured - set_delta) > LINEAR_EPSILON_MM:
        failures.append({"kind": "measured_signed_offset_mm", "expected": set_delta, "actual": measured})
    if "contact_area_mm2" in expected:
        value = geometry.get("positive_common_area_mm2")
        if not _finite(value) or abs(value - expected["contact_area_mm2"]) > AREA_EPSILON_MM2: failures.append({"kind": "positive_common_area_mm2", "expected": expected["contact_area_mm2"], "actual": value})
    elif "material_common_volume_mm3" in expected:
        value = geometry.get("material_common_volume_mm3")
        if not _finite(value) or abs(value - expected["material_common_volume_mm3"]) > VOLUME_EPSILON_MM3: failures.append({"kind": "material_common_volume_mm3", "expected": expected["material_common_volume_mm3"], "actual": value})
    elif expected.get("exact_intersection_dimension") == "none":
        volume = geometry.get("material_common_volume_mm3")
        if not _finite(volume) or abs(volume) > VOLUME_EPSILON_MM3 or geometry.get("positive_common_area_mm2") is not None: failures.append({"kind": "gap_no_intersection", "actual": geometry})
    direct = actual.get("direct_fuse")
    if not isinstance(direct, dict) or not isinstance(direct.get("solid_count"), int) or direct.get("one_valid_connected_solid") != (direct.get("solid_count") == 1 and direct.get("valid") is True and direct.get("closed") is True): failures.append({"kind": "direct_fuse_consistency", "actual": direct})
    native = {"status": "PASS" if not failures else "FAIL", "failures": failures, "definition": "current-scale analytic truth with approved absolute dimensional limits"}
    reference, normalized_failures = expected.get("normalized_reference"), []
    if not isinstance(reference, dict):
        normalized_failures.append({"kind": "normalized_reference", "actual": reference})
    else:
        if geometry.get("exact_intersection_dimension") != reference.get("exact_intersection_dimension"):
            normalized_failures.append({"kind": "exact_intersection_dimension", "expected": reference.get("exact_intersection_dimension"), "actual": geometry.get("exact_intersection_dimension")})
        scale = actual.get("scale")
        if not _finite(scale) or scale <= 0:
            normalized_failures.append({"kind": "scale", "actual": scale})
        elif "contact_area_mm2" in reference:
            value = geometry.get("positive_common_area_mm2")
            if not _finite(value) or abs(value / scale ** 2 - reference["contact_area_mm2"]) > AREA_EPSILON_MM2:
                normalized_failures.append({"kind": "positive_common_area_mm2", "expected": reference["contact_area_mm2"], "actual": value})
        elif "material_common_volume_mm3" in reference:
            value = geometry.get("material_common_volume_mm3")
            if not _finite(value) or abs(value / scale ** 3 - reference["material_common_volume_mm3"]) > VOLUME_EPSILON_MM3:
                normalized_failures.append({"kind": "material_common_volume_mm3", "expected": reference["material_common_volume_mm3"], "actual": value})
        elif reference.get("exact_intersection_dimension") == "none":
            value = geometry.get("material_common_volume_mm3")
            if not _finite(value) or abs(value / scale ** 3) > VOLUME_EPSILON_MM3:
                normalized_failures.append({"kind": "gap_no_intersection", "actual": value})
    normalized = {"status": "PASS" if not normalized_failures else "FAIL", "failures": normalized_failures, "definition": "auxiliary current-scale reference using delta/s"}
    status = "PASS" if native["status"] == "PASS" else "METHOD_MISMATCH"
    return {"schema_version": 1, "native_absolute_validation": native, "normalized_validation": normalized, "status": status}


def _run_one(row: dict[str, Any], output_root: Path, batch: int, view: bool) -> dict[str, Any]:
    sample_dir = output_root / f"batch_{batch}" / "samples" / row["sample_id"]
    sample_dir.mkdir(parents=True, exist_ok=True)
    debug = output_root / "views" / f"{row['sample_id']}.FCStd" if view else None
    actual = _run_freecad({"action": "analyze", "case_id": row["case_id"], "step_path": row["step_path"], "tauE_mm": FIXED_TAU_E_MM, "debug_path": str(debug) if debug else None})
    actual.pop("status", None); actual.update({"scale": row["scale"], "pilot_level": PILOT_LEVEL, "input_step_sha256": sha256_file(Path(row["step_path"]))})
    write_json(sample_dir / "actual.json", actual)
    expected = {**row["expected"], "normalized_reference": normalized_reference(row["case_id"], row["scale"], row["parameters"]["delta_over_tauE"])}
    validation = validate_fixed_actual(actual, expected)
    if row["case_id"] == "A07":
        failures = [{"kind": key, "expected": value, "actual": actual.get("construction", {}).get(key)} for key, value in row["parameters"]["construction_invariants"].items() if not _finite(actual.get("construction", {}).get(key)) or abs(actual["construction"][key] - value) > LINEAR_EPSILON_MM * row["scale"]]
        validation["construction_validation"] = {"status": "PASS" if not failures else "FAIL", "failures": failures}
        if failures: validation["status"] = "METHOD_MISMATCH"
    else:
        validation["construction_validation"] = {"status": "NOT_APPLICABLE", "failures": []}
    write_json(sample_dir / "validation.json", validation)
    return {"actual": actual, "validation": validation}


def run_contact_fixed_tolerance_pilot(manifest_path: Path, output_root: Path) -> dict[str, Any]:
    manifest, output_root = read_json(Path(manifest_path)), Path(output_root)
    rows, repeatability = [], []
    for row in manifest["samples"]:
        if row["planned_status"] != "CONSTRUCTIBLE":
            rows.append({"sample_id": row["sample_id"], "case_id": row["case_id"], "scale": row["scale"], "q": row["parameters"]["delta_over_tauE"], "final_status": "OUT_OF_CONSTRUCTION_DOMAIN", "reason": row["parameters"]["construction_domain"].get("reason", "")})
            continue
        try:
            view = row["scale"] in (0.01, 100.0) and row["parameters"]["delta_over_tauE"] == 0.5
            first, second = _run_one(row, output_root, 1, view), _run_one(row, output_root, 2, False)
            actual, validation = first["actual"], first["validation"]
            geometry, fuse = actual["geometry_state"], actual["direct_fuse"]
            final = "MEASURED_PASS" if validation["status"] == "PASS" else "METHOD_MISMATCH"
            rows.append({"sample_id": row["sample_id"], "case_id": row["case_id"], "scale": row["scale"], "q": row["parameters"]["delta_over_tauE"], "tauE_mm": actual["tauE_mm"], "L_mm": actual["L_mm"], "tauE_over_L": actual["tauE_over_L"], "measured_delta_mm": actual.get("measured_signed_offset_mm"), "engineering_state": actual["engineering_state"], "exact_dimension": geometry["exact_intersection_dimension"], "common_area_mm2": geometry.get("positive_common_area_mm2"), "common_volume_mm3": geometry.get("material_common_volume_mm3"), "direct_fuse_solid_count": fuse.get("solid_count"), "native_status": validation["native_absolute_validation"]["status"], "normalized_status": validation["normalized_validation"]["status"], "construction_status": validation["construction_validation"]["status"], "final_status": final, "reason": "; ".join(item["kind"] for item in validation["native_absolute_validation"]["failures"])})
            repeatability.append({"sample_id": row["sample_id"], "actual_match": first["actual"] == second["actual"], "validation_match": first["validation"] == second["validation"], "input_hash_match": first["actual"]["input_step_sha256"] == second["actual"]["input_step_sha256"] == row["step_sha256"]})
        except TimeoutError as error:
            rows.append({"sample_id": row["sample_id"], "case_id": row["case_id"], "scale": row["scale"], "q": row["parameters"]["delta_over_tauE"], "final_status": "TIMEOUT", "reason": str(error)})
        except Exception as error:
            rows.append({"sample_id": row["sample_id"], "case_id": row["case_id"], "scale": row["scale"], "q": row["parameters"]["delta_over_tauE"], "final_status": "RUN_EXCEPTION", "reason": str(error)})
    output_root.mkdir(parents=True, exist_ok=True)
    with (output_root / "results.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=sorted({key for row in rows for key in row})); writer.writeheader(); writer.writerows(rows)
    with (output_root / "repeatability.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["sample_id", "actual_match", "validation_match", "input_hash_match"]); writer.writeheader(); writer.writerows(repeatability)
    counts = {status: sum(row["final_status"] == status for row in rows) for status in {row["final_status"] for row in rows}}
    summary = {"schema_version": 1, "pilot_level": PILOT_LEVEL, "planned_count": manifest["planned_count"], "constructible_count": manifest["constructible_count"], "domain_excluded_count": manifest["domain_excluded_count"], "measured_count": sum(row["final_status"] in {"MEASURED_PASS", "METHOD_MISMATCH"} for row in rows), "final_status_counts": counts, "two_independent_measurements": {"processes_per_valid_sample": 2, "pair_count": len(repeatability), "matching_pair_count": sum(all(item[key] for key in ("actual_match", "validation_match", "input_hash_match")) for item in repeatability)}, "samples": rows}
    write_json(output_root / "summary.json", summary)
    (output_root / "VIEW_INDEX.md").write_text("# 05C 代表性 FCStd 索引\n\n四个文件为 A01/A07 在 0.01×、100×、q=+0.5 的真实输入与测量；正间隙不会隐藏输入实体。\n", encoding="utf-8")
    (output_root / "CONCLUSION.md").write_text("# 05C 有限结论\n\n本结果只覆盖清单中的 90 个离散计划条件。构造域外条目保留在分母中，不作为测量失败；native absolute 是主验收，normalized 仅为辅助。\n", encoding="utf-8")
    return summary


def revalidate_contact_fixed_tolerance_pilot(manifest_path: Path, output_root: Path) -> dict[str, Any]:
    """Revalidate already-saved two-round actual evidence without calling FreeCAD."""
    manifest, output_root = read_json(Path(manifest_path)), Path(output_root)
    changed, missing = 0, []
    for row in manifest["samples"]:
        if row["planned_status"] != "CONSTRUCTIBLE":
            continue
        expected = {**row["expected"], "normalized_reference": normalized_reference(row["case_id"], row["scale"], row["parameters"]["delta_over_tauE"])}
        for batch in (1, 2):
            folder = output_root / f"batch_{batch}" / "samples" / row["sample_id"]
            actual_path = folder / "actual.json"
            if not actual_path.is_file():
                missing.append({"sample_id": row["sample_id"], "batch": batch}); continue
            validation = validate_fixed_actual(read_json(actual_path), expected)
            prior = folder / "validation.json"
            if prior.is_file() and isinstance(read_json(prior).get("construction_validation"), dict):
                validation["construction_validation"] = read_json(prior)["construction_validation"]
                if validation["construction_validation"]["status"] == "FAIL": validation["status"] = "METHOD_MISMATCH"
            write_json(prior, validation); changed += 1
    report = {"revalidation_mode": "saved_actual_only_no_freecad", "validated_records": changed, "missing_records": missing}
    write_json(output_root / "revalidation.json", report)
    return report


def _main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("generate", "run", "revalidate"))
    parser.add_argument("--root", type=Path, default=Path("outputs/contact_fixed_tolerance_05c"))
    parser.add_argument("--tracked-05a", type=Path, default=Path("benchmarks/contact_tolerance_pilot_05a"))
    args = parser.parse_args()
    manifest_path = args.root / "manifest.json"
    if args.action == "generate":
        generate_contact_fixed_tolerance_manifest(args.root, args.tracked_05a)
        materialize_fixed_inputs(manifest_path)
    elif args.action == "run":
        run_contact_fixed_tolerance_pilot(manifest_path, args.root)
    else:
        revalidate_contact_fixed_tolerance_pilot(manifest_path, args.root)


if __name__ == "__main__":
    _main()
