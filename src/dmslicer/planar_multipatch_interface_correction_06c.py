"""06C: evidence-first correction of planar multi-patch interface face sets."""

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
FIXTURE_ROOT = REPO_ROOT / "benchmarks" / "planar_multipatch_interface_correction_06c"
FREECAD_SCRIPT = Path(__file__).with_name(
    "freecad_planar_multipatch_interface_correction_06c.py"
)
VISIBILITY_SCRIPT = Path(__file__).with_name("freecad_visibility_profile_06c.py")
RULES = {
    "linear_epsilon_mm": 1e-7,
    "area_epsilon_mm2": 1e-8,
    "volume_epsilon_mm3": 1e-6,
}
POLICY = {
    "schema_version": 1,
    "policy_valid": True,
    "allow_motion": True,
    "tauE_mm": 0.1,
    "max_translation_mm": 0.1,
}
SCENARIOS: dict[str, dict[str, Any]] = {
    "P10": {
        "status": "SUPPORTED_UNIQUE_INTERFACE_FACESET",
        "common_area_mm2": 384.0,
        "patch_count": 2,
        "component_count": 2,
        "boundary_component_count": 2,
        "hole_count": 0,
        "coverage": {"Side_1": 0.16, "Side_2": 1.0},
        "remaining_area_mm2": {"Side_1": 2016.0, "Side_2": 0.0},
        "candidate_face_set_pair_count": 1,
    },
    "P11": {
        "status": "SUPPORTED_UNIQUE_INTERFACE_FACESET",
        "common_area_mm2": 300.0 * math.pi,
        "patch_count": 1,
        "component_count": 1,
        "boundary_component_count": 2,
        "hole_count": 1,
        "coverage": {"Side_1": math.pi / 12.0, "Side_2": 1.0},
        "remaining_area_mm2": {
            "Side_1": 3600.0 - 300.0 * math.pi,
            "Side_2": 0.0,
        },
        "candidate_face_set_pair_count": 1,
    },
    "P12": {
        "status": "UNSUPPORTED_AMBIGUOUS_INTERFACE_SET",
        "candidate_face_set_pair_count": 2,
        "candidate_gaps_mm": [0.05, 0.08],
        "candidate_common_areas_mm2": [192.0, 192.0],
    },
}


def _freecad_executable() -> Path:
    discovered = shutil.which("freecadcmd") or shutil.which("FreeCADCmd.exe")
    candidates = (
        Path(discovered) if discovered else None,
        Path(r"C:\Program Files\FreeCAD 1.1\bin\freecadcmd.exe"),
    )
    for candidate in candidates:
        if candidate and candidate.is_file():
            return candidate
    raise FileNotFoundError("FreeCADCmd.exe was not found")


def _run_freecad(request: dict[str, Any]) -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="dmslicer_multipatch_06c_") as temporary:
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
                "FreeCADCmd did not write a response; "
                f"exit={result.returncode}; stdout={result.stdout}; stderr={result.stderr}"
            )
        response = read_json(response_path)
        if result.returncode or response.get("status") == "FAILED":
            raise RuntimeError(
                f"FreeCADCmd 06C failed; exit={result.returncode}; response={response}; "
                f"stdout={result.stdout}; stderr={result.stderr}"
            )
        return response


def _apply_visibility_profile(fcstd_path: Path, visible_objects: list[str]) -> dict[str, Any]:
    gui_executable = _freecad_executable().with_name("FreeCAD.exe")
    if not gui_executable.is_file():
        raise FileNotFoundError("FreeCAD.exe was not found for persisted GUI visibility")
    with tempfile.TemporaryDirectory(prefix="dmslicer_visibility_06c_") as temporary:
        request_path = Path(temporary) / "request.json"
        response_path = Path(temporary) / "response.json"
        write_json(
            request_path,
            {"fcstd_path": str(fcstd_path), "visible_objects": visible_objects},
        )
        environment = os.environ.copy()
        environment.update(
            {
                "DMSLICER_VISIBILITY_REQUEST": str(request_path),
                "DMSLICER_VISIBILITY_RESPONSE": str(response_path),
            }
        )
        startupinfo = None
        if os.name == "nt":
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = subprocess.SW_HIDE
        result = subprocess.run(
            [str(gui_executable), "--safe-mode", str(VISIBILITY_SCRIPT)],
            env=environment,
            text=True,
            capture_output=True,
            timeout=180,
            check=False,
            startupinfo=startupinfo,
        )
        if not response_path.is_file():
            raise RuntimeError(
                "FreeCAD GUI visibility helper did not write a response; "
                f"exit={result.returncode}; stdout={result.stdout}; stderr={result.stderr}"
            )
        response = read_json(response_path)
        if result.returncode or response.get("status") != "SUCCEEDED" or response.get("profile_matches") is not True:
            raise RuntimeError(
                f"FreeCAD GUI visibility profile failed; exit={result.returncode}; "
                f"response={response}; stdout={result.stdout}; stderr={result.stderr}"
            )
        return {key: value for key, value in response.items() if key != "status"}


def _source_commit() -> str | None:
    result = subprocess.run(
        ["git", "-C", str(REPO_ROOT), "rev-parse", "HEAD"],
        text=True,
        capture_output=True,
        check=False,
    )
    return result.stdout.strip() if result.returncode == 0 else None


def _artifact_names(value: Any) -> list[str]:
    if isinstance(value, str):
        return [] if value == "EMPTY" else [value]
    if isinstance(value, list):
        return [name for item in value for name in _artifact_names(item)]
    if isinstance(value, dict):
        return [name for item in value.values() for name in _artifact_names(item)]
    return []


