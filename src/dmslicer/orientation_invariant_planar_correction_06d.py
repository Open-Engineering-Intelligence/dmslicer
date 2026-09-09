"""06D host contract for orientation-invariant planar correction."""

from __future__ import annotations

import math
import argparse
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from .evidence import read_json, sha256_file, write_json
from .planar_multipatch_interface_correction_06c import (
    _apply_visibility_profile,
    _artifact_names,
    _freecad_executable,
)
from . import planar_multipatch_interface_correction_06c as baseline_06c


REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURE_ROOT = REPO_ROOT / "benchmarks" / "orientation_invariant_planar_correction_06d"
FREECAD_SCRIPT = Path(__file__).with_name(
    "freecad_orientation_invariant_planar_correction_06d.py"
)
RULES = {
    "linear_epsilon_mm": 1.0e-7,
    "area_epsilon_mm2": 1.0e-8,
    "volume_epsilon_mm3": 1.0e-6,
}
POLICY = {
    "schema_version": 1,
    "policy_valid": True,
    "allow_motion": True,
    "tauE_mm": 0.1,
    "max_translation_mm": 0.1,
}
SCENARIOS = {
    "D01": {
        "status": "SUPPORTED_UNIQUE_INTERFACE_FACESET",
        "gap_mm": 0.05,
        "common_area_mm2": 480.0,
        "coverage": {"Side_1": 0.6, "Side_2": 0.6},
        "remaining_area_mm2": {"Side_1": 320.0, "Side_2": 320.0},
        "patch_count": 1,
        "component_count": 1,
        "boundary_component_count": 1,
        "hole_count": 0,
    },
    "D02": {
        "status": "SUPPORTED_UNIQUE_INTERFACE_FACESET",
        "gap_mm": 0.05,
        "common_area_mm2": 384.0,
        "coverage": {"Side_1": 0.16, "Side_2": 1.0},
        "remaining_area_mm2": {"Side_1": 2016.0, "Side_2": 0.0},
        "patch_count": 2,
        "component_count": 2,
        "boundary_component_count": 2,
        "hole_count": 0,
    },
    "D03": {
        "status": "SUPPORTED_UNIQUE_INTERFACE_FACESET",
        "gap_mm": 0.05,
        "common_area_mm2": 300.0 * math.pi,
        "coverage": {"Side_1": math.pi / 12.0, "Side_2": 1.0},
        "remaining_area_mm2": {"Side_1": 3600.0 - 300.0 * math.pi, "Side_2": 0.0},
        "patch_count": 1,
        "component_count": 1,
        "boundary_component_count": 2,
        "hole_count": 1,
    },
}
_USE_FIXTURE_REFERENCE = object()


def _finite_number(value: Any) -> bool:
    return type(value) in {int, float} and math.isfinite(float(value))


def normalize_reference_direction(value: Any) -> list[float] | None:
    """Return a unit 3-vector, or ``None`` for every invalid input."""
    if not isinstance(value, (list, tuple)) or len(value) != 3:
        return None
    if not all(_finite_number(component) for component in value):
        return None
    raw = [float(component) for component in value]
    norm = math.sqrt(sum(component * component for component in raw))
    if not math.isfinite(norm) or norm <= 0.0:
        return None
    return [component / norm for component in raw]


def pure_normal_translation(
    gap_mm: float, reference_direction: Any
) -> list[float] | None:
    """Compute the only authorized correction: ``-gap * unit(reference)``."""
    if not _finite_number(gap_mm):
        return None
    direction = normalize_reference_direction(reference_direction)
    if direction is None:
        return None
    return [-float(gap_mm) * component for component in direction]


def validate_rotation_matrix(value: Any, *, epsilon: float = 1.0e-10) -> dict[str, Any]:
    """Validate a finite 3x3 proper rotation and report its measured defects."""
    valid_shape = (
        isinstance(value, (list, tuple))
        and len(value) == 3
        and all(isinstance(row, (list, tuple)) and len(row) == 3 for row in value)
    )
    if not valid_shape or not all(_finite_number(item) for row in value for item in row):
        return {
            "status": "FAIL",
            "orthogonality_error": None,
            "determinant": None,
        }
    matrix = [[float(item) for item in row] for row in value]
    gram = [
        [sum(matrix[k][i] * matrix[k][j] for k in range(3)) for j in range(3)]
        for i in range(3)
    ]
    orthogonality_error = max(
        abs(gram[i][j] - (1.0 if i == j else 0.0))
        for i in range(3)
        for j in range(3)
    )
    determinant = (
        matrix[0][0] * (matrix[1][1] * matrix[2][2] - matrix[1][2] * matrix[2][1])
        - matrix[0][1] * (matrix[1][0] * matrix[2][2] - matrix[1][2] * matrix[2][0])
        + matrix[0][2] * (matrix[1][0] * matrix[2][1] - matrix[1][1] * matrix[2][0])
    )
    valid = orthogonality_error <= epsilon and abs(determinant - 1.0) <= epsilon
    return {
        "status": "PASS" if valid else "FAIL",
        "orthogonality_error": orthogonality_error,
        "determinant": determinant,
    }


