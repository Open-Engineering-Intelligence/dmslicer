"""FreeCAD-side worker for the fixture-scoped P2 CAD evidence demo."""

from __future__ import annotations

import json
import os
import traceback
from pathlib import Path

import FreeCAD
import Part

try:
    import FreeCADGui
except ImportError:  # FreeCADCmd intentionally has no GUI module.
    FreeCADGui = None


def _write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _fixture_shape(radius_mm: float):
    block = Part.makeBox(40.0, 30.0, 12.0)
    bore = Part.makeCylinder(
        radius_mm, 12.0, FreeCAD.Vector(20.0, 15.0, 0.0)
    )
    return block.cut(bore).removeSplitter()


def _count(value: int) -> dict:
    return {"value": value, "unit": "count"}


def _measurement(value: float, unit: str) -> dict:
    return {"value": float(value), "unit": unit}


def _source_id(case_id: str) -> str:
    return f"p2-fixture/{case_id}/fixture.FCStd"


def _shape_snapshots(case_id: str, shape, radius_mm: float) -> tuple[dict, dict]:
    box = shape.BoundBox
    counts = {
        "solid_count": _count(len(shape.Solids)),
        "shell_count": _count(len(shape.Shells)),
        "face_count": _count(len(shape.Faces)),
        "edge_count": _count(len(shape.Edges)),
        "vertex_count": _count(len(shape.Vertexes)),
    }
    cylinders = []
    for face in shape.Faces:
        surface = face.Surface
        observed_radius = getattr(surface, "Radius", None)
        if observed_radius is not None and abs(float(observed_radius) - radius_mm) <= 0.001:
            cylinders.append(float(observed_radius))
    if len(cylinders) == 1:
        through_hole = {
            "status": "PROVEN",
            "count": _count(1),
            "selection": (
                "unique cylindrical face matching declared radius "
                f"{radius_mm:.6f} mm within 0.001 mm"
            ),
        }
    else:
        through_hole = {
            "status": "UNKNOWN",
            "reason": (
                "fixture-scoped radius selection found "
                f"{len(cylinders)} matching cylindrical faces"
            ),
        }
    common = {
        "schema_version": "1.0.0",
        "case_id": case_id,
        "artifact_role": "CLOSING",
        "source_artifact_id": _source_id(case_id),
    }
    geometry = {
        **common,
        "artifact_type": "geometry_semantic_snapshot",
        "length_unit": "mm",
        "semantic_binding": {
            "component_role": "fixture_body",
            "interface_role": "through_hole_wall",
            "allowed_transform": "IDENTITY",
        },
        "shape": {
            **counts,
            "area": _measurement(shape.Area, "mm2"),
            "volume": _measurement(shape.Volume, "mm3"),
            "bounding_box": {
                "x_min": _measurement(box.XMin, "mm"),
                "y_min": _measurement(box.YMin, "mm"),
                "z_min": _measurement(box.ZMin, "mm"),
                "x_max": _measurement(box.XMax, "mm"),
                "y_max": _measurement(box.YMax, "mm"),
                "z_max": _measurement(box.ZMax, "mm"),
            },
            "valid": bool(shape.isValid()),
            "closed": bool(shape.isClosed()),
        },
    }
    topology = {
        **common,
        "artifact_type": "topology_snapshot",
        "topology": {
            **counts,
            "connected_solid_count": _count(len(shape.Solids)),
            "valid": bool(shape.isValid()),
            "closed": bool(shape.isClosed()),
            "through_hole": through_hole,
            "manifold": {
                "status": "UNKNOWN",
                "reason": "manifold inference is deferred for the P2 fixture",
            },
        },
    }
    return geometry, topology


def _supported_ui(view_object, name: str, transform=lambda value: value) -> dict:
    if view_object is None or not hasattr(view_object, name):
        return {
            "status": "UNSUPPORTED",
            "reason": f"saved {name} property is unavailable in this FreeCAD build",
        }
    return {"status": "SUPPORTED", "value": transform(getattr(view_object, name))}