def _comparison_epsilon(path: tuple[str, ...]) -> float:
    field = ".".join(path).lower()
    if "volume" in field:
        return RULES["volume_epsilon_mm3"]
    if "area" in field:
        return RULES["area_epsilon_mm2"]
    if "coverage" in field:
        return 1.0e-7
    if any(
        token in field
        for token in ("_mm", "length", "gap", "support", "distance", "spread", "normal")
    ):
        return RULES["linear_epsilon_mm"]
    return 0.0


def _semantic_equal(first: Any, second: Any, path: tuple[str, ...] = ()) -> bool:
    """Compare measured evidence with declared unit tolerances, never hashes."""
    ignored = {
        "representation_identity",
        "artifact_sha256",
        "input_step_sha256",
        "source_step_sha256",
        "validator_source_commit",
    }
    if isinstance(first, bool) or isinstance(second, bool):
        return type(first) is type(second) and first == second
    if isinstance(first, (int, float)) and isinstance(second, (int, float)):
        if not math.isfinite(float(first)) or not math.isfinite(float(second)):
            return False
        epsilon = _comparison_epsilon(path)
        return abs(float(first) - float(second)) <= epsilon
    if isinstance(first, dict) and isinstance(second, dict):
        first_keys = set(first) - ignored
        second_keys = set(second) - ignored
        return first_keys == second_keys and all(
            _semantic_equal(first[key], second[key], path + (str(key),))
            for key in first_keys
        )
    if isinstance(first, list) and isinstance(second, list):
        return len(first) == len(second) and all(
            _semantic_equal(left, right, path + (str(index),))
            for index, (left, right) in enumerate(zip(first, second))
        )
    return type(first) is type(second) and first == second


def compare_multipatch_repeatability(
    first: dict[str, Any], second: dict[str, Any]
) -> dict[str, Any]:
    equivalent = _semantic_equal(
        _repeatable_projection(first), _repeatable_projection(second)
    )
    return {
        "status": "PASS" if equivalent else "FAIL",
        "comparison": "UNIT_TOLERANCED_GEOMETRY_AND_TOPOLOGY_EVIDENCE",
        "representation_hash_used": False,
    }


def generate_multipatch_fixtures(root: Path) -> dict[str, Any]:
    """Generate independent STEP, construction, policy, and analytic truth bundles."""
    root = Path(root)
    rows = []
    for scenario_id in ("P10", "P11", "P12"):
        case = root / scenario_id
        case.mkdir(parents=True, exist_ok=True)
        step = case / "inputs.step"
        generation = _run_freecad(
            {"action": "generate", "scenario_id": scenario_id, "step_path": str(step)}
        )
        expected = {
            "schema_version": 1,
            "scenario_id": scenario_id,
            "numeric_rules": RULES,
            **SCENARIOS[scenario_id],
        }
        parameters = {
            "schema_version": 1,
            "scenario_id": scenario_id,
            "units": "mm",
            "construction": generation["construction"],
            "truth_source": "analytic_dimensions_not_production_geometry",
        }
        write_json(case / "parameters.json", parameters)
        write_json(case / "policy.json", POLICY)
        write_json(case / "expected.json", expected)
        rows.append(
            {
                "scenario_id": scenario_id,
                "step_sha256": "sha256:" + sha256_file(step),
                "status": expected["status"],
            }
        )
    manifest = {
        "schema_version": 1,
        "operation": "PLANAR_MULTIPATCH_INTERFACE_CORRECTION_06C",
        "numeric_rules": RULES,
        "scenarios": rows,
    }
    write_json(root / "manifest.json", manifest)
    return manifest


def _finite(value: Any) -> bool:
    return type(value) in {int, float} and math.isfinite(float(value))


def _number(
    failures: list[dict[str, Any]],
    value: Any,
    field: str,
    *,
    nonnegative: bool = False,
) -> float | None:
    if not _finite(value):
        failures.append({"kind": "invalid_numeric", "field": field, "actual": value})
        return None
    result = float(value)
    if nonnegative and result < 0:
        failures.append({"kind": "numeric_constraint", "field": field, "actual": value})
    return result


def _close(actual: Any, expected: Any, tolerance: float) -> bool:
    return _finite(actual) and _finite(expected) and abs(float(actual) - float(expected)) <= tolerance


def _validate_expected(
    failures: list[dict[str, Any]], operation: dict[str, Any], expected: dict[str, Any]
) -> None:
    if operation.get("status") != expected.get("status"):
        failures.append(
            {"kind": "expected_status", "expected": expected.get("status"), "actual": operation.get("status")}
        )
    faces = operation.get("face_sets", {})
    expected_candidates = expected.get("candidate_face_set_pair_count")
    if expected_candidates is not None and faces.get("candidate_face_set_pair_count") != expected_candidates:
        failures.append({"kind": "expected_candidate_count"})
    if operation.get("status") != "SUPPORTED_UNIQUE_INTERFACE_FACESET":
        return
    partition = operation.get("partition", {})
    topology = operation.get("topology", {})
    area_epsilon = RULES["area_epsilon_mm2"]
    if "common_area_mm2" in expected and not _close(
        partition.get("common_area_mm2"), expected["common_area_mm2"], area_epsilon
    ):
        failures.append({"kind": "expected_common_area"})
    for key in ("patch_count", "component_count", "boundary_component_count", "hole_count"):
        if key in expected and topology.get(key) != expected[key]:
            failures.append({"kind": "expected_topology", "field": key})
    for side in ("Side_1", "Side_2"):
        if side in expected.get("coverage", {}) and not _close(
            partition.get("coverage", {}).get(side), expected["coverage"][side], 1e-7
        ):
            failures.append({"kind": "expected_coverage", "field": side})
        if side in expected.get("remaining_area_mm2", {}) and not _close(
            partition.get("remaining_area_mm2", {}).get(side),
            expected["remaining_area_mm2"][side],
            area_epsilon,
        ):
            failures.append({"kind": "expected_remaining", "field": side})


