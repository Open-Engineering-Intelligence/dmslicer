"""FreeCADCmd adapter for 07A actual B-rep measurement and correction."""

import json
import math
import os
import sys
from pathlib import Path

import FreeCAD
import Import
import Part


def _finite(value):
    return type(value) in (int, float) and math.isfinite(float(value))


def _objects(document, reverse=False):
    values = []
    for obj in document.Objects:
        shape = getattr(obj, "Shape", None)
        if obj.TypeId == "Part::Feature" and shape is not None and not shape.isNull() and len(shape.Solids) == 1:
            values.append((obj.Label or obj.Name, shape.Solids[0]))
    return list(reversed(values)) if reverse else values


def _cylinder(face):
    surface = getattr(face, "Surface", None)
    return surface if surface is not None and "cylinder" in type(surface).__name__.lower() else None


def _unit(vector):
    value = FreeCAD.Vector(vector.x, vector.y, vector.z)
    if value.Length <= 0.0:
        raise ValueError("zero cylinder axis")
    value.normalize()
    return value


def _point_on_axis(center, axis, point):
    return center + axis * ((point - center).dot(axis))


def _candidate(shape, face, index, occurrence, rules):
    cylinder = _cylinder(face)
    if cylinder is None:
        return None
    axis = _unit(cylinder.Axis)
    center = FreeCAD.Vector(cylinder.Center.x, cylinder.Center.y, cylinder.Center.z)
    u_min, u_max, v_min, v_max = [float(value) for value in face.ParameterRange]
    angular_span = abs(u_max - u_min)
    full_period = abs(angular_span - 2.0 * math.pi) <= rules["periodic_epsilon_rad"]
    u_mid, v_mid = (u_min + u_max) / 2.0, (v_min + v_max) / 2.0
    point = face.valueAt(u_mid, v_mid)
    normal = face.normalAt(u_mid, v_mid)
    if normal.Length <= 0.0:
        return None
    normal.normalize()
    radial = point - _point_on_axis(center, axis, point)
    if radial.Length <= rules["linear_epsilon_mm"]:
        return None
    radial.normalize()
    orientation_dot = float(normal.dot(radial))
    role = "SHAFT_CONVEX" if orientation_dot > 0.5 else "BORE_CONCAVE" if orientation_dot < -0.5 else "UNSUPPORTED"
    probe = rules["material_probe_offset_mm"]
    material_minus = bool(shape.isInside(point - normal * probe, rules["linear_epsilon_mm"], True))
    material_plus = bool(shape.isInside(point + normal * probe, rules["linear_epsilon_mm"], True))
    material_side_confirmed = material_minus and not material_plus
    projections = [float(vertex.Point.dot(axis)) for vertex in face.Vertexes]
    if not projections:
        projections = [float(face.valueAt(u_mid, v_min).dot(axis)), float(face.valueAt(u_mid, v_max).dot(axis))]
    lo, hi = min(projections), max(projections)
    circle_edges = sum(1 for edge in face.Edges if "circle" in type(getattr(edge, "Curve", None)).__name__.lower())
    supported = full_period and circle_edges >= 2 and material_side_confirmed and role != "UNSUPPORTED"
    return {
        "surface_family": "Cylinder",
        "axis_point_mm": [float(center.x), float(center.y), float(center.z)],
        "axis_direction": [float(axis.x), float(axis.y), float(axis.z)],
        "radius_mm": float(cylinder.Radius),
        "axial_interval_mm": [lo, hi],
        "uv_bounds": [u_min, u_max, v_min, v_max],
        "angular_span_rad": angular_span,
        "full_period": full_period,
        "circle_end_boundary_count": circle_edges,
        "face_area_mm2": float(face.Area),
        "role_evidence": role,
        "orientation_radial_dot": orientation_dot,
        "material_side_confirmed": material_side_confirmed,
        "supported": supported,
        "occurrence": occurrence,
        "run_local_face_label": "Face%d" % index,
        "provenance": "reimported_step_actual_brep",
        "_face": face,
        "_shape": shape,
    }


def _public(candidate):
    return {key: value for key, value in candidate.items() if not key.startswith("_")}


def _extract(sources, rules, reverse=False):
    records = []
    iterable = list(reversed(sources)) if reverse else sources
    for occurrence, shape in iterable:
        faces = list(enumerate(shape.Faces, 1))
        if reverse:
            faces.reverse()
        for index, face in faces:
            record = _candidate(shape, face, index, occurrence, rules)
            if record is not None:
                records.append(record)
    return records


