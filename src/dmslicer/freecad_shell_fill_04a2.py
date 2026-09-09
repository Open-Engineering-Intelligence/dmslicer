"""FreeCAD/OpenCASCADE implementation of the bounded 04A2 shell-fill cases."""

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
from freecad_contact_03a import _objects


def _digest(shape):
    return "sha256:" + hashlib.sha256(shape.exportBrepToString().encode("utf-8")).hexdigest()


def _sphere(radius, lower=-90.0, upper=90.0):
    return Part.makeSphere(radius, FreeCAD.Vector(0, 0, 0), FreeCAD.Vector(0, 0, 1), lower, upper, 360.0)


def _inputs(case_id, outer, inner):
    full_shell = _sphere(outer).cut(_sphere(inner))
    upper_shell = _sphere(outer, 0.0, 90.0).cut(_sphere(inner, 0.0, 90.0))
    if case_id == "U01_sphere_full_fill":
        return full_shell, _sphere(inner)
    if case_id == "U02_sphere_half_fill":
        return upper_shell, _sphere(inner, 0.0, 90.0)
    if case_id == "U03_sphere_partial_fill":
        return full_shell, _sphere(inner, 0.0, 90.0)
    raise ValueError(f"unsupported shell-fill case: {case_id}")


def _reference(case_id, outer, inner):
    if case_id == "U01_sphere_full_fill":
        return _sphere(outer)
    if case_id == "U02_sphere_half_fill":
        return _sphere(outer, 0.0, 90.0)
    if case_id == "U03_sphere_partial_fill":
        return _sphere(outer).cut(_sphere(inner, -90.0, 0.0))
    raise ValueError(f"unsupported shell-fill case: {case_id}")


def _is_sphere_radius(face, radius, linear_epsilon):
    surface = face.Surface
    if "sphere" not in type(surface).__name__.lower():
        return False
    center = getattr(surface, "Center", None)
    return center is not None and center.Length <= linear_epsilon and abs(float(surface.Radius) - radius) <= linear_epsilon


def _face_common(carrier_a, carrier_b, area_epsilon):
    records, seen = [], set()
    for ia, face_a in carrier_a:
        for ib, face_b in carrier_b:
            for face in face_a.common(face_b).Faces:
                if face.Area <= area_epsilon:
                    continue
                digest = _digest(face)
                if digest in seen:
                    continue
                seen.add(digest)
                records.append({"id": f"C_{len(records) + 1}", "source_face_side_1": f"Face{ia}", "source_face_side_2": f"Face{ib}", "area_mm2": float(face.Area), "digest": digest, "shape": face})
    return records


def _remaining(carriers, common_shapes, area_epsilon):
    common = Part.makeCompound(common_shapes)
    pieces = []
    for _, carrier in carriers:
        pieces.extend(face for face in carrier.cut(common).Faces if face.Area > area_epsilon)
    unique = []
    seen = set()
    for face in pieces:
        digest = _digest(face)
        if digest not in seen:
            seen.add(digest); unique.append(face)
    return unique


def _export_shapes(document, output, prefix, shapes):
    exported = []
    for index, shape in enumerate(shapes, 1):
        name = f"{prefix}_{index}"
        brep = output / "patches" / f"{name}.brep"
        step = output / "patches" / f"{name}.step"
        brep.parent.mkdir(parents=True, exist_ok=True)
        shape.exportBrep(str(brep))
        obj = document.addObject("Part::Feature", f"Export_{name}"); obj.Shape = shape
        Import.export([obj], str(step)); document.removeObject(obj.Name)
        exported.append({"id": name, "area_mm2": float(shape.Area), "digest": _digest(shape), "brep_file": str(brep.relative_to(output)).replace("\\", "/"), "step_file": str(step.relative_to(output)).replace("\\", "/")})
    return exported


def _props(obj, values):
    for name, value in values.items():
        obj.addProperty("App::PropertyString", name, "04A2 shell fill")
        setattr(obj, name, str(value))


