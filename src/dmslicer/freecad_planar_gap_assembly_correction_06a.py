"""FreeCADCmd-side A01 planar-gap correction; executed as a script."""

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
    sources = []
    for obj in doc.Objects:
        if obj.TypeId != "Part::Feature" or not hasattr(obj, "Shape") or obj.Shape.isNull():
            continue
        sources.append((obj.Label, obj.Shape))
    sources.sort(key=lambda item: item[0], reverse=reverse)
    return sources


def _role_sources(sources):
    if len(sources) != 2 or any(len(shape.Solids) != 1 for _, shape in sources):
        return None, {"status": "UNSUPPORTED", "reason": "A01 requires exactly two one-solid Part::Feature inputs"}
    resolved = {}
    for role in ("Side_1", "Side_2"):
        matches = [(label, shape.Solids[0]) for label, shape in sources if label == role]
        if len(matches) != 1:
            return None, {"status": "UNSUPPORTED", "reason": f"A01 role {role} is missing or duplicated"}
        resolved[role] = matches[0][1]
    return (resolved["Side_1"], resolved["Side_2"]), {"Side_1": "Side_1", "Side_2": "Side_2"}


def _plane(face):
    return face.Surface if "plane" in type(face.Surface).__name__.lower() else None


def _interface_face(shape, normal_sign, reverse=False):
    faces = list(enumerate(shape.Faces, 1))
    if reverse:
        faces.reverse()
    found = []
    for index, face in faces:
        plane = _plane(face)
        if not plane:
            continue
        try:
            normal = face.normalAt(0, 0).normalize()
        except Exception:  # noqa: BLE001, S112
            # FreeCAD surface adaptors expose multiple backend exception types;
            # an unreadable face is simply not a valid interface candidate.
            continue
        if normal.z * normal_sign > 1.0 - 1e-7:
            found.append((index, face, plane, normal))
    return found


def _measure(first, second, role_binding, reverse=False):
    positive = _interface_face(first, 1, reverse)
    negative = _interface_face(second, -1, reverse)
    if len(positive) != 1 or len(negative) != 1:
        return {"status": "UNSUPPORTED", "reason": "A01 role-constrained interface faces are missing or ambiguous"}
    ia, face_a, plane_a, normal = positive[0]
    ib, face_b, plane_b, opposite = negative[0]
    if abs(normal.dot(plane_b.Axis.normalize())) < 1.0 - 1e-7 or normal.dot(opposite) > -1.0 + 1e-7:
        return {"status": "UNSUPPORTED", "reason": "A01 role-constrained planes are not parallel and opposing"}
    signed = (plane_b.Position - plane_a.Position).dot(normal)
    return {
        "status": "SUPPORTED",
        "measurement_kind": "ROLE_CONSTRAINED_INTERFACE_SIGNED_OFFSET",
        "measured_signed_offset_mm": float(signed),
        "role_binding": role_binding,
        "selected_faces": {"Side_1": f"Face{ia}", "Side_2": f"Face{ib}"},
        "reference_direction": [float(normal.x), float(normal.y), float(normal.z)],
        "coordinate_convention": "STEP world coordinates; translation vector = -d * Side_1 interface outward unit normal",
        "plane_points_mm": {
            "Side_1": [float(plane_a.Position.x), float(plane_a.Position.y), float(plane_a.Position.z)],
            "Side_2": [float(plane_b.Position.x), float(plane_b.Position.y), float(plane_b.Position.z)],
        },
        "interface_face_areas_mm2": {"Side_1": float(face_a.Area), "Side_2": float(face_b.Area)},
    }