def _axis_relation(first, second):
    p1, p2 = FreeCAD.Vector(*first["axis_point_mm"]), FreeCAD.Vector(*second["axis_point_mm"])
    u1, u2 = _unit(FreeCAD.Vector(*first["axis_direction"])), _unit(FreeCAD.Vector(*second["axis_direction"]))
    dot = float(u1.dot(u2))
    angle = math.acos(max(0.0, min(1.0, abs(dot))))
    if dot < 0.0:
        u2 = -u2
    delta = p2 - p1
    cross = u1.cross(u2)
    if cross.Length > 0.0:
        cross.normalize()
        offset = cross * delta.dot(cross)
    else:
        offset = delta - u1 * delta.dot(u1)
    return {
        "axis_angle_rad": angle,
        "axis_offset_vector_mm": [float(offset.x), float(offset.y), float(offset.z)],
        "axis_offset_mm": float(offset.Length),
    }


def _axial_overlap(first, second):
    p1 = FreeCAD.Vector(*first["axis_point_mm"])
    u1 = _unit(FreeCAD.Vector(*first["axis_direction"]))
    values = []
    for candidate in (first, second):
        face = candidate["_face"]
        projections = [float((vertex.Point - p1).dot(u1)) for vertex in face.Vertexes]
        if not projections:
            projections = list(candidate["axial_interval_mm"])
        values.append((min(projections), max(projections)))
    return max(0.0, min(values[0][1], values[1][1]) - max(values[0][0], values[1][0]))


def _geometry(first, second, rules):
    face_common = first["_face"].common(second["_face"])
    solid_common = first["_shape"].common(second["_shape"])
    return {
        "actual_common_area_mm2": float(face_common.Area),
        "material_common_volume_mm3": float(solid_common.Volume),
        "minimum_surface_distance_mm": float(first["_face"].distToShape(second["_face"])[0]),
        "actual_common_shape": face_common,
        "material_common_shape": solid_common,
    }


def _classification(measurement, geometry, rules):
    components = []
    if measurement["axis_angle_rad"] > rules["angular_epsilon_rad"]:
        components.append("ANGULAR")
    if measurement["axis_offset_mm"] > rules["linear_epsilon_mm"]:
        components.append("POSITIONAL")
    if abs(measurement["radial_clearance_mm"]) > rules["radius_epsilon_mm"]:
        components.append("DIMENSIONAL")
    if measurement["axial_overlap_mm"] <= rules["linear_epsilon_mm"]:
        kind = "UNSUPPORTED_INSUFFICIENT_AXIAL_OVERLAP"
    elif len(components) > 1:
        kind = "COMPOUND_ERROR_UNSUPPORTED"
    elif components == ["ANGULAR"]:
        kind = "ANGULAR_AXIS_MISALIGNMENT"
    elif components == ["POSITIONAL"]:
        kind = "AXIS_TRANSLATIONAL_MISALIGNMENT"
    elif components == ["DIMENSIONAL"]:
        kind = "DIMENSIONAL_RADIAL_CLEARANCE" if measurement["radial_clearance_mm"] > 0 else "DIMENSIONAL_RADIAL_INTERFERENCE"
    elif geometry["actual_common_area_mm2"] > rules["area_epsilon_mm2"]:
        kind = "EXACT_CYLINDRICAL_CONTACT"
    else:
        kind = "GEOMETRY_RELATION_MISMATCH"
    return {"classification": kind, "error_components": components}


def _zero_motion():
    return {
        "motion_authorized": False,
        "proposed_translation_mm": [0.0, 0.0, 0.0],
        "executed_translation_mm": [0.0, 0.0, 0.0],
        "execution_count": 0,
        "rotation_executed": False,
    }


