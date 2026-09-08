import json
import os
import subprocess
import sys
from pathlib import Path

import pytest


CASES = {
    "A02": "contact_canonical_03a",
    "A08": "contact_canonical_03b",
}


def _command(*arguments: str) -> subprocess.CompletedProcess[str]:
    environment = os.environ.copy()
    environment["PYTHONPATH"] = str(Path("src").resolve())
    return subprocess.run(
        [sys.executable, "-m", "dmslicer", *arguments], cwd=Path.cwd(), env=environment,
        text=True, capture_output=True, check=False,
    )


@pytest.mark.parametrize("case_id", sorted(CASES))
def test_partition_union_exports_actual_patches_and_a_valid_connected_union(tmp_path: Path, case_id: str) -> None:
    fixture = Path("benchmarks") / CASES[case_id] / case_id / "fixture.step"
    output = tmp_path / case_id

    completed = _command("run-contact-partition-union", str(fixture), str(output))

    assert completed.returncode == 0, completed.stderr
    operation = json.loads((output / "operation.json").read_text(encoding="utf-8"))
    validation = json.loads((output / "validation.json").read_text(encoding="utf-8"))
    assert operation["analysis_input"] == "reimported_step"
    assert operation["input_unchanged"] is True
    assert operation["common_patches"]
    assert operation["union"]["solid_count"] == 1
    assert operation["union"]["valid"] is True
    assert operation["union"]["closed"] is True
    assert validation["status"] == "PASS"
    assert validation["common_not_on_union_boundary"] is True
    assert (output / "fused.step").is_file()
    assert (output / "operation_debug.FCStd").is_file()
    assert (output / "patches" / "common_1.brep").is_file()
    assert (output / "patches" / "common_1.step").is_file()
    for side in ("side_1", "side_2"):
        assert operation["partitions"][side]["area_conserved"] is True
        for patch in operation["partitions"][side]["remaining_patches"]:
            assert (output / patch["brep_file"]).is_file()
            assert (output / patch["step_file"]).is_file()
    if case_id == "A08":
        prerequisites = operation["a08_prerequisites"]
        assert prerequisites["checked_from_brep"] is True
        assert prerequisites["two_valid_closed_solids"] is True
        assert prerequisites["material_interference_volume_mm3"] == pytest.approx(0, abs=1e-6)
        assert operation["union"]["shell_count"] >= 1


def test_operation_does_not_consume_expected_json_for_actual_geometry(tmp_path: Path) -> None:
    """A changed expected manifest must not alter any 04A actual B-rep selection."""
    fixture = Path("benchmarks/contact_canonical_03a/A02/fixture.step")

    first = _command("run-contact-partition-union", str(fixture), str(tmp_path / "first"))
    second = _command("run-contact-partition-union", str(fixture), str(tmp_path / "second"))

    assert first.returncode == second.returncode == 0
    left = json.loads((tmp_path / "first" / "operation.json").read_text(encoding="utf-8"))
    right = json.loads((tmp_path / "second" / "operation.json").read_text(encoding="utf-8"))
    assert left["common_patches"] == right["common_patches"]
    assert left["partitions"] == right["partitions"]


def test_suite_writes_view_index_and_compares_two_freecad_processes(tmp_path: Path) -> None:
    output = tmp_path / "contact_partition_union_04a"

    completed = _command("run-contact-partition-union-suite", str(output))

    assert completed.returncode == 0, completed.stderr
    summary = json.loads((output / "summary.json").read_text(encoding="utf-8"))
    assert summary["status"] == "PASS"
    assert set(summary["cases"]) == set(CASES)
    for case_id in CASES:
        assert (output / case_id / "repeatability" / "repeatability.json").is_file()
        assert json.loads((output / case_id / "repeatability" / "repeatability.json").read_text(encoding="utf-8"))["status"] == "PASS"
    assert "Union_Result" in (output / "VIEW_INDEX.md").read_text(encoding="utf-8")