def _decision(offset, policy, rules):
    epsilon = float(rules["linear_epsilon_mm"])
    base = {"executed_translation_mm": [0.0, 0.0, 0.0], "executed_translation_norm_mm": 0.0, "motion_authorized": False}
    if offset < -epsilon:
        return dict(base, status="PENETRATION_OUT_OF_SCOPE", reason="negative signed offset is not auto-separated")
    if abs(offset) <= epsilon:
        return dict(base, status="ALREADY_CONTACT", reason="interface is already within the numerical zero rule")
    if policy.get("policy_valid") is False:
        return dict(base, status="MOTION_NOT_AUTHORIZED", reason="operation policy is missing or invalid")
    if offset > float(policy.get("tauE_mm", 0.0)) + epsilon:
        return dict(base, status="ENGINEERING_TOLERANCE_EXCEEDED", reason="measured gap exceeds tauE_mm")
    if policy.get("allow_motion") is not True:
        return dict(base, status="MOTION_NOT_AUTHORIZED", reason="operation policy does not explicitly authorize motion")
    if offset > float(policy.get("max_translation_mm", 0.0)) + epsilon:
        return dict(base, status="TRANSLATION_BUDGET_EXCEEDED", reason="required translation exceeds max_translation_mm")
    return dict(base, status="CORRECTED_AND_FUSED", reason="authorized within tolerance and budget", motion_authorized=True, executed_translation_norm_mm=float(offset))


def _face_common(first, second, reverse=False):
    first_faces = list(first.Faces)
    second_faces = list(second.Faces)
    if reverse:
        first_faces.reverse()
        second_faces.reverse()
    patches = []
    fingerprints = set()
    for face_a in first_faces:
        for face_b in second_faces:
            candidate = face_a.common(face_b)
            for patch in candidate.Faces:
                if patch.Area <= 1e-8:
                    continue
                key = _digest(patch)
                if key not in fingerprints:
                    fingerprints.add(key)
                    patches.append(patch)
    patches.sort(key=lambda patch: (round(patch.CenterOfMass.x, 9), round(patch.CenterOfMass.y, 9), round(patch.CenterOfMass.z, 9), round(patch.Area, 9)))
    return patches


def _boundary_overlap_area(fused, patches):
    total = 0.0
    for patch in patches:
        for face in fused.Faces:
            total += sum(float(piece.Area) for piece in patch.common(face).Faces if piece.Area > 1e-8)
    return total


def _export_assembly(path, first, second):
    doc = FreeCAD.newDocument("CorrectedAssembly06AExport")
    try:
        objects = []
        for name, shape in (("Side_1", first), ("Side_2", second)):
            obj = doc.addObject("Part::Feature", name)
            obj.Label = name
            obj.Shape = shape
            objects.append(obj)
        doc.recompute()
        Import.export(objects, str(path))
    finally:
        FreeCAD.closeDocument(doc.Name)


def _export_fused(path, fused):
    doc = FreeCAD.newDocument("FusedResult06AExport")
    try:
        obj = doc.addObject("Part::Feature", "Fused_Result")
        obj.Label = "Fused_Result"
        obj.Shape = fused
        doc.recompute()
        Import.export([obj], str(path))
    finally:
        FreeCAD.closeDocument(doc.Name)


def _reimport_assembly(path, reverse=False):
    doc = FreeCAD.newDocument("CorrectedAssembly06AReimport")
    try:
        Import.insert(str(path), doc.Name)
        resolved, binding = _role_sources(_objects(doc, reverse))
        if resolved is None:
            return {"role_binding": None, "reason": binding.get("reason")}
        first, second = resolved
        measurement = _measure(first, second, binding, reverse)
        patches = _face_common(first, second, reverse)
        return {
            "role_binding": binding,
            "residual_offset_mm": measurement.get("measured_signed_offset_mm"),
            "contact_dimension": "2D" if patches else "none",
            "contact_area_mm2": float(sum(patch.Area for patch in patches)),
            "solid_count": len(first.Solids) + len(second.Solids),
            "valid_closed": bool(first.isValid() and second.isValid() and _closed(first) and _closed(second)),
        }
    finally:
        FreeCAD.closeDocument(doc.Name)


def _reimport_fused(path):
    doc = FreeCAD.newDocument("FusedResult06AReimport")
    try:
        Import.insert(str(path), doc.Name)
        shapes = [shape for _, shape in _objects(doc)]
        solids = [solid for shape in shapes for solid in shape.Solids]
        compound = Part.makeCompound(solids) if solids else Part.Shape()
        return {
            "solid_count": len(solids),
            "valid": bool(solids and compound.isValid()),
            "closed": bool(solids and all(_closed(solid) for solid in solids)),
            "volume_mm3": float(sum(solid.Volume for solid in solids)),
        }
    finally:
        FreeCAD.closeDocument(doc.Name)