def _run_freecad(request: dict[str, Any]) -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="dmslicer_orientation_06d_") as temporary:
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
        console = (
            "import os; p=os.environ['DMSLICER_FREECAD_SCRIPT']; "
            "exec(compile(open(p, encoding='utf-8').read(), p, 'exec'))\n"
        )
        result = subprocess.run(
            [str(_freecad_executable()), "--safe-mode", "-c"],
            input=console,
            env=environment,
            text=True,
            capture_output=True,
            timeout=300,
            check=False,
        )
        if not response_path.is_file():
            raise RuntimeError(
                f"FreeCADCmd did not write a response; exit={result.returncode}; "
                f"stdout={result.stdout}; stderr={result.stderr}"
            )
        response = read_json(response_path)
        if result.returncode or response.get("status") == "FAILED":
            raise RuntimeError(
                f"FreeCADCmd 06D failed; exit={result.returncode}; response={response}; "
                f"stdout={result.stdout}; stderr={result.stderr}"
            )
        return response


def generate_orientation_fixtures(
    root: Path, *, scenarios: tuple[str, ...] = ("D01", "D02", "D03")
) -> dict[str, Any]:
    root = Path(root)
    rows = []
    for scenario_id in scenarios:
        if scenario_id not in SCENARIOS:
            raise ValueError("unknown 06D scenario " + scenario_id)
        case = root / scenario_id
        case.mkdir(parents=True, exist_ok=True)
        generation = _run_freecad(
            {
                "action": "generate",
                "scenario_id": scenario_id,
                "step_path": str(case / "inputs.step"),
            }
        )
        base_generation = _run_freecad(
            {
                "action": "generate",
                "scenario_id": scenario_id,
                "step_path": str(case / "base_inputs.step"),
                "apply_transform": False,
            }
        )
        orientation = generation["orientation"]
        write_json(case / "operation_policy.json", POLICY)
        write_json(
            case / "orientation_semantics.json",
            {
                "schema_version": 1,
                "reference_direction": orientation["reference_direction"],
                "semantic_role": "SIDE_1_EXPECTED_OUTWARD_INTERFACE_NORMAL",
            },
        )
        write_json(
            case / "expected.json",
            {"schema_version": 1, "scenario_id": scenario_id, **SCENARIOS[scenario_id]},
        )
        write_json(
            case / "generation_manifest.json",
            {
                "schema_version": 1,
                "scenario_id": scenario_id,
                "construction": generation["construction"],
                **orientation,
                "base_step_sha256": "sha256:" + sha256_file(case / "base_inputs.step"),
                "base_representation_families": base_generation["orientation"]["representation_families"],
            },
        )
        rows.append(
            {
                "scenario_id": scenario_id,
                "step_sha256": "sha256:" + sha256_file(case / "inputs.step"),
            }
        )
    manifest = {
        "schema_version": 1,
        "operation": "ORIENTATION_INVARIANT_PLANAR_CORRECTION_06D",
        "numeric_rules": RULES,
        "scenarios": rows,
    }
    write_json(root / "manifest.json", manifest)
    return manifest


def _close(actual: Any, expected: Any, epsilon: float) -> bool:
    return _finite_number(actual) and _finite_number(expected) and abs(float(actual) - float(expected)) <= epsilon


def validate_orientation_evidence(
    operation: dict[str, Any], expected: dict[str, Any]
) -> dict[str, Any]:
    failures: list[dict[str, Any]] = []
    if operation.get("status") != expected.get("status"):
        failures.append({"kind": "expected_status"})
    if operation.get("status") == "SUPPORTED_UNIQUE_INTERFACE_FACESET":
        reference = normalize_reference_direction(
            operation.get("reference_direction", {}).get("normalized_reference_direction")
        )
        selected = operation.get("face_sets", {}).get("selected_pair", {})
        gap = selected.get("gap_mm")
        vector = operation.get("motion", {}).get("executed_translation_mm")
        target = pure_normal_translation(gap, reference)
        if target is None or not isinstance(vector, list) or len(vector) != 3 or any(
            not _close(actual, wanted, RULES["linear_epsilon_mm"])
            for actual, wanted in zip(vector or [], target or [])
        ):
            failures.append({"kind": "translation_direction"})
        partition = operation.get("partition", {})
        topology = operation.get("topology", {})
        if not _close(gap, expected.get("gap_mm"), RULES["linear_epsilon_mm"]):
            failures.append({"kind": "expected_gap"})
        if not _close(partition.get("common_area_mm2"), expected.get("common_area_mm2"), RULES["area_epsilon_mm2"]):
            failures.append({"kind": "expected_common_area"})
        for side in ("Side_1", "Side_2"):
            if not _close(partition.get("coverage", {}).get(side), expected["coverage"][side], 1.0e-7):
                failures.append({"kind": "expected_coverage", "field": side})
            if not _close(partition.get("remaining_area_mm2", {}).get(side), expected["remaining_area_mm2"][side], RULES["area_epsilon_mm2"]):
                failures.append({"kind": "expected_remaining", "field": side})
        for field in ("patch_count", "component_count", "boundary_component_count", "hole_count"):
            if topology.get(field) != expected.get(field):
                failures.append({"kind": "expected_topology", "field": field})
        if operation.get("fuse", {}).get("executed") is not True:
            failures.append({"kind": "fuse"})
    elif operation.get("status") == "UNSUPPORTED_INVALID_REFERENCE_DIRECTION":
        motion = operation.get("motion", {})
        if motion.get("executed_translation_norm_mm") != 0.0 or operation.get("fuse", {}).get("executed") is not False:
            failures.append({"kind": "invalid_reference_fail_closed"})
    return {
        "schema_version": 1,
        "status": "PASS" if not failures else "FAIL",
        "failures": failures,
    }


