"""FreeCADCmd adapter for frozen A11/A12 contact-interface topology cases."""

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


def _face_patches(shape_a, shape_b, area_epsilon):
    raw = []
    for index_a, face_a in enumerate(shape_a.Faces, start=1):
        for index_b, face_b in enumerate(shape_b.Faces, start=1):
            common = face_a.common(face_b)
            for raw_index, face in enumerate(common.Faces, start=1):
                if face.Area > area_epsilon:
                    raw.append({
                        "source_face_a": f"Face{index_a}", "source_face_b": f"Face{index_b}",
                        "area_mm2": float(face.Area), "shape_digest": _shape_digest(face),
                        "shape": face, "raw_common_face_index": raw_index,
                    })
    return raw


def _contract_patches(raw):
    patches = []
    by_geometry = {}
    for evidence in raw:
        key = evidence["shape_digest"]
        patch = by_geometry.get(key)
        linkage = {"source_face_a": evidence["source_face_a"], "source_face_b": evidence["source_face_b"]}
        if patch is None:
            patch = {"shape": evidence["shape"], "area_mm2": evidence["area_mm2"], "shape_digest": key, "source_face_linkage": []}
            by_geometry[key] = patch
            patches.append(patch)
        if linkage not in patch["source_face_linkage"]:
            patch["source_face_linkage"].append(linkage)
    for patch in patches:
        patch["source_face_linkage"].sort(key=lambda link: (link["source_face_a"], link["source_face_b"]))
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
    grouped = {}
    for index in range(len(patches)):
        grouped.setdefault(find(index), []).append(index)
    return [grouped[key] for key in sorted(grouped)]


def _wire_descriptor(wire):
    try:
        enclosed_area = float(Part.Face(wire).Area)
    except Exception:
        enclosed_area = 0.0
    return {
        "geometry_digest": _shape_digest(wire), "edge_count": len(wire.Edges),
        "length_mm": float(wire.Length), "enclosed_area_mm2": enclosed_area,
    }


def _component_boundary_loops(component_patches):
    # A wire occurs only once on a component exterior in these trimmed-face
    # results.  Shared interiors occur twice and are removed before topology is
    # counted; this keeps face splits from becoming false boundaries.
    candidates = []
    for patch in component_patches:
        candidates.extend(_wire_descriptor(wire) for wire in patch["shape"].Wires)
    candidates.sort(key=lambda loop: (-loop["enclosed_area_mm2"], loop["geometry_digest"]))
    for index, loop in enumerate(candidates):
        loop["kind"] = "outer" if index == 0 else "hole"
    return candidates


def _coverage(patches, shapes_a, shapes_b):
    def side(index, shapes, key):
        used = {}
        for patch in patches:
            for linkage in patch["source_face_linkage"]:
                face_key = linkage[key]
                face_index = int(face_key.removeprefix("Face")) - 1
                used[face_key] = float(shapes[face_index].Area)
        denominator = sum(used.values())
        return sum(patch["area_mm2"] for patch in patches) / denominator if denominator else 0.0
    return min(1.0, _coverage_side(patches, shapes_a, "source_face_a")), min(1.0, _coverage_side(patches, shapes_b, "source_face_b"))


def _coverage_side(patches, shapes, linkage_key):
    used = {}
    numerator_by_face = {}
    for patch in patches:
        for linkage in patch["source_face_linkage"]:
            face_key = linkage[linkage_key]
            face_index = int(face_key.removeprefix("Face")) - 1
            used[face_key] = float(shapes[face_index].Area)
            numerator_by_face[face_key] = numerator_by_face.get(face_key, 0.0) + patch["area_mm2"]
    return sum(numerator_by_face.values()) / sum(used.values()) if used else 0.0