def _ui_snapshot(case_id: str, view_object) -> dict:
    unsupported_camera = {
        "status": "UNSUPPORTED",
        "reason": "stable per-object saved camera extraction is outside the P2 fixture contract",
    }
    return {
        "schema_version": "1.0.0",
        "artifact_type": "ui_state_snapshot",
        "case_id": case_id,
        "artifact_role": "CLOSING",
        "source_artifact_id": _source_id(case_id),
        "object_role": "fixture_body",
        "state": {
            "visibility": _supported_ui(view_object, "Visibility", bool),
            "shape_color": _supported_ui(
                view_object,
                "ShapeColor",
                lambda value: [float(item) for item in value[:3]],
            ),
            "transparency": _supported_ui(view_object, "Transparency", int),
            "display_mode": _supported_ui(view_object, "DisplayMode", str),
            "camera": unsupported_camera,
        },
    }


def _write_snapshots(output_root: Path, case_id: str, document, radius_mm: float) -> None:
    matches = [obj for obj in document.Objects if obj.Name == "FixtureBody"]
    if len(matches) != 1:
        raise RuntimeError("EXPECTED_ONE_FIXTURE_BODY")
    fixture = matches[0]
    geometry, topology = _shape_snapshots(case_id, fixture.Shape, radius_mm)
    snapshot_root = output_root / "snapshots" / case_id
    _write_json(snapshot_root / "geometry_semantic_snapshot.json", geometry)
    _write_json(snapshot_root / "topology_snapshot.json", topology)
    _write_json(snapshot_root / "ui_state_snapshot.json", _ui_snapshot(case_id, fixture.ViewObject))


def _generate_fixture_set(output_root: Path) -> dict:
    definitions = {
        "original": {"radius_mm": 4.0, "color": (0.82, 0.82, 0.82), "transparency": 0, "visible": True},
        "ui_only_changed": {"radius_mm": 4.0, "color": (0.10, 0.45, 0.90), "transparency": 60, "visible": False},
        "geometry_changed": {"radius_mm": 5.0, "color": (0.82, 0.82, 0.82), "transparency": 0, "visible": True},
    }
    for case_id, definition in definitions.items():
        case_root = output_root / "cad" / case_id
        case_root.mkdir(parents=True, exist_ok=False)
        document = FreeCAD.newDocument(f"P2_{case_id}")
        try:
            fixture = document.addObject("Part::Feature", "FixtureBody")
            fixture.Label = "Fixture Body"
            fixture.Shape = _fixture_shape(definition["radius_mm"])
            fixture.addProperty("App::PropertyString", "ComponentRole", "P2Evidence")
            fixture.addProperty("App::PropertyString", "InterfaceRole", "P2Evidence")
            fixture.addProperty("App::PropertyString", "AllowedTransform", "P2Evidence")
            fixture.ComponentRole = "fixture_body"
            fixture.InterfaceRole = "through_hole_wall"
            fixture.AllowedTransform = "IDENTITY"
            if fixture.ViewObject is None:
                raise RuntimeError("GUI_VIEW_OBJECT_UNAVAILABLE")
            fixture.ViewObject.ShapeColor = definition["color"]
            fixture.ViewObject.Transparency = definition["transparency"]
            fixture.ViewObject.Visibility = definition["visible"]
            document.recompute()
            document.saveAs(str(case_root / "fixture.FCStd"))
            fixture.Shape.exportBrep(str(case_root / "fixture.brep"))
            Part.export([fixture], str(case_root / "fixture.step"))
        finally:
            FreeCAD.closeDocument(document.Name)

        reopened = FreeCAD.openDocument(str(case_root / "fixture.FCStd"))
        try:
            _write_snapshots(output_root, case_id, reopened, definition["radius_mm"])
        finally:
            FreeCAD.closeDocument(reopened.Name)

    serialization_root = output_root / "cad" / "serialization_reopen"
    serialization_root.mkdir(parents=True, exist_ok=False)
    reopened = FreeCAD.openDocument(str(output_root / "cad/original/fixture.FCStd"))
    try:
        reopened.saveAs(str(serialization_root / "fixture.FCStd"))
    finally:
        FreeCAD.closeDocument(reopened.Name)
    serialized = FreeCAD.openDocument(str(serialization_root / "fixture.FCStd"))
    try:
        matches = [obj for obj in serialized.Objects if obj.Name == "FixtureBody"]
        if len(matches) != 1:
            raise RuntimeError("EXPECTED_ONE_FIXTURE_BODY")
        matches[0].Shape.exportBrep(str(serialization_root / "fixture.brep"))
        Part.export([matches[0]], str(serialization_root / "fixture.step"))
        _write_snapshots(output_root, "serialization_reopen", serialized, 4.0)
    finally:
        FreeCAD.closeDocument(serialized.Name)
    return {
        "status": "PASS",
        "cases": sorted(definitions),
        "freecad_version": ".".join(str(item) for item in FreeCAD.Version()[:3]),
        "occt_version": getattr(Part, "OCC_VERSION", "unknown"),
    }


