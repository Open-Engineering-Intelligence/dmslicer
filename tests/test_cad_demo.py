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