def _debug(output, operation, shell, core, common, remaining_1, remaining_2, union):
    doc = FreeCAD.newDocument("ShellFill04A2Debug")
    try:
        originals = doc.addObject("App::DocumentObjectGroup", "Originals")
        partitions = doc.addObject("App::DocumentObjectGroup", "Partitions")
        union_group = doc.addObject("App::DocumentObjectGroup", "Union_Result")
        for name, shape, structure in (("Side_1_Shell", shell, operation["input_structure"]["side_1"]), ("Side_2_Core", core, operation["input_structure"]["side_2"])):
            obj = doc.addObject("Part::Feature", name); obj.Shape = shape
            _props(obj, {"InputStructure": structure, "InputStepHash": operation["input_step_sha256"]})
            originals.addObject(obj); obj.Visibility = False
        for name, shape, state in (("Common_Interface", Part.makeCompound(common), "NON_EMPTY"), ("Side_1_Remaining", Part.makeCompound(remaining_1), "EMPTY" if not remaining_1 else "NON_EMPTY"), ("Side_2_Remaining", Part.makeCompound(remaining_2), "EMPTY" if not remaining_2 else "NON_EMPTY")):
            obj = doc.addObject("Part::Feature", name); obj.Shape = shape
            _props(obj, {"AreaMm2": shape.Area, "ResultState": state, "CoverageDenominatorsMm2": operation["coverage_denominators_mm2"]})
            partitions.addObject(obj); obj.Visibility = False
        fused = doc.addObject("Part::Feature", "Fused_Union"); fused.Shape = union
        _props(fused, {"SolidCount": operation["union"]["solid_count"], "ShellCount": operation["union"]["shell_count"], "Valid": operation["union"]["valid"], "Closed": operation["union"]["closed"], "VolumeMm3": operation["union"]["volume_mm3"], "VolumeErrorMm3": operation["checks"]["volume_error_mm3"], "ShapeValidation": "evaluated in validation.json"})
        union_group.addObject(fused); fused.Visibility = True
        originals.Visibility = False; partitions.Visibility = False; union_group.Visibility = True
        doc.recompute(); doc.saveAs(str(output / "operation_debug.FCStd"))
    finally:
        FreeCAD.closeDocument(doc.Name)
    reopened = FreeCAD.openDocument(str(output / "operation_debug.FCStd"))
    try:
        required = ("Originals", "Partitions", "Union_Result", "Fused_Union")
        if not all(reopened.getObject(name) for name in required):
            raise RuntimeError("reopened FCStd lacks required objects")
        return {"reopened": True, "visibility_state_saved": bool(reopened.getObject("Union_Result").Visibility and not reopened.getObject("Originals").Visibility and not reopened.getObject("Partitions").Visibility)}
    finally:
        FreeCAD.closeDocument(reopened.Name)


def _generate(request):
    params = request["parameters"]
    shell, core = _inputs(request["case_id"], float(params["outer_radius_mm"]), float(params["inner_radius_mm"]))
    doc = FreeCAD.newDocument("ShellFill04A2Generator")
    try:
        side_1 = doc.addObject("Part::Feature", "Side_1_Shell"); side_1.Label = "Side_1_Shell"; side_1.Shape = shell
        side_2 = doc.addObject("Part::Feature", "Side_2_Core"); side_2.Label = "Side_2_Core"; side_2.Shape = core
        doc.recompute(); Import.export([side_1, side_2], request["step_path"])
        return {"case_id": request["case_id"], "input_solid_counts": [len(shell.Solids), len(core.Solids)], "valid": [shell.isValid(), core.isValid()], "closed": [all(item.isClosed() for item in shell.Shells), all(item.isClosed() for item in core.Shells)]}
    finally:
        FreeCAD.closeDocument(doc.Name)