def _debug_document(debug_path, case_id, label_a, shape_a, label_b, shape_b, relation, component_shapes, boundary_shapes):
    document = FreeCAD.newDocument("ContactCanonical03CDebug")
    try:
        for name, label, shape, transparency in (("Body_1", label_a, shape_a, 82), ("Body_2", label_b, shape_b, 82)):
            obj = document.addObject("Part::Feature", name)
            obj.Label, obj.Shape = label, shape
            if obj.ViewObject is not None:
                obj.ViewObject.Transparency = transparency
        result = document.addObject("Part::Feature", "Actual_Result")
        result.Label, result.Shape = "Actual contact result", Part.makeCompound(component_shapes)
        if result.ViewObject is not None:
            result.ViewObject.ShapeColor = (1.0, 0.2, 0.1)
        for prop in ("CaseID", "Relation", "Dimension", "Area", "CoverageA", "CoverageB", "SourceFaceLinkage", "RawCommonFaces", "PatchCount", "ComponentCount", "BoundaryComponentCount", "HoleCount", "GeometryDigest"):
            result.addProperty("App::PropertyString", prop, "Contact analysis")
        result.CaseID, result.Relation, result.Dimension = case_id, relation["relation"], relation["dimension"]
        result.Area, result.CoverageA, result.CoverageB = str(relation["area_mm2"]), str(relation["coverage_a"]), str(relation["coverage_b"])
        result.SourceFaceLinkage = json.dumps([patch["source_face_linkage"] for patch in relation["patches"]], sort_keys=True)
        result.RawCommonFaces, result.PatchCount, result.ComponentCount = str(relation["raw_common_face_count"]), str(relation["patch_count"]), str(relation["component_count"])
        result.BoundaryComponentCount, result.HoleCount = str(relation["boundary_component_count"]), str(relation["hole_count"])
        result.GeometryDigest = relation["evidence"]["geometry_digest"]
        for index, (component, shape) in enumerate(zip(relation["components"], component_shapes), start=1):
            obj = document.addObject("Part::Feature", f"Component_{index}")
            obj.Label, obj.Shape = f"Component_{index} actual contact", shape
            if obj.ViewObject is not None:
                obj.ViewObject.ShapeColor = (1.0, 0.5, 0.0)
            for prop in ("Area", "SourceFaceLinkage", "BoundaryLoops"):
                obj.addProperty("App::PropertyString", prop, "Contact analysis")
            obj.Area, obj.SourceFaceLinkage, obj.BoundaryLoops = str(component["area_mm2"]), json.dumps(component["source_face_linkage"], sort_keys=True), json.dumps(component["boundary_loops"], sort_keys=True)
        for index, shape in enumerate(boundary_shapes, start=1):
            obj = document.addObject("Part::Feature", f"Boundary_{index}")
            obj.Label, obj.Shape = f"Actual boundary {index}", shape
            if obj.ViewObject is not None:
                obj.ViewObject.LineColor, obj.ViewObject.LineWidth = (1.0, 1.0, 0.0), 3.0
        document.recompute()
        Path(debug_path).parent.mkdir(parents=True, exist_ok=True)
        document.saveAs(str(debug_path))
    finally:
        FreeCAD.closeDocument(document.Name)
    reopened = FreeCAD.openDocument(str(debug_path))
    try:
        result = reopened.getObject("Actual_Result")
        if result is None or reopened.getObject("Component_1") is None:
            raise RuntimeError("debug FCStd does not retain actual components")
        measured = float(result.Shape.Area)
        if abs(measured - relation["area_mm2"]) > 1e-8:
            raise RuntimeError("reopened debug result does not retain actual area")
        return {"reopened": True, "result_object": result.Name, "measured": measured}
    finally:
        FreeCAD.closeDocument(reopened.Name)


def _generate(request):
    vector, scale, case_id = FreeCAD.Vector, float(request["scale"]), request["case_id"]
    plate = Part.makeBox(60, 40, 5, vector(0, 0, -5)) if case_id == "A11" else Part.makeBox(50, 50, 5, vector(-25, -25, -5))
    if case_id == "A11":
        left = Part.makeBox(12, 16, 15, vector(6, 12, 0))
        right = Part.makeBox(12, 16, 15, vector(42, 12, 0))
        bridge = Part.makeBox(48, 8, 5, vector(6, 16, 10))
        contact_body = left.fuse(right).fuse(bridge).removeSplitter()
    elif case_id == "A12":
        contact_body = Part.makeCylinder(20, 10).cut(Part.makeCylinder(10, 10))
    else:
        raise ValueError(f"unsupported canonical topology case: {case_id}")
    matrix = FreeCAD.Matrix()
    matrix.scale(scale, scale, scale)
    plate, contact_body = plate.transformGeometry(matrix), contact_body.transformGeometry(matrix)
    document = FreeCAD.newDocument("ContactCanonical03CGenerator")
    try:
        first, second = document.addObject("Part::Feature", "Body_1"), document.addObject("Part::Feature", "Body_2")
        first.Label, first.Shape, second.Label, second.Shape = "Body_1", plate, "Body_2", contact_body
        document.recompute()
        step_path = Path(request["step_path"])
        step_path.parent.mkdir(parents=True, exist_ok=True)
        Import.export([first, second], str(step_path))
        return {"case_id": case_id, "step_path": str(step_path)}
    finally:
        FreeCAD.closeDocument(document.Name)


