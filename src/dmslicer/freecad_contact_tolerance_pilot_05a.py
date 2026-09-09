"""FreeCADCmd-side construction for the limited A01/A07 tolerance pilot."""

import hashlib, json, os, sys, traceback
from pathlib import Path

import FreeCAD, Import, Part


def _a01(params):
    g, delta = params["geometry"], float(params["set_signed_offset_mm"])
    lower = Part.makeBox(g["a_mm"], g["b_mm"], g["h_mm"])
    upper = Part.makeBox(g["a_mm"], g["b_mm"], g["h_mm"], FreeCAD.Vector(0, 0, g["h_mm"] + delta))
    return lower, upper


def _a07(params):
    g, delta = params["geometry"], float(params["set_signed_offset_mm"])
    shaft = Part.makeCylinder(g["shaft_radius_mm"], g["shaft_z_max_mm"] - g["shaft_z_min_mm"], FreeCAD.Vector(0, 0, g["shaft_z_min_mm"]))
    bore_radius = g["shaft_radius_mm"] + delta
    outer = Part.makeCylinder(g["sleeve_outer_radius_mm"], g["sleeve_z_max_mm"] - g["sleeve_z_min_mm"], FreeCAD.Vector(0, 0, g["sleeve_z_min_mm"]))
    bore = Part.makeCylinder(bore_radius, g["bore_cutter_z_max_mm"] - g["bore_cutter_z_min_mm"], FreeCAD.Vector(0, 0, g["bore_cutter_z_min_mm"]))
    return shaft, outer.cut(bore)


def _generate(request):
    first, second = _a01(request["parameters"]) if request["case_id"] == "A01" else _a07(request["parameters"])
    doc = FreeCAD.newDocument("TolerancePilot05AGenerator")
    try:
        for name, shape in (("Side_1", first), ("Side_2", second)):
            obj = doc.addObject("Part::Feature", name); obj.Shape = shape
        doc.recompute(); Import.export([doc.getObject("Side_1"), doc.getObject("Side_2")], request["step_path"])
        return {"valid_closed": [first.isValid() and all(shell.isClosed() for shell in first.Shells), second.isValid() and all(shell.isClosed() for shell in second.Shells)]}
    finally:
        FreeCAD.closeDocument(doc.Name)


def _objects(doc):
    return sorted([(obj.Label, obj.Shape.Solids[0]) for obj in doc.Objects if obj.TypeId == "Part::Feature" and hasattr(obj, "Shape") and len(obj.Shape.Solids) == 1], key=lambda item: item[0])


def _digest(shape):
    return "sha256:" + hashlib.sha256(shape.exportBrepToString().encode("utf-8")).hexdigest()


def _plane(face):
    surface = face.Surface
    return surface if "plane" in type(surface).__name__.lower() else None


def _cylinder(face):
    surface = face.Surface
    return surface if "cylinder" in type(surface).__name__.lower() else None


def _measure(case_id, first, second):
    if case_id == "A01":
        candidates = []
        for face_a in first.Faces:
            plane_a = _plane(face_a)
            if not plane_a or abs(plane_a.Axis.z) < 1 - 1e-7: continue
            for face_b in second.Faces:
                plane_b = _plane(face_b)
                if not plane_b or abs(plane_b.Axis.z) < 1 - 1e-7: continue
                normal_a = plane_a.Axis.normalize()
                signed = (plane_b.Position - plane_a.Position).dot(normal_a)
                candidates.append((abs(signed), signed))
        if not candidates: return {"status": "UNSUPPORTED", "reason": "opposing planar carriers not found"}
        _, signed = min(candidates)
        return {"status": "SUPPORTED", "measured_signed_offset_mm": float(signed), "measurement_kind": "parallel_planes"}
    candidates = []
    for face_a in first.Faces:
        cyl_a = _cylinder(face_a)
        if not cyl_a: continue
        for face_b in second.Faces:
            cyl_b = _cylinder(face_b)
            if not cyl_b: continue
            if cyl_a.Axis.cross(cyl_b.Axis).Length > 1e-7 or (cyl_a.Center - cyl_b.Center).cross(cyl_a.Axis).Length > 1e-7: continue
            candidates.append((abs(float(cyl_a.Radius) - float(cyl_b.Radius)), float(cyl_b.Radius) - float(cyl_a.Radius)))
    if not candidates: return {"status": "UNSUPPORTED", "reason": "coaxial cylindrical carriers not found"}
    _, signed = min(candidates)
    return {"status": "SUPPORTED", "measured_signed_offset_mm": float(signed), "measurement_kind": "coaxial_cylinders"}