def _decide(classification, measurement, policy, rules):
    kind = classification["classification"]
    motion = _zero_motion()
    if kind == "EXACT_CYLINDRICAL_CONTACT":
        return "NO_CORRECTION_REQUIRED", "NO_CORRECTION_REQUIRED", motion
    if kind in ("DIMENSIONAL_RADIAL_CLEARANCE", "DIMENSIONAL_RADIAL_INTERFERENCE"):
        return "RIGID_POSITION_CORRECTION_NOT_APPLICABLE", "RIGID_POSITION_CORRECTION_NOT_APPLICABLE", motion
    if kind == "ANGULAR_AXIS_MISALIGNMENT":
        return "UNSUPPORTED_BY_07A_TRANSLATION_ONLY", "UNSUPPORTED_BY_07A_TRANSLATION_ONLY", motion
    if kind != "AXIS_TRANSLATIONAL_MISALIGNMENT":
        return kind, kind, motion
    repairability = "RIGID_TRANSLATION_REPAIRABLE"
    valid = (
        policy.get("policy_valid") is True
        and policy.get("allow_motion") is True
        and policy.get("allow_pose_interference_resolution") is True
        and _finite(policy.get("tauE_mm"))
        and _finite(policy.get("max_translation_mm"))
        and float(policy["tauE_mm"]) >= 0.0
        and float(policy["max_translation_mm"]) >= 0.0
    )
    if not valid:
        return "MOTION_NOT_AUTHORIZED", repairability, motion
    offset = measurement["axis_offset_mm"]
    if offset > float(policy["tauE_mm"]) + rules["linear_epsilon_mm"]:
        return "ENGINEERING_TOLERANCE_EXCEEDED", repairability, motion
    if offset > float(policy["max_translation_mm"]) + rules["linear_epsilon_mm"]:
        return "TRANSLATION_BUDGET_EXCEEDED", repairability, motion
    proposed = [-value for value in measurement["axis_offset_vector_mm"]]
    motion.update({"motion_authorized": True, "proposed_translation_mm": proposed})
    return "AUTHORIZED_FOR_SINGLE_TRANSLATION", repairability, motion


def _measure(first, second, rules):
    relation = _axis_relation(first, second)
    relation.update({
        "bore_radius_mm": first["radius_mm"],
        "shaft_radius_mm": second["radius_mm"],
        "radial_clearance_mm": first["radius_mm"] - second["radius_mm"],
        "axial_overlap_mm": _axial_overlap(first, second),
    })
    return relation


def _closed(shape):
    return bool(shape.isValid() and shape.Solids and all(shell.isClosed() for shell in shape.Shells))


def _export_step(path, values):
    doc = FreeCAD.newDocument("Export07A")
    try:
        objects = []
        for name, shape in values:
            obj = doc.addObject("Part::Feature", name)
            obj.Label, obj.Shape = name, shape
            objects.append(obj)
        Import.export(objects, str(path))
    finally:
        FreeCAD.closeDocument(doc.Name)


def _add_feature(document, group, name, label, shape, visible=True):
    obj = document.addObject("Part::Feature", name)
    obj.Label, obj.Shape = label, shape
    obj.Visibility = visible
    group.addObject(obj)
    return obj


def _axis_shape(candidate):
    axis = _unit(FreeCAD.Vector(*candidate["axis_direction"]))
    start = FreeCAD.Vector(*candidate["axis_point_mm"])
    lo, hi = candidate["axial_interval_mm"]
    current = start.dot(axis)
    return Part.makeCylinder(0.04, max(hi - lo, 0.1), start + axis * (lo - current), axis)


def _display_vector_shape(start, vector, radius=0.06):
    direction = FreeCAD.Vector(*vector) if not isinstance(vector, FreeCAD.Vector) else vector
    if direction.Length <= 0.0:
        return Part.Shape()
    return Part.makeCylinder(radius, direction.Length, start, direction)


