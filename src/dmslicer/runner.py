"""Host-side CASE01 fixture generation, analysis, and repeatability runner."""

from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import time
from typing import Any

from .evidence import artifact_digest, git_metadata, read_json, sha256_file, write_json
from .identity import (
    canonical_digest,
    document_id,
    face_geometry_fingerprint,
    patch_id,
    quantized_number,
    region_id,
    solid_geometry_fingerprint,
    source_face_id,
)


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
FREECAD_SCRIPT = Path(__file__).with_name("freecad_case01.py")
TOLERANCES = {
    "length_unit": "mm",
    "area_unit": "mm2",
    "candidate_tolerance_mm": 0.05,
    "near_miss_max_gap_mm": 0.05,
    "nominal_fuzzy_value_mm": 0.0,
    "area_epsilon_mm2": 1e-8,
    "angular_same_domain_tolerance_rad": 1e-6,
}


def _freecad_executable() -> Path:
    discovered = shutil.which("freecadcmd") or shutil.which("FreeCADCmd.exe")
    candidates = [
        Path(discovered) if discovered else None,
        Path(r"C:\Program Files\FreeCAD 1.1\bin\freecadcmd.exe"),
    ]
    for candidate in candidates:
        if candidate is not None and candidate.is_file():
            return candidate
    raise FileNotFoundError("FreeCADCmd.exe was not found on PATH or at the recorded CASE01 probe location")


def _run_freecad(request: dict[str, Any]) -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="dmslicer_case01_") as temporary_directory:
        temporary_path = Path(temporary_directory)
        request_path = temporary_path / "request.json"
        response_path = temporary_path / "response.json"
        write_json(request_path, request)
        environment = os.environ.copy()
        environment["DMSLICER_FREECAD_REQUEST"] = str(request_path)
        environment["DMSLICER_FREECAD_RESPONSE"] = str(response_path)
        environment["DMSLICER_FREECAD_SCRIPT"] = str(FREECAD_SCRIPT)
        console_program = (
            "import os; _p=os.environ['DMSLICER_FREECAD_SCRIPT']; "
            "exec(compile(open(_p, encoding='utf-8').read(), _p, 'exec'))\n"
        )
        completed = subprocess.run(
            [str(_freecad_executable()), "--safe-mode", "-c"],
            input=console_program,
            env=environment,
            cwd=REPOSITORY_ROOT,
            text=True,
            capture_output=True,
            timeout=120,
            check=False,
        )
        if not response_path.is_file():
            raise RuntimeError(
                "FreeCADCmd did not write a response JSON. "
                + repr({"returncode": completed.returncode, "stdout": completed.stdout, "stderr": completed.stderr})
            )
        response = read_json(response_path)
        if completed.returncode != 0 or response.get("status") == "FAILED":
            raise RuntimeError(
                "FreeCADCmd CASE01 action failed. "
                + repr({"response": response, "returncode": completed.returncode, "stdout": completed.stdout, "stderr": completed.stderr})
            )
        response["headless_execution"] = {
            "freecadcmd_path": str(_freecad_executable()),
            "safe_mode": True,
            "console_launcher": "FreeCADCmd --safe-mode -c with JSON request/response files",
        }
        return response


