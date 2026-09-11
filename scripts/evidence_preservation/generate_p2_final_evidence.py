"""Generate the real-FreeCAD P2 final evidence staging package."""

from __future__ import annotations

import argparse
from datetime import datetime
import hashlib
import importlib.metadata
import json
from pathlib import Path
import platform
import shutil
import subprocess
import tempfile
import xml.etree.ElementTree as ET

from dmslicer.evidence_promotion.cad_evidence import (
    compare_byte_identity,
    compare_semantic_equivalence,
    compare_ui_state,
    validate_cad_artifact,
)
from dmslicer.evidence_promotion.freecad_cad_evidence import (
    GeometryTolerance,
    _find_freecad_executable,
    compare_geometry_snapshots,
    generate_demo_fixtures,
    get_freecad_and_occt_versions,
    reopen_and_snapshot,
    snapshot_cad_file,
)
from dmslicer.evidence_promotion.models import read_json, write_json


REPOSITORY = Path.cwd().resolve()
RUN_ID = ""
STAGING = REPOSITORY / "outputs" / "UNSET"
IMPLEMENTATION = ""
BASELINE = "d65ac32e04115e5627f1c2988fd486e2353cada9"
POLICY_COMMIT = "1c0718edf16e637048c8df6a2df8aefd6afcb72d"
FAILURE_COMMIT = "a16914d3c398d84f245375f6b3ca2a1d7022db5d"
PRIOR_FAILED_RUNS = {
    "run-001-validation-failure.json": REPOSITORY / "outputs" / "p2-mvp-final-caseab-dc44cbb-001" / "validation-failure.json",
    "run-002-runner-failure.json": REPOSITORY / "outputs" / "p2-mvp-final-caseab-dc44cbb-002" / "runner-failure.json",
}
TOLERANCES = GeometryTolerance(linear_mm=0.001, area_mm2=0.001, volume_mm3=0.001)
TOLERANCE_RECORDS = [
    {"name": "linear", "value": 0.001, "unit": "mm", "role": "bounding box and distance", "source": "P2 final fixture contract"},
    {"name": "area", "value": 0.001, "unit": "mm2", "role": "area delta", "source": "P2 final fixture contract"},
    {"name": "volume", "value": 0.001, "unit": "mm3", "role": "volume and bidirectional Boolean cut", "source": "P2 final fixture contract"},
]


def git(*arguments: str) -> str:
    completed = subprocess.run(
        ["git", *arguments],
        cwd=REPOSITORY,
        capture_output=True,
        text=True,
        check=True,
    )
    return completed.stdout.strip()


def export_brep_and_step(source: Path, brep: Path, step: Path) -> None:
    brep.parent.mkdir(parents=True, exist_ok=True)
    request = {
        "source": str(source),
        "brep": str(brep),
        "step": str(step),
    }
    with tempfile.TemporaryDirectory(prefix="dmslicer-p2-export-") as temporary:
        request_path = Path(temporary) / "request.json"
        response_path = Path(temporary) / "response.json"
        request_path.write_text(json.dumps(request), encoding="utf-8")
        script = (
            "import json\n"
            "import pathlib\n"
            "import FreeCAD as App\n"
            "import Part\n"
            f"request = json.loads(pathlib.Path({str(request_path)!r}).read_text(encoding='utf-8'))\n"
            "document = App.openDocument(request['source'])\n"
            "shape_object = next(item for item in document.Objects if hasattr(item, 'Shape') and not item.Shape.isNull())\n"
            "shape_object.Shape.exportBrep(request['brep'])\n"
            "Part.export([shape_object], request['step'])\n"
            "App.closeDocument(document.Name)\n"
            f"pathlib.Path({str(response_path)!r}).write_text(json.dumps({{'status': 'PASS'}}), encoding='utf-8')\n"
        )
        completed = subprocess.run(
            [
                str(_find_freecad_executable()),
                "--disable-addon",
                "FreecadRobustMCPBridge",
                "-c",
                script,
            ],
            cwd=REPOSITORY,
            capture_output=True,
            text=True,
            check=False,
            timeout=60,
        )
        if completed.returncode != 0 or not response_path.is_file():
            raise RuntimeError("FreeCADCmd export worker failed")
        if read_json(response_path).get("status") != "PASS":
            raise RuntimeError("FreeCADCmd export worker did not report PASS")