def _debug(path, operation, sources, candidates, corrected=None, common=None, fused=None, rejection=None):
    doc = FreeCAD.newDocument("CylindricalRepair07ADebug")
    try:
        semantic_objects = []
        group_specs = (
            ("Input", "00_Input"), ("Originals", "01_Originals"),
            ("Selected_Interface", "02_Selected_Interface"), ("Precommit_Preview", "03_Precommit_Preview"),
            ("Corrected_Assembly", "04_Corrected_Assembly"), ("Common_Patches", "05_Common_Patches"),
            ("Remaining", "06_Remaining"), ("Fused_Result_Group", "09_Fused_Result"),
            ("Rejection_Evidence", "10_Rejection_Evidence"),
        )
        groups = {}
        for internal, label in group_specs:
            group = doc.addObject("App::DocumentObjectGroup", internal)
            group.Label = label
            groups[label] = group
        for index, (label, shape) in enumerate(sources, 1):
            _add_feature(doc, groups["01_Originals"], "Original_%d" % index, label, shape, operation["status"] != "CORRECTED_AND_FUSED")
        for index, candidate in enumerate(candidates, 1):
            axis = _add_feature(doc, groups["02_Selected_Interface"], "Candidate_Axis_%d" % index, "%s %s axis" % (candidate["role_evidence"], candidate["run_local_face_label"]), _axis_shape(candidate), True)
            axis.addProperty("App::PropertyString", "RoleEvidence", "07A")
            axis.RoleEvidence = candidate["role_evidence"]
        proposed = operation["motion"]["proposed_translation_mm"]
        length = math.sqrt(sum(value * value for value in proposed))
        if length > 0.0 and candidates:
            selected = operation.get("selected_candidates", {})
            bore_point = FreeCAD.Vector(*selected.get("Side_1", candidates[0])["axis_point_mm"])
            offset = operation.get("pre_measurement", {}).get("axis_offset_vector_mm", [0.0, 0.0, 0.0])
            offset_arrow = _add_feature(doc, groups["03_Precommit_Preview"], "Axis_Offset_Vector", "Measured axis offset vector", _display_vector_shape(bore_point, offset), True)
            offset_arrow.addProperty("App::PropertyString", "EvidenceRole", "07A")
            offset_arrow.EvidenceRole = "ACTUAL_BREP_AXIS_GEOMETRY"
            semantic_objects.append("Axis_Offset_Vector")
            start = bore_point + FreeCAD.Vector(*offset)
            arrow = _add_feature(doc, groups["03_Precommit_Preview"], "Proposed_Translation", "DISPLAY_ONLY / NOT_EXECUTED proposed correction", _display_vector_shape(start, proposed), True)
            arrow.addProperty("App::PropertyString", "ExecutionState", "07A")
            arrow.ExecutionState = "DISPLAY_ONLY / NOT_EXECUTED"
            semantic_objects.append("Proposed_Translation")
        clearance = operation.get("pre_measurement", {}).get("radial_clearance_mm")
        selected = operation.get("selected_candidates", {})
        if _finite(clearance) and abs(float(clearance)) > operation["numeric_rules"]["radius_epsilon_mm"] and selected:
            bore = selected["Side_1"]
            axis = _unit(FreeCAD.Vector(*bore["axis_direction"]))
            reference = FreeCAD.Vector(1.0, 0.0, 0.0) if abs(axis.x) < 0.8 else FreeCAD.Vector(0.0, 1.0, 0.0)
            radial = axis.cross(reference)
            radial.normalize()
            lower = min(bore["radius_mm"], selected["Side_2"]["radius_mm"])
            start = FreeCAD.Vector(*bore["axis_point_mm"]) + radial * lower
            indicator = _add_feature(doc, groups["03_Precommit_Preview"], "Radial_Clearance_Indicator", "DIMENSIONAL_ERROR / NO RIGID TRANSLATION EXECUTED", _display_vector_shape(start, radial * abs(float(clearance)), radius=0.08), True)
            indicator.addProperty("App::PropertyString", "SignedRadialClearanceMm", "07A")
            indicator.SignedRadialClearanceMm = str(clearance)
            semantic_objects.append("Radial_Clearance_Indicator")
        if corrected:
            _add_feature(doc, groups["04_Corrected_Assembly"], "Corrected_Side_1", "Corrected Side_1 bore (unchanged)", corrected[0], False)
            _add_feature(doc, groups["04_Corrected_Assembly"], "Corrected_Side_2", "Corrected Side_2 shaft", corrected[1], False)
            corrected_candidates = _extract((("Corrected_Side_1", corrected[0]), ("Corrected_Side_2", corrected[1])), operation["numeric_rules"])
            corrected_bore = next((item for item in corrected_candidates if item["occurrence"] == "Corrected_Side_1" and item["role_evidence"] == "BORE_CONCAVE" and item["supported"]), None)
            corrected_shaft = next((item for item in corrected_candidates if item["occurrence"] == "Corrected_Side_2" and item["role_evidence"] == "SHAFT_CONVEX" and item["supported"]), None)
            if corrected_bore:
                _add_feature(doc, groups["04_Corrected_Assembly"], "Corrected_Bore_Axis", "Corrected bore axis", _axis_shape(corrected_bore), False)
                semantic_objects.append("Corrected_Bore_Axis")
            if corrected_shaft:
                _add_feature(doc, groups["04_Corrected_Assembly"], "Corrected_Shaft_Axis", "Corrected shaft axis", _axis_shape(corrected_shaft), False)
                semantic_objects.append("Corrected_Shaft_Axis")
            if common is not None and not common.isNull() and corrected_bore and corrected_shaft:
                for side, candidate in (("Side_1", corrected_bore), ("Side_2", corrected_shaft)):
                    remaining_shape = candidate["_face"].cut(common)
                    if remaining_shape.Area > operation["numeric_rules"]["area_epsilon_mm2"]:
                        name = "Remaining_%s" % side
                        _add_feature(doc, groups["06_Remaining"], name, "%s cylindrical carrier Remaining" % side, remaining_shape, False)
                    else:
                        name = "Remaining_%s_EMPTY" % side
                        empty = doc.addObject("App::FeaturePython", name)
                        empty.Label = "%s Remaining: EMPTY" % side
                        empty.addProperty("App::PropertyString", "PartitionStatus", "07A")
                        empty.PartitionStatus = "EMPTY"
                        groups["06_Remaining"].addObject(empty)
                    semantic_objects.append(name)
        if common is not None and not common.isNull():
            _add_feature(doc, groups["05_Common_Patches"], "Actual_Common", "Actual cylindrical B-rep Common", common, operation["status"] != "CORRECTED_AND_FUSED")
        if fused is not None and not fused.isNull():
            _add_feature(doc, groups["09_Fused_Result"], "Fused_Result", "Fused result", fused, operation["status"] == "CORRECTED_AND_FUSED")
        if rejection is not None and not rejection.isNull():
            _add_feature(doc, groups["10_Rejection_Evidence"], "Pre_Material_Common", "Actual pre-correction material common", rejection, True)
        root = doc.addObject("App::FeaturePython", "Operation_Status")
        for name, value in (("Classification", operation["classification"]["classification"]), ("Repairability", operation["repairability"]), ("Status", operation["status"])):
            root.addProperty("App::PropertyString", name, "07A")
            setattr(root, name, value)
        doc.recompute()
        doc.saveAs(str(path))
    finally:
        FreeCAD.closeDocument(doc.Name)
    reopened = FreeCAD.openDocument(str(path))
    try:
        required = tuple(internal for internal, _ in group_specs)
        return {"reopened": all(reopened.getObject(name) is not None for name in required), "required_groups": [label for _, label in group_specs], "semantic_objects": semantic_objects}
    finally:
        FreeCAD.closeDocument(reopened.Name)