def _unavailable(reason: str) -> dict:
    return {"status": "NOT_PROVEN", "reason": reason}


def _topology_counts(shape) -> tuple[int, int, int, int, int]:
    return (
        len(shape.Solids),
        len(shape.Shells),
        len(shape.Faces),
        len(shape.Edges),
        len(shape.Vertexes),
    )


def _comparison(case_id: str, role: str, first, second) -> dict:
    tolerances = [
        {"name": "linear", "value": 0.001, "unit": "mm", "role": "bounding box and minimum distance", "source": "P2-MVP fixture contract"},
        {"name": "area", "value": 0.001, "unit": "mm2", "role": "surface area delta", "source": "P2-MVP fixture contract"},
        {"name": "volume", "value": 0.001, "unit": "mm3", "role": "volume delta and Boolean differences", "source": "P2-MVP fixture contract"},
    ]
    common = {
        "schema_version": "1.0.0",
        "artifact_type": "geometry_comparison",
        "case_id": case_id,
        "comparison_role": role,
        "sha256_role": "file_and_copy_integrity_only_not_geometry_equivalence",
        "tolerances": tolerances,
        "geometry_decision_inputs": [
            "topology",
            "area",
            "volume",
            "bounding_box",
            "bidirectional_boolean_cut",
        ],
    }
    valid = all(
        (len(shape.Solids) == 1 and bool(shape.isValid()) and bool(shape.isClosed()))
        for shape in (first, second)
    )
    if not valid:
        unavailable = _unavailable("input is not a valid closed single solid")
        return {
            **common,
            "status": "GEOMETRIC_EQUIVALENCE_NOT_PROVEN",
            "method": "NOT_EVALUATED",
            "measurements": {name: unavailable for name in (
                "area_delta", "volume_delta", "max_bounding_box_delta",
                "minimum_distance", "first_minus_second_volume", "second_minus_first_volume",
            )},
            "checks": {
                "valid_closed_single_solids": False,
                **{name: unavailable for name in (
                    "topology_counts", "area_delta", "volume_delta", "bounding_box",
                    "first_minus_second", "second_minus_first",
                )},
            },
            "failed_checks": ["valid_closed_single_solids"],
            "reasons": ["INPUT_NOT_VALID_CLOSED_SINGLE_SOLID"],
        }
    try:
        area_delta = abs(float(first.Area) - float(second.Area))
        volume_delta = abs(float(first.Volume) - float(second.Volume))
        first_box, second_box = first.BoundBox, second.BoundBox
        bbox_delta = max(
            abs(float(getattr(first_box, name)) - float(getattr(second_box, name)))
            for name in ("XMin", "YMin", "ZMin", "XMax", "YMax", "ZMax")
        )
        minimum_distance = float(first.distToShape(second)[0])
        first_minus_second = float(first.cut(second).Volume)
        second_minus_first = float(second.cut(first).Volume)
    except Exception:
        unavailable = _unavailable("required B-rep operation failed")
        return {
            **common,
            "status": "GEOMETRIC_EQUIVALENCE_NOT_PROVEN",
            "method": "BREP_BOOLEAN_AND_MEASUREMENTS",
            "measurements": {name: unavailable for name in (
                "area_delta", "volume_delta", "max_bounding_box_delta",
                "minimum_distance", "first_minus_second_volume", "second_minus_first_volume",
            )},
            "checks": {
                "valid_closed_single_solids": True,
                **{name: unavailable for name in (
                    "topology_counts", "area_delta", "volume_delta", "bounding_box",
                    "first_minus_second", "second_minus_first",
                )},
            },
            "failed_checks": [],
            "reasons": ["REQUIRED_BREP_OPERATION_FAILED"],
        }
    checks = {
        "valid_closed_single_solids": True,
        "topology_counts": _topology_counts(first) == _topology_counts(second),
        "area_delta": area_delta <= 0.001,
        "volume_delta": volume_delta <= 0.001,
        "bounding_box": bbox_delta <= 0.001,
        "first_minus_second": first_minus_second <= 0.001,
        "second_minus_first": second_minus_first <= 0.001,
    }
    reason_codes = {
        "topology_counts": "TOPOLOGY_COUNTS_DIFFER",
        "area_delta": "AREA_DELTA_EXCEEDS_TOLERANCE",
        "volume_delta": "VOLUME_DELTA_EXCEEDS_TOLERANCE",
        "bounding_box": "BOUNDING_BOX_DELTA_EXCEEDS_TOLERANCE",
        "first_minus_second": "FIRST_MINUS_SECOND_VOLUME_EXCEEDS_TOLERANCE",
        "second_minus_first": "SECOND_MINUS_FIRST_VOLUME_EXCEEDS_TOLERANCE",
    }
    failed = [name for name, passed in checks.items() if not passed]
    return {
        **common,
        "status": "GEOMETRY_DIFFERENT" if failed else "GEOMETRY_EQUIVALENT",
        "method": "BREP_BOOLEAN_AND_MEASUREMENTS",
        "measurements": {
            "area_delta": _measurement(area_delta, "mm2"),
            "volume_delta": _measurement(volume_delta, "mm3"),
            "max_bounding_box_delta": _measurement(bbox_delta, "mm"),
            "minimum_distance": _measurement(minimum_distance, "mm"),
            "first_minus_second_volume": _measurement(first_minus_second, "mm3"),
            "second_minus_first_volume": _measurement(second_minus_first, "mm3"),
        },
        "checks": checks,
        "failed_checks": failed,
        "reasons": [reason_codes[name] for name in failed if name in reason_codes],
    }


