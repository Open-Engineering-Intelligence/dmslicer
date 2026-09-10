import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from dmslicer.contact_partition_union_04a import evaluate_partition_union_validation


CASES = {
    "A02": "contact_canonical_03a",
    "A08": "contact_canonical_03b",
}


def test_production_validation_rejects_excess_volume_error() -> None:
    """Catches volume_error_mm3 being recorded but omitted from overall status."""
    facts = {
        "common_not_on_union_boundary": True,
        "common_not_on_reimported_boundary": True,
        "input_material_retained": True,
        "no_added_material": True,
        "volume_error_mm3": 1.1e-6,
        "solid_count": 1,
        "valid": True,
        "closed": True,
        "roundtrip_solid_count": 1,
        "roundtrip_valid": True,
        "roundtrip_volume_error_mm3": 0.0,
    }

    validation = evaluate_partition_union_validation(facts, volume_epsilon_mm3=1e-6)

    assert validation["status"] == "FAIL"
    assert {failure["kind"] for failure in validation["failures"]} == {"volume_error_mm3"}


def test_production_validation_rejects_invalid_or_disconnected_union() -> None:
    """Catches solid connectivity, validity, or closure being recorded but not gated."""
    facts = {
        "common_not_on_union_boundary": True, "common_not_on_reimported_boundary": True,
        "input_material_retained": True, "no_added_material": True, "volume_error_mm3": 0.0,
        "solid_count": 2, "valid": False, "closed": False,
        "roundtrip_solid_count": 1, "roundtrip_valid": True, "roundtrip_volume_error_mm3": 0.0,
    }

    validation = evaluate_partition_union_validation(facts, volume_epsilon_mm3=1e-6)

    assert validation["status"] == "FAIL"
    assert {failure["kind"] for failure in validation["failures"]} == {"solid_count", "valid", "closed"}


def test_validation_cli_returns_nonzero_for_excess_volume_error(tmp_path: Path) -> None:
    """Catches the CLI ignoring a FAIL returned by the production final status gate."""
    facts = {
        "common_not_on_union_boundary": True, "common_not_on_reimported_boundary": True,
        "input_material_retained": True, "no_added_material": True, "volume_error_mm3": 2e-6,
        "solid_count": 1, "valid": True, "closed": True,
        "roundtrip_solid_count": 1, "roundtrip_valid": True, "roundtrip_volume_error_mm3": 0.0,
    }
    facts_path = tmp_path / "facts.json"
    facts_path.write_text(json.dumps(facts), encoding="utf-8")

    completed = _command("validate-contact-partition-union-facts", str(facts_path), "1e-6")

    assert completed.returncode != 0
    assert "volume_error_mm3" in completed.stderr


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
