"""FreeCADCmd adapter for the frozen A07--A09 analytic curved-contact cases."""

import hashlib
import json
import math
import os
import sys
import traceback
from pathlib import Path

import FreeCAD
import Import
import Part

sys.path.insert(0, str(Path(os.environ["DMSLICER_FREECAD_SCRIPT"]).parent))
from freecad_contact_03a import _objects, _shape_digest


def _surface_family(face):
    surface = face.Surface
    description = " ".join((type(surface).__name__, str(getattr(surface, "TypeId", "")))).lower()
    for family in ("cylinder", "sphere", "cone", "plane"):
        if family in description:
            return family
    return "unknown"


def _face_patches(shape_a, shape_b, area_epsilon):
    patches = []
    for index_a, face_a in enumerate(shape_a.Faces, start=1):
        for index_b, face_b in enumerate(shape_b.Faces, start=1):
            common = face_a.common(face_b)
            for raw_index, face in enumerate(common.Faces, start=1):
                if face.Area > area_epsilon:
                    family_a, family_b = _surface_family(face_a), _surface_family(face_b)
                    patches.append(
                        {
                            "source_face_a": f"Face{index_a}",
                            "source_face_b": f"Face{index_b}",
                            "area_mm2": float(face.Area),
                            "source_face_a_area_mm2": float(face_a.Area),
                            "source_face_b_area_mm2": float(face_b.Area),
                            "support_surface_family": family_a if family_a == family_b else f"{family_a}/{family_b}",
                            "shape_digest": _shape_digest(face),
                            "shape": face,
                            "raw_common_face_index": raw_index,
                        }
                    )
    return patches


def _component_groups(patches, linear_epsilon):
    parent = list(range(len(patches)))

    def find(index):
        while parent[index] != index:
            parent[index] = parent[parent[index]]
            index = parent[index]
        return index

    def union(first, second):
        first, second = find(first), find(second)
        if first != second:
            parent[second] = first

    for first, patch_a in enumerate(patches):
        for second in range(first + 1, len(patches)):
            distance, _, _ = patch_a["shape"].distToShape(patches[second]["shape"])
            if distance <= linear_epsilon:
                union(first, second)
    groups = {}
    for index in range(len(patches)):
        groups.setdefault(find(index), []).append(index)
    return list(groups.values())


def _circle_key(edge):
    try:
        curve = edge.Curve
    except TypeError:
        return None
    description = type(curve).__name__.lower() if curve is not None else ""
    if "circle" not in description:
        return None
    center = getattr(curve, "Center", None)
    radius = getattr(curve, "Radius", None)
    if center is None or radius is None:
        return None
    return tuple(round(float(value), 7) for value in (center.x, center.y, center.z, radius))


def _component_topology(groups, patches):
    boundary_counts = []
    for group in groups:
        circles = set()
        for patch_index in group:
            for edge in patches[patch_index]["shape"].Edges:
                key = _circle_key(edge)
                if key is not None:
                    circles.add(key)
        families = {patches[patch_index]["support_surface_family"] for patch_index in group}
        if families & {"cylinder", "cone"} and len(circles) >= 2:
            boundary_counts.append(2)
        elif families == {"sphere"} and circles:
            boundary_counts.append(1)
        else:
            boundary_counts.append(max(1, len(circles)))
    component_count = len(groups)
    boundary_component_count = sum(boundary_counts)
    hole_count = max(0, boundary_component_count - component_count)
    return {
        "raw_common_face_count": len(patches),
        "patch_count": component_count,
        "component_count": component_count,
        "connectedness": "connected" if component_count == 1 else "disconnected",
        "boundary_component_count": boundary_component_count,
        "first_betti_number": hole_count,
        "hole_count": hole_count,
        "annular_or_multiply_connected": hole_count > 0,
    }


def _spherical_cavity_wall(patches, coverage_a, coverage_b):
    if not patches or patches[0]["support_surface_family"] != "sphere":
        return False
    if not (coverage_a < 1.0 - 1e-7 and abs(coverage_b - 1.0) <= 1e-7):
        return False
    face = patches[0]["source_shape_b"]
    surface = face.Surface
    center = getattr(surface, "Center", None)
    if center is None:
        return False
    u_min, u_max, v_min, v_max = face.ParameterRange
    normal = face.normalAt((u_min + u_max) / 2.0, (v_min + v_max) / 2.0)
    radial = face.CenterOfMass.sub(center)
    return normal.dot(radial) < 0