def actual_geometry_projection(operation: dict[str, Any]) -> dict[str, Any]:
    """Return actual decisions and measurements, excluding expected and byte identity."""
    selected = operation.get("face_sets", {}).get("selected_pair", {})
    partition = operation.get("partition", {})
    return {
        "status": operation.get("status"),
        "reference_direction": operation.get("reference_direction"),
        "gap_mm": selected.get("gap_mm"),
        "face_sets": {
            side: selected.get(side) for side in ("Side_1", "Side_2")
        },
        "motion": operation.get("motion"),
        "partition": {
            key: partition.get(key)
            for key in (
                "common_area_mm2", "coverage", "remaining_area_mm2",
                "remaining_empty", "common_patches", "member_level_partition",
            )
        },
        "topology": operation.get("topology"),
        "fuse": operation.get("fuse"),
        "provenance": operation.get("provenance"),
    }


def validate_published_artifacts(
    operation: dict[str, Any], artifact_root: Path
) -> dict[str, Any]:
    """Validate exact bytes separately; never infer geometric inequality from a hash."""
    recorded = operation.get("artifact_sha256", {})
    required = set(_artifact_names(operation.get("artifacts", {})))
    manifest_complete = isinstance(recorded, dict) and set(recorded) == required
    failures = []
    for name in sorted(required):
        path = Path(artifact_root) / name
        actual = "sha256:" + sha256_file(path) if path.is_file() else None
        if actual != recorded.get(name):
            failures.append({"artifact": name, "recorded": recorded.get(name), "actual": actual})
    byte_status = "PASS" if manifest_complete and not failures else "FAIL"
    return {
        "artifact_byte_integrity": byte_status,
        "geometric_equivalence": (
            "NOT_REEVALUATED" if byte_status == "PASS"
            else "NOT_EVALUATED_INVALID_ARTIFACT"
        ),
        "hash_used_as_geometry_predicate": False,
        "manifest_complete": manifest_complete,
        "failures": failures,
    }


