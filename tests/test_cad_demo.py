from __future__ import annotations

from pathlib import Path

import pytest

from dmslicer.evidence_promotion.cad_evidence import (
    BYTE_DIFFERENT,
    BYTE_IDENTICAL,
    SEMANTIC_EQUIVALENT,
    UI_DIFFERENT,
    compare_byte_identity,
    compare_semantic_equivalence,
    compare_ui_state,
)
from dmslicer.evidence_promotion.freecad_cad_evidence import (
    GEOMETRIC_EQUIVALENCE_NOT_PROVEN,
    GEOMETRY_DIFFERENT,
    GEOMETRY_EQUIVALENT,
    GeometryTolerance,
    generate_demo_fixtures,
    get_freecad_and_occt_versions,
    reopen_and_snapshot,
    snapshot_cad_file,
    compare_geometry_snapshots,
)


pytest.importorskip("FreeCAD", reason="FreeCAD is required for CAD demo tests")


@pytest.fixture
def demo_fixtures(tmp_path: Path):
    return generate_demo_fixtures(tmp_path / "cad_demo")


def test_case_a_demo_is_ui_only_change(demo_fixtures):
    original = snapshot_cad_file(demo_fixtures["original"])
    ui_changed = snapshot_cad_file(demo_fixtures["ui_only_changed"])

    assert original.through_hole_wall is True
    assert ui_changed.through_hole_wall is True

    geometry_result = compare_geometry_snapshots(
        original,
        ui_changed,
        tolerances=GeometryTolerance(),
    )
    assert geometry_result.status == GEOMETRY_EQUIVALENT
    assert compare_semantic_equivalence(
        original.geometry_semantic_snapshot,
        ui_changed.geometry_semantic_snapshot,
    ) == SEMANTIC_EQUIVALENT
    assert compare_ui_state(original.ui_state_snapshot, ui_changed.ui_state_snapshot) == UI_DIFFERENT


def test_case_b_demo_is_real_geometry_change(demo_fixtures):
    original = snapshot_cad_file(demo_fixtures["original"])
    geometry_changed = snapshot_cad_file(demo_fixtures["geometry_changed"])

    result = compare_geometry_snapshots(
        original,
        geometry_changed,
        tolerances=GeometryTolerance(),
    )
    assert result.status == GEOMETRY_DIFFERENT
    assert any(
        "delta exceeds tolerance" in reason
        or "Boolean cut volume exceeds tolerance" in reason
        for reason in result.reasons
    )


def test_serialization_reopen_keeps_geometry(demo_fixtures, tmp_path: Path):
    source = Path(demo_fixtures["original"])
    reopened = reopen_and_snapshot(source, target_path=tmp_path / "cad_demo_reopen" / "original_reopened.FCStd")
    before = snapshot_cad_file(source)

    byte_result = compare_byte_identity(source, reopened.source_path)
    assert byte_result in (BYTE_IDENTICAL, BYTE_DIFFERENT)

    geometry_result = compare_geometry_snapshots(before, reopened, tolerances=GeometryTolerance())
    assert geometry_result.status == GEOMETRY_EQUIVALENT


def test_case_b_not_marked_by_hash(demo_fixtures):
    original = snapshot_cad_file(demo_fixtures["original"])
    geometry_changed = snapshot_cad_file(demo_fixtures["geometry_changed"])
    result = compare_geometry_snapshots(
        original,
        geometry_changed,
        tolerances=GeometryTolerance(),
    )
    assert result.status != GEOMETRIC_EQUIVALENCE_NOT_PROVEN
    assert result.status == GEOMETRY_DIFFERENT


def test_cad_worker_reports_runtime_versions():
    versions = get_freecad_and_occt_versions()
    assert "freecad_version" in versions
    assert "occt_version" in versions