def _debug_document(debug_path, case_id, label_a, shape_a, label_b, shape_b, relation, result_shape):
    document = FreeCAD.newDocument("ContactCanonical03BDebug")
    try:
        for name, label, shape, transparency in (
            ("Body_1", label_a, shape_a, 82),
            ("Body_2", label_b, shape_b, 82),
            ("Actual_Result", "Actual contact result", result_shape, 0),
        ):
            obj = document.addObject("Part::Feature", name)
            obj.Label = label
            obj.Shape = shape
            if obj.ViewObject is not None:
                obj.ViewObject.Transparency = transparency
            if name == "Actual_Result":
                if obj.ViewObject is not None:
                    obj.ViewObject.ShapeColor = (1.0, 0.2, 0.1)
                for prop in ("CaseID", "Relation", "Dimension", "Area", "CoverageA", "CoverageB", "SourceFaceLinkage", "SurfaceFamily", "RawCommonFaces", "PatchCount", "ComponentCount", "GeometryDigest"):
                    obj.addProperty("App::PropertyString", prop, "Contact analysis")
                obj.CaseID = case_id
                obj.Relation = relation["relation"]
                obj.Dimension = relation["dimension"]
                obj.Area = str(relation.get("area_mm2", "not_applicable"))
                obj.CoverageA = str(relation.get("coverage_a", "not_applicable"))
                obj.CoverageB = str(relation.get("coverage_b", "not_applicable"))
                obj.SourceFaceLinkage = json.dumps([{"a": patch["source_face_a"], "b": patch["source_face_b"]} for patch in relation.get("patches", [])], sort_keys=True)
                obj.SurfaceFamily = relation.get("support_surface_family", "not_applicable")
                obj.RawCommonFaces = str(relation.get("raw_common_face_count", "not_applicable"))
                obj.PatchCount = str(relation.get("patch_count", "not_applicable"))
                obj.ComponentCount = str(relation.get("component_count", "not_applicable"))
                obj.GeometryDigest = relation["evidence"]["geometry_digest"]
        document.recompute()
        document.saveAs(str(debug_path))
    finally:
        FreeCAD.closeDocument(document.Name)
    reopened = FreeCAD.openDocument(str(debug_path))
    try:
        result = reopened.getObject("Actual_Result")
        if result is None:
            raise RuntimeError("debug FCStd does not contain Actual_Result")
        measured = float(result.Shape.Area)
        if abs(measured - relation["area_mm2"]) > 1e-8:
            raise RuntimeError("reopened debug result does not retain the actual area")
        return {"reopened": True, "result_object": result.Name, "measured": measured}
    finally:
        FreeCAD.closeDocument(reopened.Name)


def _generate(request):
    case_id = request["case_id"]
    scale = float(request["scale"])
    vector = FreeCAD.Vector
    if case_id == "A07":
        first = Part.makeCylinder(10, 30)
        second = Part.makeCylinder(20, 40, vector(0, 0, -5)).cut(Part.makeCylinder(10, 60, vector(0, 0, -10)))
    elif case_id == "A08":
        first = Part.makeSphere(10)
        shell = Part.makeSphere(15).cut(Part.makeSphere(10))
        second = shell.common(Part.makeBox(40, 40, 20, vector(-20, -20, 0)))
    elif case_id == "A09":
        first = Part.makeCone(10, 20, 10)
        second = Part.makeCone(10, 27, 17, vector(0, 0, -5)).cut(Part.makeCone(5, 22, 17, vector(0, 0, -5)))
    else:
        raise ValueError(f"unsupported canonical analytic case: {case_id}")
    matrix = FreeCAD.Matrix()
    matrix.scale(scale, scale, scale)
    first, second = first.transformShape(matrix), second.transformShape(matrix)
    document = FreeCAD.newDocument("ContactCanonical03BGenerator")
    try:
        first_object = document.addObject("Part::Feature", "Body_1")
        first_object.Label = "Body_1"
        first_object.Shape = first
        second_object = document.addObject("Part::Feature", "Body_2")
        second_object.Label = "Body_2"
        second_object.Shape = second
        document.recompute()
        step_path = Path(request["step_path"])
        step_path.parent.mkdir(parents=True, exist_ok=True)
        Import.export([first_object, second_object], str(step_path))
        return {"case_id": case_id, "step_path": str(step_path)}
    finally:
        FreeCAD.closeDocument(document.Name)


