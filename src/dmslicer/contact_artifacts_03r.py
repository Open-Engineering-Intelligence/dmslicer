"""Package stable 03A research artifacts without treating them as inputs."""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

from .contact_canonical_03a import _run_freecad
from .evidence import read_json, write_json


CASE_IDS = ("A01", "A02", "A03", "A04", "A05", "A06")


def _measure_name(relation: dict[str, Any]) -> str:
    return {"2D": "area_mm2", "1D": "length_mm", "3D": "volume_mm3", "0D": "point_count"}[relation["dimension"]]


def package_contact_artifacts(output_root: Path, artifact_root: Path) -> dict[str, Any]:
    """Copy six debug artifacts and write a path-free reference snapshot from verified outputs."""
    output_root, artifact_root = Path(output_root), Path(artifact_root)
    summary = read_json(output_root / "summary.json")
    debug_root = artifact_root / "freecad_debug"
    references: dict[str, Any] = {}
    verified: dict[str, Any] = {}
    for case_id in CASE_IDS:
        source_debug = output_root / case_id / "debug.FCStd"
        target_debug = debug_root / f"{case_id}.FCStd"
        target_debug.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_debug, target_debug)
        inspection = _run_freecad({"action": "verify_debug", "fcstd_path": str(target_debug)})
        actual = read_json(output_root / case_id / "actual.json")
        relation = actual["relation"]
        summary_row = summary["cases"][case_id]
        measure_name = _measure_name(relation)
        expected_measure = summary_row["expected_measure"][measure_name]
        if inspection["case_id"] != case_id or inspection["relation"] != relation["relation"] or inspection["dimension"] != relation["dimension"]:
            raise RuntimeError(f"debug artifact does not match canonical result for {case_id}")
        if abs(inspection["measure"] - relation[measure_name]) > 1e-6:
            raise RuntimeError(f"debug artifact measurement does not match actual evidence for {case_id}")
        verified[case_id] = {key: inspection[key] for key in ("body_count", "result_object", "relation", "dimension", "measure")}
        references[case_id] = {
            "case_id": case_id,
            "step_sha256": actual["step_sha256"],
            "relation": relation["relation"],
            "dimension": relation["dimension"],
            "expected_measure": {measure_name: expected_measure},
            "actual_measure": {measure_name: relation[measure_name]},
            "absolute_error": summary_row["absolute_error"],
            "coverage_a": relation.get("coverage_a", "not_applicable"),
            "coverage_b": relation.get("coverage_b", "not_applicable"),
            "patch_component_count": len(relation.get("patches", [])) if relation["dimension"] == "2D" else "not_applicable",
            "provenance_scope": summary_row["provenance_scope"],
            "freecad_version": inspection["freecad_version"],
            "occt_version": inspection["occt_version"],
        }
    verification = {"schema_version": 1, "status": "PASS", "artifact_classification": "NON_AUTHORITATIVE_HUMAN_INSPECTION", "cases": verified}
    write_json(debug_root / "verification.json", verification)
    reference = {"schema_version": 1, "artifact_classification": "VERIFIED_REFERENCE_RESULT_NOT_PRODUCTION_INPUT", "cases": references}
    write_json(artifact_root / "reference_results" / "contact_canonical_03a.json", reference)
    return {"status": "PASS", "case_count": len(CASE_IDS)}
