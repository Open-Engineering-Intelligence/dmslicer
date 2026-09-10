"""FreeCAD-backed CAD worker for P2-MVP geometry evidence and demos."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


GEOMETRY_EQUIVALENT = "GEOMETRY_EQUIVALENT"
GEOMETRY_DIFFERENT = "GEOMETRY_DIFFERENT"
GEOMETRIC_EQUIVALENCE_NOT_PROVEN = "GEOMETRIC_EQUIVALENCE_NOT_PROVEN"


_BLOCK_LENGTH_MM = 40.0
_BLOCK_WIDTH_MM = 30.0
_BLOCK_HEIGHT_MM = 20.0
_HOLE_AXIS_MARGIN_MM = 0.01
_DEFAULT_HOLE_RADIUS_MM = 4.0
_CHANGED_HOLE_RADIUS_MM = 5.0

_DEFAULT_TOLERANCE_MM = 0.001
_DEFAULT_TOLERANCE_MM2 = 0.001
_DEFAULT_TOLERANCE_MM3 = 0.001


@dataclass(frozen=True)
class GeometryTolerance:
    linear_mm: float = _DEFAULT_TOLERANCE_MM
    area_mm2: float = _DEFAULT_TOLERANCE_MM2
    volume_mm3: float = _DEFAULT_TOLERANCE_MM3


@dataclass
class CADSnapshot:
    source_path: Path
    solid_count: int
    shell_count: int
    face_count: int
    edge_count: int
    vertex_count: int
    valid: bool
    closed: bool
    area: float
    volume: float
    bounding_box: dict[str, float]
    connected_solid_count: int
    through_hole_wall: bool
    geometry_semantic_snapshot: dict[str, Any]
    ui_state_snapshot: dict[str, Any]
    _shape: Any = field(default=None, repr=False)

    def topology_counts(self) -> dict[str, int]:
        return {
            "solid_count": self.solid_count,
            "shell_count": self.shell_count,
            "face_count": self.face_count,
            "edge_count": self.edge_count,
            "vertex_count": self.vertex_count,
            "connected_solid_count": self.connected_solid_count,
        }

    def to_evidence_payload(self) -> dict[str, Any]:
        return {
            "geometry_semantic_snapshot": self.geometry_semantic_snapshot,
            "topology_snapshot": {
                "solid_count": self.solid_count,
                "shell_count": self.shell_count,
                "face_count": self.face_count,
                "edge_count": self.edge_count,
                "vertex_count": self.vertex_count,
                "valid": self.valid,
                "closed": self.closed,
                "solid_area": {"value": self.area, "unit": "mm2"},
                "solid_volume": {"value": self.volume, "unit": "mm3"},
                "bounding_box": self.bounding_box,
                "connected_solid_count": self.connected_solid_count,
                "through_hole_wall": self.through_hole_wall,
            },
            "ui_state_snapshot": self.ui_state_snapshot,
        }


@dataclass(frozen=True)
class GeometryComparison:
    status: str
    reasons: tuple[str, ...]
    deltas: dict[str, Any]


def _require_freecad() -> tuple[Any, Any, Any]:
    import FreeCAD as App
    import Part
    from FreeCAD import Vector

    return App, Part, Vector


def _clear_and_close(document: Any) -> None:
    if document is None:
        return
    app = document.Application
    app.closeDocument(document.Name)


def _first_shape_object(document: Any) -> Any:
    for obj in document.Objects:
        if hasattr(obj, "Shape"):
            return obj
    raise ValueError("No shape object found in FreeCAD document")


def _normalize_color(color: Any) -> tuple[float, float, float] | tuple[float, float, float, float] | None:
    if color is None:
        return None
    if isinstance(color, tuple):
        normalized = tuple(float(value) for value in color)
        if len(normalized) in {3, 4}:
            return normalized
        return None
    if isinstance(color, list):
        normalized = tuple(float(value) for value in color)
        if len(normalized) in {3, 4}:
            return normalized
        return None
    return None


def _normalize_transparency(value: Any) -> float | None:
    if value is None:
        return None
    numeric = float(value)
    return numeric / 100.0 if numeric > 1.0 else numeric


def _read_view_state(shape_object: Any) -> dict[str, Any]:
    view = shape_object.ViewObject
    color = _normalize_color(view.ShapeColor)
    transparency = _normalize_transparency(view.Transparency)
    return {
        "visibility": bool(view.Visibility),
        "color": list(color) if color is not None else [1.0, 1.0, 1.0],
        "transparency": transparency if transparency is not None else 0.0,
    }


def _fixture_identity() -> dict[str, Any]:
    return {
        "object_name": "fixture_body",
        "semantic": {
            "component_role": "fixture_body",
            "interface_role": "through_hole_wall",
        },
    }


def _build_rectangular_block_with_through_hole(
    part_module: Any,
    vector_class: Any,
    *,
    radius_mm: float,
) -> Any:
    block = part_module.makeBox(_BLOCK_LENGTH_MM, _BLOCK_WIDTH_MM, _BLOCK_HEIGHT_MM, vector_class(0, 0, 0))
    hole = part_module.makeCylinder(
        radius_mm,
        _BLOCK_HEIGHT_MM + 2 * _HOLE_AXIS_MARGIN_MM,
        vector_class(_BLOCK_LENGTH_MM / 2, _BLOCK_WIDTH_MM / 2, -_HOLE_AXIS_MARGIN_MM),
        vector_class(0, 0, 1),
    )
    return block.cut(hole)


def _is_cylinder_face(face: Any) -> bool:
    surface = getattr(face, "Surface", None)
    if surface is None:
        return False
    surface_type = getattr(surface, "TypeId", "").lower()
    if "cylinder" in surface_type:
        return True
    return "cylinder" in type(surface).__name__.lower()


def _has_through_hole_wall(shape: Any) -> bool:
    faces = list(getattr(shape, "Faces", []))
    if not faces:
        return False
    cylinder_count = sum(1 for face in faces if _is_cylinder_face(face))
    return cylinder_count >= 1


def _count_shared_vertex(v_left: Any, v_right: Any, *, tolerance: float = 1.0e-6) -> int:
    left = list(v_left)
    right = list(v_right)
    count = 0
    for left_vertex in left:
        left_point = left_vertex.Point
        for right_vertex in right:
            right_point = right_vertex.Point
            if (
                abs(float(left_point.x - right_point.x)) <= tolerance
                and abs(float(left_point.y - right_point.y)) <= tolerance
                and abs(float(left_point.z - right_point.z)) <= tolerance
            ):
                count += 1
                break
    return count


def _connected_solid_count(shape: Any) -> int:
    solids = list(getattr(shape, "Solids", []))
    if not solids:
        return 0
    if len(solids) == 1:
        return 1

    graph: dict[int, set[int]] = {index: set() for index in range(len(solids))}
    for i in range(len(solids)):
        for j in range(i + 1, len(solids)):
            if _count_shared_vertex(solids[i].Vertices, solids[j].Vertices):
                graph[i].add(j)
                graph[j].add(i)

    seen: set[int] = set()
    components = 0
    for start in range(len(solids)):
        if start in seen:
            continue
        components += 1
        stack = [start]
        seen.add(start)
        while stack:
            current = stack.pop()
            for next_index in graph[current]:
                if next_index not in seen:
                    seen.add(next_index)
                    stack.append(next_index)
    return components


def _snapshot_shape(path: Path) -> CADSnapshot:
    App, Part, Vector = _require_freecad()
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(f"CAD fixture is missing: {path}")

    document = App.openDocument(str(path))
    try:
        shape_object = _first_shape_object(document)
        shape = shape_object.Shape.copy()
        bbox = shape.BoundBox

        return CADSnapshot(
            source_path=path,
            solid_count=len(shape.Solids),
            shell_count=len(shape.Shells),
            face_count=len(shape.Faces),
            edge_count=len(shape.Edges),
            vertex_count=len(shape.Vertexes),
            valid=bool(shape.isValid()),
            closed=bool(shape.isClosed()),
            area=float(shape.Area),
            volume=float(shape.Volume),
            bounding_box={
                "xmin": float(bbox.XMin),
                "ymin": float(bbox.YMin),
                "zmin": float(bbox.ZMin),
                "xmax": float(bbox.XMax),
                "ymax": float(bbox.YMax),
                "zmax": float(bbox.ZMax),
            },
            connected_solid_count=_connected_solid_count(shape),
            through_hole_wall=_has_through_hole_wall(shape),
            geometry_semantic_snapshot={
                **_fixture_identity()["semantic"],
                "evidence_fixture": "rectangular_block_one_through_hole",
            },
            ui_state_snapshot=_read_view_state(shape_object),
            _shape=shape,
        )
    finally:
        _clear_and_close(document)


def _apply_ui_state(view_object: Any, *, color: tuple[float, float, float], transparency: float, visible: bool) -> None:
    view_object.ShapeColor = tuple(float(component) for component in color)
    view_object.Transparency = float(transparency) * 100.0
    view_object.Visibility = bool(visible)


def _create_fixture(path: Path, *, hole_radius_mm: float, color: tuple[float, float, float], transparency: float, visible: bool) -> Path:
    App, Part, Vector = _require_freecad()
    path.parent.mkdir(parents=True, exist_ok=True)

    document = App.newDocument("p2_mvp_demo")
    try:
        fixture = _build_rectangular_block_with_through_hole(
            Part,
            Vector,
            radius_mm=hole_radius_mm,
        )
        fixture_object = document.addObject("Part::Feature", _fixture_identity()["object_name"])
        fixture_object.Shape = fixture
        _apply_ui_state(fixture_object.ViewObject, color=color, transparency=transparency, visible=visible)
        document.recompute()
        document.saveAs(str(path))
    finally:
        _clear_and_close(document)
    return path


def _copy_ui_changed_fixture(original: Path, target: Path, *, color: tuple[float, float, float], transparency: float, visible: bool) -> Path:
    App, _Part, _Vector = _require_freecad()
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        target.unlink()

    import shutil

    shutil.copy2(original, target)
    document = App.openDocument(str(target))
    try:
        target_object = _first_shape_object(document)
        _apply_ui_state(target_object.ViewObject, color=color, transparency=transparency, visible=visible)
        document.recompute()
        document.saveAs(str(target))
    finally:
        _clear_and_close(document)
    return target


def generate_demo_fixtures(
    staging_root: Path,
    *,
    original_name: str = "original.FCStd",
    ui_only_changed_name: str = "ui_only_changed.FCStd",
    geometry_changed_name: str = "geometry_changed.FCStd",
) -> dict[str, Path]:
    staging_root = Path(staging_root)
    original_path = staging_root / original_name
    ui_only_changed_path = staging_root / ui_only_changed_name
    geometry_changed_path = staging_root / geometry_changed_name

    _create_fixture(
        original_path,
        hole_radius_mm=_DEFAULT_HOLE_RADIUS_MM,
        color=(1.0, 0.5, 0.0),
        transparency=0.0,
        visible=True,
    )

    _copy_ui_changed_fixture(
        original_path,
        ui_only_changed_path,
        color=(0.0, 0.7, 0.2),
        transparency=0.6,
        visible=False,
    )

    _create_fixture(
        geometry_changed_path,
        hole_radius_mm=_CHANGED_HOLE_RADIUS_MM,
        color=(1.0, 0.5, 0.0),
        transparency=0.0,
        visible=True,
    )

    return {
        "original": original_path,
        "ui_only_changed": ui_only_changed_path,
        "geometry_changed": geometry_changed_path,
    }


def snapshot_cad_file(path: Path) -> CADSnapshot:
    return _snapshot_shape(path)


def _bounding_box_delta(left: CADSnapshot, right: CADSnapshot) -> float:
    return max(
        abs(left.bounding_box[axis] - right.bounding_box[axis])
        for axis in ("xmin", "xmax", "ymin", "ymax", "zmin", "zmax")
    )


def _cut_volume(left_shape: Any, right_shape: Any) -> float:
    cut_shape = left_shape.cut(right_shape)
    if cut_shape is None:
        raise ValueError("Boolean cut returned no shape")
    if hasattr(cut_shape, "isNull") and cut_shape.isNull():
        return 0.0
    try:
        return max(0.0, float(cut_shape.Volume))
    except Exception as error:
        raise ValueError("Boolean cut volume could not be evaluated") from error


def compare_geometry_snapshots(
    left: CADSnapshot,
    right: CADSnapshot,
    *,
    tolerances: GeometryTolerance | None = None,
) -> GeometryComparison:
    tolerances = tolerances or GeometryTolerance()
    for name, value in (("linear_mm", tolerances.linear_mm), ("area_mm2", tolerances.area_mm2), ("volume_mm3", tolerances.volume_mm3)):
        if not isinstance(value, (int, float)):
            raise TypeError(f"Tolerance {name} must be numeric")
        if value < 0:
            raise ValueError(f"Tolerance {name} must be non-negative")

    if not (left.valid and right.valid):
        return GeometryComparison(
            status=GEOMETRIC_EQUIVALENCE_NOT_PROVEN,
            reasons=("At least one snapshot is invalid",),
            deltas={},
        )

    left_shape = left._shape
    right_shape = right._shape
    if left_shape is None:
        left_shape = snapshot_cad_file(left.source_path)._shape
    if right_shape is None:
        right_shape = snapshot_cad_file(right.source_path)._shape

    reasons: list[str] = []
    deltas: dict[str, Any] = {
        "area_delta_mm2": abs(left.area - right.area),
        "volume_delta_mm3": abs(left.volume - right.volume),
        "bbox_delta_mm": _bounding_box_delta(left, right),
    }

    if left.solid_count != right.solid_count:
        reasons.append("solid count differs")
    if left.shell_count != right.shell_count:
        reasons.append("shell count differs")
    if left.face_count != right.face_count:
        reasons.append("face count differs")
    if left.edge_count != right.edge_count:
        reasons.append("edge count differs")
    if left.vertex_count != right.vertex_count:
        reasons.append("vertex count differs")
    if left.connected_solid_count != right.connected_solid_count:
        reasons.append("connected solid count differs")
    if left.valid != right.valid:
        reasons.append("validity differs")
    if left.closed != right.closed:
        reasons.append("closedness differs")

    if deltas["area_delta_mm2"] > tolerances.area_mm2:
        reasons.append("area delta exceeds tolerance")
    if deltas["volume_delta_mm3"] > tolerances.volume_mm3:
        reasons.append("volume delta exceeds tolerance")
    if deltas["bbox_delta_mm"] > tolerances.linear_mm:
        reasons.append("bounding box delta exceeds tolerance")

    try:
        cut_left_volume = _cut_volume(left_shape, right_shape)
        cut_right_volume = _cut_volume(right_shape, left_shape)
        deltas["boolean_cut_left_right_mm3"] = cut_left_volume
        deltas["boolean_cut_right_left_mm3"] = cut_right_volume
        if cut_left_volume > tolerances.volume_mm3 or cut_right_volume > tolerances.volume_mm3:
            reasons.append("bidirectional Boolean cut volume exceeds tolerance")
    except Exception as error:
        return GeometryComparison(
            status=GEOMETRIC_EQUIVALENCE_NOT_PROVEN,
            reasons=(f"Boolean residual unavailable: {error}",),
            deltas=deltas,
        )

    if reasons:
        return GeometryComparison(status=GEOMETRY_DIFFERENT, reasons=tuple(reasons), deltas=deltas)

    return GeometryComparison(status=GEOMETRY_EQUIVALENT, reasons=(), deltas=deltas)


def reopen_and_snapshot(path: Path, *, target_path: Path) -> CADSnapshot:
    App, _Part, _Vector = _require_freecad()
    source = Path(path)
    target = Path(target_path)
    if not source.is_file():
        raise FileNotFoundError(f"Source CAD fixture missing: {source}")
    target.parent.mkdir(parents=True, exist_ok=True)

    document = App.openDocument(str(source))
    try:
        document.recompute()
        document.saveAs(str(target))
    finally:
        _clear_and_close(document)
    return snapshot_cad_file(target)


def get_freecad_and_occt_versions() -> dict[str, str | None]:
    App, Part, _Vector = _require_freecad()

    freecad_version = ".".join(str(token) for token in App.Version()) if hasattr(App, "Version") else None
    occt_version = None
    for candidate in ("OCC_VERSION", "OcctVersion", "OCCT_VERSION"):
        if hasattr(Part, candidate):
            occt_version = str(getattr(Part, candidate))
            break

    return {
        "freecad_version": freecad_version,
        "occt_version": occt_version,
    }