def validate_covariance(
    operation: dict[str, Any],
    generation: dict[str, Any],
    base_operation: dict[str, Any] | None = None,
    *,
    geometry_equivalence: str | dict[str, Any] | None = None,
) -> dict[str, Any]:
    failures: list[dict[str, Any]] = []
    rotation = validate_rotation_matrix(generation.get("rotation_matrix"))
    if rotation["status"] != "PASS":
        failures.append({"kind": "invalid_proper_rotation"})
    if base_operation is not None:
        base_reference = base_operation.get("reference_direction", {}).get(
            "normalized_reference_direction"
        )
        if not isinstance(base_reference, list):
            base_reference = base_operation.get("face_sets", {}).get(
                "selected_pair", {}
            ).get("Side_1", {}).get("reference_normal")
    else:
        base_reference = [0.0, 0.0, 1.0]
    if (
        not isinstance(base_reference, list)
        or len(base_reference) != 3
        or not all(_finite_number(value) for value in base_reference)
    ):
        failures.append({"kind": "invalid_base_reference_direction"})
        base_reference = []
    matrix = generation.get("rotation_matrix", [])
    transformed_reference = [sum(matrix[i][j] * base_reference[j] for j in range(3)) for i in range(3)] if rotation["status"] == "PASS" and base_reference else []
    actual_reference = operation.get("reference_direction", {}).get("normalized_reference_direction")
    if len(transformed_reference) != 3 or not isinstance(actual_reference, list) or any(
        not _close(a, b, RULES["linear_epsilon_mm"])
        for a, b in zip(actual_reference or [], transformed_reference)
    ):
        failures.append({"kind": "reference_direction_covariance"})
    if base_operation is not None:
        base_translation = base_operation.get("motion", {}).get(
            "executed_translation_mm"
        )
    else:
        gap = operation.get("face_sets", {}).get("selected_pair", {}).get("gap_mm")
        base_translation = [0.0, 0.0, -float(gap)] if _finite_number(gap) else []
    if (
        not isinstance(base_translation, list)
        or len(base_translation) != 3
        or not all(_finite_number(value) for value in base_translation)
    ):
        failures.append({"kind": "invalid_base_translation"})
        base_translation = []
    transformed_translation = [sum(matrix[i][j] * base_translation[j] for j in range(3)) for i in range(3)] if base_translation and rotation["status"] == "PASS" else []
    actual_translation = operation.get("motion", {}).get("executed_translation_mm")
    if len(transformed_translation) != 3 or not isinstance(actual_translation, list) or any(
        not _close(a, b, RULES["linear_epsilon_mm"])
        for a, b in zip(actual_translation or [], transformed_translation)
    ):
        failures.append({"kind": "translation_covariance"})
    q = generation.get("translation_vector")
    q_valid = isinstance(q, list) and len(q) == 3 and all(_finite_number(value) for value in q)
    if not q_valid:
        failures.append({"kind": "invalid_rigid_translation"})
    normal_status = "NOT_EVALUATED"
    centroid_statuses: dict[str, str] = {}
    if base_operation is not None and rotation["status"] == "PASS":
        def rotate(vector):
            return [sum(matrix[i][j] * float(vector[j]) for j in range(3)) for i in range(3)]

        def vectors_match_as_multiset(expected_vectors, actual_vectors):
            if len(expected_vectors) != len(actual_vectors):
                return False
            unused = list(range(len(actual_vectors)))
            for expected_vector in expected_vectors:
                match = next(
                    (
                        index for index in unused
                        if all(
                            _close(expected_vector[axis], actual_vectors[index][axis], RULES["linear_epsilon_mm"])
                            for axis in range(3)
                        )
                    ),
                    None,
                )
                if match is None:
                    return False
                unused.remove(match)
            return not unused

        normal_ok = True
        for side in ("Side_1", "Side_2"):
            base_descriptors = base_operation.get("face_sets", {}).get("selected_pair", {}).get(side, {}).get("member_face_descriptors", [])
            actual_descriptors = operation.get("face_sets", {}).get("selected_pair", {}).get(side, {}).get("member_face_descriptors", [])
            base_normals = [item.get("outward_normal") for item in base_descriptors]
            actual_normals = [item.get("outward_normal") for item in actual_descriptors]
            if any(not isinstance(vector, list) or len(vector) != 3 for vector in base_normals + actual_normals):
                normal_ok = False
                continue
            normal_ok = normal_ok and vectors_match_as_multiset(
                [rotate(vector) for vector in base_normals], actual_normals
            )
        normal_status = "PASS" if normal_ok else "FAIL"
        if not normal_ok:
            failures.append({"kind": "normal_vector_covariance"})

        centroid_paths = {
            "Side_1": ("body_evidence", "Side_1", "centroid_mm"),
            "Side_2_before": ("body_evidence", "Side_2_before", "centroid_mm"),
            "Side_2_after": ("body_evidence", "Side_2_after", "centroid_mm"),
            "Common": ("partition", "common_centroid_mm"),
            "Fused": ("fuse", "centroid_mm"),
        }
        def vector_at(source, path):
            for key in path:
                source = source.get(key) if isinstance(source, dict) else None
            return source
        for name, path in centroid_paths.items():
            base_centroid = vector_at(base_operation, path)
            actual_centroid = vector_at(operation, path)
            passed = bool(
                q_valid
                and isinstance(base_centroid, list) and len(base_centroid) == 3
                and isinstance(actual_centroid, list) and len(actual_centroid) == 3
                and all(_finite_number(value) for value in base_centroid + actual_centroid)
                and all(
                    _close(rotate(base_centroid)[axis] + float(q[axis]), actual_centroid[axis], RULES["linear_epsilon_mm"])
                    for axis in range(3)
                )
            )
            centroid_statuses[name] = "PASS" if passed else "FAIL"
            if not passed:
                failures.append({"kind": "centroid_covariance", "field": name})
    scalar_invariants = {}
    topology_invariants = {}
    if base_operation is not None:
        scalar_paths = {
            "gap": ("face_sets", "selected_pair", "gap_mm", RULES["linear_epsilon_mm"]),
            "common_area": ("partition", "common_area_mm2", RULES["area_epsilon_mm2"]),
            "coverage_side_1": ("partition", "coverage", "Side_1", 1.0e-7),
            "coverage_side_2": ("partition", "coverage", "Side_2", 1.0e-7),
            "remaining_side_1": ("partition", "remaining_area_mm2", "Side_1", RULES["area_epsilon_mm2"]),
            "remaining_side_2": ("partition", "remaining_area_mm2", "Side_2", RULES["area_epsilon_mm2"]),
            "fused_volume": ("fuse", "volume_mm3", RULES["volume_epsilon_mm3"]),
        }
        def lookup(source, path):
            for key in path:
                source = source.get(key) if isinstance(source, dict) else None
            return source
        for name, path_and_epsilon in scalar_paths.items():
            *path, tolerance = path_and_epsilon
            passed = _close(lookup(operation, path), lookup(base_operation, path), tolerance)
            scalar_invariants[name] = "PASS" if passed else "FAIL"
            if not passed:
                failures.append({"kind": "scalar_covariance", "field": name})
        for field in ("patch_count", "component_count", "boundary_component_count", "hole_count", "first_betti_number"):
            passed = operation.get("topology", {}).get(field) == base_operation.get("topology", {}).get(field)
            topology_invariants[field] = "PASS" if passed else "FAIL"
            if not passed:
                failures.append({"kind": "topology_covariance", "field": field})
        if operation.get("fuse", {}).get("executed") != base_operation.get("fuse", {}).get("executed"):
            failures.append({"kind": "fuse_status_covariance"})
    geometry_status = (
        geometry_equivalence.get("geometric_equivalence")
        if isinstance(geometry_equivalence, dict)
        else geometry_equivalence
    )
    if geometry_status is not None and geometry_status != "PASS":
        failures.append({"kind": "geometric_equivalence_not_proven"})
    return {
        "schema_version": 1,
        "status": "PASS" if not failures else "FAIL",
        "base_case_id": generation.get("base_case_id"),
        "rotation_matrix": matrix,
        "translation_vector": generation.get("translation_vector"),
        "rotation_validity": rotation,
        "base_reference_direction": base_reference,
        "transformed_reference_direction": transformed_reference,
        "vector_covariants": {
            "reference_direction": "PASS" if not any(item["kind"] == "reference_direction_covariance" for item in failures) else "FAIL",
            "executed_translation": "PASS" if not any(item["kind"] == "translation_covariance" for item in failures) else "FAIL",
            "normal_vectors": normal_status,
            "centroids": centroid_statuses,
        },
        "scalar_invariants": scalar_invariants,
        "topology_invariants": topology_invariants,
        "representation_identity": (
            geometry_equivalence.get("representation_identity", "NOT_USED_FOR_GEOMETRIC_ACCEPTANCE")
            if isinstance(geometry_equivalence, dict)
            else "NOT_USED_FOR_GEOMETRIC_ACCEPTANCE"
        ),
        "geometric_equivalence": geometry_status or "NOT_YET_PROVEN",
        "geometry_equivalence_details": (
            geometry_equivalence.get("geometry_equivalence_details", {})
            if isinstance(geometry_equivalence, dict)
            else {}
        ),
        "failures": failures,
    }