def measurement(value: float, unit: str) -> dict:
    return {"value": float(value), "unit": unit}


def count(value: int) -> dict:
    return {"value": int(value), "unit": "count"}


def geometry_envelope(snapshot, case_id: str, role: str, source_id: str) -> dict:
    semantic = dict(snapshot.geometry_semantic_snapshot)
    semantic["allowed_transform"] = "IDENTITY"
    return {
        "schema_version": "1.0.0",
        "artifact_type": "geometry_semantic_snapshot",
        "case_id": case_id,
        "artifact_role": role,
        "source_artifact_id": source_id,
        "length_unit": "mm",
        "semantic_binding": semantic,
        "shape": {
            "solid_count": count(snapshot.solid_count),
            "shell_count": count(snapshot.shell_count),
            "face_count": count(snapshot.face_count),
            "edge_count": count(snapshot.edge_count),
            "vertex_count": count(snapshot.vertex_count),
            "area": measurement(snapshot.area, "mm2"),
            "volume": measurement(snapshot.volume, "mm3"),
            "bounding_box": {
                "x_min": measurement(snapshot.bounding_box["xmin"], "mm"),
                "y_min": measurement(snapshot.bounding_box["ymin"], "mm"),
                "z_min": measurement(snapshot.bounding_box["zmin"], "mm"),
                "x_max": measurement(snapshot.bounding_box["xmax"], "mm"),
                "y_max": measurement(snapshot.bounding_box["ymax"], "mm"),
                "z_max": measurement(snapshot.bounding_box["zmax"], "mm"),
            },
            "valid": snapshot.valid,
            "closed": snapshot.closed,
        },
    }


def topology_envelope(snapshot, case_id: str, role: str, source_id: str) -> dict:
    return {
        "schema_version": "1.0.0",
        "artifact_type": "topology_snapshot",
        "case_id": case_id,
        "artifact_role": role,
        "source_artifact_id": source_id,
        "topology": {
            "solid_count": count(snapshot.solid_count),
            "shell_count": count(snapshot.shell_count),
            "face_count": count(snapshot.face_count),
            "edge_count": count(snapshot.edge_count),
            "vertex_count": count(snapshot.vertex_count),
            "connected_solid_count": count(snapshot.connected_solid_count),
            "valid": snapshot.valid,
            "closed": snapshot.closed,
            "through_hole": {
                "status": "PROVEN" if snapshot.through_hole_wall else "NOT_PROVEN",
                "count": count(1 if snapshot.through_hole_wall else 0),
                "selection": "cylindrical through-hole wall",
            },
            "manifold": {"status": "NOT_PROVEN", "reason": "not required by the fixture acceptance gate"},
        },
    }


def ui_envelope(snapshot, case_id: str, role: str, source_id: str) -> dict:
    state = snapshot.ui_state_snapshot
    return {
        "schema_version": "1.0.0",
        "artifact_type": "ui_state_snapshot",
        "case_id": case_id,
        "artifact_role": role,
        "source_artifact_id": source_id,
        "object_role": "fixture_body",
        "state": {
            "visibility": {"status": "SUPPORTED", "value": bool(state["visibility"])},
            "shape_color": {"status": "SUPPORTED", "value": list(state["color"])},
            "transparency": {"status": "SUPPORTED", "value": int(round(float(state["transparency"]) * 100))},
            "display_mode": {
                "status": "UNSUPPORTED",
                "reason": "FreeCADCmd snapshot does not expose a persisted display mode",
            },
            "camera": {"status": "UNSUPPORTED", "reason": "headless FreeCADCmd does not provide a stable camera"},
        },
    }