def _analyze(request):
    output = Path(request["output_dir"]); output.mkdir(parents=True, exist_ok=True)
    params, tolerances = request["parameters"], request["tolerances"]
    inner = float(params["inner_radius_mm"]); area_epsilon = float(tolerances["area_epsilon_mm2"]); linear_epsilon = float(tolerances["linear_epsilon_mm"]); volume_epsilon = float(tolerances["volume_epsilon_mm3"])
    doc = FreeCAD.newDocument("ShellFill04A2Analysis")
    try:
        Import.insert(request["step_path"], doc.Name)
        sources = _objects(doc)
        if len(sources) != 2:
            raise RuntimeError(f"expected two imported solids, found {len(sources)}")
        (_, shell), (_, core) = sources
        carrier_1 = [(index, face) for index, face in enumerate(shell.Faces, 1) if _is_sphere_radius(face, inner, linear_epsilon)]
        carrier_2 = [(index, face) for index, face in enumerate(core.Faces, 1) if _is_sphere_radius(face, inner, linear_epsilon)]
        if not carrier_1 or not carrier_2:
            raise RuntimeError("designated spherical carrier region not found on both inputs")
        common = _face_common(carrier_1, carrier_2, area_epsilon)
        if not common:
            raise RuntimeError("no positive-area spherical common region")
        common_shapes = [record["shape"] for record in common]
        remaining_1 = _remaining(carrier_1, common_shapes, area_epsilon)
        remaining_2 = _remaining(carrier_2, common_shapes, area_epsilon)
        denominators = [sum(face.Area for _, face in carrier_1), sum(face.Area for _, face in carrier_2)]
        common_area = sum(face.Area for face in common_shapes)
        partition_evidence = []
        for carriers, remaining in ((carrier_1, remaining_1), (carrier_2, remaining_2)):
            carrier_shape = Part.makeCompound([face for _, face in carriers])
            common_shape = Part.makeCompound(common_shapes)
            remaining_shape = Part.makeCompound(remaining)
            remaining_area = sum(face.Area for face in remaining)
            coverage_gap = carrier_shape.cut(Part.makeCompound(common_shapes + remaining)).Area
            overlap = common_shape.common(remaining_shape).Area if remaining else 0.0
            partition_evidence.append({"carrier_area_mm2": float(carrier_shape.Area), "common_area_mm2": float(common_area), "remaining_area_mm2": float(remaining_area), "area_error_mm2": float(abs(carrier_shape.Area - common_area - remaining_area)), "coverage_gap_mm2": float(coverage_gap), "positive_overlap_mm2": float(overlap), "area_conserved": abs(carrier_shape.Area - common_area - remaining_area) <= area_epsilon and coverage_gap <= area_epsilon and overlap <= area_epsilon})
        material_intersection = shell.common(core)
        if material_intersection.Volume > volume_epsilon:
            raise RuntimeError("shell-fill inputs have material volume interference")
        union = shell.fuse(core).removeSplitter()
        common_on_boundary = any(patch.common(face).Area > area_epsilon for patch in common_shapes for face in union.Faces)
        volume_error = abs(union.Volume - (shell.Volume + core.Volume - material_intersection.Volume))
        fused_obj = doc.addObject("Part::Feature", "FusedExport"); fused_obj.Shape = union
        Import.export([fused_obj], str(output / "fused.step")); doc.removeObject(fused_obj.Name)
        roundtrip_doc = FreeCAD.newDocument("ShellFill04A2Roundtrip")
        try:
            Import.insert(str(output / "fused.step"), roundtrip_doc.Name)
            imported = _objects(roundtrip_doc)
            roundtrip = imported[0][1] if len(imported) == 1 else Part.Shape()
            checks = {"input_solids_valid_closed": shell.isValid() and core.isValid() and all(item.isClosed() for item in shell.Shells + core.Shells), "material_intersection_volume_mm3": float(material_intersection.Volume), "partition_area_conserved": all(item["area_conserved"] for item in partition_evidence), "solid_count": len(union.Solids), "valid": union.isValid(), "closed": all(item.isClosed() for item in union.Shells), "common_not_on_boundary": not common_on_boundary, "volume_error_mm3": float(volume_error), "roundtrip_solid_count": len(roundtrip.Solids), "roundtrip_valid": roundtrip.isValid(), "roundtrip_volume_error_mm3": float(abs(roundtrip.Volume - union.Volume)), "roundtrip_shape_match": union.cut(roundtrip).Volume <= volume_epsilon and roundtrip.cut(union).Volume <= volume_epsilon}
        finally:
            FreeCAD.closeDocument(roundtrip_doc.Name)
        common_exports = _export_shapes(doc, output, "common", common_shapes)
        side_1_exports = _export_shapes(doc, output, "side_1_remaining", remaining_1)
        side_2_exports = _export_shapes(doc, output, "side_2_remaining", remaining_2)
        for record, exported in zip(common, common_exports): record.update(exported); del record["shape"]
        operation = {"schema_version": 1, "case_id": request["case_id"], "analysis_input": "reimported_step", "side_order": {"side_1": "shell", "side_2": "core"}, "input_structure": params["construction"], "input_step_sha256": request["step_hash"], "input_hashes": {"side_1_brep": _digest(shell), "side_2_brep": _digest(core)}, "common_area_mm2": float(common_area), "common_patches": common, "coverage_denominators_mm2": denominators, "coverage": [float(common_area / value) for value in denominators], "partitions": {"side_1": {"status": "EMPTY" if not remaining_1 else "NON_EMPTY", "remaining_patches": side_1_exports, **partition_evidence[0]}, "side_2": {"status": "EMPTY" if not remaining_2 else "NON_EMPTY", "remaining_patches": side_2_exports, **partition_evidence[1]}}, "union": {"volume_mm3": float(union.Volume), "surface_area_mm2": float(union.Area), "solid_count": len(union.Solids), "shell_count": len(union.Shells), "valid": union.isValid(), "closed": all(item.isClosed() for item in union.Shells), "digest": _digest(union)}, "checks": checks}
        debug = _debug(output, operation, shell, core, common_shapes, remaining_1, remaining_2, union)
        operation["debug"] = debug
        return {"operation": operation, "checks": checks}
    finally:
        FreeCAD.closeDocument(doc.Name)