def run_orientation_case(
    fixture_root: Path,
    scenario_id: str,
    output_root: Path,
    *,
    create_view: bool = False,
    traversal_order: str = "normal",
    reference_direction_override: Any = _USE_FIXTURE_REFERENCE,
) -> dict[str, Any]:
    case = Path(fixture_root) / scenario_id
    output_root = Path(output_root)
    output_root.mkdir(parents=True, exist_ok=True)
    policy = read_json(case / "operation_policy.json")
    expected = read_json(case / "expected.json")
    semantics = read_json(case / "orientation_semantics.json")
    generation = read_json(case / "generation_manifest.json")
    reference = semantics["reference_direction"] if reference_direction_override is _USE_FIXTURE_REFERENCE else reference_direction_override
    staged = Path(tempfile.mkdtemp(prefix=f".{scenario_id}-06d-", dir=output_root))
    base_staged = Path(tempfile.mkdtemp(prefix=f".{scenario_id}-06d-base-", dir=output_root))
    base_operation = _run_freecad(
        {
            "action": "analyze",
            "scenario_id": scenario_id,
            "step_path": str(case / "base_inputs.step"),
            "reference_direction": [0.0, 0.0, 1.0],
            "policy": policy,
            "rules": RULES,
            "output_dir": str(base_staged),
            "create_view": False,
            "traversal_order": traversal_order,
        }
    )["operation"]
    response = _run_freecad(
        {
            "action": "analyze",
            "scenario_id": scenario_id,
            "step_path": str(case / "inputs.step"),
            "reference_direction": reference,
            "policy": policy,
            "rules": RULES,
            "output_dir": str(staged),
            "create_view": create_view,
            "traversal_order": traversal_order,
        }
    )
    operation = response["operation"]
    operation.setdefault("reference_direction", {
        "raw_reference_direction": reference,
        "normalized_reference_direction": normalize_reference_direction(reference),
        "original_norm": math.sqrt(sum(float(x) ** 2 for x in reference)) if normalize_reference_direction(reference) is not None else None,
    })
    if create_view and (staged / "operation_debug.FCStd").is_file():
        operation["view_reopen"] = _apply_visibility_profile(
            staged / "operation_debug.FCStd",
            ["Reference_Direction", "Reference_Vector", "Fused_Result", "Fused_Solid"],
        )
    artifacts = operation.get("artifacts", {})
    names = _artifact_names(artifacts)
    if create_view and (staged / "operation_debug.FCStd").is_file():
        names.append("operation_debug.FCStd")
    operation["artifact_sha256"] = {
        name: "sha256:" + sha256_file(staged / name) for name in sorted(set(names))
    }
    if operation.get("status") == "SUPPORTED_UNIQUE_INTERFACE_FACESET":
        verification = _run_freecad(
            {
                "action": "verify_artifacts",
                "output_dir": str(staged),
                "artifacts": artifacts,
                "rules": RULES,
                "reference_direction": reference,
            }
        )
        operation["artifact_verification"] = {
            key: value for key, value in verification.items() if key != "status"
        }
    operation["input_step_sha256"] = "sha256:" + sha256_file(case / "inputs.step")
    operation["policy"] = policy
    operation["validator_version"] = "06D"
    validation = validate_orientation_evidence(operation, expected)
    geometry_equivalence = None
    if (
        operation.get("status") == "SUPPORTED_UNIQUE_INTERFACE_FACESET"
        and base_operation.get("status") == "SUPPORTED_UNIQUE_INTERFACE_FACESET"
    ):
        geometry_response = _run_freecad(
            {
                "action": "validate_covariance_artifacts",
                "base_output_dir": str(base_staged),
                "transformed_output_dir": str(staged),
                "base_artifacts": base_operation.get("artifacts", {}),
                "transformed_artifacts": operation.get("artifacts", {}),
                "rotation_matrix": generation["rotation_matrix"],
                "translation_vector": generation["translation_vector"],
                "rules": RULES,
            }
        )
        geometry_equivalence = {
            key: value for key, value in geometry_response.items() if key != "status"
        }
    covariance = validate_covariance(
        operation, generation, base_operation, geometry_equivalence=geometry_equivalence
    )
    if covariance["status"] != "PASS":
        validation["failures"].append({"kind": "covariance"})
        validation["status"] = "FAIL"
    for name, value in (
        ("operation.json", operation),
        ("validation.json", validation),
        ("covariance.json", covariance),
        ("facesets.json", operation.get("face_sets", {})),
        ("patches.json", operation.get("partition", {}).get("common_patches", [])),
        ("components.json", operation.get("topology", {})),
        ("provenance.json", operation.get("provenance", {})),
    ):
        write_json(staged / name, value)
    target = output_root / scenario_id
    if target.exists():
        shutil.rmtree(target)
    staged.replace(target)
    shutil.rmtree(base_staged)
    return {
        "operation": operation,
        "validation": validation,
        "covariance": covariance,
        "expected": expected,
        "generation": generation,
        "base_operation": base_operation,
        "output_dir": str(target),
    }