def _fixture_shape_from_fcstd(path: Path):
    document = FreeCAD.openDocument(str(path))
    try:
        matches = [obj for obj in document.Objects if obj.Name == "FixtureBody"]
        if len(matches) != 1:
            raise RuntimeError("EXPECTED_ONE_FIXTURE_BODY")
        return matches[0].Shape.copy()
    finally:
        FreeCAD.closeDocument(document.Name)


def _snapshot_and_compare(output_root: Path, requested: list[str]) -> dict:
    completed = []
    if "case_a" in requested:
        first = _fixture_shape_from_fcstd(output_root / "cad/original/fixture.FCStd")
        second = _fixture_shape_from_fcstd(output_root / "cad/ui_only_changed/fixture.FCStd")
        value = _comparison("case_a", "UI_ONLY_MUTATION", first, second)
        _write_json(output_root / "comparisons/case_a_ui_only.json", value)
        completed.append("case_a")
    if "case_b" in requested:
        first = _fixture_shape_from_fcstd(output_root / "cad/original/fixture.FCStd")
        second = _fixture_shape_from_fcstd(output_root / "cad/geometry_changed/fixture.FCStd")
        value = _comparison("case_b", "GEOMETRY_MUTATION", first, second)
        _write_json(output_root / "comparisons/case_b_geometry_changed.json", value)
        completed.append("case_b")
    if "serialization" in requested:
        first = _fixture_shape_from_fcstd(output_root / "cad/original/fixture.FCStd")
        second = _fixture_shape_from_fcstd(
            output_root / "cad/serialization_reopen/fixture.FCStd"
        )
        value = _comparison(
            "serialization_reopen", "SERIALIZATION_REOPEN", first, second
        )
        _write_json(output_root / "comparisons/serialization_reopen.json", value)
        completed.append("serialization")
    return {"status": "PASS", "comparisons": completed}


def main() -> None:
    request_path = Path(os.environ["DMSLICER_CAD_REQUEST"])
    response_path = Path(os.environ["DMSLICER_CAD_RESPONSE"])
    try:
        request = json.loads(request_path.read_text(encoding="utf-8"))
        operation = request.get("operation")
        if operation == "generate_fixture_set":
            response = _generate_fixture_set(Path(request["output_root"]))
        elif operation == "snapshot_and_compare":
            response = _snapshot_and_compare(
                Path(request["output_root"]), list(request.get("comparisons", []))
            )
        else:
            raise RuntimeError("UNSUPPORTED_OPERATION")
    except Exception as error:
        response = {
            "status": "FAILED",
            "error_code": str(error) if str(error).isupper() else error.__class__.__name__,
            "traceback": traceback.format_exc(),
        }
    _write_json(response_path, response)
    if FreeCADGui is not None and FreeCAD.GuiUp:
        FreeCADGui.getMainWindow().close()


main()