def _a07_construction(first, second):
    shaft_cylinders = [float(_cylinder(face).Radius) for face in first.Faces if _cylinder(face)]
    sleeve_cylinders = [float(_cylinder(face).Radius) for face in second.Faces if _cylinder(face)]
    if not shaft_cylinders or len(sleeve_cylinders) < 2:
        return {"status": "UNSUPPORTED", "reason": "shaft or sleeve cylindrical controls not found"}
    shaft_box, sleeve_box = first.BoundBox, second.BoundBox
    shaft_radius, outer_radius = max(shaft_cylinders), max(sleeve_cylinders)
    shaft_min, shaft_max = float(shaft_box.ZMin), float(shaft_box.ZMax)
    sleeve_min, sleeve_max = float(sleeve_box.ZMin), float(sleeve_box.ZMax)
    box = Part.makeCompound([first, second]).BoundBox
    return {"status": "SUPPORTED", "shaft_radius_mm": shaft_radius, "shaft_z_min_mm": shaft_min, "shaft_z_max_mm": shaft_max, "sleeve_outer_radius_mm": outer_radius, "sleeve_bore_radius_mm": min(sleeve_cylinders), "sleeve_z_min_mm": sleeve_min, "sleeve_z_max_mm": sleeve_max, "sleeve_length_mm": sleeve_max - sleeve_min, "interface_length_mm": min(shaft_max, sleeve_max) - max(shaft_min, sleeve_min), "lower_end_clearance_mm": shaft_min - sleeve_min, "upper_end_clearance_mm": sleeve_max - shaft_max, "combined_L_mm": float((box.XLength ** 2 + box.YLength ** 2 + box.ZLength ** 2) ** 0.5), "shaft_material_volume_mm3": float(first.Volume), "sleeve_material_volume_mm3": float(second.Volume)}


def _debug(path, case_id, first, second, common, fuse, facts):
    path.parent.mkdir(parents=True, exist_ok=True)
    doc = FreeCAD.newDocument("TolerancePilot05AView")
    try:
        has_intersection = facts["geometry_state"]["exact_intersection_dimension"] in {"2D", "3D"}
        for name, shape, visible in (("Actual_Input_1", first, True), ("Actual_Input_2", second, True), ("Actual_Intersection", common, has_intersection), ("Direct_Fuse", fuse, False)):
            obj = doc.addObject("Part::Feature", name); obj.Shape = shape; obj.Visibility = visible
            if name.startswith("Actual_Input_") and obj.ViewObject is not None: obj.ViewObject.Transparency = 65
            for key in ("MeasuredDeltaMm", "EngineeringState", "ExactDimension", "SolidCount"):
                obj.addProperty("App::PropertyString", key, "Tolerance Pilot")
            obj.MeasuredDeltaMm = str(facts.get("measured_signed_offset_mm", "UNSUPPORTED")); obj.EngineeringState = str(facts.get("engineering_state", "UNSUPPORTED")); obj.ExactDimension = facts["geometry_state"]["exact_intersection_dimension"]; obj.SolidCount = str(facts["direct_fuse"]["solid_count"])
        doc.recompute(); doc.saveAs(str(path))
    finally: FreeCAD.closeDocument(doc.Name)


