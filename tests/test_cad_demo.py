from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from dmslicer.evidence_promotion.cad_evidence import compare_ui_states, generate_demo


FREECAD_GUI_AVAILABLE = bool(
    shutil.which("FreeCAD.exe")
    or shutil.which("freecad")
    or Path(r"C:\Program Files\FreeCAD 1.1\bin\FreeCAD.exe").is_file()
)
pytestmark = pytest.mark.skipif(
    not FREECAD_GUI_AVAILABLE, reason="FreeCAD GUI executable is unavailable"
)


SCHEMA_PATH = (
    Path(__file__).parents[1]
    / "docs"
    / "evidence_preservation"
    / "schemas"
    / "cad_evidence.schema.json"
)


def _cad_validator() -> Draft202012Validator:
    return Draft202012Validator(json.loads(SCHEMA_PATH.read_text(encoding="utf-8")))


def _read_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.mark.freecad
def test_demo_generates_three_distinct_reopenable_cad_sets(tmp_path: Path) -> None:
    result = generate_demo(tmp_path / "demo")
    assert result["status"] == "PASS"
    for case in ("original", "ui_only_changed", "geometry_changed"):
        case_root = tmp_path / "demo" / "cad" / case
        assert (case_root / "fixture.FCStd").is_file()
        assert (case_root / "fixture.brep").is_file()
        assert (case_root / "fixture.step").is_file()


@pytest.mark.freecad
def test_each_case_emits_three_schema_valid_snapshots(tmp_path: Path) -> None:
    generate_demo(tmp_path / "demo")
    validator = _cad_validator()
    for case in ("original", "ui_only_changed", "geometry_changed"):
        paths = [
            tmp_path / "demo/snapshots" / case / "geometry_semantic_snapshot.json",
            tmp_path / "demo/snapshots" / case / "topology_snapshot.json",
            tmp_path / "demo/snapshots" / case / "ui_state_snapshot.json",
        ]
        values = [_read_json(path) for path in paths]
        assert [value["artifact_type"] for value in values] == [
            "geometry_semantic_snapshot",
            "topology_snapshot",
            "ui_state_snapshot",
        ]
        for value in values:
            validator.validate(value)


@pytest.mark.freecad
def test_ui_properties_survive_actual_fcstd_reopen(tmp_path: Path) -> None:
    generate_demo(tmp_path / "demo")
    original = _read_json(
        tmp_path / "demo/snapshots/original/ui_state_snapshot.json"
    )
    changed = _read_json(
        tmp_path / "demo/snapshots/ui_only_changed/ui_state_snapshot.json"
    )
    assert compare_ui_states(original, changed)["status"] == "UI_DIFFERENT"


@pytest.mark.freecad
def test_case_a_proves_geometry_and_semantics_while_ui_differs(tmp_path: Path) -> None:
    result = generate_demo(tmp_path / "demo")
    case = result["case_a"]
    assert case["geometry_status"] == "GEOMETRY_EQUIVALENT"
    assert case["semantic_status"] == "SEMANTIC_EQUIVALENT"
    assert case["ui_status"] == "UI_DIFFERENT"
    assert case["byte_status"] in {"BYTE_SAME", "BYTE_DIFFERENT"}
    comparison = _read_json(tmp_path / "demo/comparisons/case_a_ui_only.json")
    _cad_validator().validate(comparison)
    assert (
        comparison["sha256_role"]
        == "file_and_copy_integrity_only_not_geometry_equivalence"
    )
    assert comparison["measurements"]["first_minus_second_volume"]["value"] <= 0.001
    assert comparison["measurements"]["second_minus_first_volume"]["value"] <= 0.001


@pytest.mark.freecad
def test_case_b_reports_actual_geometry_measurement_reasons(tmp_path: Path) -> None:
    result = generate_demo(tmp_path / "demo")
    case = result["case_b"]
    assert case["geometry_status"] == "GEOMETRY_DIFFERENT"
    comparison = _read_json(
        tmp_path / "demo/comparisons/case_b_geometry_changed.json"
    )
    _cad_validator().validate(comparison)
    assert "SHA" not in " ".join(comparison["reasons"]).upper()
    assert any(
        check in comparison["failed_checks"]
        for check in (
            "area_delta",
            "volume_delta",
            "first_minus_second",
            "second_minus_first",
        )
    )
    assert comparison["measurements"]["volume_delta"]["unit"] == "mm3"


@pytest.mark.freecad
def test_serialization_reopen_geometry_is_not_decided_by_bytes(tmp_path: Path) -> None:
    result = generate_demo(tmp_path / "demo")
    serialization = result["serialization"]
    assert serialization["byte_status"] in {"BYTE_SAME", "BYTE_DIFFERENT"}
    assert serialization["geometry_status"] == "GEOMETRY_EQUIVALENT"
    assert serialization["geometry_decision_inputs"] == [
        "topology",
        "area",
        "volume",
        "bounding_box",
        "bidirectional_boolean_cut",
    ]
    _cad_validator().validate(
        _read_json(tmp_path / "demo/comparisons/serialization_reopen.json")
    )