def _add_text_properties(obj, values):
    for name, value in values.items():
        obj.addProperty("App::PropertyString", name, "06A 装配校正")
        setattr(obj, name, str(value))


def _view(path, scenario_id, first, second, corrected, patches, fused, operation):
    doc = FreeCAD.newDocument("PlanarGapAssemblyCorrection06A")
    try:
        originals = doc.addObject("App::DocumentObjectGroup", "Originals")
        originals.Label = "Originals（原始两件，均未修改）"
        for name, shape in (("Original_Side_1", first), ("Original_Side_2", second)):
            obj = doc.addObject("Part::Feature", name)
            obj.Shape = shape
            obj.Visibility = operation["status"] != "CORRECTED_AND_FUSED"
            _add_text_properties(obj, {"角色说明": "Side_1 固定" if name.endswith("1") else "Side_2 原件未修改", "场景": scenario_id})
            originals.addObject(obj)
        if operation["status"] in {"CORRECTED_AND_FUSED", "ALREADY_CONTACT"}:
            assembly = doc.addObject("App::DocumentObjectGroup", "Corrected_Assembly")
            assembly.Label = "Corrected_Assembly（校正后独立实体）"
            for name, shape in (("Corrected_Side_1", first), ("Corrected_Side_2", corrected)):
                obj = doc.addObject("Part::Feature", name)
                obj.Shape = shape
                obj.Visibility = False
                _add_text_properties(obj, {"移动说明": "固定，零位移" if name.endswith("1") else "仅沿接口法向平移副本", "执行位移_mm": operation["decision"]["executed_translation_norm_mm"]})
                assembly.addObject(obj)
            patch_group = doc.addObject("App::DocumentObjectGroup", "Contact_Patch")
            patch_group.Label = "Contact_Patch（校正后实际共同面）"
            patch_obj = doc.addObject("Part::Feature", "Actual_Contact_Patch")
            patch_obj.Shape = Part.makeCompound(patches)
            patch_obj.Visibility = False
            patch_group.addObject(patch_obj)
            fused_group = doc.addObject("App::DocumentObjectGroup", "Fused_Result")
            fused_group.Label = "Fused_Result（实际融合整体，默认显示）"
            fused_obj = doc.addObject("Part::Feature", "Actual_Fused_Result")
            fused_obj.Shape = fused
            fused_obj.Visibility = True
            _add_text_properties(fused_obj, {"校正前间隙_mm": operation["pre_measurement"]["measured_signed_offset_mm"], "校正后间隙_mm": operation["post_measurement"]["measured_signed_offset_mm"], "执行位移_mm": operation["decision"]["executed_translation_norm_mm"]})
            fused_group.addObject(fused_obj)
        else:
            note = doc.addObject("App::FeaturePython", "Rejection_Evidence")
            note.Label = "拒绝证据（零执行位移）"
            _add_text_properties(note, {"拒绝原因": operation["decision"]["reason"], "执行位移_mm": 0.0, "状态": operation["status"]})
        doc.recompute()
        doc.saveAs(str(path))
    finally:
        FreeCAD.closeDocument(doc.Name)


def _reopen_view(path):
    doc = FreeCAD.openDocument(str(path))
    try:
        visible = sorted(
            obj.Name
            for obj in doc.Objects
            if obj.TypeId == "Part::Feature" and hasattr(obj, "Visibility") and obj.Visibility
        )
        return {"reopened": True, "visible_objects": visible}
    finally:
        FreeCAD.closeDocument(doc.Name)