def _analyze(request):
    doc = FreeCAD.newDocument("TolerancePilot05AAnalysis")
    try:
        Import.insert(request["step_path"], doc.Name); sources = _objects(doc)
        if len(sources) != 2: raise RuntimeError("expected exactly two imported solids")
        _, first = sources[0]; _, second = sources[1]
        measure = _measure(request["case_id"], first, second)
        tolerance = float(request["tauE_mm"])
        common = first.common(second); volume = float(common.Volume)
        face_common = Part.Shape()
        face_areas, face_digests = [], set()
        for face_a in first.Faces:
            for face_b in second.Faces:
                candidate = face_a.common(face_b)
                for patch in candidate.Faces:
                    digest = _digest(patch)
                    if patch.Area > 1e-8 and digest not in face_digests:
                        face_digests.add(digest); face_areas.append(patch)
        face_common = Part.makeCompound(face_areas) if face_areas else Part.Shape()
        area = float(sum(patch.Area for patch in face_areas))
        dimension = "3D" if volume > 1e-6 else "2D" if area > 1e-8 else "none"
        copied_first, copied_second = first.copy(), second.copy()
        try:
            fused = copied_first.fuse(copied_second)
            direct = {"executed": True, "solid_count": len(fused.Solids), "valid": bool(fused.isValid()), "closed": bool(all(shell.isClosed() for shell in fused.Shells)), "material_volume_mm3": volume, "volume_conservation_error_mm3": float(abs(fused.Volume - (first.Volume + second.Volume - volume)))}
            direct["one_valid_connected_solid"] = direct["solid_count"] == 1 and direct["valid"] and direct["closed"]
        except Exception as error:
            fused = Part.Shape(); direct = {"executed": False, "reason": str(error), "solid_count": 0, "valid": False, "closed": False, "material_volume_mm3": volume, "volume_conservation_error_mm3": None, "one_valid_connected_solid": False}
        offset = measure.get("measured_signed_offset_mm")
        state = "UNSUPPORTED" if offset is None else ("exact" if abs(offset) <= 1e-12 else "positive_gap_within_tolerance" if 0 < offset <= tolerance + 1e-12 else "positive_gap_beyond_tolerance" if offset > 0 else "penetration_within_tolerance" if offset >= -tolerance - 1e-12 else "penetration_beyond_tolerance")
        box = Part.makeCompound([first, second]).BoundBox
        current_l = float((box.XLength ** 2 + box.YLength ** 2 + box.ZLength ** 2) ** 0.5)
        facts = {"schema_version": 1, "case_id": request["case_id"], "analysis_input": "reimported_step", "measurement": measure, "measured_signed_offset_mm": offset, "tauE_mm": tolerance, "tauK_mm": "NOT_AVAILABLE", "L_mm": current_l, "tauE_over_L": tolerance / current_l, "engineering_state": state, "geometry_state": {"minimum_distance_mm": max(0.0, float(offset)) if offset is not None else None, "material_common_volume_mm3": volume, "exact_intersection_dimension": dimension, "positive_common_area_mm2": area if dimension == "2D" else None}, "direct_fuse": direct, "geometry_digest": [_digest(first), _digest(second)]}
        if request["case_id"] == "A07": facts["construction"] = _a07_construction(first, second)
        if request.get("debug_path"): _debug(Path(request["debug_path"]), request["case_id"], first, second, face_common if dimension == "2D" else common, fused, facts)
        return facts
    finally: FreeCAD.closeDocument(doc.Name)


def _main():
    response_path = Path(os.environ["DMSLICER_FREECAD_RESPONSE"])
    try:
        request = json.loads(Path(os.environ["DMSLICER_FREECAD_REQUEST"]).read_text(encoding="utf-8"))
        if request["action"] == "generate": response = _generate(request)
        elif request["action"] == "analyze": response = _analyze(request)
        else: raise ValueError("unknown action")
        response["status"] = "SUCCEEDED"
    except Exception:
        response = {"status": "FAILED", "traceback": traceback.format_exc()}
    response_path.write_text(json.dumps(response, sort_keys=True), encoding="utf-8")


_main()