def _candidate(request):
    outer = float(request["parameters"]["outer_radius_mm"]); inner = float(request["parameters"]["inner_radius_mm"])
    kind = request["candidate_kind"]
    if kind == "half_shell_plus_full_core":
        candidate = _sphere(outer, 0.0, 90.0).cut(_sphere(inner, 0.0, 90.0)).fuse(_sphere(inner)).removeSplitter()
    elif kind == "full_outer_ball":
        candidate = _sphere(outer)
    else:
        raise ValueError(f"unsupported candidate kind: {kind}")
    return candidate


def _validate_shape(candidate, request, actual_checks=None):
    case_id = request["case_id"]; expected = request["expected"]; params = request["parameters"]; tolerances = expected["tolerances"]
    outer = float(params["outer_radius_mm"]); inner = float(params["inner_radius_mm"]); volume_epsilon = float(tolerances["volume_epsilon_mm3"]); area_epsilon = float(tolerances["area_epsilon_mm2"]); linear_epsilon = float(tolerances["linear_epsilon_mm"])
    reference = _reference(case_id, outer, inner)
    actual_minus = float(candidate.cut(reference).Volume); reference_minus = float(reference.cut(candidate).Volume)
    upper_filled = candidate.isInside(FreeCAD.Vector(0, 0, inner / 2), linear_epsilon, True)
    lower_filled = candidate.isInside(FreeCAD.Vector(0, 0, -inner / 2), linear_epsilon, True)
    outer_material = candidate.isInside(FreeCAD.Vector(0, 0, (outer + inner) / 2), linear_epsilon, True)
    lower_inner_area = sum(face.Area for face in candidate.Faces if _is_sphere_radius(face, inner, linear_epsilon) and face.CenterOfMass.z < -linear_epsilon)
    inner_disk_area = sum(face.Area for face in candidate.Faces if "plane" in type(face.Surface).__name__.lower() and abs(face.CenterOfMass.z) <= linear_epsilon and abs(face.Area - math.pi * inner**2) <= area_epsilon)
    lower_cavity_empty = not lower_filled
    if case_id == "U01_sphere_full_fill": cavity_state = "none" if upper_filled and lower_filled else "unexpected_void"
    elif case_id == "U02_sphere_half_fill": cavity_state = "none" if upper_filled and not lower_filled else "unexpected_shape"
    else: cavity_state = "lower_hemisphere" if upper_filled and lower_cavity_empty else "incorrectly_filled"
    facts = {"actual_minus_reference_mm3": actual_minus, "reference_minus_actual_mm3": reference_minus, "analytic_volume_error_mm3": float(abs(candidate.Volume - float(expected["union_volume_mm3"]))), "analytic_surface_area_error_mm2": float(abs(candidate.Area - float(expected["union_area_mm2"]))), "upper_core_material": bool(upper_filled), "lower_core_material": bool(lower_filled), "lower_cavity_empty": bool(lower_cavity_empty), "outer_shell_material": bool(outer_material), "cavity_state": cavity_state, "lower_inner_sphere_boundary_area_mm2": float(lower_inner_area), "inner_equator_disk_boundary_area_mm2": float(inner_disk_area), "solid_count": len(candidate.Solids), "valid": candidate.isValid(), "closed": all(item.isClosed() for item in candidate.Shells)}
    if actual_checks:
        facts.update(actual_checks)
    required = {"shape_actual_minus_reference": actual_minus <= volume_epsilon, "shape_reference_minus_actual": reference_minus <= volume_epsilon, "analytic_volume": facts["analytic_volume_error_mm3"] <= volume_epsilon, "analytic_surface_area": facts["analytic_surface_area_error_mm2"] <= area_epsilon, "cavity_state": cavity_state == expected["cavity_state"], "outer_shell_material": bool(outer_material), "solid_count": facts["solid_count"] == 1, "valid": facts["valid"] is True, "closed": facts["closed"] is True}
    if case_id == "U03_sphere_partial_fill":
        required.update({"lower_inner_sphere_boundary": abs(lower_inner_area - 2 * math.pi * inner**2) <= area_epsilon, "inner_equator_disk_boundary": abs(inner_disk_area - math.pi * inner**2) <= area_epsilon})
    if actual_checks:
        required.update({"input_solids_valid_closed": actual_checks["input_solids_valid_closed"] is True, "material_intersection": actual_checks["material_intersection_volume_mm3"] <= volume_epsilon, "partition_area_conserved": actual_checks["partition_area_conserved"] is True, "common_not_on_boundary": actual_checks["common_not_on_boundary"] is True, "volume_conservation": actual_checks["volume_error_mm3"] <= volume_epsilon, "roundtrip_solid_count": actual_checks["roundtrip_solid_count"] == 1, "roundtrip_valid": actual_checks["roundtrip_valid"] is True, "roundtrip_volume": actual_checks["roundtrip_volume_error_mm3"] <= volume_epsilon, "roundtrip_shape": actual_checks["roundtrip_shape_match"] is True})
    failures = [{"kind": key, "actual": facts.get(key, value)} for key, value in required.items() if not value]
    return {**facts, "checks": required, "status": "PASS" if not failures else "FAIL", "failures": failures}


