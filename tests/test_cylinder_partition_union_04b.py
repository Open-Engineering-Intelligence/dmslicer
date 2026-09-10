import json
import math
import os
import subprocess
import sys
from pathlib import Path

import pytest

from dmslicer.cylinder_partition_union_04b import validate_cylinder_candidate


CASES = {
    "U04_cylinder_full_fill": {"area": 1600 * math.pi, "coverage": [1.0, 1.0], "remaining": [0, 0], "volume": 36000 * math.pi},
    "U05_cylinder_short_core": {"area": 800 * math.pi, "coverage": [0.5, 1.0], "remaining": [1, 0], "volume": 28000 * math.pi},
    "U06_cylinder_unequal_overlap": {"area": 800 * math.pi, "coverage": [0.5, 0.2], "remaining": [1, 1], "volume": 60000 * math.pi},
}


def _command(*arguments: str) -> subprocess.CompletedProcess[str]:
    environment = os.environ.copy()
    environment["PYTHONPATH"] = str(Path("src").resolve())
    return subprocess.run([sys.executable, "-m", "dmslicer", *arguments], cwd=Path.cwd(), env=environment, text=True, capture_output=True, check=False)


def test_generator_creates_tracked_cylinder_step_bundles(tmp_path: Path) -> None:
    completed = _command("generate-cylinder-fit-cases", str(tmp_path))

    assert completed.returncode == 0, completed.stderr
    assert {item.name for item in tmp_path.iterdir()} == set(CASES)
    for case_id, expected in CASES.items():
        case = tmp_path / case_id
        parameters = json.loads((case / "parameters.json").read_text(encoding="utf-8"))
        truth = json.loads((case / "expected.json").read_text(encoding="utf-8"))
        assert (case / "inputs.step").is_file()
        assert parameters["side_order"] == {"side_1": "sleeve", "side_2": "core"}
        assert truth["common_area_mm2"] == pytest.approx(expected["area"])


@pytest.mark.parametrize("case_id", sorted(CASES))
def test_cylinder_operation_measures_reimported_step_and_validates_shape(tmp_path: Path, case_id: str) -> None:
    completed = _command("run-cylinder-fit-case", f"benchmarks/cylinder_fit_04b/{case_id}", str(tmp_path / case_id))

    assert completed.returncode == 0, completed.stderr
    operation = json.loads((tmp_path / case_id / "operation.json").read_text(encoding="utf-8"))
    validation = json.loads((tmp_path / case_id / "validation.json").read_text(encoding="utf-8"))
    expected = CASES[case_id]
    assert operation["analysis_input"] == "reimported_step"
    assert operation["side_order"] == {"side_1": "sleeve", "side_2": "core"}
    assert operation["common_area_mm2"] == pytest.approx(expected["area"], abs=1e-7)
    assert operation["coverage"] == pytest.approx(expected["coverage"], abs=1e-9)
    assert [len(operation["partitions"][side]["remaining_patches"]) for side in ("side_1", "side_2")] == expected["remaining"]
    assert operation["union"]["volume_mm3"] == pytest.approx(expected["volume"], abs=1e-6)
    assert validation["status"] == "PASS"
    assert validation["actual_minus_reference_mm3"] <= 1e-6
    assert validation["reference_minus_actual_mm3"] <= 1e-6
    assert (tmp_path / case_id / "operation_debug.FCStd").is_file()


def test_negative_candidates_reject_filled_blind_hole_and_truncated_extension() -> None:
    assert validate_cylinder_candidate("U05_cylinder_short_core", "full_outer_cylinder")["status"] == "FAIL"
    assert validate_cylinder_candidate("U06_cylinder_unequal_overlap", "truncated_to_sleeve")["status"] == "FAIL"


def test_suite_publishes_chinese_view_index_and_two_process_repeatability(tmp_path: Path) -> None:
    completed = _command("run-cylinder-fit-suite", "benchmarks/cylinder_fit_04b", str(tmp_path))

    assert completed.returncode == 0, completed.stderr
    assert json.loads((tmp_path / "summary.json").read_text(encoding="utf-8"))["status"] == "PASS"
    assert "盲孔" in (tmp_path / "VIEW_INDEX.md").read_text(encoding="utf-8")