def _validate_faceset_record(
    failures: list[dict[str, Any]], record: dict[str, Any], field: str, linear: float, area_epsilon: float
) -> None:
    descriptors = record.get("member_face_descriptors")
    if not isinstance(descriptors, list) or not descriptors:
        failures.append({"kind": "faceset_members", "field": field})
        return
    if record.get("member_face_count") != len(descriptors):
        failures.append({"kind": "faceset_member_count", "field": field})
    labels = [descriptor.get("human_face_label") for descriptor in descriptors]
    member_ids = [descriptor.get("member_id") for descriptor in descriptors]
    if record.get("member_faces") != labels:
        failures.append({"kind": "faceset_member_labels", "field": field})
    if (
        any(not isinstance(member_id, str) or not member_id for member_id in member_ids)
        or len(set(member_ids)) != len(member_ids)
    ):
        failures.append({"kind": "faceset_member_ids", "field": field})
    coordinates = []
    areas = []
    for index, descriptor in enumerate(descriptors):
        coordinate = _number(
            failures,
            descriptor.get("support_coordinate_mm"),
            f"{field}.member_face_descriptors.{index}.support_coordinate_mm",
        )
        area = _number(
            failures,
            descriptor.get("area_mm2"),
            f"{field}.member_face_descriptors.{index}.area_mm2",
            nonnegative=True,
        )
        if coordinate is not None:
            coordinates.append(coordinate)
        if area is not None:
            areas.append(area)
        normal = descriptor.get("outward_normal")
        if not isinstance(normal, list) or len(normal) != 3 or not all(_finite(value) for value in normal):
            failures.append({"kind": "faceset_member_normal", "field": field})
    support = _number(failures, record.get("support_coordinate_mm"), f"{field}.support_coordinate_mm")
    spread = _number(failures, record.get("spread_mm"), f"{field}.spread_mm", nonnegative=True)
    total_area = _number(failures, record.get("total_area_mm2"), f"{field}.total_area_mm2", nonnegative=True)
    if coordinates:
        actual_spread = max(coordinates) - min(coordinates)
        if support is None or abs(support - min(coordinates)) > linear:
            failures.append({"kind": "faceset_support_coordinate", "field": field})
        if spread is None or abs(spread - actual_spread) > linear or actual_spread > linear:
            failures.append({"kind": "faceset_spread", "field": field})
        if record.get("member_support_coordinates_mm") != coordinates:
            failures.append({"kind": "faceset_member_supports", "field": field})
    if total_area is None or abs(total_area - sum(areas)) > area_epsilon:
        failures.append({"kind": "faceset_area", "field": field})