def _analyze(request):
    document = FreeCAD.newDocument("ContactCanonical03CAnalysis")
    try:
        Import.insert(request["step_path"], document.Name)
        sources = _objects(document)
        if len(sources) != 2:
            raise RuntimeError(f"expected two imported bodies, found {len(sources)}")
        (label_a, shape_a), (label_b, shape_b) = sources
        if len(shape_a.Solids) != 1 or len(shape_b.Solids) != 1:
            raise RuntimeError("frozen topology fixture did not re-import as two connected solids")
        raw = _face_patches(shape_a, shape_b, float(request["tolerances"]["area_epsilon_mm2"]))
        if request.get("reverse_raw_order"):
            raw.reverse()
        if not raw:
            raise RuntimeError("actual direct face common found no positive-area interface")
        patches = _contract_patches(raw)
        patches.sort(key=lambda patch: patch["shape_digest"])
        groups = _component_groups(patches, float(request["tolerances"]["linear_epsilon_mm"]))
        component_records = []
        for group in groups:
            component_patches = [patches[index] for index in group]
            shape = Part.makeCompound([patch["shape"] for patch in component_patches])
            loops = _component_boundary_loops(component_patches)
            linkage = sorted({(link["source_face_a"], link["source_face_b"]) for patch in component_patches for link in patch["source_face_linkage"]})
            component_records.append({
                "patch_indices": group,
                "area_mm2": sum(patch["area_mm2"] for patch in component_patches),
                "boundary_loops": loops,
                "source_face_linkage": [{"source_face_a": a, "source_face_b": b} for a, b in linkage],
                "geometry_digest": _shape_digest(shape),
                "shape": shape,
            })
        component_records.sort(key=lambda record: record["geometry_digest"])
        components, component_shapes, boundary_shapes = [], [], []
        for component_index, record in enumerate(component_records, start=1):
            component_id = f"Component_{component_index}"
            for patch_index in record["patch_indices"]:
                patches[patch_index]["component_id"] = component_id
            component_shapes.append(record.pop("shape"))
            boundary_shapes.extend(edge for patch_index in record["patch_indices"] for wire in patches[patch_index]["shape"].Wires for edge in wire.Edges)
            record["component_id"] = component_id
            record["patch_indices"] = [patch_index + 1 for patch_index in record["patch_indices"]]
            components.append(record)
        coverage_a, coverage_b = _coverage(patches, shape_a.Faces, shape_b.Faces)
        boundary_count = sum(len(component["boundary_loops"]) for component in components)
        hole_count = sum(sum(loop["kind"] == "hole" for loop in component["boundary_loops"]) for component in components)
        relation = {
            "relation": "exact", "dimension": "2D", "support_surface_family": "plane",
            "raw_common_face_count": len(raw), "patch_count": len(patches), "component_count": len(components),
            "connectedness": "connected" if len(components) == 1 else "disconnected",
            "boundary_component_count": boundary_count, "first_betti_number": hole_count, "hole_count": hole_count,
            "annular_or_multiply_connected": hole_count > 0,
            "area_mm2": sum(patch["area_mm2"] for patch in patches), "coverage_a": coverage_a, "coverage_b": coverage_b,
            "raw_common_faces": [{key: value for key, value in evidence.items() if key != "shape"} for evidence in raw],
            "patches": [{key: value for key, value in patch.items() if key != "shape"} for patch in patches],
            "components": components,
        }
        result_shape = Part.makeCompound(component_shapes)
        relation["evidence"] = {"source": "actual_brep_direct_common", "geometry_digest": _shape_digest(result_shape)}
        debug = _debug_document(Path(request["debug_path"]), request["case_id"], label_a, shape_a, label_b, shape_b, relation, component_shapes, boundary_shapes) if request.get("debug_path") else None
        return {
            "case_id": request["case_id"], "analysis_input": "reimported_step", "imported_body_count": 2,
            "imported_solid_counts": [len(shape_a.Solids), len(shape_b.Solids)], "source_labels": [label_a, label_b],
            "relation": relation, "debug": debug,
        }
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