def _expected_manifest() -> dict[str, Any]:
    manifest: dict[str, Any] = {
        "schema_version": 1,
        "case_id": "CASE01_planar_agb_exact",
        "units": {"length": "mm", "area": "mm2", "volume": "mm3"},
        "regions": [
            {
                "semantic_id": "A",
                "source_label": "A",
                "semantic_role": "SOURCE",
                "material_key": "A",
                "participation_policy": {"mode": "ACTIVE", "source_eligible": True, "gradient_eligible": False},
                "bounds_mm": {"x": [0, 10], "y": [0, 20], "z": [0, 20]},
            },
            {
                "semantic_id": "G",
                "source_label": "G",
                "semantic_role": "GRADIENT",
                "material_key": "Gradient",
                "participation_policy": {"mode": "ACTIVE", "source_eligible": False, "gradient_eligible": True},
                "bounds_mm": {"x": [10, 20], "y": [0, 20], "z": [0, 20]},
            },
            {
                "semantic_id": "B",
                "source_label": "B",
                "semantic_role": "SOURCE",
                "material_key": "B",
                "participation_policy": {"mode": "ACTIVE", "source_eligible": True, "gradient_eligible": False},
                "bounds_mm": {"x": [20, 30], "y": [0, 20], "z": [0, 20]},
            },
        ],
        "expected_relation_matrix": [
            {"semantic_pair": ["A", "G"], "relation_type": "FACE_CONTACT", "intersection_dimension": 2, "area_mm2": 400.0},
            {"semantic_pair": ["G", "B"], "relation_type": "FACE_CONTACT", "intersection_dimension": 2, "area_mm2": 400.0},
            {"semantic_pair": ["A", "B"], "relation_type": "DISJOINT", "intersection_dimension": None, "area_mm2": 0.0},
        ],
        "expected_patch_count": 2,
        "tolerance_contract": TOLERANCES,
        "implementation_decisions": [
            {
                "status": "IMPLEMENTATION_DECISION",
                "decision": "The CASE01 coordinates in this Goal use x=0..30 mm.",
                "rationale": "This is a +15 mm translation of the frozen illustrative fixture; geometry and analytic areas are unchanged.",
            }
        ],
    }
    manifest["truth_digest"] = "sha256:" + canonical_digest(manifest)
    return manifest


def generate_case01_fixture(step_path: Path, expected_path: Path | None = None) -> dict[str, Any]:
    """Generate the real three-solid STEP fixture through FreeCAD/Part."""
    step_path = Path(step_path)
    expected_path = Path(expected_path) if expected_path is not None else step_path.with_name("expected.json")
    response = _run_freecad({"action": "generate", "step_path": str(step_path)})
    if not step_path.is_file():
        raise RuntimeError("FreeCAD reported STEP generation success but no STEP file was written")
    write_json(expected_path, _expected_manifest())
    return {**response, "step_sha256": sha256_file(step_path), "expected_path": str(expected_path)}


def _materialize_identities(step_sha256: str, raw_regions: list[dict[str, Any]]) -> tuple[str, list[dict[str, Any]], dict[str, dict[int, str]]]:
    source_document_id = document_id(step_sha256)
    regions = []
    face_ids_by_semantic: dict[str, dict[int, str]] = {}
    for raw_region in raw_regions:
        face_fingerprints = [face_geometry_fingerprint(face) for face in raw_region["faces"]]
        solid_fingerprint = solid_geometry_fingerprint(raw_region, face_fingerprints)
        identifier = region_id(source_document_id, solid_fingerprint)
        faces = []
        face_ids_by_index = {}
        for face in raw_region["faces"]:
            face_fingerprint = face_geometry_fingerprint(face)
            face_identifier = source_face_id(identifier, face_fingerprint)
            face_ids_by_index[face["index"]] = face_identifier
            faces.append(
                {
                    "face_id": face_identifier,
                    "geometry_fingerprint": face_fingerprint,
                    "geometry_type": face["surface_type"],
                    "area_mm2": quantized_number(face["area_mm2"]),
                    "center_of_mass_mm": face["center_of_mass_mm"],
                    "bounding_box_mm": face["bounding_box_mm"],
                    "edge_count": face["edge_count"],
                    "wire_count": face["wire_count"],
                }
            )
        face_ids_by_semantic[raw_region["semantic_id"]] = face_ids_by_index
        regions.append(
            {
                "region_id": identifier,
                "source_document_id": source_document_id,
                "semantic_id": raw_region["semantic_id"],
                "source_locator": {
                    "document_id": source_document_id,
                    "product_path": [raw_region["source_label"]],
                    "entity_kind": "SOLID",
                    "source_ordinal": raw_region["source_ordinal"],
                    "persistent_label": raw_region["source_label"],
                    "geometry_digest": solid_fingerprint,
                    "identity_schema": "case01-geometry:v1",
                },
                "geometry_fingerprint": solid_fingerprint,
                "shape_type": raw_region["shape_type"],
                "volume_mm3": quantized_number(raw_region["volume_mm3"]),
                "area_mm2": quantized_number(raw_region["area_mm2"]),
                "center_of_mass_mm": raw_region["center_of_mass_mm"],
                "bounding_box_mm": raw_region["bounding_box_mm"],
                "validation": raw_region["validation"],
                "faces": sorted(faces, key=lambda face: face["face_id"]),
            }
        )
    return source_document_id, sorted(regions, key=lambda region: region["region_id"]), face_ids_by_semantic


