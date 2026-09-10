"""FreeCADCmd geometry for 06B partial planar-interface correction."""

import hashlib
import json
import math
import os
import traceback
from pathlib import Path

import FreeCAD
import Import
import Part


def _digest(shape):
    return "sha256:" + hashlib.sha256(shape.exportBrepToString().encode("utf-8")).hexdigest()


def _closed(shape):
    return bool(shape.Shells) and all(shell.isClosed() for shell in shape.Shells)


def _objects(doc, reverse=False):
    objects = [(obj.Label, obj.Shape) for obj in doc.Objects if obj.TypeId == "Part::Feature" and hasattr(obj, "Shape") and not obj.Shape.isNull()]
    return sorted(objects, key=lambda item: item[0], reverse=reverse)


def _roles(doc, reverse=False):
    sources = _objects(doc, reverse)
    if len(sources) != 2:
        raise ValueError("06B requires exactly two imported Part::Feature solids")
    found = {}
    for role in ("Side_1", "Side_2"):
        matches = [shape for label, shape in sources if label == role and len(shape.Solids) == 1]
        if len(matches) != 1:
            raise ValueError("missing or ambiguous role " + role)
        found[role] = matches[0].Solids[0]
    return found["Side_1"], found["Side_2"]


def _plane(face):
    return face.Surface if "plane" in type(face.Surface).__name__.lower() else None


def _carrier(shape, sign, reverse=False):
    items = list(enumerate(shape.Faces, 1))
    if reverse:
        items.reverse()
    found = []
    for index, face in items:
        plane = _plane(face)
        if not plane:
            continue
        try:
            normal = face.normalAt(0, 0).normalize()
        except Exception:
            continue
        if normal.z * sign > 1 - 1e-7:
            found.append((index, face, plane, normal))
    if len(found) != 1:
        raise ValueError("carrier interface face missing or ambiguous")
    return found[0]


def _measure(first, second, reverse=False):
    i1, f1, p1, normal = _carrier(first, 1, reverse)
    i2, f2, p2, opposite = _carrier(second, -1, reverse)
    if abs(normal.dot(p2.Axis.normalize())) < 1 - 1e-7 or normal.dot(opposite) > -1 + 1e-7:
        raise ValueError("carriers are not parallel and opposed")
    return {
        "measured_signed_offset_mm": float((p2.Position - p1.Position).dot(normal)),
        "reference_direction": [float(normal.x), float(normal.y), float(normal.z)],
        "carrier_faces": {"Side_1": "Face%d" % i1, "Side_2": "Face%d" % i2},
        "carrier_area_mm2": {"Side_1": float(f1.Area), "Side_2": float(f2.Area)},
        "selection": "ROLE_CONSTRAINED_A01_STYLE_CARRIER_FACES",
    }, f1, f2


def _positive_faces(shape, epsilon):
    return [face for face in shape.Faces if face.Area > epsilon]


def _patch_data(first_face, second_face, epsilon):
    common = first_face.common(second_face)
    patches = _positive_faces(common, epsilon)
    common_shape = Part.makeCompound(patches) if patches else Part.Shape()
    r1 = _positive_faces(first_face.cut(common_shape), epsilon) if patches else []
    r2 = _positive_faces(second_face.cut(common_shape), epsilon) if patches else []
    common_area = float(sum(face.Area for face in patches))
    areas = {"Side_1": float(first_face.Area), "Side_2": float(second_face.Area)}
    remains = {"Side_1": float(sum(face.Area for face in r1)), "Side_2": float(sum(face.Area for face in r2))}
    side_pieces = {"Side_1": r1, "Side_2": r2}
    if not patches:
        return {
            "common_shape": common_shape,
            "common_patches": [],
            "remaining_shapes": side_pieces,
            "common_area_mm2": 0.0,
            "coverage": {"Side_1": 0.0, "Side_2": 0.0},
            "remaining_area_mm2": areas,
            "carrier_area_mm2": areas,
            "remaining_empty": {"Side_1": False, "Side_2": False},
            "area_conserved": True,
            "spatial_coverage": True,
        }
    spatial = True
    for side, face in (("Side_1", first_face), ("Side_2", second_face)):
        pieces = patches + side_pieces[side]
        union = Part.makeCompound(pieces) if pieces else Part.Shape()
        uncovered = face.cut(union).Area
        outside = union.cut(face).Area if pieces else 0.0
        overlap = common_shape.common(Part.makeCompound(side_pieces[side])).Area if side_pieces[side] else 0.0
        spatial = spatial and uncovered <= epsilon and outside <= epsilon and overlap <= epsilon
    return {
        "common_shape": common_shape,
        "common_patches": patches,
        "remaining_shapes": side_pieces,
        "common_area_mm2": common_area,
        "coverage": {side: common_area / area for side, area in areas.items()},
        "remaining_area_mm2": remains,
        "carrier_area_mm2": areas,
        "remaining_empty": {side: not side_pieces[side] for side in side_pieces},
        "area_conserved": all(abs(areas[side] - common_area - remains[side]) <= epsilon for side in areas),
        "spatial_coverage": spatial,
    }