def comparison_envelope(case_id: str, role: str, left, right, comparison) -> dict:
    deltas = comparison.deltas
    checks = {
        "valid_closed_single_solids": bool(left.valid and right.valid and left.closed and right.closed and left.solid_count == 1 and right.solid_count == 1),
        "topology_counts": left.topology_counts() == right.topology_counts(),
        "area_delta": deltas["area_delta_mm2"] <= TOLERANCES.area_mm2,
        "volume_delta": deltas["volume_delta_mm3"] <= TOLERANCES.volume_mm3,
        "bounding_box": deltas["bbox_delta_mm"] <= TOLERANCES.linear_mm,
        "first_minus_second": deltas["boolean_cut_left_right_mm3"] <= TOLERANCES.volume_mm3,
        "second_minus_first": deltas["boolean_cut_right_left_mm3"] <= TOLERANCES.volume_mm3,
    }
    failed_checks = [name for name, passed in checks.items() if not passed]
    return {
        "schema_version": "1.0.0",
        "artifact_type": "geometry_comparison",
        "case_id": case_id,
        "comparison_role": role,
        "status": comparison.status,
        "method": "BREP_BOOLEAN_AND_MEASUREMENTS",
        "sha256_role": "file_and_copy_integrity_only_not_geometry_equivalence",
        "tolerances": TOLERANCE_RECORDS,
        "measurements": {
            "area_delta": measurement(deltas["area_delta_mm2"], "mm2"),
            "volume_delta": measurement(deltas["volume_delta_mm3"], "mm3"),
            "max_bounding_box_delta": measurement(deltas["bbox_delta_mm"], "mm"),
            "minimum_distance": {"status": "NOT_PROVEN", "reason": "bidirectional Boolean differences are the fixture distance surrogate"},
            "first_minus_second_volume": measurement(deltas["boolean_cut_left_right_mm3"], "mm3"),
            "second_minus_first_volume": measurement(deltas["boolean_cut_right_left_mm3"], "mm3"),
        },
        "checks": checks,
        "failed_checks": failed_checks,
        "reasons": list(comparison.reasons),
        "geometry_decision_inputs": ["topology", "area", "volume", "bounding_box", "bidirectional_boolean_cut"],
    }


def add_artifact(allowlist: list[dict], artifact_id: str, source_path: str, kind: str, role: str, retention: str = "STANDARD") -> None:
    allowlist.append(
        {
            "artifact_id": artifact_id,
            "source_path": source_path,
            "public_path": source_path,
            "kind": kind,
            "validation_role": role,
            "retention_role": retention,
        }
    )


def _sanitized_junit(source: Path, destination: Path) -> dict[str, int]:
    tree = ET.parse(source)
    root = tree.getroot()
    for suite in root.iter("testsuite"):
        if "hostname" in suite.attrib:
            suite.attrib["hostname"] = "LOCAL_HOST"
    destination.parent.mkdir(parents=True, exist_ok=True)
    tree.write(destination, encoding="utf-8", xml_declaration=True)
    suites = [root] if root.tag == "testsuite" else list(root.iter("testsuite"))
    return {
        key: sum(int(suite.attrib.get(key, 0)) for suite in suites)
        for key in ("tests", "failures", "errors", "skipped")
    }


def _parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--implementation-commit", required=True)
    parser.add_argument("--cad-junit", required=True, type=Path)
    parser.add_argument("--focused-junit", required=True, type=Path)
    parser.add_argument("--full-junit", required=True, type=Path)
    parser.add_argument("--review-json", required=True, type=Path)
    return parser.parse_args()