def _generate(request):
    scenario = request["scenario_id"]
    r, outer = 10.0, 20.0
    bore = Part.makeCylinder(outer, 40.0, FreeCAD.Vector(0, 0, -5)).cut(Part.makeCylinder(r, 50.0, FreeCAD.Vector(0, 0, -10)))
    if scenario in ("C02", "ROTATED_C02"):
        shaft = Part.makeCylinder(r, 30.0, FreeCAD.Vector(0.05, 0, 0))
    elif scenario == "C05":
        shaft = Part.makeCylinder(r, 30.0, FreeCAD.Vector(0, 0, 0), FreeCAD.Vector(math.sin(1e-3), 0, math.cos(1e-3)))
    elif scenario == "AMBIGUOUS":
        second_bore = Part.makeCylinder(outer, 40.0, FreeCAD.Vector(60, 0, -5)).cut(Part.makeCylinder(r, 50.0, FreeCAD.Vector(60, 0, -10)))
        bridge = Part.makeBox(60.0, 8.0, 8.0, FreeCAD.Vector(0, -4, 27))
        bore = bore.fuse(second_bore).fuse(bridge).removeSplitter()
        shaft = Part.makeCylinder(r, 30.0, FreeCAD.Vector(0.05, 0, 0))
    else:
        raise ValueError("unsupported generated scenario")
    if scenario == "ROTATED_C02":
        placement = FreeCAD.Placement(FreeCAD.Vector(17.0, -23.0, 31.0), FreeCAD.Rotation(FreeCAD.Vector(0.0, 1.0, 0.0), 45.0))
        bore.Placement = placement
        shaft.Placement = placement
    _export_step(Path(request["step_path"]), (("Side_1_Bore", bore), ("Side_2_Shaft", shaft)))
    return {"valid_closed": [_closed(bore), _closed(shaft)]}


