"""FreeCADCmd adapter for the semantic-free 03A pairwise contact cases."""

import hashlib
import json
import os
import sys
import traceback
from pathlib import Path

import FreeCAD
import Import
import Part


def _shape_digest(shape):
    return "sha256:" + hashlib.sha256(shape.exportBrepToString().encode("utf-8")).hexdigest()


def _objects(document):
    objects = []
    for obj in document.Objects:
        if obj.TypeId == "Part::Feature" and hasattr(obj, "Shape") and len(obj.Shape.Solids) == 1:
            objects.append((obj.Label, obj.Shape.Solids[0]))
    return sorted(objects, key=lambda item: item[0])


def _face_patches(shape_a, shape_b, area_epsilon):
    patches = []
    for index_a, face_a in enumerate(shape_a.Faces, start=1):
        for index_b, face_b in enumerate(shape_b.Faces, start=1):
            common = face_a.common(face_b)
            for patch_index, face in enumerate(common.Faces, start=1):
                if face.Area > area_epsilon:
                    patches.append(
                        {
                            "source_face_a": f"Face{index_a}",
                            "source_face_b": f"Face{index_b}",
                            "area_mm2": float(face.Area),
                            "source_face_a_area_mm2": float(face_a.Area),
                            "source_face_b_area_mm2": float(face_b.Area),
                            "shape_digest": _shape_digest(face),
                            "shape": face,
                            "patch_index": patch_index,
                        }
                    )
    return patches


def _debug_document(debug_path, case_id, label_a, shape_a, label_b, shape_b, relation, result_shape):
    document = FreeCAD.newDocument("ContactCanonical03ADebug")
    try:
        for name, label, shape, transparency in (
            ("Body_1", label_a, shape_a, 78),
            ("Body_2", label_b, shape_b, 78),
            ("Actual_Result", "Actual contact / interference", result_shape, 0),
        ):
            obj = document.addObject("Part::Feature", name)
            obj.Label = label
            obj.Shape = shape
            if obj.ViewObject is not None:
                obj.ViewObject.Transparency = transparency
            if name == "Actual_Result":
                if obj.ViewObject is not None:
                    obj.ViewObject.ShapeColor = (1.0, 0.2, 0.1)
                for prop in ("CaseID", "Relation", "Dimension", "Area", "Length", "Volume", "CoverageA", "CoverageB", "ProvenanceScope", "GeometryDigest"):
                    obj.addProperty("App::PropertyString", prop, "Contact analysis")
                obj.CaseID = case_id
                obj.Relation = relation["relation"]
                obj.Dimension = relation["dimension"]
                obj.Area = str(relation.get("area_mm2", "not_applicable"))
                obj.Length = str(relation.get("length_mm", "not_applicable"))
                obj.Volume = str(relation.get("volume_mm3", "not_applicable"))
                obj.CoverageA = str(relation.get("coverage_a", "not_applicable"))
                obj.CoverageB = str(relation.get("coverage_b", "not_applicable"))
                obj.ProvenanceScope = "actual_brep_direct_common"
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
        measured = float(result.Shape.Volume if relation["dimension"] == "3D" else result.Shape.Area if relation["dimension"] == "2D" else result.Shape.Length if relation["dimension"] == "1D" else len(result.Shape.Vertexes))
        return {"reopened": True, "result_object": result.Name, "measured": measured}
    finally:
        FreeCAD.closeDocument(reopened.Name)


def _generate(request):
    case_id = request["case_id"]
    scale = float(request["scale"])
    params = request["parameters"]
    vector = FreeCAD.Vector
    if case_id == "A01":
        a = Part.makeBox(20, 20, 10)
        b = Part.makeBox(20, 20, 10, vector(0, 0, 10))
    elif case_id == "A02":
        a = Part.makeBox(20, 20, 10)
        b = Part.makeBox(20, 20, 10, vector(8, 0, 10))
    elif case_id == "A03":
        a = Part.makeBox(20, 20, 10)
        b = Part.makeBox(10, 8, 10, vector(5, 6, 10))
    elif case_id == "A04":
        a = Part.makeBox(60, 60, 10, vector(-30, -30, -10))
        b = Part.makeSphere(10, vector(0, 0, 10))
    elif case_id == "A05":
        a = Part.makeBox(20, 10, 20)
        b = Part.makeBox(10, 20, 20, vector(20, 10, 0))
    elif case_id == "A06":
        a = Part.makeBox(20, 20, 20)
        b = Part.makeBox(20, 20, 20, vector(8, 6, 4))
    else:
        raise ValueError(f"unsupported canonical case: {case_id}")
    matrix = FreeCAD.Matrix()
    matrix.scale(scale, scale, scale)
    a = a.transformGeometry(matrix)
    b = b.transformGeometry(matrix)
    document = FreeCAD.newDocument("ContactCanonical03AGenerator")
    try:
        first = document.addObject("Part::Feature", "Body_1")
        first.Label = "Body_1"
        first.Shape = a
        second = document.addObject("Part::Feature", "Body_2")
        second.Label = "Body_2"
        second.Shape = b
        document.recompute()
        step_path = Path(request["step_path"])
        step_path.parent.mkdir(parents=True, exist_ok=True)
        Import.export([first, second], str(step_path))
        return {"case_id": case_id, "step_path": str(step_path), "parameters": params}
    finally:
        FreeCAD.closeDocument(document.Name)