def _validate_result(request):
    doc = FreeCAD.newDocument("ShellFill04A2Validate")
    try:
        Import.insert(request["fused_step"], doc.Name)
        sources = _objects(doc)
        if len(sources) != 1:
            raise RuntimeError(f"expected one fused STEP solid, found {len(sources)}")
        validation = _validate_shape(sources[0][1], request, request["actual_checks"])
        validation["roundtrip_shape_match"] = request["actual_checks"]["roundtrip_shape_match"]
        debug = FreeCAD.openDocument(request["debug_path"])
        try:
            fused = debug.getObject("Fused_Union")
            if fused is None:
                raise RuntimeError("debug FCStd lacks Fused_Union during validation annotation")
            fused.ShapeValidation = validation["status"]
            for name, value in (("ActualMinusReferenceMm3", validation["actual_minus_reference_mm3"]), ("ReferenceMinusActualMm3", validation["reference_minus_actual_mm3"]), ("CavityState", validation["cavity_state"])):
                if not hasattr(fused, name):
                    fused.addProperty("App::PropertyString", name, "04A2 shell fill")
                setattr(fused, name, str(value))
            debug.recompute(); debug.save()
        finally:
            FreeCAD.closeDocument(debug.Name)
        reopened = FreeCAD.openDocument(request["debug_path"])
        try:
            annotated = reopened.getObject("Fused_Union")
            validation["debug_annotation_saved"] = bool(annotated is not None and annotated.ShapeValidation == validation["status"])
        finally:
            FreeCAD.closeDocument(reopened.Name)
        return {"validation": validation}
    finally:
        FreeCAD.closeDocument(doc.Name)


def _main():
    response_path = Path(os.environ["DMSLICER_FREECAD_RESPONSE"])
    try:
        request = json.loads(Path(os.environ["DMSLICER_FREECAD_REQUEST"]).read_text(encoding="utf-8"))
        if request["action"] == "generate": response = _generate(request)
        elif request["action"] == "analyze": response = _analyze(request)
        elif request["action"] == "validate_result": response = _validate_result(request)
        elif request["action"] == "validate_candidate": response = {"validation": _validate_shape(_candidate(request), request)}
        else: raise ValueError(f"unknown action: {request['action']}")
        response["status"] = "SUCCEEDED"
    except Exception:
        response = {"status": "FAILED", "traceback": traceback.format_exc()}
    response_path.write_text(json.dumps(response, sort_keys=True), encoding="utf-8")


_main()