def _analyze(request):
    rules, reverse = request["numeric_rules"], bool(request.get("reverse"))
    output = Path(request["output_dir"])
    output.mkdir(parents=True, exist_ok=True)
    document = FreeCAD.newDocument("CylindricalRepair07A")
    try:
        Import.insert(request["step_path"], document.Name)
        sources = _objects(document, reverse=False)
        candidates = _extract(sources, rules, reverse=reverse)
        bores = [item for item in candidates if item["supported"] and item["role_evidence"] == "BORE_CONCAVE"]
        shafts = [item for item in candidates if item["supported"] and item["role_evidence"] == "SHAFT_CONVEX"]
        pairs = [(bore, shaft) for bore in bores for shaft in shafts if bore["_shape"] is not shaft["_shape"]]
        base = {
            "schema_version": 1,
            "scenario_id": request["scenario_id"],
            "analysis_input": "reimported_step_actual_brep",
            "input_step_sha256": request["input_step_sha256"],
            "numeric_rules": rules,
            "candidate_pair_count": len(pairs),
            "candidates": [_public(item) for item in candidates],
        }
        if len(pairs) != 1:
            status = "UNSUPPORTED_AMBIGUOUS_CYLINDRICAL_INTERFACE" if len(pairs) > 1 else "UNSUPPORTED_CYLINDRICAL_INTERFACE"
            operation = dict(base, status=status, classification={"classification": status, "error_components": []}, repairability=status, motion=_zero_motion())
            operation["debug"] = _debug(output / "operation_debug.FCStd", operation, sources, candidates)
            return operation
        bore, shaft = pairs[0]
        measurement = _measure(bore, shaft, rules)
        pre_geometry = _geometry(bore, shaft, rules)
        classification = _classification(measurement, pre_geometry, rules)
        decision_status, repairability, motion = _decide(classification, measurement, request["policy"], rules)
        operation = dict(
            base,
            status=decision_status,
            classification=classification,
            repairability=repairability,
            selected_candidates={"Side_1": _public(bore), "Side_2": _public(shaft)},
            pre_measurement=measurement,
            pre_geometry={key: value for key, value in pre_geometry.items() if not key.endswith("_shape")},
            policy=request["policy"],
            motion=motion,
        )
        corrected = common_shape = fused = None
        if decision_status == "AUTHORIZED_FOR_SINGLE_TRANSLATION":
            translation = FreeCAD.Vector(*motion["proposed_translation_mm"])
            corrected_bore, corrected_shaft = bore["_shape"].copy(), shaft["_shape"].copy()
            corrected_shaft.translate(translation)
            motion["executed_translation_mm"] = list(motion["proposed_translation_mm"])
            motion["execution_count"] = 1
            corrected = (corrected_bore, corrected_shaft)
            corrected_sources = [("Side_1_Bore", corrected_bore), ("Side_2_Shaft", corrected_shaft)]
            corrected_candidates = _extract(corrected_sources, rules)
            corrected_bores = [item for item in corrected_candidates if item["supported"] and item["role_evidence"] == "BORE_CONCAVE"]
            corrected_shafts = [item for item in corrected_candidates if item["supported"] and item["role_evidence"] == "SHAFT_CONVEX"]
            corrected_pairs = [(candidate_bore, candidate_shaft) for candidate_bore in corrected_bores for candidate_shaft in corrected_shafts if candidate_bore["_shape"] is not candidate_shaft["_shape"]]
            if len(corrected_pairs) == 1:
                post_bore, post_shaft = corrected_pairs[0]
                post = _measure(post_bore, post_shaft, rules)
                post_geometry_raw = _geometry(post_bore, post_shaft, rules)
                common_shape = post_geometry_raw["actual_common_shape"]
                post_geometry = {key: value for key, value in post_geometry_raw.items() if not key.endswith("_shape")}
                fused = corrected_bore.fuse(corrected_shaft).removeSplitter()
                inverse = corrected_shaft.copy()
                inverse.translate(-translation)
                inverse_equivalence = {
                    "actual_minus_original_mm3": float(inverse.cut(shaft["_shape"]).Volume),
                    "original_minus_actual_mm3": float(shaft["_shape"].cut(inverse).Volume),
                    "minimum_distance_mm": float(inverse.distToShape(shaft["_shape"])[0]),
                }
                common_area = post_geometry["actual_common_area_mm2"]
                remaining = {
                    "Side_1_area_mm2": float(post_bore["_face"].cut(common_shape).Area),
                    "Side_2_area_mm2": float(post_shaft["_face"].cut(common_shape).Area),
                    "coverage": {
                        "Side_1": common_area / post_bore["face_area_mm2"],
                        "Side_2": common_area / post_shaft["face_area_mm2"],
                    },
                }
                fuse = {
                    "executed": True,
                    "solid_count": len(fused.Solids),
                    "valid": bool(fused.isValid()),
                    "closed": bool(all(shell.isClosed() for shell in fused.Shells)),
                    "volume_mm3": float(fused.Volume),
                    "volume_conservation_error_mm3": float(abs(fused.Volume - (corrected_bore.Volume + corrected_shaft.Volume - corrected_bore.common(corrected_shaft).Volume))),
                }
                post_ok = (
                    post["axis_offset_mm"] <= rules["linear_epsilon_mm"]
                    and post["axis_angle_rad"] <= rules["angular_epsilon_rad"]
                    and abs(post["radial_clearance_mm"]) <= rules["radius_epsilon_mm"]
                    and post_geometry["actual_common_area_mm2"] > rules["area_epsilon_mm2"]
                    and post_geometry["material_common_volume_mm3"] <= rules["volume_epsilon_mm3"]
                    and fuse["solid_count"] == 1 and fuse["valid"] and fuse["closed"]
                    and fuse["volume_conservation_error_mm3"] <= rules["volume_epsilon_mm3"]
                    and inverse_equivalence["actual_minus_original_mm3"] <= rules["volume_epsilon_mm3"]
                    and inverse_equivalence["original_minus_actual_mm3"] <= rules["volume_epsilon_mm3"]
                    and inverse_equivalence["minimum_distance_mm"] <= rules["linear_epsilon_mm"]
                )
                operation.update(post_measurement=post, post_geometry=post_geometry, partition=remaining, fuse=fuse, inverse_translation_equivalence=inverse_equivalence)
                operation["status"] = "CORRECTED_AND_FUSED" if post_ok else "POSTCHECK_FAILED"
                _export_step(output / "corrected_assembly.step", (("Side_1_Bore", corrected_bore), ("Side_2_Shaft", corrected_shaft)))
                _export_step(output / "fused.step", (("Fused_Result", fused if False else corrected_bore.fuse(corrected_shaft).removeSplitter()),))
                if common_shape and not common_shape.isNull():
                    common_shape.exportBrep(str(output / "actual_common.brep"))
            else:
                operation["status"] = "POSTCHECK_FAILED"
                operation["postcheck_failure"] = {
                    "reason": "corrected role-valid candidates are not unique",
                    "pair_count": len(corrected_pairs),
                    "candidates": [_public(item) for item in corrected_candidates],
                }
        elif decision_status == "NO_CORRECTION_REQUIRED":
            common_shape = pre_geometry["actual_common_shape"]
            fused = bore["_shape"].fuse(shaft["_shape"]).removeSplitter()
            operation["post_measurement"] = dict(measurement)
            operation["post_geometry"] = dict(operation["pre_geometry"])
            operation["fuse"] = {"executed": False, "validation_only": True, "solid_count": len(fused.Solids), "valid": bool(fused.isValid()), "closed": bool(all(shell.isClosed() for shell in fused.Shells))}
        rejection = pre_geometry["material_common_shape"] if pre_geometry["material_common_volume_mm3"] > rules["volume_epsilon_mm3"] and operation["status"] != "CORRECTED_AND_FUSED" else None
        operation["debug"] = _debug(output / "operation_debug.FCStd", operation, sources, candidates, corrected, common_shape, fused, rejection)
        return operation
    finally:
        FreeCAD.closeDocument(document.Name)