def validate_multipatch_evidence(
    operation: dict[str, Any],
    expected: dict[str, Any],
    *,
    artifact_root: Path | None = None,
) -> dict[str, Any]:
    """Validate actual geometry evidence without constructing or selecting geometry."""
    failures: list[dict[str, Any]] = []
    linear = RULES["linear_epsilon_mm"]
    area_epsilon = RULES["area_epsilon_mm2"]
    _validate_expected(failures, operation, expected)
    status = operation.get("status")
    faces = operation.get("face_sets", {})
    candidate_count = faces.get("candidate_face_set_pair_count")
    candidates = faces.get("candidate_pairs")
    if type(candidate_count) is not int or candidate_count < 0:
        failures.append({"kind": "candidate_count"})
    if not isinstance(candidates, list) or candidate_count != len(candidates):
        failures.append({"kind": "candidate_count"})
    for index, candidate in enumerate(candidates or []):
        _number(failures, candidate.get("gap_mm"), f"face_sets.candidate_pairs.{index}.gap_mm", nonnegative=True)
        _number(
            failures,
            candidate.get("prospective_common_area_mm2"),
            f"face_sets.candidate_pairs.{index}.prospective_common_area_mm2",
            nonnegative=True,
        )
        for side in ("Side_1", "Side_2"):
            record = candidate.get(side, {})
            _validate_faceset_record(
                failures,
                record,
                f"face_sets.candidate_pairs.{index}.{side}",
                linear,
                area_epsilon,
            )
            _number(
                failures,
                record.get("support_coordinate_mm"),
                f"face_sets.candidate_pairs.{index}.{side}.support_coordinate_mm",
            )
            _number(
                failures,
                record.get("spread_mm"),
                f"face_sets.candidate_pairs.{index}.{side}.spread_mm",
                nonnegative=True,
            )
    motion = operation.get("motion", {})
    vector = motion.get("executed_translation_mm")
    if not isinstance(vector, list) or len(vector) != 3:
        failures.append({"kind": "invalid_vector", "field": "motion.executed_translation_mm"})
        vector_values = None
    else:
        vector_values = [
            _number(failures, item, f"motion.executed_translation_mm.{index}")
            for index, item in enumerate(vector)
        ]
    norm = _number(
        failures,
        motion.get("executed_translation_norm_mm"),
        "motion.executed_translation_norm_mm",
        nonnegative=True,
    )
    tangent = _number(
        failures,
        motion.get("tangential_translation_norm_mm"),
        "motion.tangential_translation_norm_mm",
        nonnegative=True,
    )
    if vector_values and all(item is not None for item in vector_values):
        calculated_norm = math.sqrt(sum(float(item) ** 2 for item in vector_values))
        calculated_tangent = math.sqrt(float(vector_values[0]) ** 2 + float(vector_values[1]) ** 2)
        if norm is None or abs(calculated_norm - norm) > linear:
            failures.append({"kind": "translation_norm"})
        if tangent is None or calculated_tangent > linear or abs(calculated_tangent - tangent) > linear:
            failures.append({"kind": "tangential_translation"})

    if status == "UNSUPPORTED_AMBIGUOUS_INTERFACE_SET":
        if candidate_count is None or candidate_count <= 1:
            failures.append({"kind": "ambiguity_count"})
        if motion.get("motion_authorized") is not False:
            failures.append({"kind": "rejected_motion"})
        if norm is None or norm > linear:
            failures.append({"kind": "rejected_motion"})
        if operation.get("fuse", {}).get("executed") is not False:
            failures.append({"kind": "rejected_fuse"})
        artifacts = operation.get("artifacts", {})
        if any(key in artifacts for key in ("corrected_assembly_step", "fused_step")):
            failures.append({"kind": "rejected_artifact"})
    elif status == "SUPPORTED_UNIQUE_INTERFACE_FACESET":
        if candidate_count != 1 or faces.get("eligible_face_set_pair_count") != 1:
            failures.append({"kind": "unique_candidate_count"})
        selected = faces.get("selected_pair", {})
        if candidates:
            selected_comparable = dict(selected)
            candidate_comparable = dict(candidates[0])
            selected_comparable["selection_reason"] = candidate_comparable.get("selection_reason")
            if selected_comparable != candidate_comparable:
                failures.append({"kind": "selected_candidate_parity"})
        gap = _number(failures, selected.get("gap_mm"), "face_sets.selected_pair.gap_mm", nonnegative=True)
        spread = _number(
            failures, selected.get("gap_spread_mm"), "face_sets.selected_pair.gap_spread_mm", nonnegative=True
        )
        if spread is None or spread > linear:
            failures.append({"kind": "gap_spread"})
        for side in ("Side_1", "Side_2"):
            record = selected.get(side, {})
            _validate_faceset_record(
                failures,
                record,
                f"face_sets.selected_pair.{side}",
                linear,
                area_epsilon,
            )
            _number(
                failures,
                record.get("support_coordinate_mm"),
                f"face_sets.selected_pair.{side}.support_coordinate_mm",
            )
            member_spread = _number(
                failures,
                record.get("spread_mm"),
                f"face_sets.selected_pair.{side}.spread_mm",
                nonnegative=True,
            )
            if member_spread is None or member_spread > linear:
                failures.append({"kind": "faceset_spread", "field": side})
        first_support = selected.get("Side_1", {}).get("support_coordinate_mm")
        second_support = selected.get("Side_2", {}).get("support_coordinate_mm")
        if gap is not None and _finite(first_support) and _finite(second_support):
            if abs((float(second_support) - float(first_support)) - gap) > linear:
                failures.append({"kind": "gap_support_coordinate_parity"})
        if motion.get("motion_authorized") is not True:
            failures.append({"kind": "authorization"})
        if gap is not None and vector_values and all(item is not None for item in vector_values):
            if any(abs(float(actual) - target) > linear for actual, target in zip(vector_values, (0.0, 0.0, -gap))):
                failures.append({"kind": "translation_direction"})
        partition = operation.get("partition", {})
        common = _number(
            failures, partition.get("common_area_mm2"), "partition.common_area_mm2", nonnegative=True
        )
        patches = partition.get("common_patches")
        if not isinstance(patches, list) or not patches:
            failures.append({"kind": "patches"})
            patches = []
        patch_areas = []
        patch_ids = []
        topology_components = operation.get("topology", {}).get("components", [])
        component_ids = {component.get("component_id") for component in topology_components}
        component_patch_ids = {
            component.get("component_id"): set(component.get("patch_ids", []))
            for component in topology_components
        }
        for index, patch in enumerate(patches):
            patch_area = _number(
                failures, patch.get("area_mm2"), f"partition.common_patches.{index}.area_mm2", nonnegative=True
            )
            if patch_area is not None:
                patch_areas.append(patch_area)
            patch_id = patch.get("patch_id")
            if patch_id != f"Patch_{index + 1}":
                failures.append({"kind": "patch_id", "field": index})
            else:
                patch_ids.append(patch_id)
            if patch.get("component_id") not in component_ids:
                failures.append({"kind": "patch_component_mapping", "field": index})
            elif patch_id not in component_patch_ids.get(patch.get("component_id"), set()):
                failures.append({"kind": "patch_component_mapping", "field": index})
            if not patch.get("source_face_linkage"):
                failures.append({"kind": "patch_source_linkage", "field": index})
        if len(set(patch_ids)) != len(patch_ids):
            failures.append({"kind": "duplicated_common_patch"})
        listed_component_patch_ids = {
            patch_id for values in component_patch_ids.values() for patch_id in values
        }
        if listed_component_patch_ids != set(patch_ids):
            failures.append({"kind": "component_patch_id_parity"})
        if common is None or abs(sum(patch_areas) - common) > area_epsilon:
            failures.append({"kind": "patch_area_sum"})
        provenance_records = operation.get("provenance", {}).get("common_patches", [])
        provenance_by_patch_id = {
            record.get("actual_common_patch_id"): record for record in provenance_records
        }
        if set(provenance_by_patch_id) != set(patch_ids) or len(provenance_records) != len(patches):
            failures.append({"kind": "patch_provenance_parity"})
        for patch in patches:
            provenance_record = provenance_by_patch_id.get(patch.get("patch_id"), {})
            if (
                provenance_record.get("component_id") != patch.get("component_id")
                or provenance_record.get("source_face_member_pair")
                != patch.get("source_face_linkage")
                or provenance_record.get("artifact") != patch.get("artifact")
                or provenance_record.get("artifact_sha256")
                != patch.get("artifact_sha256")
                or operation.get("artifact_sha256", {}).get(patch.get("artifact"))
                != patch.get("artifact_sha256")
            ):
                failures.append({"kind": "patch_provenance_parity"})
            for linkage in patch.get("source_face_linkage", []):
                for side in ("Side_1", "Side_2"):
                    selected_labels = selected.get(side, {}).get("member_faces", [])
                    selected_member_ids = {
                        descriptor.get("member_id")
                        for descriptor in selected.get(side, {}).get(
                            "member_face_descriptors", []
                        )
                    }
                    if linkage.get(side) not in selected_labels:
                        failures.append({"kind": "patch_source_linkage", "field": side})
                    if linkage.get(side + "_member_id") not in selected_member_ids:
                        failures.append({"kind": "patch_source_linkage", "field": side})
        topology = operation.get("topology", {})
        if topology.get("patch_count") != len(patches):
            failures.append({"kind": "patch_count"})
        components = topology.get("components", [])
        if topology.get("component_count") != len(components):
            failures.append({"kind": "component_count"})
        loop_count = 0
        hole_count = 0
        for component_index, component in enumerate(components):
            loops = component.get("boundary_loops", [])
            loop_count += len(loops)
            for loop_index, loop in enumerate(loops):
                _number(
                    failures,
                    loop.get("length_mm"),
                    f"topology.components.{component_index}.boundary_loops.{loop_index}.length_mm",
                    nonnegative=True,
                )
                _number(
                    failures,
                    loop.get("enclosed_area_mm2"),
                    f"topology.components.{component_index}.boundary_loops.{loop_index}.enclosed_area_mm2",
                    nonnegative=True,
                )
                if loop.get("kind") == "hole":
                    hole_count += 1
        if topology.get("boundary_component_count") != loop_count:
            failures.append({"kind": "boundary_loop_count"})
        if topology.get("hole_count") != hole_count or topology.get("first_betti_number") != hole_count:
            failures.append({"kind": "hole_count"})
        for side in ("Side_1", "Side_2"):
            carrier = _number(
                failures, partition.get("carrier_area_mm2", {}).get(side), f"partition.carrier_area_mm2.{side}"
            )
            remaining = _number(
                failures,
                partition.get("remaining_area_mm2", {}).get(side),
                f"partition.remaining_area_mm2.{side}",
                nonnegative=True,
            )
            coverage = _number(
                failures, partition.get("coverage", {}).get(side), f"partition.coverage.{side}"
            )
            if coverage is None or not 0.0 <= coverage <= 1.0:
                failures.append({"kind": "coverage", "field": side})
            if None not in (carrier, common, remaining) and abs(carrier - common - remaining) > area_epsilon:
                failures.append({"kind": "area_conservation", "field": side})
            if carrier and common is not None and coverage is not None and abs(coverage - common / carrier) > 1e-7:
                failures.append({"kind": "coverage_formula", "field": side})
        member_records = partition.get("member_level_partition", [])
        if operation.get("provenance", {}).get("remaining_patches") != member_records:
            failures.append({"kind": "remaining_provenance_parity"})
        expected_members = {
            (
                side,
                descriptor.get("member_id"),
            )
            for side in ("Side_1", "Side_2")
            for descriptor in selected.get(side, {}).get("member_face_descriptors", [])
        }
        recorded_members = {
            (
                record.get("role"),
                record.get("source_member_id"),
            )
            for record in member_records
        }
        if recorded_members != expected_members:
            failures.append({"kind": "member_partition_coverage"})
        for index, record in enumerate(member_records):
            area = _number(
                failures,
                record.get("area_mm2"),
                f"partition.member_level_partition.{index}.area_mm2",
                nonnegative=True,
            )
            status_value = record.get("status")
            if status_value not in {"EMPTY", "NONEMPTY"}:
                failures.append({"kind": "member_partition_status", "field": index})
            if status_value == "EMPTY" and (area != 0.0 or record.get("result_patch_id") is not None):
                failures.append({"kind": "member_partition_empty", "field": index})
            if status_value == "NONEMPTY" and not record.get("result_patch_id"):
                failures.append({"kind": "member_partition_result", "field": index})
            linked = record.get("linked_patch_ids")
            if not isinstance(linked, list) or not linked or not set(linked) <= set(patch_ids):
                failures.append({"kind": "member_partition_linkage", "field": index})
        for side in ("Side_1", "Side_2"):
            recorded_area = sum(
                float(record["area_mm2"])
                for record in member_records
                if record.get("role") == side and _finite(record.get("area_mm2"))
            )
            expected_area = partition.get("remaining_area_mm2", {}).get(side)
            if not _finite(expected_area) or abs(recorded_area - float(expected_area)) > area_epsilon:
                failures.append({"kind": "member_partition_area", "field": side})
        spatial = partition.get("spatial_validation", {})
        for side in ("Side_1", "Side_2"):
            record = spatial.get(side, {})
            for name in ("common_remaining_overlap_area_mm2", "coverage_missing_area_mm2", "outside_area_mm2"):
                value = _number(failures, record.get(name), f"partition.spatial_validation.{side}.{name}", nonnegative=True)
                if value is None or value > area_epsilon:
                    failures.append({"kind": "spatial_partition", "field": f"{side}.{name}"})
        fuse = operation.get("fuse", {})
        if not (
            fuse.get("executed") is True
            and fuse.get("solid_count") == 1
            and fuse.get("valid") is True
            and fuse.get("closed") is True
        ):
            failures.append({"kind": "fuse"})
        volume_error = _number(
            failures, fuse.get("volume_conservation_error_mm3"), "fuse.volume_conservation_error_mm3", nonnegative=True
        )
        boundary_overlap = _number(
            failures, fuse.get("boundary_overlap_area_mm2"), "fuse.boundary_overlap_area_mm2", nonnegative=True
        )
        if volume_error is None or volume_error > RULES["volume_epsilon_mm3"]:
            failures.append({"kind": "volume_conservation"})
        if boundary_overlap is None or boundary_overlap > area_epsilon:
            failures.append({"kind": "fused_interface_boundary"})
        reimport = operation.get("step_reimport", {}).get("corrected_assembly", {})
        residual = _number(
            failures, reimport.get("residual_gap_mm"), "step_reimport.corrected_assembly.residual_gap_mm"
        )
        if residual is None or abs(residual) > linear:
            failures.append({"kind": "step_reimport_residual"})
        if reimport.get("patch_count") != topology.get("patch_count"):
            failures.append({"kind": "step_reimport_patch_count"})
        if reimport.get("component_count") != topology.get("component_count"):
            failures.append({"kind": "step_reimport_component_count"})
        if reimport.get("hole_count") != topology.get("hole_count"):
            failures.append({"kind": "step_reimport_hole_count"})
        if reimport.get("boundary_component_count") != topology.get("boundary_component_count"):
            failures.append({"kind": "step_reimport_boundary_count"})
        if reimport.get("roles") != ["Side_1", "Side_2"]:
            failures.append({"kind": "step_reimport_roles"})
        for side in ("Side_1", "Side_2"):
            expected_support = selected.get("Side_1", {}).get("support_coordinate_mm")
            actual_support = reimport.get("support_coordinates_mm", {}).get(side)
            if not _close(actual_support, expected_support, linear):
                failures.append({"kind": "step_reimport_support", "field": side})
            if not _close(
                reimport.get("coverage", {}).get(side),
                partition.get("coverage", {}).get(side),
                1e-7,
            ):
                failures.append({"kind": "step_reimport_coverage", "field": side})
            if not _close(
                reimport.get("remaining_area_mm2", {}).get(side),
                partition.get("remaining_area_mm2", {}).get(side),
                area_epsilon,
            ):
                failures.append({"kind": "step_reimport_remaining", "field": side})
        if not _close(reimport.get("common_area_mm2"), common, area_epsilon):
            failures.append({"kind": "step_reimport_common_area"})
        if reimport.get("solid_counts") != [1, 1]:
            failures.append({"kind": "step_reimport_solid_counts"})
        if reimport.get("valid") is not True or reimport.get("closed") is not True:
            failures.append({"kind": "step_reimport_solid_validity"})
        body_evidence = operation.get("body_evidence", {})
        reimport_volumes = reimport.get("volumes_mm3")
        expected_volumes = [
            body_evidence.get("Side_1", {}).get("volume_mm3"),
            body_evidence.get("Side_2_after", {}).get("volume_mm3"),
        ]
        if (
            not isinstance(reimport_volumes, list)
            or len(reimport_volumes) != 2
            or any(
                not _close(actual, expected_volume, RULES["volume_epsilon_mm3"])
                for actual, expected_volume in zip(reimport_volumes, expected_volumes)
            )
        ):
            failures.append({"kind": "step_reimport_volumes"})
        fused_reimport = operation.get("step_reimport", {}).get("fused", {})
        if (
            fused_reimport.get("solid_count") != 1
            or fused_reimport.get("valid") is not True
            or fused_reimport.get("closed") is not True
        ):
            failures.append({"kind": "fused_step_reimport"})
        if not _close(
            fused_reimport.get("volume_mm3"),
            fuse.get("volume_mm3"),
            RULES["volume_epsilon_mm3"],
        ):
            failures.append({"kind": "fused_step_reimport_volume"})
        verification = operation.get("artifact_verification", {})
        if not _close(
            verification.get("common", {}).get("area_mm2"), common, area_epsilon
        ) or verification.get("common", {}).get("face_count") != len(patches):
            failures.append({"kind": "artifact_common_parity"})
        verified_patches = verification.get("common_patches", [])
        if len(verified_patches) != len(patches):
            failures.append({"kind": "artifact_patch_parity"})
        else:
            verified_patch_ids = verification.get("artifact_patch_ids", [])
            for index, (patch, verified) in enumerate(zip(patches, verified_patches)):
                if (
                    not _close(patch.get("area_mm2"), verified.get("area_mm2"), area_epsilon)
                    or verified.get("face_count") != 1
                    or verified.get("surface_types") != [patch.get("surface_type")]
                    or verified.get("boundary_curve_types")
                    != patch.get("boundary_curve_types")
                    or index >= len(verified_patch_ids)
                    or verified_patch_ids[index] != patch.get("patch_id")
                ):
                    failures.append({"kind": "artifact_patch_parity"})
        for side in ("Side_1", "Side_2"):
            verified_remaining = verification.get("remaining", {}).get(side, {})
            expected_empty = partition.get("remaining_empty", {}).get(side)
            if (verified_remaining.get("status") == "EMPTY") is not expected_empty:
                failures.append({"kind": "artifact_remaining_parity", "field": side})
            if not _close(
                verified_remaining.get("area_mm2"),
                partition.get("remaining_area_mm2", {}).get(side),
                area_epsilon,
            ):
                failures.append({"kind": "artifact_remaining_parity", "field": side})
        if not _semantic_equal(verification.get("corrected_assembly"), reimport):
            failures.append({"kind": "artifact_corrected_step_parity"})
        if not _semantic_equal(verification.get("fused"), fused_reimport):
            failures.append({"kind": "artifact_fused_step_parity"})
        if verification.get("artifact_patch_geometric_equivalence") != "PASS":
            failures.append({"kind": "artifact_patch_geometry_equivalence"})
        verified_spatial = verification.get("spatial_validation", {})
        for side in ("Side_1", "Side_2"):
            for name in (
                "common_remaining_overlap_area_mm2",
                "coverage_missing_area_mm2",
                "outside_area_mm2",
                "source_area_mm2",
                "result_area_mm2",
            ):
                if not _close(
                    verified_spatial.get(side, {}).get(name),
                    spatial.get(side, {}).get(name),
                    area_epsilon,
                ):
                    failures.append({"kind": "artifact_spatial_parity", "field": f"{side}.{name}"})
            if verified_spatial.get(side, {}).get("within_area_epsilon") is not True:
                failures.append({"kind": "artifact_spatial_partition", "field": side})
        if not _close(
            verification.get("fused_boundary_overlap_area_mm2"),
            boundary_overlap,
            area_epsilon,
        ):
            failures.append({"kind": "artifact_fused_boundary_parity"})
    elif status in {
        "MOTION_NOT_AUTHORIZED",
        "ENGINEERING_TOLERANCE_EXCEEDED",
        "TRANSLATION_BUDGET_EXCEEDED",
        "NO_POSITIVE_AREA_INTERFACE",
        "UNSUPPORTED_NONCOPLANAR_INTERFACE_FACESET",
        "UNSUPPORTED_COMPLEX_MULTIFACE_COMPONENT_BOUNDARY",
        "UNSUPPORTED",
    }:
        if motion.get("motion_authorized") is not False:
            failures.append({"kind": "rejected_motion"})
        if norm is None or norm > linear:
            failures.append({"kind": "rejected_motion"})
        if operation.get("fuse", {}).get("executed") is not False:
            failures.append({"kind": "rejected_fuse"})
        artifacts = operation.get("artifacts", {})
        if any(key in artifacts for key in ("corrected_assembly_step", "fused_step")):
            failures.append({"kind": "rejected_artifact"})
    else:
        failures.append({"kind": "unsupported_status", "actual": status})
    recorded_hashes = operation.get("artifact_sha256", {})
    if not isinstance(recorded_hashes, dict):
        failures.append({"kind": "artifact_hash"})
        recorded_hashes = {}
    required_hashes = set(_artifact_names(operation.get("artifacts", {})))
    if operation.get("view_reopen") is not None:
        required_hashes.add("operation_debug.FCStd")
    valid_manifest = set(recorded_hashes) == required_hashes and all(
        isinstance(value, str)
        and value.startswith("sha256:")
        and len(value) == 71
        and all(character in "0123456789abcdef" for character in value[7:])
        for value in recorded_hashes.values()
    )
    if not valid_manifest:
        failures.append({"kind": "artifact_hash_manifest"})
    if artifact_root is not None:
        artifact_root = Path(artifact_root)
        artifact_hashes_match = valid_manifest
        for name, recorded_hash in recorded_hashes.items():
            path = artifact_root / name
            actual_hash = "sha256:" + sha256_file(path) if path.is_file() else None
            if actual_hash != recorded_hash:
                failures.append({"kind": "artifact_hash", "artifact": name})
                artifact_hashes_match = False
        if status == "SUPPORTED_UNIQUE_INTERFACE_FACESET" and artifact_hashes_match:
            try:
                observed = _run_freecad(
                    {
                        "action": "verify_artifacts",
                        "output_dir": str(artifact_root),
                        "artifacts": operation.get("artifacts", {}),
                        "rules": RULES,
                    }
                )
                observed = {key: value for key, value in observed.items() if key != "status"}
                if not _semantic_equal(observed, operation.get("artifact_verification")):
                    failures.append({"kind": "artifact_revalidation"})
            except Exception as error:
                failures.append({"kind": "artifact_revalidation", "error": str(error)})
    return {
        "schema_version": 1,
        "status": "PASS" if not failures else "FAIL",
        "expected_status": expected.get("status"),
        "failures": failures,
    }