def run_translation_only_control(root: Path) -> dict[str, Any]:
    """Run P07 at two world origins and compare only relative geometry evidence."""
    root = Path(root) / "translation_only_control"
    root.mkdir(parents=True, exist_ok=True)
    base_step = root / "base_inputs.step"
    translated_step = root / "translated_inputs.step"
    _run_freecad(
        {
            "action": "generate",
            "scenario_id": "D01",
            "step_path": str(base_step),
            "apply_transform": False,
        }
    )
    _run_freecad(
        {
            "action": "generate",
            "scenario_id": "D01",
            "step_path": str(translated_step),
            "translation_only": True,
        }
    )

    def analyze(name: str, step: Path) -> dict[str, Any]:
        return _run_freecad(
            {
                "action": "analyze",
                "scenario_id": "D05",
                "step_path": str(step),
                "reference_direction": [0.0, 0.0, 1.0],
                "policy": POLICY,
                "rules": RULES,
                "output_dir": str(root / name),
                "create_view": False,
                "traversal_order": "normal",
            }
        )["operation"]

    base = analyze("base", base_step)
    translated = analyze("translated", translated_step)
    base_selected = base.get("face_sets", {}).get("selected_pair", {})
    translated_selected = translated.get("face_sets", {}).get("selected_pair", {})

    def topology_projection(operation: dict[str, Any]) -> dict[str, Any]:
        topology = operation.get("topology", {})
        loops = []
        for component in topology.get("components", []):
            for loop in component.get("boundary_loops", []):
                loops.append(
                    {
                        "kind": loop.get("kind"),
                        "length_mm": loop.get("length_mm"),
                        "enclosed_area_mm2": loop.get("enclosed_area_mm2"),
                        "curve_types": loop.get("curve_types"),
                    }
                )
        loops.sort(key=lambda loop: (str(loop["kind"]), float(loop["length_mm"] or 0.0)))
        return {
            key: topology.get(key)
            for key in (
                "patch_count", "component_count", "boundary_component_count",
                "hole_count", "first_betti_number",
            )
        } | {"loops": loops}
    invariants = {
        "gap": _close(base_selected.get("gap_mm"), translated_selected.get("gap_mm"), RULES["linear_epsilon_mm"]),
        "translation": all(
            _close(first, second, RULES["linear_epsilon_mm"])
            for first, second in zip(
                base.get("motion", {}).get("executed_translation_mm", []),
                translated.get("motion", {}).get("executed_translation_mm", []),
            )
        ),
        "common_area": _close(
            base.get("partition", {}).get("common_area_mm2"),
            translated.get("partition", {}).get("common_area_mm2"),
            RULES["area_epsilon_mm2"],
        ),
        "coverage": all(
            _close(
                base.get("partition", {}).get("coverage", {}).get(side),
                translated.get("partition", {}).get("coverage", {}).get(side),
                1.0e-7,
            )
            for side in ("Side_1", "Side_2")
        ),
        "topology": topology_projection(base) == topology_projection(translated),
    }
    evidence = {
        "schema_version": 1,
        "status": "PASS" if all(invariants.values()) else "FAIL",
        "world_translation_mm": [1000.0, -700.0, 250.0],
        "base_support_coordinate_mm": base_selected.get("Side_1", {}).get("support_coordinate_mm"),
        "translated_support_coordinate_mm": translated_selected.get("Side_1", {}).get("support_coordinate_mm"),
        "gap_invariant": "PASS" if invariants["gap"] else "FAIL",
        "translation_vector_invariant": "PASS" if invariants["translation"] else "FAIL",
        "common_area_invariant": "PASS" if invariants["common_area"] else "FAIL",
        "coverage_invariant": "PASS" if invariants["coverage"] else "FAIL",
        "topology_invariant": "PASS" if invariants["topology"] else "FAIL",
    }
    write_json(root / "translation_only_covariance.json", evidence)
    return evidence


