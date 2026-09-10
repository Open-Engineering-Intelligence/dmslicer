import json
import math
import os
import subprocess
import sys
from pathlib import Path

import pytest

from dmslicer.shell_fill_04a2 import validate_shell_fill_candidate


CASE_EXPECTATIONS = {
    "U01_sphere_full_fill": {"area": 4 * math.pi * 20**2, "coverage": [1.0, 1.0], "remaining": [0, 0], "cavity": "none"},
    "U02_sphere_half_fill": {"area": 2 * math.pi * 20**2, "coverage": [1.0, 1.0], "remaining": [0, 0], "cavity": "none"},
    "U03_sphere_partial_fill": {"area": 2 * math.pi * 20**2, "coverage": [0.5, 1.0], "remaining": [1, 0], "cavity": "lower_hemisphere"},
}


def _command(*arguments: str) -> subprocess.CompletedProcess[str]:
    environment = os.environ.copy()
    environment["PYTHONPATH"] = str(Path("src").resolve())
    return subprocess.run([sys.executable, "-m", "dmslicer", *arguments], cwd=Path.cwd(), env=environment, text=True, capture_output=True, check=False)


def test_shell_fill_generator_creates_three_independent_tracked_step_bundles(tmp_path: Path) -> None:
    completed = _command("generate-shell-fill-cases", str(tmp_path))

    assert completed.returncode == 0, completed.stderr
    assert {path.name for path in tmp_path.iterdir()} == set(CASE_EXPECTATIONS)
    for case_id in CASE_EXPECTATIONS:
        case = tmp_path / case_id
        parameters = json.loads((case / "parameters.json").read_text(encoding="utf-8"))
        expected = json.loads((case / "expected.json").read_text(encoding="utf-8"))
        assert (case / "inputs.step").is_file()
        assert parameters["outer_radius_mm"] == 30
        assert parameters["inner_radius_mm"] == 20
        assert parameters["hemisphere"] == "z>=0"
        assert expected["case_id"] == case_id
        assert expected["common_area_mm2"] == pytest.approx(CASE_EXPECTATIONS[case_id]["area"])


@pytest.mark.parametrize("case_id", sorted(CASE_EXPECTATIONS))
def test_tracked_shell_fill_case_validates_actual_shape_not_only_closedness(tmp_path: Path, case_id: str) -> None:
    fixture = Path("benchmarks/shell_fill_04a2") / case_id
    output = tmp_path / case_id

    completed = _command("run-shell-fill-case", str(fixture), str(output))

    assert completed.returncode == 0, completed.stderr
    operation = json.loads((output / "operation.json").read_text(encoding="utf-8"))
    validation = json.loads((output / "validation.json").read_text(encoding="utf-8"))
    expected = CASE_EXPECTATIONS[case_id]
    assert operation["analysis_input"] == "reimported_step"
    assert len(operation["fused_step_sha256"]) == 64
    assert operation["side_order"] == {"side_1": "shell", "side_2": "core"}
    assert operation["common_area_mm2"] == pytest.approx(expected["area"], abs=1e-7)
    assert operation["coverage"] == pytest.approx(expected["coverage"], abs=1e-9)
    assert [len(operation["partitions"][side]["remaining_patches"]) for side in ("side_1", "side_2")] == expected["remaining"]
    assert all(operation["partitions"][side]["area_conserved"] for side in ("side_1", "side_2"))
    assert operation["union"]["solid_count"] == 1
    assert operation["union"]["valid"] is True
    assert operation["union"]["closed"] is True
    assert operation["debug"]["reopened"] is True
    assert operation["debug"]["visibility_state_saved"] is True
    assert validation["status"] == "PASS"
    assert validation["actual_minus_reference_mm3"] <= 1e-6
    assert validation["reference_minus_actual_mm3"] <= 1e-6
    assert validation["common_not_on_boundary"] is True
    assert validation["cavity_state"] == expected["cavity"]
    assert validation["roundtrip_shape_match"] is True
    assert validation["debug_annotation_saved"] is True
    if case_id == "U03_sphere_partial_fill":
        assert validation["lower_inner_sphere_boundary_area_mm2"] == pytest.approx(2 * math.pi * 20**2, abs=1e-7)
        assert validation["inner_equator_disk_boundary_area_mm2"] == pytest.approx(math.pi * 20**2, abs=1e-7)
    assert (output / "fused.step").is_file()
    assert (output / "operation_debug.FCStd").is_file()


def test_u01_rejects_half_shell_plus_full_core_with_same_radii() -> None:
    validation = validate_shell_fill_candidate("U01_sphere_full_fill", "half_shell_plus_full_core")

    assert validation["status"] == "FAIL"
    assert validation["reference_minus_actual_mm3"] > 1e-6


def test_u03_rejects_filled_lower_cavity() -> None:
    validation = validate_shell_fill_candidate("U03_sphere_partial_fill", "full_outer_ball")

    assert validation["status"] == "FAIL"
    assert validation["lower_cavity_empty"] is False


def test_shell_fill_suite_publishes_chinese_view_index_and_two_process_repeatability(tmp_path: Path) -> None:
    completed = _command("run-shell-fill-suite", "benchmarks/shell_fill_04a2", str(tmp_path))

    assert completed.returncode == 0, completed.stderr
    summary = json.loads((tmp_path / "summary.json").read_text(encoding="utf-8"))
    assert summary["status"] == "PASS"
    assert set(summary["cases"]) == set(CASE_EXPECTATIONS)
    assert all(row["repeatability"] == "PASS" for row in summary["cases"].values())
    index = (tmp_path / "VIEW_INDEX.md").read_text(encoding="utf-8")
    assert "内腔" in index
    assert "Union_Result" in index