def _read_brep(path):
    shape = Part.Shape()
    shape.read(str(path))
    if shape.isNull():
        raise RuntimeError("empty BREP artifact")
    return shape


def _verify_artifacts(request):
    rules = request["numeric_rules"]
    corrected_doc = FreeCAD.newDocument("CylindricalRepair07ACorrectedRoundtrip")
    fused_doc = FreeCAD.newDocument("CylindricalRepair07AFusedRoundtrip")
    try:
        Import.insert(request["corrected_step"], corrected_doc.Name)
        corrected_sources = _objects(corrected_doc)
        candidates = _extract(corrected_sources, rules)
        bores = [item for item in candidates if item["supported"] and item["role_evidence"] == "BORE_CONCAVE"]
        shafts = [item for item in candidates if item["supported"] and item["role_evidence"] == "SHAFT_CONVEX"]
        pairs = [(bore, shaft) for bore in bores for shaft in shafts if bore["_shape"] is not shaft["_shape"]]
        if len(pairs) != 1:
            return {"status": "FAIL", "failures": [{"kind": "corrected_candidate_pair_count", "actual": len(pairs)}]}
        bore, shaft = pairs[0]
        measurement = _measure(bore, shaft, rules)
        geometry = _geometry(bore, shaft, rules)
        stored_common = _read_brep(request["common_brep"])
        direct_common = geometry["actual_common_shape"]
        common_equivalence = {
            "direct_minus_artifact_mm2": float(direct_common.cut(stored_common).Area),
            "artifact_minus_direct_mm2": float(stored_common.cut(direct_common).Area),
            "minimum_distance_mm": float(direct_common.distToShape(stored_common)[0]),
        }
        Import.insert(request["fused_step"], fused_doc.Name)
        fused_objects = _objects(fused_doc)
        fused = fused_objects[0][1] if len(fused_objects) == 1 else Part.Shape()
        reference_fused = bore["_shape"].fuse(shaft["_shape"]).removeSplitter()
        fused_equivalence = {
            "roundtrip_minus_reference_mm3": float(fused.cut(reference_fused).Volume) if not fused.isNull() else math.inf,
            "reference_minus_roundtrip_mm3": float(reference_fused.cut(fused).Volume) if not fused.isNull() else math.inf,
            "minimum_distance_mm": float(fused.distToShape(reference_fused)[0]) if not fused.isNull() else math.inf,
        }
        failures = []
        if measurement["axis_offset_mm"] > rules["linear_epsilon_mm"]:
            failures.append({"kind": "roundtrip_axis_offset"})
        if measurement["axis_angle_rad"] > rules["angular_epsilon_rad"]:
            failures.append({"kind": "roundtrip_axis_angle"})
        if abs(measurement["radial_clearance_mm"]) > rules["radius_epsilon_mm"]:
            failures.append({"kind": "roundtrip_radius"})
        if measurement["axial_overlap_mm"] <= rules["linear_epsilon_mm"]:
            failures.append({"kind": "roundtrip_axial_overlap"})
        if geometry["actual_common_area_mm2"] <= rules["area_epsilon_mm2"]:
            failures.append({"kind": "roundtrip_actual_common"})
        if geometry["material_common_volume_mm3"] > rules["volume_epsilon_mm3"]:
            failures.append({"kind": "roundtrip_material_interference"})
        if common_equivalence["direct_minus_artifact_mm2"] > rules["area_epsilon_mm2"] or common_equivalence["artifact_minus_direct_mm2"] > rules["area_epsilon_mm2"] or common_equivalence["minimum_distance_mm"] > rules["linear_epsilon_mm"]:
            failures.append({"kind": "common_geometric_equivalence"})
        if any(value > rules["volume_epsilon_mm3"] for key, value in fused_equivalence.items() if key.endswith("_mm3")) or fused_equivalence["minimum_distance_mm"] > rules["linear_epsilon_mm"]:
            failures.append({"kind": "fused_geometric_equivalence"})
        if fused.isNull() or len(fused.Solids) != 1 or not fused.isValid() or not all(shell.isClosed() for shell in fused.Shells):
            failures.append({"kind": "fused_roundtrip_validity"})
        return {
            "status": "PASS" if not failures else "FAIL",
            "failures": failures,
            "corrected_measurement": measurement,
            "corrected_geometry": {key: value for key, value in geometry.items() if not key.endswith("_shape")},
            "common_geometric_equivalence": common_equivalence,
            "fused_geometric_equivalence": fused_equivalence,
            "topology": {
                "corrected_solid_counts": [len(shape.Solids) for _, shape in corrected_sources],
                "fused_solid_count": len(fused.Solids) if not fused.isNull() else 0,
                "common_face_count": len(stored_common.Faces),
                "common_edge_count": len(stored_common.Edges),
                "common_vertex_count": len(stored_common.Vertexes),
            },
        }
    finally:
        FreeCAD.closeDocument(corrected_doc.Name)
        FreeCAD.closeDocument(fused_doc.Name)


def _main():
    request = json.loads(Path(os.environ["DMSLICER_FREECAD_REQUEST"]).read_text(encoding="utf-8"))
    try:
        if request["action"] == "generate":
            result = _generate(request)
        elif request["action"] == "analyze":
            result = _analyze(request)
        elif request["action"] == "verify_artifacts":
            result = _verify_artifacts(request)
        else:
            raise ValueError("unsupported 07A action")
        response = {"status": "ok", "result": result}
    except Exception as error:
        response = {"status": "error", "error": "%s: %s" % (type(error).__name__, error)}
    Path(os.environ["DMSLICER_FREECAD_RESPONSE"]).write_text(json.dumps(response, sort_keys=True), encoding="utf-8")


if __name__ == "__main__":
    _main()