def _export_shape(document, output, name, shape):
    path = output / "patches" / (name + ".brep")
    path.parent.mkdir(parents=True, exist_ok=True)
    if shape.Faces:
        shape.exportBrep(str(path))
        return str(path.relative_to(output)).replace("\\", "/")
    return None


def _export_assembly(output, first, second, fused):
    doc = FreeCAD.newDocument("PartialOverlap06BExport")
    try:
        objects = []
        for name, shape in (("Side_1", first), ("Side_2", second)):
            obj = doc.addObject("Part::Feature", name); obj.Label = name; obj.Shape = shape; objects.append(obj)
        assembly = output / "corrected_assembly.step"
        Import.export(objects, str(assembly))
        obj = doc.addObject("Part::Feature", "Fused_Result"); obj.Shape = fused
        fused_path = output / "fused.step"
        Import.export([obj], str(fused_path))
        return {"corrected_assembly_step": str(assembly), "fused_step": str(fused_path)}
    finally:
        FreeCAD.closeDocument(doc.Name)


def _reimport_assembly(path, reverse):
    doc = FreeCAD.newDocument("PartialOverlap06BReimport")
    try:
        Import.insert(str(path), doc.Name)
        first, second = _roles(doc, reverse)
        measurement, face_1, face_2 = _measure(first, second, reverse)
        common = _patch_data(face_1, face_2, 1e-8)
        return {
            "role_binding": {"Side_1": "Side_1", "Side_2": "Side_2"},
            "residual_offset_mm": measurement["measured_signed_offset_mm"],
            "common_area_mm2": common["common_area_mm2"],
            "solid_count": len(first.Solids) + len(second.Solids),
            "valid_closed": bool(first.isValid() and second.isValid() and _closed(first) and _closed(second)),
        }
    finally:
        FreeCAD.closeDocument(doc.Name)


def _debug(output, status, first, original_second, corrected, partition, fused, operation):
    doc = FreeCAD.newDocument("PlanarPartialOverlap06B")
    try:
        originals = doc.addObject("App::DocumentObjectGroup", "Originals")
        corrected_group = doc.addObject("App::DocumentObjectGroup", "Corrected_Assembly")
        interface = doc.addObject("App::DocumentObjectGroup", "Interface_Partition")
        fused_group = doc.addObject("App::DocumentObjectGroup", "Fused_Result")
        rejection = doc.addObject("App::DocumentObjectGroup", "Rejection_Evidence")
        def add(group, name, shape, visible=False):
            obj = doc.addObject("Part::Feature", name); obj.Shape = shape; obj.Visibility = visible; group.addObject(obj); return obj
        add(originals, "Original_Side_1", first, status == "NO_POSITIVE_AREA_INTERFACE")
        add(originals, "Original_Side_2", original_second, status == "NO_POSITIVE_AREA_INTERFACE")
        if status == "NO_POSITIVE_AREA_INTERFACE":
            preview = add(rejection, "Preview_Candidate_DISPLAY_ONLY_NOT_EXECUTED", corrected, False)
            preview.addProperty("App::PropertyString", "PreviewStatus"); preview.PreviewStatus = "DISPLAY_ONLY / NOT_EXECUTED"
        else:
            add(corrected_group, "Corrected_Side_1", first)
            add(corrected_group, "Corrected_Side_2", corrected)
            add(interface, "Common", partition["common_shape"])
            for side, title in (("Side_1", "Side_1_Remaining"), ("Side_2", "Side_2_Remaining")):
                shape = Part.makeCompound(partition["remaining_shapes"][side])
                obj = add(interface, title, shape)
                obj.addProperty("App::PropertyString", "State")
                obj.State = "EMPTY" if partition["remaining_empty"][side] else "NON_EMPTY"
            add(fused_group, "Actual_Fused_Result", fused, True)
        doc.recompute(); doc.saveAs(str(output / "operation_debug.FCStd"))
    finally:
        FreeCAD.closeDocument(doc.Name)
    reopened = FreeCAD.openDocument(str(output / "operation_debug.FCStd"))
    try:
        visible = sorted(obj.Name for obj in reopened.Objects if obj.TypeId == "Part::Feature" and obj.Visibility)
        return {"reopened": True, "visible_objects": visible}
    finally:
        FreeCAD.closeDocument(reopened.Name)