def _run(request):
    rules = request["numeric_rules"]
    reverse = request.get("traversal_order") == "reverse"
    output = Path(request["output_dir"])
    output.mkdir(parents=True, exist_ok=True)
    doc = FreeCAD.newDocument("PlanarGapAssemblyCorrection06AInput")
    try:
        Import.insert(request["step_path"], doc.Name)
        resolved, binding = _role_sources(_objects(doc, reverse))
        if resolved is None:
            return {
                "schema_version": 1,
                "status": "UNSUPPORTED",
                "pre_measurement": binding,
                "decision": {"status": "UNSUPPORTED", "reason": binding["reason"], "executed_translation_mm": [0.0, 0.0, 0.0], "executed_translation_norm_mm": 0.0},
                "post_measurement": {},
                "contact_patch": {},
                "fuse": {"executed": False},
                "invariants": {"input_step_hash_unchanged": True},
                "reimport": {},
                "artifacts": {},
            }
        first, second = resolved
        if not (first.isValid() and second.isValid() and _closed(first) and _closed(second)):
            raise ValueError("A01 requires two valid closed material solids")
        original_digests = [_digest(first), _digest(second)]
        original_volumes = [float(first.Volume), float(second.Volume)]
        pre = _measure(first, second, binding, reverse)
        if pre.get("status") != "SUPPORTED":
            raise ValueError(pre.get("reason", "unsupported A01 measurement"))
        offset = float(pre["measured_signed_offset_mm"])
        decision = _decision(offset, request["policy"], rules)
        corrected = second.copy()
        translation = FreeCAD.Vector(0.0, 0.0, 0.0)
        if decision["status"] == "CORRECTED_AND_FUSED":
            normal = pre["reference_direction"]
            translation = FreeCAD.Vector(-offset * normal[0], -offset * normal[1], -offset * normal[2])
            decision["executed_translation_mm"] = [float(translation.x), float(translation.y), float(translation.z)]
            decision["executed_translation_norm_mm"] = float(translation.Length)
            corrected.translate(translation)
        matrix = [
            [1.0, 0.0, 0.0, float(translation.x)],
            [0.0, 1.0, 0.0, float(translation.y)],
            [0.0, 0.0, 1.0, float(translation.z)],
            [0.0, 0.0, 0.0, 1.0],
        ]
        decision["transform_matrix_row_major"] = matrix
        decision["coordinate_convention"] = pre["coordinate_convention"]
        operation = {
            "schema_version": 1,
            "scenario_id": request["scenario_id"],
            "status": decision["status"],
            "pre_measurement": pre,
            "decision": decision,
            "post_measurement": {},
            "contact_patch": {},
            "fuse": {"executed": False},
            "invariants": {
                "input_step_hash_unchanged": True,
                "original_shapes_unchanged": original_digests == [_digest(first), _digest(second)],
                "side_1_unchanged": original_digests[0] == _digest(first),
                "rotation_is_identity": True,
                "scale_is_one": True,
            },
            "reimport": {},
            "artifacts": {},
        }
        if decision["status"] not in {"CORRECTED_AND_FUSED", "ALREADY_CONTACT"}:
            operation["invariants"].update({"side_2_inverse_transform_match": True, "side_2_volume_unchanged": True})
            if request.get("create_view"):
                view_path = output / "rejected_operation.FCStd"
                _view(view_path, request["scenario_id"], first, second, corrected, [], Part.Shape(), operation)
                operation["artifacts"]["fcstd"] = str(view_path)
                operation["view_reopen"] = _reopen_view(view_path)
            return operation

        post = _measure(first, corrected, binding, reverse)
        patches = _face_common(first, corrected, reverse)
        patch_area = float(sum(patch.Area for patch in patches))
        material_common = first.common(corrected)
        copied_first, copied_second = first.copy(), corrected.copy()
        try:
            fused = copied_first.fuse(copied_second).removeSplitter()
            volume_error = abs(float(fused.Volume) - (float(first.Volume) + float(corrected.Volume) - float(material_common.Volume)))
            fuse = {
                "executed": True,
                "solid_count": len(fused.Solids),
                "valid": bool(fused.isValid()),
                "closed": bool(_closed(fused)),
                "volume_mm3": float(fused.Volume),
                "intersection_volume_mm3": float(material_common.Volume),
                "volume_conservation_error_mm3": float(volume_error),
            }
        except Exception as error:  # noqa: BLE001
            fused = Part.Shape()
            fuse = {"executed": False, "reason": str(error), "solid_count": 0, "valid": False, "closed": False, "volume_conservation_error_mm3": None}
        side_areas = post.get("interface_face_areas_mm2", {})
        contact = {
            "dimension": "2D" if patch_area > float(rules["area_epsilon_mm2"]) and material_common.Volume <= float(rules["volume_epsilon_mm3"]) else "INVALID",
            "area_mm2": patch_area,
            "side_1_area_mm2": float(side_areas.get("Side_1", 0.0)),
            "side_2_area_mm2": float(side_areas.get("Side_2", 0.0)),
            "centers_mm": [[float(p.CenterOfMass.x), float(p.CenterOfMass.y), float(p.CenterOfMass.z)] for p in patches],
            "source_faces": post.get("selected_faces"),
            "fused_boundary_overlap_area_mm2": float(_boundary_overlap_area(fused, patches)) if not fused.isNull() else math.inf,
        }
        inverse = corrected.copy()
        inverse.translate(FreeCAD.Vector(-translation.x, -translation.y, -translation.z))
        inverse_delta = float(inverse.cut(second).Volume + second.cut(inverse).Volume)
        operation["post_measurement"] = post
        operation["contact_patch"] = contact
        operation["fuse"] = fuse
        operation["invariants"].update(
            {
                "side_2_inverse_transform_match": inverse_delta <= float(rules["volume_epsilon_mm3"]) and inverse.distToShape(second)[0] <= float(rules["linear_epsilon_mm"]),
                "side_2_inverse_symmetric_difference_mm3": inverse_delta,
                "side_2_volume_unchanged": abs(float(corrected.Volume) - original_volumes[1]) <= float(rules["volume_epsilon_mm3"]),
            }
        )
        assembly_path = output / "corrected_assembly.step"
        fused_path = output / "fused.step"
        _export_assembly(assembly_path, first, corrected)
        _export_fused(fused_path, fused)
        operation["reimport"] = {"corrected_assembly": _reimport_assembly(assembly_path, reverse), "fused": _reimport_fused(fused_path)}
        operation["artifacts"] = {"corrected_assembly_step": str(assembly_path), "fused_step": str(fused_path)}
        preliminary_failures = []
        if abs(float(post.get("measured_signed_offset_mm", math.inf))) > float(rules["linear_epsilon_mm"]):
            preliminary_failures.append("residual_offset")
        if contact["dimension"] != "2D" or abs(contact["area_mm2"] - contact["side_1_area_mm2"]) > float(rules["area_epsilon_mm2"]) or abs(contact["area_mm2"] - contact["side_2_area_mm2"]) > float(rules["area_epsilon_mm2"]):
            preliminary_failures.append("contact_patch")
        if not (fuse["executed"] and fuse["solid_count"] == 1 and fuse["valid"] and fuse["closed"] and fuse["volume_conservation_error_mm3"] <= float(rules["volume_epsilon_mm3"])):
            preliminary_failures.append("fuse")
        if contact["fused_boundary_overlap_area_mm2"] > float(rules["area_epsilon_mm2"]):
            preliminary_failures.append("internal_interface_retained")
        if not operation["invariants"]["side_2_inverse_transform_match"]:
            preliminary_failures.append("inverse_transform")
        if preliminary_failures:
            operation["status"] = "POSTCHECK_FAILED"
            operation["postcheck_failures"] = preliminary_failures
        if request.get("create_view"):
            view_path = output / "operation_debug.FCStd"
            _view(view_path, request["scenario_id"], first, second, corrected, patches, fused, operation)
            operation["artifacts"]["fcstd"] = str(view_path)
            operation["view_reopen"] = _reopen_view(view_path)
        return operation
    finally:
        FreeCAD.closeDocument(doc.Name)


def _main():
    response_path = Path(os.environ["DMSLICER_FREECAD_RESPONSE"])
    try:
        request = json.loads(Path(os.environ["DMSLICER_FREECAD_REQUEST"]).read_text(encoding="utf-8"))
        if request.get("action") != "correct":
            raise ValueError("unknown action")
        response = {"status": "SUCCEEDED", "operation": _run(request)}
    except Exception:  # noqa: BLE001
        response = {"status": "FAILED", "traceback": traceback.format_exc()}
    response_path.write_text(json.dumps(response, sort_keys=True), encoding="utf-8")


_main()
