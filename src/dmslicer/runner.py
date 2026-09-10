"""Host-side CASE01 fixture generation, analysis, and repeatability runner."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any

from .evidence import git_metadata, read_json, sha256_file, write_json
from .identity import (
    canonical_digest,
    document_id,
    face_geometry_fingerprint,
    occurrence_locator_digest,
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


class ValidationError(RuntimeError):
    """Raised only after structured CASE01 validation failure evidence is written."""


def _area_close(actual: float, expected: float, tolerance: float) -> bool:
    return abs(actual - expected) <= tolerance


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
                "source_boundary": {"boundary_role": "SOURCE_A", "condition_kind": "DIRICHLET_SCALAR", "scalar_value": 0.0},
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
                "source_boundary": {"boundary_role": "SOURCE_B", "condition_kind": "DIRICHLET_SCALAR", "scalar_value": 1.0},
                "bounds_mm": {"x": [20, 30], "y": [0, 20], "z": [0, 20]},
            },
        ],
        "expected_relation_matrix": [
            {"semantic_pair": ["A", "G"], "relation_type": "FULL_FACE_OVERLAP", "intersection_dimension": 2, "area_mm2": 400.0},
            {"semantic_pair": ["G", "B"], "relation_type": "FULL_FACE_OVERLAP", "intersection_dimension": 2, "area_mm2": 400.0},
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


def _semantics_manifest() -> dict[str, Any]:
    """Return CASE01 input roles without any expected geometry truth."""
    return {
        "schema_version": 1,
        "case_id": "CASE01_planar_agb_exact",
        "semantic_order": ["A", "G", "B"],
        "occurrences": [
            {
                "product_path": ["A"],
                "source_label": "A",
                "semantic_id": "A",
                "semantic_role": "SOURCE",
                "material_key": "A",
                "participation_policy": {"mode": "ACTIVE", "source_eligible": True, "gradient_eligible": False},
                "source_boundary": {"boundary_role": "SOURCE_A", "condition_kind": "DIRICHLET_SCALAR", "scalar_value": 0.0},
            },
            {
                "product_path": ["G"],
                "source_label": "G",
                "semantic_id": "G",
                "semantic_role": "GRADIENT",
                "material_key": "Gradient",
                "participation_policy": {"mode": "ACTIVE", "source_eligible": False, "gradient_eligible": True},
            },
            {
                "product_path": ["B"],
                "source_label": "B",
                "semantic_id": "B",
                "semantic_role": "SOURCE",
                "material_key": "B",
                "participation_policy": {"mode": "ACTIVE", "source_eligible": True, "gradient_eligible": False},
                "source_boundary": {"boundary_role": "SOURCE_B", "condition_kind": "DIRICHLET_SCALAR", "scalar_value": 1.0},
            },
        ],
    }


def generate_case01_fixture(
    step_path: Path, expected_path: Path | None = None, semantics_path: Path | None = None
) -> dict[str, Any]:
    """Generate the real three-solid STEP fixture through FreeCAD/Part."""
    step_path = Path(step_path)
    expected_path = Path(expected_path) if expected_path is not None else step_path.with_name("expected.json")
    semantics_path = Path(semantics_path) if semantics_path is not None else step_path.with_name("semantics.json")
    response = _run_freecad({"action": "generate", "step_path": str(step_path)})
    if not step_path.is_file():
        raise RuntimeError("FreeCAD reported STEP generation success but no STEP file was written")
    write_json(expected_path, _expected_manifest())
    write_json(semantics_path, _semantics_manifest())
    return {**response, "step_sha256": sha256_file(step_path), "expected_path": str(expected_path), "semantics_path": str(semantics_path)}


def _materialize_identities(step_sha256: str, raw_regions: list[dict[str, Any]]) -> tuple[str, list[dict[str, Any]], dict[str, dict[int, str]]]:
    source_document_id = document_id(step_sha256)
    regions = []
    face_ids_by_occurrence: dict[str, dict[int, str]] = {}
    for raw_region in raw_regions:
        face_fingerprints = [face_geometry_fingerprint(face) for face in raw_region["faces"]]
        solid_fingerprint = solid_geometry_fingerprint(raw_region, face_fingerprints)
        occurrence_locator = {**raw_region["source_occurrence_locator"], "entity_kind": "SOLID"}
        identifier = region_id(source_document_id, solid_fingerprint, occurrence_locator)
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
        face_ids_by_occurrence[raw_region["occurrence_key"]] = face_ids_by_index
        regions.append(
            {
                "region_id": identifier,
                "source_document_id": source_document_id,
                "occurrence_key": raw_region["occurrence_key"],
                "source_label": raw_region["source_label"],
                "source_locator": {
                    "document_id": source_document_id,
                    "product_path": occurrence_locator["product_path"],
                    "entity_kind": "SOLID",
                    "source_ordinal": raw_region["source_ordinal"],
                    "persistent_label": occurrence_locator["persistent_label"],
                    "geometry_digest": solid_fingerprint,
                    "occurrence_locator_digest": occurrence_locator_digest(occurrence_locator),
                    "identity_schema": "case01-geometry-occurrence:v2",
                    "identity_scope": "stable within this imported STEP only; cross-STEP correspondence is not claimed",
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
    return source_document_id, sorted(regions, key=lambda region: region["region_id"]), face_ids_by_occurrence


def _region_lookup(regions: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {region["semantic_id"]: region for region in regions}


def _semantic_layer(regions: list[dict[str, Any]], patches: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], str]:
    """Activate CASE01 Γ boundaries from semantic roles plus confirmed patches.

    Geometry only supplies patches.  The explicit fixture semantic manifest
    supplies SOURCE/GRADIENT roles; neither physical ordering nor case IDs are
    used to create the mapping.
    """
    by_semantic = _region_lookup(regions)
    gradient_regions = [region for region in regions if region["semantic_role"] == "GRADIENT" and region["participation_policy"]["gradient_eligible"]]
    if len(gradient_regions) != 1:
        raise RuntimeError("CASE01 semantic activation requires exactly one gradient region")
    gradient = gradient_regions[0]
    domain_id = "gradient-domain:v1:" + canonical_digest({"region_ids": [gradient["region_id"]]})
    boundaries = []
    for patch in patches:
        semantic_a, semantic_b = patch["semantic_pair"]
        source_semantic = semantic_b if by_semantic[semantic_a]["region_id"] == gradient["region_id"] else semantic_a if by_semantic[semantic_b]["region_id"] == gradient["region_id"] else None
        if source_semantic is None:
            continue
        source = by_semantic[source_semantic]
        boundary_spec = source.get("source_boundary")
        if source["semantic_role"] != "SOURCE" or not source["participation_policy"]["source_eligible"] or not boundary_spec:
            continue
        value = boundary_spec["scalar_value"]
        boundary_payload = {
            "gradient_domain_id": domain_id,
            "source_material_region_id": source["region_id"],
            "interface_patch_id": patch["patch_id"],
            "condition_kind": boundary_spec["condition_kind"],
            "scalar_value": value,
        }
        boundary_id = "source-boundary:v1:" + canonical_digest(boundary_payload)
        boundaries.append(
            {
                "source_boundary_id": boundary_id,
                "interface_patch_id": patch["patch_id"],
                "gradient_domain_region_id": gradient["region_id"],
                "gradient_domain_id": domain_id,
                "source_material_region_id": source["region_id"],
                "boundary_role": boundary_spec["boundary_role"],
                "condition_kind": boundary_spec["condition_kind"],
                "boundary_value_placeholder": value,
                "selection": {"mode": "AUTO", "basis": "explicit benchmark semantic role + confirmed 2D patch"},
                "provenance_linkage": {"patch_provenance_id": patch["provenance_id"], "selection_operation": "SELECT_SOURCE_BOUNDARY"},
            }
        )
    boundaries = sorted(boundaries, key=lambda boundary: boundary["source_boundary_id"])
    semantic_digest = "sha256:" + canonical_digest({"domain_id": domain_id, "source_boundaries": boundaries})
    return boundaries, semantic_digest


def validate_case01(result: dict[str, Any], expected: dict[str, Any], evidence_dir: Path) -> dict[str, Any]:
    """Compare measured output to tracked truth; never contribute to geometry calculation."""
    failures: list[dict[str, Any]] = []
    expected_without_digest = {key: value for key, value in expected.items() if key != "truth_digest"}
    computed_truth_digest = "sha256:" + canonical_digest(expected_without_digest)
    if expected.get("truth_digest") != computed_truth_digest:
        failures.append({"kind": "expected_truth_digest", "expected": computed_truth_digest, "actual": expected.get("truth_digest")})
    expected_pair_rows = [tuple(truth["semantic_pair"]) for truth in expected["expected_relation_matrix"]]
    actual_pair_rows = [tuple(relation["semantic_pair"]) for relation in result["relations"]]
    if len(expected_pair_rows) != len(set(expected_pair_rows)):
        failures.append({"kind": "duplicate_expected_relation", "semantic_pairs": [list(pair) for pair in expected_pair_rows]})
    if len(actual_pair_rows) != len(set(actual_pair_rows)):
        failures.append({"kind": "duplicate_actual_relation", "semantic_pairs": [list(pair) for pair in actual_pair_rows]})
    actual_relations = {tuple(relation["semantic_pair"]): relation for relation in result["relations"]}
    actual_patches = result["interface_patches"]
    expected_pairs = set(expected_pair_rows)
    if len(actual_pair_rows) != len(expected_pair_rows):
        failures.append({"kind": "relation_cardinality", "expected": len(expected_pair_rows), "actual": len(actual_pair_rows)})
    for pair in sorted(set(actual_relations) - expected_pairs):
        failures.append({"kind": "unexpected_relation", "semantic_pair": list(pair), "actual": actual_relations[pair]})
    for patch in actual_patches:
        pair = tuple(patch["semantic_pair"])
        if pair not in expected_pairs:
            failures.append({"kind": "unexpected_interface_patch", "semantic_pair": list(pair), "actual": patch})
    if result["manifest"]["imported_solid_count"] != len(expected["regions"]):
        failures.append({"kind": "solid_count", "expected": len(expected["regions"]), "actual": result["manifest"]["imported_solid_count"]})
    if len(actual_patches) != expected["expected_patch_count"]:
        failures.append({"kind": "interface_patch_count", "expected": expected["expected_patch_count"], "actual": len(actual_patches)})
    area_tolerance = float(expected["tolerance_contract"]["area_epsilon_mm2"])
    for truth in expected["expected_relation_matrix"]:
        pair = tuple(truth["semantic_pair"])
        actual = actual_relations.get(pair)
        if actual is None:
            failures.append({"kind": "missing_relation", "semantic_pair": list(pair), "expected": truth})
            continue
        for field in ("relation_type", "intersection_dimension"):
            if actual[field] != truth[field]:
                failures.append({"kind": field, "semantic_pair": list(pair), "expected": truth[field], "actual": actual[field]})
        actual_area = sum(patch["area_mm2"] for patch in actual_patches if patch["semantic_pair"] == list(pair))
        if not _area_close(actual_area, float(truth["area_mm2"]), area_tolerance):
            failures.append({"kind": "interface_area_mm2", "semantic_pair": list(pair), "expected": truth["area_mm2"], "actual": actual_area, "tolerance": area_tolerance})
    expected_semantics = {item["semantic_id"]: item for item in expected["regions"]}
    actual_semantics = {item["semantic_id"] for item in result["regions"]}
    if set(expected_semantics) != actual_semantics:
        failures.append({"kind": "semantic_mappings", "expected": sorted(expected_semantics), "actual": sorted(actual_semantics)})
    validation = {"schema_version": 1, "status": "PASS" if not failures else "FAIL", "expected_truth_digest": expected.get("truth_digest"), "failures": failures}
    write_json(Path(evidence_dir) / "validation.json", validation)
    return validation


def _semantic_pair_order(semantics: dict[str, Any], pair: list[str]) -> list[str]:
    """Render semantic pairs using input semantics, never expected truth."""
    order = {semantic_id: index for index, semantic_id in enumerate(semantics["semantic_order"])}
    return sorted(pair, key=lambda semantic_id: (order.get(semantic_id, len(order)), semantic_id))


def _materialize_analysis(step_path: Path, semantics: dict[str, Any], raw: dict[str, Any], elapsed_ms: float) -> dict[str, Any]:
    step_sha256 = sha256_file(step_path)
    source_document_id, regions, face_ids_by_occurrence = _materialize_identities(step_sha256, raw["regions"])
    geometry = {
        "schema_version": 1,
        "source_document_id": source_document_id,
        "regions": regions,
        "candidates": raw["candidates"],
        "relations": raw["relations"],
        "interface_patches": raw["patches"],
    }
    geometry_digest = "sha256:" + canonical_digest(geometry)
    semantic_by_source_label = {
        item["source_label"]: item for item in semantics["occurrences"]
    }
    actual_source_labels = {region["source_label"] for region in regions}
    if actual_source_labels != set(semantic_by_source_label):
        raise RuntimeError(
            "CASE01 semantic input must map each imported occurrence exactly once: "
            + repr({"semantic_labels": sorted(semantic_by_source_label), "actual_labels": sorted(actual_source_labels)})
        )
    regions = [
        {
            **region,
            **{
                key: semantic_by_source_label[region["source_label"]][key]
                for key in ("semantic_id", "semantic_role", "material_key", "participation_policy", "source_boundary")
                if key in semantic_by_source_label[region["source_label"]]
            },
        }
        for region in regions
    ]
    region_by_semantic = _region_lookup(regions)
    semantic_by_occurrence_key = {
        region["occurrence_key"]: region["semantic_id"] for region in regions
    }

    candidates = []
    for candidate in raw["candidates"]:
        semantic_pair = _semantic_pair_order(
            semantics, [semantic_by_occurrence_key[key] for key in candidate["occurrence_pair"]]
        )
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
        semantic_pair = _semantic_pair_order(
            semantics, [semantic_by_occurrence_key[key] for key in relation["occurrence_pair"]]
        )
        relations.append(
            {
                **relation,
                "semantic_pair": semantic_pair,
                "region_pair": sorted(region_by_semantic[semantic]["region_id"] for semantic in semantic_pair),
                "relation_id": "relation:v1:" + canonical_digest(
                    {
                        "pair": sorted(region_by_semantic[semantic]["region_id"] for semantic in semantic_pair),
                        "relation_type": relation["relation_type"],
                        "intersection_dimension": relation["intersection_dimension"],
                    }
                ),
            }
        )

    patches = []
    provenance = []
    for raw_patch in raw["patches"]:
        semantic_a, semantic_b = [semantic_by_occurrence_key[key] for key in raw_patch["occurrence_pair"]]
        semantic_pair = _semantic_pair_order(semantics, [semantic_a, semantic_b])
        region_a = region_by_semantic[semantic_a]
        region_b = region_by_semantic[semantic_b]
        source_face_a = face_ids_by_occurrence[raw_patch["occurrence_pair"][0]][raw_patch["source_face_index_a"]]
        source_face_b = face_ids_by_occurrence[raw_patch["occurrence_pair"][1]][raw_patch["source_face_index_b"]]
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
                "method": "DIRECT_BREP_FACE_COMMON",
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
            "coverage_a": quantized_number(raw_patch["coverage_a"]),
            "coverage_b": quantized_number(raw_patch["coverage_b"]),
            "geometry_fingerprint": patch_fingerprint,
            "source_face_a_id": source_face_a,
            "source_face_b_id": source_face_b,
            "extraction_method": raw_patch["extraction_method"],
            "tolerance": TOLERANCES,
            "provenance_method": "DIRECT_BREP_FACE_COMMON",
            "provenance_status": "COMPLETE_FOR_DIRECT_COMMON",
            "provenance_id": provenance_identifier,
        }
        patches.append(patch)
        provenance.append(
            {
                "provenance_id": provenance_identifier,
                "provenance_completeness": "COMPLETE_FOR_DIRECT_COMMON",
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
                "provenance_method": "DIRECT_BREP_FACE_COMMON",
                "provenance_status": "COMPLETE_FOR_DIRECT_COMMON",
            }
        )

    source_boundaries, semantic_digest = _semantic_layer(regions, patches)
    manifest = {
        "schema_version": 1,
        "case_id": semantics["case_id"],
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
        "provenance_method": "DIRECT_BREP_FACE_COMMON",
        "provenance_status": "COMPLETE_FOR_DIRECT_COMMON",
        "semantic_digest": semantic_digest,
        "geometry_digest": geometry_digest,
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
        "interface_source_boundaries": source_boundaries,
        "semantic_digest": semantic_digest,
        "geometry": {**geometry, "geometry_digest": geometry_digest},
        "geometry_digest": geometry_digest,
    }


def _write_analysis_evidence(output_dir: Path, result: dict[str, Any]) -> None:
    write_json(output_dir / "geometry.json", result["geometry"])
    write_json(output_dir / "manifest.json", result["manifest"])
    write_json(output_dir / "regions.json", {"regions": result["regions"]})
    write_json(output_dir / "relations.json", {"candidates": result["candidates"], "relations": result["relations"]})
    write_json(output_dir / "interface_patches.json", {"interface_patches": result["interface_patches"]})
    write_json(output_dir / "provenance.json", {"provenance": result["provenance"]})
    write_json(output_dir / "interface_source_boundaries.json", {"interface_source_boundaries": result["interface_source_boundaries"], "semantic_digest": result["semantic_digest"]})


def analyze_case01(
    step_path: Path,
    output_dir: Path,
    *,
    expected_path: Path | None = None,
    semantics_path: Path | None = None,
) -> dict[str, Any]:
    """Re-import a CASE01 STEP file and publish its B-rep evidence package."""
    step_path = Path(step_path)
    output_dir = Path(output_dir)
    expected_path = Path(expected_path) if expected_path is not None else step_path.with_name("expected.json")
    semantics_path = Path(semantics_path) if semantics_path is not None else step_path.with_name("semantics.json")
    if not semantics_path.is_file():
        raise RuntimeError(f"CASE01 independent semantic input is required beside the STEP fixture: {semantics_path}")
    semantics = read_json(semantics_path)
    started = time.perf_counter()
    raw = _run_freecad(
        {
            "action": "analyze",
            "step_path": str(step_path),
            "tolerances": TOLERANCES,
        }
    )
    result = _materialize_analysis(step_path, semantics, raw, (time.perf_counter() - started) * 1000.0)
    _write_analysis_evidence(output_dir, result)
    if not expected_path.is_file():
        validation = {
            "schema_version": 1,
            "status": "FAIL",
            "expected_truth_digest": None,
            "failures": [{"kind": "expected_truth_unavailable", "path": str(expected_path)}],
        }
        write_json(output_dir / "validation.json", validation)
        result["validation"] = validation
        result["manifest"]["validation_status"] = validation["status"]
        write_json(output_dir / "manifest.json", result["manifest"])
        raise ValidationError("CASE01 expected-truth validation could not load expected.json; geometry evidence was published")
    try:
        expected = read_json(expected_path)
    except (OSError, json.JSONDecodeError) as error:
        validation = {
            "schema_version": 1,
            "status": "FAIL",
            "expected_truth_digest": None,
            "failures": [{"kind": "expected_truth_unavailable", "path": str(expected_path), "detail": str(error)}],
        }
        write_json(output_dir / "validation.json", validation)
        result["validation"] = validation
        result["manifest"]["validation_status"] = validation["status"]
        write_json(output_dir / "manifest.json", result["manifest"])
        raise ValidationError("CASE01 expected-truth validation could not parse expected.json; geometry evidence was published") from error
    validation = validate_case01(result, expected, output_dir)
    result["validation"] = validation
    result["manifest"]["validation_status"] = validation["status"]
    _write_analysis_evidence(output_dir, result)
    if validation["status"] != "PASS":
        raise ValidationError("CASE01 expected-truth validation failed; see validation.json")
    return result


_PATCH_COMPARISON_FIELDS = (
    "area_mm2",
    "coverage_a",
    "coverage_b",
    "provenance_id",
    "source_face_a_id",
    "source_face_b_id",
    "provenance_input_entity_ids",
    "provenance_output_entity_ids",
)


def _repeatability_snapshot(result: dict[str, Any]) -> dict[str, Any]:
    """Freeze patch/provenance evidence for comparison without losing linkage order."""
    provenance_by_id = {record["provenance_id"]: record for record in result["provenance"]}
    patches = []
    patch_errors = []
    for patch in result["interface_patches"]:
        patch_id = patch.get("patch_id")
        values = {field: patch.get(field) for field in ("area_mm2", "coverage_a", "coverage_b", "provenance_id", "source_face_a_id", "source_face_b_id")}
        for field, value in values.items():
            if value is None:
                patch_errors.append({"patch_id": patch_id, "category": field, "detail": "required patch field is missing"})
        provenance = provenance_by_id.get(values["provenance_id"])
        if provenance is None:
            patch_errors.append({"patch_id": patch_id, "category": "provenance_id", "detail": "linked provenance record is missing"})
            input_entity_ids = None
            output_entity_ids = None
        else:
            input_entity_ids = provenance.get("input_entity_ids")
            output_entity_ids = provenance.get("output_entity_ids")
            for field, value in (("input_entity_ids", input_entity_ids), ("output_entity_ids", output_entity_ids)):
                if not value:
                    patch_errors.append({"patch_id": patch_id, "category": field, "detail": "required provenance linkage is missing"})
        patches.append(
            {
                "patch_id": patch_id,
                **values,
                "provenance_input_entity_ids": input_entity_ids,
                "provenance_output_entity_ids": output_entity_ids,
            }
        )
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
        "patches": sorted(patches, key=lambda patch: patch["patch_id"]),
        "patch_comparison_errors": sorted(patch_errors, key=lambda error: (str(error["patch_id"]), error["category"])),
        "semantic_digest": result["semantic_digest"],
        "source_boundaries": result["interface_source_boundaries"],
        "region_geometry_fingerprints": sorted(region["geometry_fingerprint"] for region in result["regions"]),
        "candidate_final_status": sorted((candidate["semantic_pair"], candidate["status"]) for candidate in result["candidates"]),
    }


def _compare_repeatability_snapshots(
    first_snapshot: dict[str, Any], second_snapshot: dict[str, Any]
) -> tuple[dict[str, bool], list[dict[str, Any]]]:
    """Compare frozen evidence and report every patch-level mismatch by stable ID."""
    failures = [
        {"run": run, **error}
        for run, snapshot in (("first", first_snapshot), ("second", second_snapshot))
        for error in snapshot["patch_comparison_errors"]
    ]
    first_patches = {patch["patch_id"]: patch for patch in first_snapshot["patches"]}
    second_patches = {patch["patch_id"]: patch for patch in second_snapshot["patches"]}
    for patch_identifier in sorted(set(first_patches) | set(second_patches)):
        first_patch = first_patches.get(patch_identifier)
        second_patch = second_patches.get(patch_identifier)
        if first_patch is None or second_patch is None:
            failures.append({"patch_id": patch_identifier, "category": "patch_id", "detail": "patch is missing from one snapshot"})
            continue
        for field in _PATCH_COMPARISON_FIELDS:
            if first_patch[field] != second_patch[field]:
                failures.append({"patch_id": patch_identifier, "category": field, "first": first_patch[field], "second": second_patch[field]})
    patch_mappings_match = not failures
    comparison = {
        "document_ids_match": first_snapshot["document_id"] == second_snapshot["document_id"],
        "region_ids_match": first_snapshot["region_ids"] == second_snapshot["region_ids"],
        "face_ids_match": first_snapshot["face_ids"] == second_snapshot["face_ids"],
        "patch_ids_match": first_snapshot["patch_ids"] == second_snapshot["patch_ids"],
        "relation_mappings_match": first_snapshot["relations"] == second_snapshot["relations"],
        "patch_mappings_match": patch_mappings_match,
        "area_mappings_match": patch_mappings_match,
        "provenance_mappings_match": patch_mappings_match,
        "semantic_digest_match": first_snapshot["semantic_digest"] == second_snapshot["semantic_digest"],
        "source_boundary_mappings_match": first_snapshot["source_boundaries"] == second_snapshot["source_boundaries"],
        "region_geometry_fingerprints_match": first_snapshot["region_geometry_fingerprints"] == second_snapshot["region_geometry_fingerprints"],
        "candidate_final_status_match": first_snapshot["candidate_final_status"] == second_snapshot["candidate_final_status"],
    }
    return comparison, failures


def run_repeatability(step_path: Path, output_dir: Path) -> dict[str, Any]:
    """Compare two independent FreeCADCmd analyses of one immutable STEP input."""
    output_dir = Path(output_dir)
    first = analyze_case01(step_path, output_dir / "repeatability_run_1")
    second = analyze_case01(step_path, output_dir / "repeatability_run_2")
    first_snapshot = _repeatability_snapshot(first)
    second_snapshot = _repeatability_snapshot(second)
    comparison, comparison_failures = _compare_repeatability_snapshots(first_snapshot, second_snapshot)
    report = {
        "schema_version": 1,
        "input_step_sha256": sha256_file(Path(step_path)),
        "processes": 2,
        "status": "PASS" if all(comparison.values()) else "FAIL",
        "comparison": comparison,
        "comparison_failures": comparison_failures,
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