def _analyze(request):
    document = FreeCAD.newDocument("ContactCanonical03BAnalysis")
    try:
        Import.insert(request["step_path"], document.Name)
        sources = _objects(document)
        if len(sources) != 2:
            raise RuntimeError(f"expected exactly two imported solids, found {len(sources)}")
        (label_a, shape_a), (label_b, shape_b) = sources
        area_epsilon = float(request["tolerances"]["area_epsilon_mm2"])
        volume_epsilon = float(request["tolerances"]["volume_epsilon_mm3"])
        linear_epsilon = float(request["tolerances"]["linear_epsilon_mm"])
        common = shape_a.common(shape_b)
        if common.Volume > volume_epsilon:
            raise RuntimeError("analytic curve fixture unexpectedly has material interference")
        patches = _face_patches(shape_a, shape_b, area_epsilon)
        if not patches:
            raise RuntimeError("actual direct face common found no positive-area curved patch")
        for patch in patches:
            patch["source_shape_b"] = shape_b.Faces[int(patch["source_face_b"].removeprefix("Face")) - 1]
        groups = _component_groups(patches, linear_epsilon)
        for component_index, group in enumerate(groups, start=1):
            for patch_index in group:
                patches[patch_index]["component_index"] = component_index
        area = sum(patch["area_mm2"] for patch in patches)
        coverage_a = min(1.0, max(patch["area_mm2"] / patch["source_face_a_area_mm2"] for patch in patches))
        coverage_b = min(1.0, max(patch["area_mm2"] / patch["source_face_b_area_mm2"] for patch in patches))
        families = {patch["support_surface_family"] for patch in patches}
        if len(families) != 1:
            raise RuntimeError(f"direct common returned mixed support families: {families}")
        family = next(iter(families))
        relation_name = "solid_cavity_wall_touch" if _spherical_cavity_wall(patches, coverage_a, coverage_b) else "exact"
        relation = {
            "relation": relation_name,
            "dimension": "2D",
            "area_mm2": area,
            "coverage_a": coverage_a,
            "coverage_b": coverage_b,
            "support_surface_family": family,
            "patches": patches,
            **_component_topology(groups, patches),
        }
        result_shape = Part.makeCompound([patch["shape"] for patch in patches])
        relation["evidence"] = {"source": "actual_brep", "geometry_digest": _shape_digest(result_shape)}
        for patch in relation["patches"]:
            patch["provenance"] = {"operation": "direct_face_common", "source_face_a": patch["source_face_a"], "source_face_b": patch["source_face_b"], "geometry_digest": patch["shape_digest"]}
            del patch["shape"]
            del patch["source_shape_b"]
        debug = None
        if request.get("debug_path"):
            debug = _debug_document(Path(request["debug_path"]), request["case_id"], label_a, shape_a, label_b, shape_b, relation, result_shape)
        return {"case_id": request["case_id"], "analysis_input": "reimported_step", "imported_solid_count": 2, "source_labels": [label_a, label_b], "relation": relation, "debug": debug}
    finally:
        FreeCAD.closeDocument(document.Name)


def _main():
    response_path = Path(os.environ["DMSLICER_FREECAD_RESPONSE"])
    try:
        request = json.loads(Path(os.environ["DMSLICER_FREECAD_REQUEST"]).read_text(encoding="utf-8"))
        response = _generate(request) if request["action"] == "generate" else _analyze(request) if request["action"] == "analyze" else (_ for _ in ()).throw(ValueError(f"unknown action: {request['action']}"))
        response["status"] = "SUCCEEDED"
    except Exception:
        response = {"status": "FAILED", "traceback": traceback.format_exc()}
    response_path.write_text(json.dumps(response, sort_keys=True), encoding="utf-8")


_main()