def _generate(request):
    def box(data):
        x0, x1, y0, y1, z0, z1 = data
        return Part.makeBox(x1 - x0, y1 - y0, z1 - z0, FreeCAD.Vector(x0, y0, z0))
    doc = FreeCAD.newDocument("PartialOverlap06BGenerator")
    try:
        objects = []
        for name, data in (("Side_1", request["side_1"]), ("Side_2", request["side_2"])):
            obj = doc.addObject("Part::Feature", name); obj.Label = name; obj.Shape = box(data); objects.append(obj)
        doc.recompute(); Import.export(objects, request["step_path"])
        return {"valid_closed": [obj.Shape.isValid() and _closed(obj.Shape) for obj in objects]}
    finally:
        FreeCAD.closeDocument(doc.Name)


def _analyze(request):
    output, epsilon, volume_epsilon = Path(request["output_dir"]), float(request["rules"]["area_epsilon_mm2"]), float(request["rules"]["volume_epsilon_mm3"])
    output.mkdir(parents=True, exist_ok=True)
    doc = FreeCAD.newDocument("PartialOverlap06BAnalysis")
    try:
        Import.insert(request["step_path"], doc.Name)
        first, second = _roles(doc, request.get("traversal_order") == "reverse")
        if not (first.isValid() and second.isValid() and _closed(first) and _closed(second)):
            raise ValueError("two valid closed solids are required")
        pre, _, _ = _measure(first, second, request.get("traversal_order") == "reverse")
        gap, normal = pre["measured_signed_offset_mm"], FreeCAD.Vector(*pre["reference_direction"])
        policy = request["policy"]
        decision = {"executed_translation_mm": [0.0, 0.0, 0.0], "executed_translation_norm_mm": 0.0, "motion_authorized": False}
        if gap <= float(request["rules"]["linear_epsilon_mm"]):
            status, reason = ("PENETRATION_OUT_OF_SCOPE", "non-positive gap") if gap < 0 else ("ALREADY_CONTACT", "already contact")
        elif policy.get("policy_valid") is not True or policy.get("allow_motion") is not True:
            status, reason = "MOTION_NOT_AUTHORIZED", "policy denied"
        elif gap > float(policy["tauE_mm"]) + float(request["rules"]["linear_epsilon_mm"]):
            status, reason = "ENGINEERING_TOLERANCE_EXCEEDED", "tauE"
        elif gap > float(policy["max_translation_mm"]) + float(request["rules"]["linear_epsilon_mm"]):
            status, reason = "TRANSLATION_BUDGET_EXCEEDED", "budget"
        else:
            status, reason = "PRECOMMIT_GEOMETRY_CHECK", "authorized candidate"
        preview = second.copy()
        candidate_translation = FreeCAD.Vector(-gap * normal.x, -gap * normal.y, -gap * normal.z)
        if status == "PRECOMMIT_GEOMETRY_CHECK":
            preview.translate(candidate_translation)
            _, preview_f1, preview_f2 = _measure(first, preview, request.get("traversal_order") == "reverse")
            prospective = _patch_data(preview_f1, preview_f2, epsilon)
            if prospective["common_area_mm2"] <= epsilon:
                status, reason = "NO_POSITIVE_AREA_INTERFACE", "PRECOMMIT_GEOMETRY_CHECK found no positive-area B-rep common"
            else:
                status, reason = "CORRECTED_PARTIAL_INTERFACE_FUSED", "authorized positive-area B-rep interface"
        else:
            prospective = {"common_area_mm2": 0.0, "diagnostic": "not evaluated because 06A authorization failed"}
        corrected = second.copy()
        if status == "CORRECTED_PARTIAL_INTERFACE_FUSED":
            corrected.translate(candidate_translation)
            decision.update({"motion_authorized": True, "executed_translation_mm": [float(candidate_translation.x), float(candidate_translation.y), float(candidate_translation.z)], "executed_translation_norm_mm": float(candidate_translation.Length)})
        decision.update({"status": status, "reason": reason, "preview_translation_mm": [float(candidate_translation.x), float(candidate_translation.y), float(candidate_translation.z)]})
        actual_translation = FreeCAD.Vector(*decision["executed_translation_mm"])
        tangential = actual_translation - normal * actual_translation.dot(normal)
        pose = {
            "side_2_centroid_pre_mm": [float(second.CenterOfMass.x), float(second.CenterOfMass.y), float(second.CenterOfMass.z)],
            "side_2_centroid_post_mm": [float(corrected.CenterOfMass.x), float(corrected.CenterOfMass.y), float(corrected.CenterOfMass.z)],
            "normal_component_mm": float(actual_translation.dot(normal)),
            "tangential_component_mm": [float(tangential.x), float(tangential.y), float(tangential.z)],
            "tangential_translation_norm_mm": float(tangential.Length),
            "tangential_projection_relation_pre_mm": [float(second.CenterOfMass.x - first.CenterOfMass.x), float(second.CenterOfMass.y - first.CenterOfMass.y)],
            "tangential_projection_relation_post_mm": [float(corrected.CenterOfMass.x - first.CenterOfMass.x), float(corrected.CenterOfMass.y - first.CenterOfMass.y)],
            "tangential_projection_relation_preserved": abs(second.CenterOfMass.x - corrected.CenterOfMass.x) <= 1e-7 and abs(second.CenterOfMass.y - corrected.CenterOfMass.y) <= 1e-7,
        }
        operation = {"schema_version": 1, "scenario_id": request["scenario_id"], "status": status, "pre_measurement": pre, "decision": decision, "prospective_interface": {"common_area_mm2": float(prospective["common_area_mm2"]), "kind": "PRECOMMIT_GEOMETRY_CHECK", "executed": False}, "pose_invariants": pose, "partition": {}, "fuse": {"executed": False}, "provenance": {"roles": {"Side_1": "Side_1", "Side_2": "Side_2"}, "carrier_faces": pre["carrier_faces"], "operation_kind": "direct_BRep_face_common_and_face_cut"}}
        if status == "CORRECTED_PARTIAL_INTERFACE_FUSED":
            post, f1, f2 = _measure(first, corrected, request.get("traversal_order") == "reverse")
            partition = _patch_data(f1, f2, epsilon)
            material_common = first.common(corrected)
            fused = first.copy().fuse(corrected.copy()).removeSplitter()
            boundary = sum(patch.common(face).Area for patch in partition["common_patches"] for face in fused.Faces)
            partition.update({"common_patch_count": len(partition["common_patches"]), "common_digest": _digest(partition["common_shape"]), "source_carrier_faces": post["carrier_faces"]})
            for side in ("Side_1", "Side_2"):
                partition[side + "_remaining_brep"] = _export_shape(doc, output, side.lower() + "_remaining", Part.makeCompound(partition["remaining_shapes"][side]))
            partition["common_brep"] = _export_shape(doc, output, "common", partition["common_shape"])
            operation["post_measurement"] = post
            operation["partition"] = {key: value for key, value in partition.items() if key not in {"common_shape", "common_patches", "remaining_shapes"}}
            operation["fuse"] = {"executed": True, "solid_count": len(fused.Solids), "valid": bool(fused.isValid()), "closed": bool(_closed(fused)), "volume_conservation_error_mm3": float(abs(fused.Volume - (first.Volume + corrected.Volume - material_common.Volume))), "boundary_overlap_area_mm2": float(boundary)}
            operation["artifacts"] = _export_assembly(output, first, corrected, fused)
            operation["reimport"] = {"corrected_assembly": _reimport_assembly(operation["artifacts"]["corrected_assembly_step"], request.get("traversal_order") == "reverse")}
            operation["view_reopen"] = _debug(output, status, first, second, corrected, partition, fused, operation)
        else:
            operation["view_reopen"] = _debug(output, status, first, second, preview, {"common_shape": Part.Shape(), "remaining_shapes": {"Side_1": [], "Side_2": []}, "remaining_empty": {"Side_1": True, "Side_2": True}}, Part.Shape(), operation)
        return operation
    finally:
        FreeCAD.closeDocument(doc.Name)


def _main():
    response_path = Path(os.environ["DMSLICER_FREECAD_RESPONSE"])
    try:
        request = json.loads(Path(os.environ["DMSLICER_FREECAD_REQUEST"]).read_text(encoding="utf-8"))
        operation = _generate(request) if request["action"] == "generate" else _analyze(request)
        response = {"status": "SUCCEEDED", **({"operation": operation} if request["action"] == "analyze" else operation)}
    except Exception:
        response = {"status": "FAILED", "traceback": traceback.format_exc()}
    response_path.write_text(json.dumps(response, sort_keys=True), encoding="utf-8")


_main()