def compare_orientation_repeatability(
    first: dict[str, Any], second: dict[str, Any]
) -> dict[str, Any]:
    failures = []
    if first.get("status") != second.get("status"):
        failures.append("status")
    for field, tolerance in (
        ("gap_mm", RULES["linear_epsilon_mm"]),
    ):
        if not _close(
            first.get("face_sets", {}).get("selected_pair", {}).get(field),
            second.get("face_sets", {}).get("selected_pair", {}).get(field),
            tolerance,
        ):
            failures.append(field)
    for path, tolerance in (
        (("partition", "common_area_mm2"), RULES["area_epsilon_mm2"]),
        (("fuse", "volume_mm3"), RULES["volume_epsilon_mm3"]),
    ):
        left, right = first, second
        for key in path:
            left = left.get(key) if isinstance(left, dict) else None
            right = right.get(key) if isinstance(right, dict) else None
        if not _close(left, right, tolerance):
            failures.append(".".join(path))
    for side in ("Side_1", "Side_2"):
        for field, tolerance in (
            ("coverage", 1.0e-7),
            ("remaining_area_mm2", RULES["area_epsilon_mm2"]),
        ):
            if not _close(
                first.get("partition", {}).get(field, {}).get(side),
                second.get("partition", {}).get(field, {}).get(side),
                tolerance,
            ):
                failures.append(f"{field}.{side}")
        first_set = first.get("face_sets", {}).get("selected_pair", {}).get(side, {})
        second_set = second.get("face_sets", {}).get("selected_pair", {}).get(side, {})
        if first_set.get("member_face_count") != second_set.get("member_face_count"):
            failures.append(f"faceset_members.{side}")
    for field in (
        "patch_count", "component_count", "boundary_component_count",
        "hole_count", "first_betti_number",
    ):
        if first.get("topology", {}).get(field) != second.get("topology", {}).get(field):
            failures.append("topology." + field)
    def reference_vector(operation: dict[str, Any]) -> list[Any]:
        explicit = operation.get("reference_direction", {}).get(
            "normalized_reference_direction"
        )
        if isinstance(explicit, list):
            return explicit
        legacy = operation.get("face_sets", {}).get("selected_pair", {}).get(
            "Side_1", {}
        ).get("reference_normal")
        return legacy if isinstance(legacy, list) else []

    first_reference = reference_vector(first)
    second_reference = reference_vector(second)
    first_motion = first.get("motion", {}).get("executed_translation_mm", [])
    second_motion = second.get("motion", {}).get("executed_translation_mm", [])
    for name, left, right in (
        ("reference_direction", first_reference, second_reference),
        ("executed_translation", first_motion, second_motion),
    ):
        if len(left) != 3 or len(right) != 3 or any(
            not _close(a, b, RULES["linear_epsilon_mm"]) for a, b in zip(left, right)
        ):
            failures.append(name)
    return {
        "processes": 2,
        "status": "PASS" if not failures else "FAIL",
        "comparison": "NORMALIZED_RELATIONS_AND_UNIT_TOLERANCED_BREP_EVIDENCE",
        "patch_id_used": False,
        "face_ordinal_used": False,
        "representation_hash_used": False,
        "world_aabb_order_used": False,
        "failures": failures,
    }


def run_plus_z_compatibility_control(
    fixture_root: Path, output_root: Path
) -> dict[str, Any]:
    output_root = Path(output_root)
    output_root.mkdir(parents=True, exist_ok=True)
    old = baseline_06c.run_multipatch_case(
        baseline_06c.FIXTURE_ROOT, "P10", output_root / "06c"
    )
    new_dir = output_root / "06d"
    new_dir.mkdir(parents=True, exist_ok=True)
    new_operation = _run_freecad(
        {
            "action": "analyze",
            "scenario_id": "D02_PLUS_Z",
            "step_path": str(Path(fixture_root) / "D02" / "base_inputs.step"),
            "reference_direction": [0.0, 0.0, 1.0],
            "policy": POLICY,
            "rules": RULES,
            "output_dir": str(new_dir),
            "create_view": False,
            "traversal_order": "normal",
        }
    )["operation"]
    geometry = _run_freecad(
        {
            "action": "validate_covariance_artifacts",
            "base_output_dir": old["output_dir"],
            "transformed_output_dir": str(new_dir),
            "base_artifacts": old["operation"]["artifacts"],
            "transformed_artifacts": new_operation["artifacts"],
            "rotation_matrix": [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]],
            "translation_vector": [0.0, 0.0, 0.0],
            "rules": RULES,
        }
    )
    comparison = compare_orientation_repeatability(old["operation"], new_operation)
    evidence = {
        "schema_version": 1,
        "status": "PASS" if comparison["status"] == "PASS" and geometry["geometric_equivalence"] == "PASS" else "FAIL",
        "reference_direction": [0.0, 0.0, 1.0],
        "06c_scenario": "P10",
        "06d_scenario": "D02_PLUS_Z",
        "numeric_and_topology_comparison": comparison,
        "geometric_equivalence": geometry["geometric_equivalence"],
        "geometry_equivalence_details": geometry["geometry_equivalence_details"],
        "representation_identity": geometry["representation_identity"],
    }
    write_json(output_root / "plus_z_compatibility.json", evidence)
    return evidence