def _region_lookup(regions: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {region["semantic_id"]: region for region in regions}


def _semantic_pair_order(expected: dict[str, Any], pair: list[str]) -> list[str]:
    """Render a geometry pair using the benchmark manifest's semantic order."""
    for expected_relation in expected["expected_relation_matrix"]:
        if frozenset(expected_relation["semantic_pair"]) == frozenset(pair):
            return expected_relation["semantic_pair"]
    return sorted(pair)


def _materialize_analysis(step_path: Path, expected: dict[str, Any], raw: dict[str, Any], elapsed_ms: float) -> dict[str, Any]:
    step_sha256 = sha256_file(step_path)
    source_document_id, regions, face_ids_by_semantic = _materialize_identities(step_sha256, raw["regions"])
    region_by_semantic = _region_lookup(regions)

    candidates = []
    for candidate in raw["candidates"]:
        semantic_pair = _semantic_pair_order(expected, candidate["semantic_pair"])
        candidates.append(
            {
                **candidate,
                "semantic_pair": semantic_pair,
                "region_pair": sorted(region_by_semantic[semantic]["region_id"] for semantic in semantic_pair),
                "candidate_id": "candidate:v1:" + canonical_digest(
                    {
                        "pair": sorted(region_by_semantic[semantic]["region_id"] for semantic in semantic_pair),
                        "bounds_gap_mm": quantized_number(candidate["bounds_gap_mm"]),
                        "candidate_tolerance_mm": candidate["candidate_tolerance_mm"],
                    }
                ),
            }
        )

    relations = []
    for relation in raw["relations"]:
        semantic_pair = _semantic_pair_order(expected, relation["semantic_pair"])
        relations.append(
            {
                **relation,
                "semantic_pair": semantic_pair,
                "region_pair": sorted(region_by_semantic[semantic]["region_id"] for semantic in relation["semantic_pair"]),
                "relation_id": "relation:v1:" + canonical_digest(
                    {
                        "pair": sorted(region_by_semantic[semantic]["region_id"] for semantic in relation["semantic_pair"]),
                        "relation_type": relation["relation_type"],
                        "intersection_dimension": relation["intersection_dimension"],
                    }
                ),
            }
        )

    patches = []
    provenance = []
    for raw_patch in raw["patches"]:
        semantic_a, semantic_b = raw_patch["semantic_pair"]
        semantic_pair = _semantic_pair_order(expected, raw_patch["semantic_pair"])
        region_a = region_by_semantic[semantic_a]
        region_b = region_by_semantic[semantic_b]
        source_face_a = face_ids_by_semantic[semantic_a][raw_patch["source_face_index_a"]]
        source_face_b = face_ids_by_semantic[semantic_b][raw_patch["source_face_index_b"]]
        if region_a["region_id"] > region_b["region_id"]:
            region_a, region_b = region_b, region_a
            source_face_a, source_face_b = source_face_b, source_face_a
        patch_fingerprint = face_geometry_fingerprint(raw_patch["geometry"])
        identifier = patch_id(
            [region_a["region_id"], region_b["region_id"]], [source_face_a, source_face_b], patch_fingerprint
        )
        provenance_identifier = "provenance:v1:" + canonical_digest(
            {
                "patch_id": identifier,
                "source_document_id": source_document_id,
                "source_face_ids": sorted([source_face_a, source_face_b]),
                "operation": "FACE_COMMON",
                "method": "explicit_geometric_matching",
            }
        )
        patch = {
            "patch_id": identifier,
            "region_a_id": region_a["region_id"],
            "region_b_id": region_b["region_id"],
            "semantic_pair": semantic_pair,
            "relation_type": raw_patch["relation_type"],
            "intersection_dimension": raw_patch["intersection_dimension"],
            "area_mm2": quantized_number(raw_patch["area_mm2"]),
            "geometry_fingerprint": patch_fingerprint,
            "source_face_a_id": source_face_a,
            "source_face_b_id": source_face_b,
            "extraction_method": raw_patch["extraction_method"],
            "tolerance": TOLERANCES,
            "provenance_method": "explicit_geometric_matching",
            "provenance_status": "COMPLETE",
            "provenance_id": provenance_identifier,
        }
        patches.append(patch)
        provenance.append(
            {
                "provenance_id": provenance_identifier,
                "provenance_completeness": "COMPLETE",
                "operation": "FACE_COMMON",
                "backend": "freecad_part",
                "backend_version": {"freecad": raw["freecad_version"], "occt": raw["opencascade_version"]},
                "input_entity_ids": [region_a["region_id"], region_b["region_id"], source_face_a, source_face_b],
                "output_entity_ids": [identifier],
                    "parameters": {"nominal_fuzzy_value_mm": 0.0, "area_epsilon_mm2": TOLERANCES["area_epsilon_mm2"]},
                "history_links": "NOT_AVAILABLE_IN_FREECAD_PART_BINDING",
                "explicit_geometric_evidence": {
                    "same_domain_brep_face_common": True,
                    "common_area_mm2": quantized_number(raw_patch["area_mm2"]),
                    "source_face_a_area_mm2": next(
                        face["area_mm2"] for face in region_a["faces"] if face["face_id"] == source_face_a
                    ),
                    "source_face_b_area_mm2": next(
                        face["area_mm2"] for face in region_b["faces"] if face["face_id"] == source_face_b
                    ),
                    "common_geometry_fingerprint": patch_fingerprint,
                },
                "provenance_method": "explicit_geometric_matching",
                "provenance_status": "COMPLETE",
            }
        )

    manifest = {
        "schema_version": 1,
        "case_id": expected["case_id"],
        "backend": "step_brep_interface",
        "analysis_input": raw["analysis_input"],
        "step_sha256": step_sha256,
        "source_document_id": source_document_id,
        "git": git_metadata(REPOSITORY_ROOT),
        "environment": {
            "freecad_version": raw["freecad_version"],
            "occt_version": raw["opencascade_version"],
            "headless_execution": raw["headless_execution"],
        },
        "tolerance": TOLERANCES,
        "runtime": {"analysis_elapsed_ms": elapsed_ms},
        "imported_solid_count": raw["imported_solid_count"],
        "candidate_pairs": candidates,
        "confirmed_relations": [{"semantic_pair": relation["semantic_pair"], "relation_type": relation["relation_type"]} for relation in relations],
        "interface_areas_mm2": [patch["area_mm2"] for patch in patches],
        "provenance_method": "explicit_geometric_matching",
        "failure_rejection_information": [
            candidate for candidate in candidates if candidate["status"] == "FILTERED_OUT"
        ],
        "implementation_deviations": [
            {
                "status": "IMPLEMENTATION_DECISION",
                "subject": "CASE01 coordinate origin",
                "detail": "Task-required 0..30 mm geometry is a +15 mm translation from the frozen illustrative fixture; DESIGN FREEZE was not edited.",
            },
            {
                "status": "IMPLEMENTATION_DEVIATION",
                "subject": "FreeCAD Boolean history",
                "detail": "Actual FreeCAD Part Python probe did not expose Generated/Modified/Deleted. This CASE01 task therefore uses explicit B-rep face-common, area-agreement and geometry-fingerprint provenance.",
            },
        ],
    }
    return {
        "manifest": manifest,
        "regions": regions,
        "candidates": candidates,
        "relations": sorted(relations, key=lambda relation: relation["relation_id"]),
        "interface_patches": sorted(patches, key=lambda patch: patch["patch_id"]),
        "provenance": sorted(provenance, key=lambda record: record["provenance_id"]),
    }


def _write_analysis_evidence(output_dir: Path, result: dict[str, Any]) -> None:
    write_json(output_dir / "manifest.json", result["manifest"])
    write_json(output_dir / "regions.json", {"regions": result["regions"]})
    write_json(output_dir / "relations.json", {"candidates": result["candidates"], "relations": result["relations"]})
    write_json(output_dir / "interface_patches.json", {"interface_patches": result["interface_patches"]})
    write_json(output_dir / "provenance.json", {"provenance": result["provenance"]})


def analyze_case01(step_path: Path, output_dir: Path) -> dict[str, Any]:
    """Re-import a CASE01 STEP file and publish its B-rep evidence package."""
    step_path = Path(step_path)
    output_dir = Path(output_dir)
    expected_path = step_path.with_name("expected.json")
    if not expected_path.is_file():
        raise FileNotFoundError(f"CASE01 semantic manifest is required beside the STEP fixture: {expected_path}")
    expected = read_json(expected_path)
    started = time.perf_counter()
    raw = _run_freecad(
        {
            "action": "analyze",
            "step_path": str(step_path),
            "semantics": expected["regions"],
            "tolerances": TOLERANCES,
        }
    )
    result = _materialize_analysis(step_path, expected, raw, (time.perf_counter() - started) * 1000.0)
    _write_analysis_evidence(output_dir, result)
    return result


def _repeatability_snapshot(result: dict[str, Any]) -> dict[str, Any]:
    return {
        "document_id": result["manifest"]["source_document_id"],
        "region_ids": sorted(region["region_id"] for region in result["regions"]),
        "face_ids": sorted(face["face_id"] for region in result["regions"] for face in region["faces"]),
        "patch_ids": sorted(patch["patch_id"] for patch in result["interface_patches"]),
        "relations": [
            {
                "semantic_pair": relation["semantic_pair"],
                "relation_type": relation["relation_type"],
                "intersection_dimension": relation["intersection_dimension"],
            }
            for relation in result["relations"]
        ],
        "patches": [
            {
                "patch_id": patch["patch_id"],
                "area_mm2": patch["area_mm2"],
                "source_face_a_id": patch["source_face_a_id"],
                "source_face_b_id": patch["source_face_b_id"],
            }
            for patch in result["interface_patches"]
        ],
        "provenance": [
            {
                "patch_id": patch["patch_id"],
                "provenance_method": patch["provenance_method"],
                "provenance_status": patch["provenance_status"],
            }
            for patch in result["interface_patches"]
        ],
    }


def run_repeatability(step_path: Path, output_dir: Path) -> dict[str, Any]:
    """Compare two independent FreeCADCmd analyses of one immutable STEP input."""
    output_dir = Path(output_dir)
    first = analyze_case01(step_path, output_dir / "repeatability_run_1")
    second = analyze_case01(step_path, output_dir / "repeatability_run_2")
    first_snapshot = _repeatability_snapshot(first)
    second_snapshot = _repeatability_snapshot(second)
    comparison = {
        "document_ids_match": first_snapshot["document_id"] == second_snapshot["document_id"],
        "region_ids_match": first_snapshot["region_ids"] == second_snapshot["region_ids"],
        "face_ids_match": first_snapshot["face_ids"] == second_snapshot["face_ids"],
        "patch_ids_match": first_snapshot["patch_ids"] == second_snapshot["patch_ids"],
        "relation_mappings_match": first_snapshot["relations"] == second_snapshot["relations"],
        "area_mappings_match": first_snapshot["patches"] == second_snapshot["patches"],
        "provenance_mappings_match": first_snapshot["provenance"] == second_snapshot["provenance"],
    }
    report = {
        "schema_version": 1,
        "input_step_sha256": sha256_file(Path(step_path)),
        "processes": 2,
        "status": "PASS" if all(comparison.values()) else "FAIL",
        "comparison": comparison,
        "first_snapshot": first_snapshot,
        "second_snapshot": second_snapshot,
    }
    write_json(output_dir / "repeatability.json", report)
    return report


def run_capability_probe(output_path: Path) -> dict[str, Any]:
    """Run the actual FreeCAD capability probe and preserve its evidence JSON."""
    probe = _run_freecad({"action": "capability_probe"})
    probe["environment_diagnostics"] = [
        {
            "status": "OBSERVED_AND_MITIGATED",
            "detail": "A non-safe-mode exploratory run loaded FreecadRobustMCPBridge and raised AttributeError for FreeCAD.GuiUp. Formal CASE01 execution uses FreeCADCmd --safe-mode.",
        }
    ]
    write_json(Path(output_path), probe)
    return probe