def _write_case_evidence(staged: Path, operation: dict[str, Any], validation: dict[str, Any], expected: dict[str, Any]) -> None:
    write_json(staged / "operation.json", operation)
    write_json(staged / "validation.json", validation)
    write_json(staged / "expected_snapshot.json", expected)
    write_json(staged / "facesets.json", operation.get("face_sets", {}))
    write_json(staged / "patches.json", operation.get("partition", {}).get("common_patches", []))
    write_json(staged / "components.json", operation.get("topology", {}))
    write_json(staged / "provenance.json", operation.get("provenance", {}))
    for role, empty in operation.get("partition", {}).get("remaining_empty", {}).items():
        if empty is True:
            write_json(
                staged / f"{role.lower()}_remaining_EMPTY.json",
                {
                    "schema_version": 1,
                    "role": role,
                    "status": "EMPTY",
                    "area_mm2": 0.0,
                    "operation_kind": "FACE_CUT_REMAINDER",
                },
            )


def run_multipatch_case(
    fixture_root: Path,
    scenario_id: str,
    output_root: Path,
    *,
    create_view: bool = False,
    traversal_order: str = "normal",
) -> dict[str, Any]:
    fixture_root = Path(fixture_root)
    output_root = Path(output_root)
    case = fixture_root / scenario_id
    step = case / "inputs.step"
    policy = read_json(case / "policy.json")
    expected = read_json(case / "expected.json")
    output_root.mkdir(parents=True, exist_ok=True)
    staged = Path(tempfile.mkdtemp(prefix=f".{scenario_id}-06c-", dir=output_root))
    response = _run_freecad(
        {
            "action": "analyze",
            "scenario_id": scenario_id,
            "step_path": str(step),
            "policy": policy,
            "rules": RULES,
            "output_dir": str(staged),
            "create_view": create_view,
            "traversal_order": traversal_order,
        }
    )
    operation = response["operation"]
    if create_view:
        fcstd_path = staged / "operation_debug.FCStd"
        if operation.get("status") == "SUPPORTED_UNIQUE_INTERFACE_FACESET":
            visible_objects = ["Fused_Result", "Fused_Solid"]
        else:
            visible_objects = [
                "Originals",
                "Original_Side_1",
                "Original_Side_2",
                "Rejection_Evidence",
                "Ambiguity_Rejection",
            ]
        operation["view_reopen"] = _apply_visibility_profile(
            fcstd_path, visible_objects
        )
    artifacts = operation.get("artifacts", {})
    artifact_names = _artifact_names(artifacts)
    if create_view:
        artifact_names.append("operation_debug.FCStd")
    operation["artifact_sha256"] = {
        name: "sha256:" + sha256_file(staged / name)
        for name in sorted(set(artifact_names))
    }
    patch_artifacts = artifacts.get("common_patch_breps", [])
    for patch, provenance_record, name in zip(
        operation.get("partition", {}).get("common_patches", []),
        operation.get("provenance", {}).get("common_patches", []),
        patch_artifacts,
    ):
        patch["artifact"] = name
        patch["artifact_sha256"] = operation["artifact_sha256"].get(name)
        provenance_record["artifact"] = name
        provenance_record["artifact_sha256"] = operation["artifact_sha256"].get(name)
    if operation.get("status") == "SUPPORTED_UNIQUE_INTERFACE_FACESET":
        verification = _run_freecad(
            {
                "action": "verify_artifacts",
                "output_dir": str(staged),
                "artifacts": artifacts,
                "rules": RULES,
            }
        )
        operation["artifact_verification"] = {
            key: value for key, value in verification.items() if key != "status"
        }
    input_step_sha256 = "sha256:" + sha256_file(step)
    operation["input_step_sha256"] = input_step_sha256
    provenance = operation.setdefault("provenance", {})
    provenance["source_step_sha256"] = input_step_sha256
    for record in provenance.get("common_patches", []):
        record["source_step_sha256"] = input_step_sha256
    for record in provenance.get("remaining_patches", []):
        record["source_step_sha256"] = input_step_sha256
    for record in operation.get("partition", {}).get("member_level_partition", []):
        record["source_step_sha256"] = input_step_sha256
    operation["policy"] = policy
    operation["validator_version"] = "06C"
    operation["validator_source_commit"] = _source_commit()
    validation = validate_multipatch_evidence(
        operation, expected, artifact_root=staged
    )
    _write_case_evidence(staged, operation, validation, expected)
    target = output_root / scenario_id
    if validation["status"] == "PASS":
        if target.exists():
            shutil.rmtree(target)
        staged.replace(target)
    else:
        failed = output_root / f"{scenario_id}_failed_validation"
        if failed.exists():
            shutil.rmtree(failed)
        staged.replace(failed)
        target = failed
    return {
        "operation": operation,
        "validation": validation,
        "expected": expected,
        "output_dir": str(target),
    }