def run_reference_direction_controls(
    fixture_root: Path, output_root: Path
) -> dict[str, Any]:
    output_root = Path(output_root)
    output_root.mkdir(parents=True, exist_ok=True)
    case = Path(fixture_root) / "D01"
    policy = read_json(case / "operation_policy.json")
    invalid_values = {
        "missing": _USE_FIXTURE_REFERENCE,
        "zero": [0.0, 0.0, 0.0],
        "nan": [math.nan, 0.0, 1.0],
        "inf": [math.inf, 0.0, 1.0],
        "bool": [True, 0.0, 1.0],
        "wrong_length": [0.0, 1.0],
    }
    rows = {}
    for name, value in invalid_values.items():
        request = {
            "action": "analyze",
            "scenario_id": "D04_" + name,
            "step_path": str(case / "inputs.step"),
            "policy": policy,
            "rules": RULES,
            "output_dir": str(output_root / name),
            "create_view": False,
            "traversal_order": "normal",
        }
        if value is not _USE_FIXTURE_REFERENCE:
            request["reference_direction"] = value
        operation = _run_freecad(request)["operation"]
        passed = (
            operation.get("status") == "UNSUPPORTED_INVALID_REFERENCE_DIRECTION"
            and operation.get("motion", {}).get("executed_translation_norm_mm") == 0.0
            and operation.get("fuse", {}).get("executed") is False
        )
        rows[name] = {"status": "PASS" if passed else "FAIL", "operation_status": operation.get("status")}
    direction = read_json(case / "orientation_semantics.json")["reference_direction"]
    reversed_operation = _run_freecad(
        {
            "action": "analyze",
            "scenario_id": "D04_reversed",
            "step_path": str(case / "inputs.step"),
            "reference_direction": [-value for value in direction],
            "policy": policy,
            "rules": RULES,
            "output_dir": str(output_root / "reversed"),
            "create_view": False,
            "traversal_order": "normal",
        }
    )["operation"]
    reversed_passed = (
        reversed_operation.get("status") != "SUPPORTED_UNIQUE_INTERFACE_FACESET"
        and reversed_operation.get("motion", {}).get("executed_translation_norm_mm") == 0.0
        and reversed_operation.get("fuse", {}).get("executed") is False
    )
    rows["reversed"] = {
        "status": "PASS" if reversed_passed else "FAIL",
        "operation_status": reversed_operation.get("status"),
        "auto_flip_used": False,
    }
    summary = {
        "schema_version": 1,
        "status": "PASS" if all(row["status"] == "PASS" for row in rows.values()) else "FAIL",
        "controls": rows,
    }
    write_json(output_root / "reference_direction_controls.json", summary)
    return summary


def run_orientation_suite(fixture_root: Path, output_root: Path) -> dict[str, Any]:
    output_root = Path(output_root)
    results = {
        scenario: run_orientation_case(
            fixture_root, scenario, output_root, create_view=True
        )
        for scenario in ("D01", "D02", "D03")
    }
    repeatability = {}
    for scenario, first in results.items():
        second = run_orientation_case(
            fixture_root,
            scenario,
            output_root / "repeatability" / "second_process",
            traversal_order="reverse",
        )
        comparison = compare_orientation_repeatability(
            first["operation"], second["operation"]
        )
        repeatability[scenario] = {
            "processes": 2,
            "status": comparison["status"],
        }
        write_json(output_root / scenario / "repeatability.json", comparison)
    controls_root = output_root / "controls"
    translation = run_translation_only_control(controls_root)
    compatibility = run_plus_z_compatibility_control(fixture_root, controls_root / "plus_z")
    reference_controls = run_reference_direction_controls(
        fixture_root, controls_root / "reference_direction"
    )
    summary = {
        "schema_version": 1,
        "status": "PASS" if (
            all(result["validation"]["status"] == "PASS" for result in results.values())
            and all(item["status"] == "PASS" for item in repeatability.values())
            and translation["status"] == compatibility["status"] == reference_controls["status"] == "PASS"
        ) else "FAIL",
        "scenarios": {
            scenario: result["operation"]["status"]
            for scenario, result in results.items()
        },
        "repeatability": repeatability,
        "controls": {
            "translation_only": translation["status"],
            "plus_z_compatibility": compatibility["status"],
            "reference_direction": reference_controls["status"],
        },
    }
    write_json(output_root / "summary.json", summary)
    (output_root / "VIEW_INDEX.md").write_text(
        "# 06D 任意朝向平面接口查看指南\n\n"
        "- D01：45° 部分覆盖；默认显示 `Fused_Result` 与 `Reference_Direction`。\n"
        "- D02：normalize([1,2,3]) 加 37° roll；查看两个 Common/Components。\n"
        "- D03：generic rotation 下的解析 annulus；查看两个 Boundary Loops 与中心孔。\n"
        "- `Reference_Vector` 为 `DISPLAY_ONLY`，几何运算只读取 operation semantics。\n",
        encoding="utf-8",
    )
    return summary


def _main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("generate", "run", "case"))
    parser.add_argument("root", type=Path)
    parser.add_argument("--scenario", default="D01")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.action == "generate":
        generate_orientation_fixtures(args.root)
        return
    if args.output is None:
        parser.error("--output is required for run/case")
    report = (
        run_orientation_suite(args.root, args.output)
        if args.action == "run"
        else run_orientation_case(args.root, args.scenario, args.output)
    )
    status = report.get("status") or report.get("validation", {}).get("status")
    if status != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    _main()