def _analyze(request):
    document = FreeCAD.newDocument("ContactCanonical03AAnalysis")
    try:
        Import.insert(request["step_path"], document.Name)
        sources = _objects(document)
        if len(sources) != 2:
            raise RuntimeError(f"expected exactly two imported solids, found {len(sources)}")
        (label_a, shape_a), (label_b, shape_b) = sources
        area_epsilon = float(request["tolerances"]["area_epsilon_mm2"])
        length_epsilon = float(request["tolerances"]["linear_epsilon_mm"])
        volume_epsilon = float(request["tolerances"]["volume_epsilon_mm3"])
        common = shape_a.common(shape_b)
        section = shape_a.section(shape_b)
        if common.Volume > volume_epsilon:
            relation = {"relation": "solid_material_interference", "dimension": "3D", "volume_mm3": float(common.Volume)}
            result_shape = common
        else:
            patches = _face_patches(shape_a, shape_b, area_epsilon)
            if patches:
                area = sum(patch["area_mm2"] for patch in patches)
                coverage_a = max(patch["area_mm2"] / patch["source_face_a_area_mm2"] for patch in patches)
                coverage_b = max(patch["area_mm2"] / patch["source_face_b_area_mm2"] for patch in patches)
                if abs(coverage_a - 1.0) <= 1e-7 and abs(coverage_b - 1.0) <= 1e-7:
                    relation_name = "full_full"
                elif abs(coverage_a - 1.0) <= 1e-7 or abs(coverage_b - 1.0) <= 1e-7:
                    relation_name = "small_face_contained_in_large_face"
                else:
                    relation_name = "partial_partial"
                relation = {"relation": relation_name, "dimension": "2D", "area_mm2": area, "coverage_a": coverage_a, "coverage_b": coverage_b, "patches": patches}
                result_shape = Part.makeCompound([patch["shape"] for patch in patches])
            elif section.Length > length_epsilon:
                relation = {"relation": "edge_touch", "dimension": "1D", "length_mm": float(section.Length)}
                result_shape = section
            elif section.Vertexes:
                relation = {"relation": "point_touch", "dimension": "0D", "point_count": len(section.Vertexes), "points_mm": [[float(v.Point.x), float(v.Point.y), float(v.Point.z)] for v in section.Vertexes]}
                result_shape = section
            else:
                distance, point_pairs, _ = shape_a.distToShape(shape_b)
                if distance > length_epsilon or not point_pairs:
                    raise RuntimeError("B-rep common, section, and near-zero distance found no dimensional evidence")
                points = sorted({tuple(round(float(value), 9) for value in point_a) for point_a, _ in point_pairs})
                result_shape = Part.makeCompound([Part.Vertex(FreeCAD.Vector(*point)) for point in points])
                relation = {"relation": "point_touch", "dimension": "0D", "point_count": len(points), "points_mm": [list(point) for point in points], "distance_mm": float(distance)}
        relation["evidence"] = {"source": "actual_brep", "geometry_digest": _shape_digest(result_shape)}
        if "patches" in relation:
            for patch in relation["patches"]:
                patch["provenance"] = {"operation": "direct_face_common", "source_face_a": patch["source_face_a"], "source_face_b": patch["source_face_b"], "geometry_digest": patch["shape_digest"]}
                del patch["shape"]
        debug_path = request.get("debug_path")
        debug = None
        if debug_path:
            debug = _debug_document(Path(debug_path), request["case_id"], label_a, shape_a, label_b, shape_b, relation, result_shape)
        return {"case_id": request["case_id"], "analysis_input": "reimported_step", "imported_solid_count": 2, "source_labels": [label_a, label_b], "relation": relation, "debug": debug}
    finally:
        FreeCAD.closeDocument(document.Name)


def _main():
    response_path = Path(os.environ["DMSLICER_FREECAD_RESPONSE"])
    try:
        request = json.loads(Path(os.environ["DMSLICER_FREECAD_REQUEST"]).read_text(encoding="utf-8"))
        if request["action"] == "generate":
            response = _generate(request)
        elif request["action"] == "analyze":
            response = _analyze(request)
        else:
            raise ValueError(f"unknown action: {request['action']}")
        response["status"] = "SUCCEEDED"
    except Exception:
        response = {"status": "FAILED", "traceback": traceback.format_exc()}
    response_path.write_text(json.dumps(response, sort_keys=True), encoding="utf-8")


if __name__ == "__main__":
    _main()