def _repeatable_projection(operation: dict[str, Any]) -> dict[str, Any]:
    return {
        key: operation.get(key)
        for key in ("status", "face_sets", "motion", "partition", "topology", "fuse", "provenance")
    }


def run_multipatch_suite(fixture_root: Path, output_root: Path) -> dict[str, Any]:
    output_root = Path(output_root)
    results = {
        scenario: run_multipatch_case(
            fixture_root, scenario, output_root, create_view=True, traversal_order="normal"
        )
        for scenario in ("P10", "P11", "P12")
    }
    repeatability = {}
    for scenario, first in results.items():
        second = run_multipatch_case(
            fixture_root,
            scenario,
            output_root / "repeatability" / "second_process",
            traversal_order="reverse",
        )
        comparison = compare_multipatch_repeatability(
            first["operation"], second["operation"]
        )
        repeatability[scenario] = {
            "processes": 2,
            "status": comparison["status"],
        }
        write_json(output_root / scenario / "repeatability.json", repeatability[scenario])
    summary = {
        "schema_version": 1,
        "status": "PASS"
        if all(item["validation"]["status"] == "PASS" for item in results.values())
        and all(item["status"] == "PASS" for item in repeatability.values())
        else "FAIL",
        "scenarios": {scenario: result["operation"]["status"] for scenario, result in results.items()},
        "repeatability": repeatability,
    }
    write_json(output_root / "summary.json", summary)
    (output_root / "VIEW_INDEX.md").write_text(
        "# 06C 多块与带孔平面接口查看指南\n\n"
        "- P10：默认仅显示 `Fused_Result`；打开 `Common_Patches` 与 `Components` 可查看两个互不连接的接触脚。\n"
        "- P11：默认仅显示 `Fused_Result`；打开 `Annular_Common` 和 `Boundary_Loops` 可查看外环与中心孔。\n"
        "- P12：默认显示原始实体与拒绝证据；候选 FaceSet 预览均为 `DISPLAY_ONLY / NOT_EXECUTED`。\n",
        encoding="utf-8",
    )
    return summary


def _main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("generate", "run", "case"))
    parser.add_argument("root", type=Path)
    parser.add_argument("--scenario", default="P10")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.action == "generate":
        generate_multipatch_fixtures(args.root)
    elif args.action == "run":
        report = run_multipatch_suite(args.root, args.output)
        if report["status"] != "PASS":
            raise SystemExit(1)
    else:
        report = run_multipatch_case(args.root, args.scenario, args.output)
        if report["validation"]["status"] != "PASS":
            raise SystemExit(1)


if __name__ == "__main__":
    _main()