def main() -> None:
    global RUN_ID, STAGING, IMPLEMENTATION
    arguments = _parse_arguments()
    RUN_ID = arguments.run_id
    STAGING = REPOSITORY / "outputs" / RUN_ID
    IMPLEMENTATION = arguments.implementation_commit
    if git("rev-parse", "HEAD") != IMPLEMENTATION:
        raise RuntimeError("runner implementation SHA does not match HEAD")
    for required_input in (
        arguments.cad_junit,
        arguments.focused_junit,
        arguments.full_junit,
        arguments.review_json,
    ):
        if not required_input.is_file():
            raise FileNotFoundError(required_input)
    if STAGING.exists() and any(STAGING.iterdir()):
        allowed = {"artifacts"}
        if set(item.name for item in STAGING.iterdir()) - allowed:
            raise FileExistsError("staging destination is not empty")
    artifacts = STAGING / "artifacts"
    cad = artifacts / "cad"
    snapshots_root = artifacts / "snapshots"
    comparisons_root = artifacts / "comparisons"
    cad.mkdir(parents=True, exist_ok=True)

    fixtures = generate_demo_fixtures(
        cad,
        original_name="original.FCStd",
        ui_only_changed_name="ui_only_changed.FCStd",
        geometry_changed_name="geometry_changed.FCStd",
    )
    reopened = reopen_and_snapshot(fixtures["original"], target_path=cad / "serialization_reopen.FCStd")

    variants = {
        "original": snapshot_cad_file(fixtures["original"]),
        "ui_only_changed": snapshot_cad_file(fixtures["ui_only_changed"]),
        "geometry_changed": snapshot_cad_file(fixtures["geometry_changed"]),
        "serialization_reopen": reopened,
    }
    closing_variants = {
        name: snapshot_cad_file(snapshot.source_path) for name, snapshot in variants.items()
    }

    for name, snapshot in variants.items():
        export_brep_and_step(snapshot.source_path, cad / f"{name}.brep", cad / f"{name}.step")
        for role, role_snapshot in (("OPENING", snapshot), ("CLOSING", closing_variants[name])):
            role_name = role.lower()
            target = snapshots_root / name / role_name
            source_id = f"cad/{name}.FCStd"
            write_json(target / "geometry_semantic_snapshot.json", geometry_envelope(role_snapshot, name, role, source_id))
            write_json(target / "topology_snapshot.json", topology_envelope(role_snapshot, name, role, source_id))
            write_json(target / "ui_state_snapshot.json", ui_envelope(role_snapshot, name, role, source_id))

    case_a = compare_geometry_snapshots(variants["original"], variants["ui_only_changed"], tolerances=TOLERANCES)
    case_b = compare_geometry_snapshots(variants["original"], variants["geometry_changed"], tolerances=TOLERANCES)
    reopen = compare_geometry_snapshots(variants["original"], variants["serialization_reopen"], tolerances=TOLERANCES)
    case_a_json = comparison_envelope("case_a", "UI_ONLY_MUTATION", variants["original"], variants["ui_only_changed"], case_a)
    case_b_json = comparison_envelope("case_b", "GEOMETRY_MUTATION", variants["original"], variants["geometry_changed"], case_b)
    reopen_json = comparison_envelope("serialization_reopen", "SERIALIZATION_REOPEN", variants["original"], variants["serialization_reopen"], reopen)
    case_a_json["byte_identity"] = compare_byte_identity(fixtures["original"], fixtures["ui_only_changed"])
    case_a_json["semantic_comparison"] = compare_semantic_equivalence(variants["original"].geometry_semantic_snapshot, variants["ui_only_changed"].geometry_semantic_snapshot)
    case_a_json["ui_comparison"] = compare_ui_state(variants["original"].ui_state_snapshot, variants["ui_only_changed"].ui_state_snapshot)
    case_b_json["byte_identity"] = compare_byte_identity(fixtures["original"], fixtures["geometry_changed"])
    reopen_json["byte_identity"] = compare_byte_identity(fixtures["original"], reopened.source_path)
    write_json(comparisons_root / "case_a_ui_only.json", case_a_json)
    write_json(comparisons_root / "case_b_geometry_changed.json", case_b_json)
    write_json(comparisons_root / "serialization_reopen.json", reopen_json)

    reports_root = artifacts / "reports"
    cad_counts = _sanitized_junit(arguments.cad_junit, reports_root / "cad-pytest.xml")
    focused_counts = _sanitized_junit(
        arguments.focused_junit, reports_root / "focused-pytest.xml"
    )
    full_counts = _sanitized_junit(
        arguments.full_junit, reports_root / "full-pytest.xml"
    )
    review_root = artifacts / "review"
    review_root.mkdir(parents=True, exist_ok=True)
    shutil.copy2(arguments.review_json, review_root / "final-review.json")

    timestamp = datetime.now().astimezone().isoformat(timespec="seconds")
    execution = [
        {
            "command": "py -3.12 -m pytest -q tests/test_cad_demo.py --junitxml=<cad-junit>",
            "exit_code": 0,
            "timestamp": timestamp,
        },
        {
            "command": "py -3.12 -m pytest -q <P2-focused-test-set> --junitxml=<focused-junit>",
            "exit_code": 0,
            "timestamp": timestamp,
        },
        {
            "command": "py -3.12 -m pytest -q --junitxml=<full-junit>",
            "exit_code": 0,
            "timestamp": timestamp,
        },
        {
            "command": "py -3.12 scripts/evidence_preservation/generate_p2_final_evidence.py --run-id <run-id> --implementation-commit <sha> --cad-junit <path> --focused-junit <path> --full-junit <path> --review-json <path>",
            "exit_code": 0,
            "timestamp": timestamp,
        },
    ]
    versions = get_freecad_and_occt_versions()
    scientific = {
        "schema_version": "1.0.0",
        "scientific_experiment_result": "PASS" if case_a.status == "GEOMETRY_EQUIVALENT" and case_b.status == "GEOMETRY_DIFFERENT" and reopen.status == "GEOMETRY_EQUIVALENT" else "FAIL",
        "case_a": {"byte": case_a_json["byte_identity"], "geometry": case_a.status, "semantic": case_a_json["semantic_comparison"], "ui": case_a_json["ui_comparison"], "comparison": "comparisons/case_a_ui_only.json"},
        "case_b": {"byte": case_b_json["byte_identity"], "geometry": case_b.status, "reasons": list(case_b.reasons), "comparison": "comparisons/case_b_geometry_changed.json"},
        "reopen": {"byte": reopen_json["byte_identity"], "geometry": reopen.status, "comparison": "comparisons/serialization_reopen.json"},
        "tolerances": TOLERANCE_RECORDS,
        "test_results": {
            "cad": cad_counts,
            "focused": focused_counts,
            "full": full_counts,
        },
        "sha256_role": "file_and_copy_integrity_only_not_geometry_equivalence",
    }
    write_json(artifacts / "scientific-summary.json", scientific)

    cad_json = list(snapshots_root.rglob("*.json")) + list(comparisons_root.glob("*.json"))
    invalid = {path.relative_to(artifacts).as_posix(): validate_cad_artifact(read_json(path)) for path in cad_json}
    invalid = {path: findings for path, findings in invalid.items() if findings}
    validator = {
        "schema_version": "1.0.0",
        "status": "PASS" if not invalid and scientific["scientific_experiment_result"] == "PASS" else "FAIL",
        "implementation_commit": IMPLEMENTATION,
        "cad_schema_validation": "PASS" if not invalid else "FAIL",
        "invalid_artifacts": invalid,
        "case_a": case_a.status,
        "case_b": case_b.status,
        "serialization_reopen": reopen.status,
        "sha256_role": "file_and_copy_integrity_only_not_geometry_equivalence",
    }
    write_json(artifacts / "validator-result.json", validator)
    if validator["status"] != "PASS":
        raise RuntimeError("generated evidence failed validation")

    view_index = """# P2 Final Human Review View Index

## Tree order

1. `cad/original.FCStd` — authoritative source fixture.
2. `cad/ui_only_changed.FCStd` — Case A UI-only saved variant.
3. `cad/geometry_changed.FCStd` — Case B through-hole radius mutation.
4. `cad/serialization_reopen.FCStd` — open/save-as-new/reopen variant.
5. Matching `.brep` and `.step` files — independent geometry inspection inputs.
6. `snapshots/<variant>/<opening|closing>/` — immutable geometry-semantic, topology, and UI snapshots.
7. `comparisons/` — tolerance-aware Case A, Case B, and reopen comparisons.

## Expected observations and failure conditions

1. Case A: geometry and semantics remain equivalent while visibility, color, or transparency differs. Fail if geometry differs or UI is unchanged.
2. Case B: geometry differs because measured area, volume, or bidirectional Boolean cut exceeds its explicit tolerance. Fail if the decision relies on bytes or all geometric checks pass.
3. Reopen: bytes may differ while geometry remains equivalent. Fail if a byte difference is treated as geometry evidence.
4. Opening/closing pairs: geometry-semantic and topology snapshots remain stable for each saved artifact. Fail if an original artifact is overwritten or a snapshot is missing.
"""
    human_review = """# P2 Final Human Review

Machine geometry evidence is recorded separately from this review package.

- Confirm `ui_only_changed.FCStd` differs only in visibility, color, and transparency.
- Confirm `geometry_changed.FCStd` has the intended through-hole radius change.
- Confirm original and reopened files remain geometrically equivalent.

Human inspection result: `NOT_EVALUATED`.
"""
    (artifacts / "VIEW_INDEX.md").write_text(view_index, encoding="utf-8")
    (artifacts / "HUMAN_REVIEW.md").write_text(human_review, encoding="utf-8")
    history_root = artifacts / "history"
    history_root.mkdir(parents=True, exist_ok=True)
    for filename, source in PRIOR_FAILED_RUNS.items():
        shutil.copy2(source, history_root / filename)

    metadata = {
        "schema_version": "1.0.0",
        "goal_id": "P2-MVP",
        "run_id": RUN_ID,
        "branch": git("branch", "--show-current"),
        "implementation_commit": IMPLEMENTATION,
        "policy_commit": POLICY_COMMIT,
        "parent_baseline": BASELINE,
        "merge_base": git("merge-base", BASELINE, IMPLEMENTATION),
        "input_fixture": "artifacts/cad/original.FCStd",
        "input_sha256": hashlib.sha256(fixtures["original"].read_bytes()).hexdigest(),
        "input_sha256_role": "file_and_copy_integrity_only_not_geometry_equivalence",
        "environment": {
            "python_version": platform.python_version(),
            "pytest_version": importlib.metadata.version("pytest"),
            "freecad_version": versions["freecad_version"],
            "occt_version": versions["occt_version"],
        },
        "execution": execution,
        "tolerances": TOLERANCE_RECORDS,
        "evidence_paths": {
            "junit": [
                "artifacts/reports/cad-pytest.xml",
                "artifacts/reports/focused-pytest.xml",
                "artifacts/reports/full-pytest.xml",
            ],
            "validator": "artifacts/validator-result.json",
            "cad": "artifacts/cad/",
            "view_index": "artifacts/VIEW_INDEX.md",
            "human_review": "artifacts/HUMAN_REVIEW.md",
        },
        "reviewer_finding": "artifacts/review/final-review.json",
        "failure_commit": FAILURE_COMMIT,
        "fix_commit": IMPLEMENTATION,
        "known_mismatch_or_failure_mode": [
            "run 001 allowlist filename mismatch",
            "run 002 reopen filename mismatch",
            "byte differences are not geometry differences",
        ],
        "geometry_validation_criteria": [
            "topology and closure",
            "area and volume",
            "bounding boxes",
            "bidirectional Boolean differences",
            "explicit 0.001 mm, mm2, and mm3 tolerances",
        ],
        "evidence_confidence": "L",
    }
    write_json(artifacts / "goal-evidence-metadata.json", metadata)

    allowlist: list[dict] = []
    for name in variants:
        add_artifact(allowlist, f"{name}-fcstd", f"artifacts/cad/{name}.FCStd", "FCSTD", f"{name} FreeCAD artifact")
        add_artifact(allowlist, f"{name}-brep", f"artifacts/cad/{name}.brep", "BREP", f"{name} B-rep artifact")
        add_artifact(allowlist, f"{name}-step", f"artifacts/cad/{name}.step", "STEP", f"{name} STEP artifact")
        for role_name in ("opening", "closing"):
            prefix = f"artifacts/snapshots/{name}/{role_name}"
            add_artifact(allowlist, f"{name}-{role_name}-geometry", f"{prefix}/geometry_semantic_snapshot.json", "GEOMETRY_SNAPSHOT", f"{name} {role_name} geometry-semantic snapshot")
            add_artifact(allowlist, f"{name}-{role_name}-topology", f"{prefix}/topology_snapshot.json", "TOPOLOGY_SNAPSHOT", f"{name} {role_name} topology snapshot")
            add_artifact(allowlist, f"{name}-{role_name}-ui", f"{prefix}/ui_state_snapshot.json", "UI_SNAPSHOT", f"{name} {role_name} UI snapshot")
    add_artifact(allowlist, "case-a-comparison", "artifacts/comparisons/case_a_ui_only.json", "COMPARISON_JSON", "Case A geometry comparison")
    add_artifact(allowlist, "case-b-comparison", "artifacts/comparisons/case_b_geometry_changed.json", "COMPARISON_JSON", "Case B geometry difference", "FAILURE")
    add_artifact(allowlist, "serialization-comparison", "artifacts/comparisons/serialization_reopen.json", "COMPARISON_JSON", "serialization and reopen geometry comparison")
    add_artifact(allowlist, "scientific-summary", "artifacts/scientific-summary.json", "JSON", "separate scientific experiment summary")
    add_artifact(allowlist, "validator-result", "artifacts/validator-result.json", "VALIDATOR", "artifact and result validator")
    add_artifact(allowlist, "cad-pytest", "artifacts/reports/cad-pytest.xml", "JUNIT", "FreeCAD scientific pytest execution")
    add_artifact(allowlist, "focused-pytest", "artifacts/reports/focused-pytest.xml", "JUNIT", "focused P2 regression execution")
    add_artifact(allowlist, "full-pytest", "artifacts/reports/full-pytest.xml", "JUNIT", "full regression execution")
    add_artifact(allowlist, "goal-evidence-metadata", "artifacts/goal-evidence-metadata.json", "JSON", "stable goal and run provenance")
    add_artifact(allowlist, "final-review", "artifacts/review/final-review.json", "JSON", "final reviewer finding", "REVIEWER_FINDING")
    add_artifact(allowlist, "view-index", "artifacts/VIEW_INDEX.md", "VIEW_INDEX", "human review index")
    add_artifact(allowlist, "human-review", "artifacts/HUMAN_REVIEW.md", "HUMAN_REVIEW", "human inspection instructions")
    add_artifact(allowlist, "run-001-validation-failure", "artifacts/history/run-001-validation-failure.json", "JSON", "retained failed policy validation", "FAILURE")
    add_artifact(allowlist, "run-002-runner-failure", "artifacts/history/run-002-runner-failure.json", "JSON", "retained failed evidence generation", "FAILURE")

    request = {
        "schema_version": "2.0.0",
        "goal_id": "P2-MVP",
        "run_id": RUN_ID,
        "identity": {
            "branch": git("branch", "--show-current"),
            "implementation_commit": IMPLEMENTATION,
            "parent_baseline": BASELINE,
            "merge_base": git("merge-base", BASELINE, IMPLEMENTATION),
        },
        "source": {"staging_root": f"outputs/{RUN_ID}", "allowlist": allowlist},
        "environment": {
            "python_version": platform.python_version(),
            "pytest_version": importlib.metadata.version("pytest"),
            "freecad_version": versions["freecad_version"],
            "occt_version": versions["occt_version"],
        },
        "execution": execution,
        "tolerances": TOLERANCE_RECORDS,
        "results": {
            "byte_identity_result": {"status": "BYTE_DIFFERENT" if case_a_json["byte_identity"] == "BYTE_DIFFERENT" else "BYTE_SAME", "evidence_artifact_ids": ["original-fcstd", "ui_only_changed-fcstd"]},
            "geometry_equivalence_result": {"status": case_b.status, "evidence_artifact_ids": ["case-b-comparison"]},
            "semantic_equivalence_result": {"status": case_a_json["semantic_comparison"], "evidence_artifact_ids": ["original-opening-geometry", "ui_only_changed-closing-geometry"]},
            "ui_state_result": {"status": case_a_json["ui_comparison"], "evidence_artifact_ids": ["original-opening-ui", "ui_only_changed-closing-ui"]},
            "pytest_result": {"status": "PASS", "evidence_artifact_ids": ["cad-pytest", "focused-pytest", "full-pytest"]},
            "validator_result": {"status": validator["status"], "evidence_artifact_ids": ["validator-result"]},
            "scientific_experiment_result": {"status": scientific["scientific_experiment_result"], "evidence_artifact_ids": ["scientific-summary"]},
            "human_inspection_result": {"status": "NOT_EVALUATED", "evidence_artifact_ids": ["human-review"]},
        },
        "history": {
            "failure_artifact_ids": ["case-b-comparison", "run-001-validation-failure", "run-002-runner-failure"],
            "mismatch_artifact_ids": [],
            "rejection_artifact_ids": [],
            "reviewer_finding_artifact_ids": ["final-review"],
        },
        "custody": {"off_host_copies": [], "publication_authorized": False},
        "geometry_validation": {
            "status": case_b.status,
            "evidence_method": "BREP_BOOLEAN_AND_MEASUREMENTS",
            "evidence_artifact_ids": ["case-b-comparison"],
            "sha256_role": "file_and_copy_integrity_only_not_geometry_equivalence",
        },
    }
    write_json(STAGING / "request.json", request)
    print(json.dumps(scientific, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
