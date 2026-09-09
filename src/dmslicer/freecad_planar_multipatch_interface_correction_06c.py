"""FreeCADCmd B-rep backend for 06C planar interface FaceSets."""

import hashlib
import json
import math
import os
import traceback
from pathlib import Path

import FreeCAD
import Import
import Part


REFERENCE = FreeCAD.Vector(0.0, 0.0, 1.0)


def _digest(shape):
    return "sha256:" + hashlib.sha256(
        shape.exportBrepToString().encode("utf-8")
    ).hexdigest()


def _closed(shape):
    return bool(shape.Shells) and all(shell.isClosed() for shell in shape.Shells)


def _objects(document, reverse=False):
    values = [
        (obj.Label, obj.Shape)
        for obj in document.Objects
        if obj.TypeId == "Part::Feature"
        and hasattr(obj, "Shape")
        and not obj.Shape.isNull()
    ]
    return sorted(values, key=lambda value: value[0], reverse=reverse)


def _roles(document, reverse=False):
    sources = _objects(document, reverse)
    if len(sources) != 2:
        raise ValueError("06C requires exactly two imported Part::Feature objects")
    roles = {}
    for role in ("Side_1", "Side_2"):
        matches = [shape for label, shape in sources if label == role]
        if len(matches) != 1 or len(matches[0].Solids) != 1:
            raise ValueError("missing, ambiguous, or non-solid role " + role)
        solid = matches[0].Solids[0]
        if not solid.isValid() or not _closed(solid):
            raise ValueError(role + " is not a valid closed solid")
        roles[role] = solid
    return roles["Side_1"], roles["Side_2"]


def _plane(face):
    return face.Surface if "plane" in type(face.Surface).__name__.lower() else None


def _normal(face):
    value = face.normalAt(0.0, 0.0)
    value.normalize()
    return value


def _face_descriptor(index, face, normal, support):
    return {
        "human_face_label": "Face" + str(index),
        "geometry_digest": _digest(face),
        "surface_type": type(face.Surface).__name__,
        "area_mm2": float(face.Area),
        "support_coordinate_mm": float(support),
        "outward_normal": [float(normal.x), float(normal.y), float(normal.z)],
    }


def _face_sets(shape, role, sign, linear_epsilon, reverse=False):
    indexed = list(enumerate(shape.Faces, start=1))
    if reverse:
        indexed.reverse()
    candidates = []
    for index, face in indexed:
        plane = _plane(face)
        if plane is None:
            continue
        try:
            normal = _normal(face)
        except Exception:
            continue
        if normal.dot(REFERENCE) * sign < 1.0 - linear_epsilon:
            continue
        support = float(plane.Position.dot(REFERENCE))
        candidates.append(
            {
                "index": index,
                "shape": face,
                "normal": normal,
                "support": support,
                "descriptor": _face_descriptor(index, face, normal, support),
            }
        )
    candidates.sort(
        key=lambda item: (item["support"], item["descriptor"]["geometry_digest"])
    )
    groups = []
    for candidate in candidates:
        matching = next(
            (
                group
                for group in groups
                if abs(group["support_coordinate_mm"] - candidate["support"])
                <= linear_epsilon
            ),
            None,
        )
        if matching is None:
            matching = {
                "role": role,
                "support_coordinate_mm": candidate["support"],
                "members": [],
            }
            groups.append(matching)
        matching["members"].append(candidate)
    groups.sort(key=lambda group: group["support_coordinate_mm"])
    for group_index, group in enumerate(groups, start=1):
        group["members"].sort(
            key=lambda member: member["descriptor"]["geometry_digest"]
        )
        coordinates = [member["support"] for member in group["members"]]
        group["face_set_id"] = f"{role}_FaceSet_{group_index}"
        group["support_coordinate_mm"] = float(min(coordinates))
        group["spread_mm"] = float(max(coordinates) - min(coordinates))
        group["total_area_mm2"] = float(
            sum(member["shape"].Area for member in group["members"])
        )
    return groups


def _public_face_set(group):
    members = [member["descriptor"] for member in group["members"]]
    return {
        "face_set_id": group["face_set_id"],
        "role": group["role"],
        "member_faces": [member["human_face_label"] for member in members],
        "member_face_descriptors": members,
        "member_face_count": len(members),
        "component_member_count": len(members),
        "reference_normal": [0.0, 0.0, 1.0]
        if group["role"] == "Side_1"
        else [0.0, 0.0, -1.0],
        "support_coordinate_mm": float(group["support_coordinate_mm"]),
        "member_support_coordinates_mm": [
            float(member["support_coordinate_mm"]) for member in members
        ],
        "spread_mm": float(group["spread_mm"]),
        "total_area_mm2": float(group["total_area_mm2"]),
        "selection_evidence": {
            "surface_family": "plane",
            "normal_role_match": True,
            "grouping_rule": "absolute_support_coordinate_difference_le_linear_epsilon",
        },
    }


def _common_patches(first_group, second_group, area_epsilon, reverse=False):
    first_members = list(first_group["members"])
    second_members = list(second_group["members"])
    if reverse:
        first_members.reverse()
        second_members.reverse()
    raw = []
    for first in first_members:
        for second in second_members:
            common = first["shape"].common(second["shape"])
            faces = list(common.Faces)
            if reverse:
                faces.reverse()
            for common_face in faces:
                if common_face.Area <= area_epsilon:
                    continue
                raw.append(
                    {
                        "shape": common_face,
                        "geometry_digest": _digest(common_face),
                        "area_mm2": float(common_face.Area),
                        "surface_type": type(common_face.Surface).__name__,
                        "boundary_curve_types": sorted(
                            type(edge.Curve).__name__ for edge in common_face.Edges
                        ),
                        "source_face_linkage": [
                            {
                                "Side_1": first["descriptor"]["human_face_label"],
                                "Side_1_geometry_digest": first["descriptor"][
                                    "geometry_digest"
                                ],
                                "Side_2": second["descriptor"]["human_face_label"],
                                "Side_2_geometry_digest": second["descriptor"][
                                    "geometry_digest"
                                ],
                            }
                        ],
                    }
                )
    by_digest = {}
    for record in raw:
        existing = by_digest.get(record["geometry_digest"])
        if existing is None:
            by_digest[record["geometry_digest"]] = record
            continue
        for linkage in record["source_face_linkage"]:
            if linkage not in existing["source_face_linkage"]:
                existing["source_face_linkage"].append(linkage)
    patches = sorted(by_digest.values(), key=lambda patch: patch["geometry_digest"])
    for patch in patches:
        patch["source_face_linkage"].sort(
            key=lambda link: (
                link["Side_1_geometry_digest"], link["Side_2_geometry_digest"]
            )
        )
    return raw, patches


def _translated_group(shape, sign, target_support, rules, reverse=False):
    groups = _face_sets(
        shape,
        "Side_2",
        sign,
        rules["linear_epsilon_mm"],
        reverse,
    )
    matches = [
        group
        for group in groups
        if abs(group["support_coordinate_mm"] - target_support)
        <= rules["linear_epsilon_mm"]
    ]
    if len(matches) != 1:
        return None
    return matches[0]


def _candidate_pairs(first, second, policy, rules, reverse=False):
    first_sets = _face_sets(
        first, "Side_1", 1.0, rules["linear_epsilon_mm"], reverse
    )
    second_sets = _face_sets(
        second, "Side_2", -1.0, rules["linear_epsilon_mm"], reverse
    )
    eligible = []
    for first_set in first_sets:
        for second_set in second_sets:
            gap = float(
                second_set["support_coordinate_mm"]
                - first_set["support_coordinate_mm"]
            )
            if gap <= rules["linear_epsilon_mm"]:
                continue
            if not (
                policy.get("policy_valid") is True
                and policy.get("allow_motion") is True
                and type(policy.get("tauE_mm")) in (int, float)
                and type(policy.get("max_translation_mm")) in (int, float)
                and math.isfinite(float(policy["tauE_mm"]))
                and math.isfinite(float(policy["max_translation_mm"]))
                and gap <= float(policy["tauE_mm"]) + rules["linear_epsilon_mm"]
                and gap
                <= float(policy["max_translation_mm"]) + rules["linear_epsilon_mm"]
            ):
                continue
            preview = second.copy()
            preview.translate(FreeCAD.Vector(0.0, 0.0, -gap))
            moved_set = _translated_group(
                preview,
                -1.0,
                first_set["support_coordinate_mm"],
                rules,
                reverse,
            )
            if moved_set is None:
                continue
            raw, patches = _common_patches(
                first_set,
                moved_set,
                rules["area_epsilon_mm2"],
                reverse,
            )
            area = float(sum(patch["area_mm2"] for patch in patches))
            if area <= rules["area_epsilon_mm2"]:
                continue
            first_public = _public_face_set(first_set)
            second_public = _public_face_set(second_set)
            member_gaps = [
                float(second_member["support"] - first_set["support_coordinate_mm"])
                for second_member in second_set["members"]
            ]
            gap_spread = float(max(member_gaps) - min(member_gaps))
            eligible.append(
                {
                    "first": first_set,
                    "second": second_set,
                    "moved_second": moved_set,
                    "preview": preview,
                    "raw": raw,
                    "patches": patches,
                    "record": {
                        "pair_id": first_public["face_set_id"]
                        + "__"
                        + second_public["face_set_id"],
                        "role_binding": {"fixed": "Side_1", "moving": "Side_2"},
                        "Side_1": first_public,
                        "Side_2": second_public,
                        "gap_mm": gap,
                        "member_gap_mm": member_gaps,
                        "min_gap_mm": float(min(member_gaps)),
                        "max_gap_mm": float(max(member_gaps)),
                        "gap_spread_mm": gap_spread,
                        "prospective_common_area_mm2": area,
                        "prospective_raw_common_face_count": len(raw),
                        "prospective_patch_count": len(patches),
                        "selection_reason": "eligible_under_finite_planar_faceset_contract",
                    },
                }
            )
    eligible.sort(key=lambda pair: pair["record"]["pair_id"])
    return first_sets, second_sets, eligible


def _component_groups(patches, linear_epsilon):
    parent = list(range(len(patches)))

    def find(index):
        while parent[index] != index:
            parent[index] = parent[parent[index]]
            index = parent[index]
        return index

    def union(first, second):
        first_root = find(first)
        second_root = find(second)
        if first_root != second_root:
            parent[second_root] = first_root

    for first_index, first in enumerate(patches):
        for second_index in range(first_index + 1, len(patches)):
            distance, _, _ = first["shape"].distToShape(patches[second_index]["shape"])
            if distance <= linear_epsilon:
                union(first_index, second_index)
    grouped = {}
    for index in range(len(patches)):
        grouped.setdefault(find(index), []).append(index)
    return list(grouped.values())


def _wire_descriptor(wire):
    try:
        enclosed = float(Part.Face(wire).Area)
    except Exception:
        enclosed = 0.0
    return {
        "geometry_digest": _digest(wire),
        "edge_count": len(wire.Edges),
        "length_mm": float(wire.Length),
        "enclosed_area_mm2": enclosed,
    }


def _topology(patches, linear_epsilon):
    groups = _component_groups(patches, linear_epsilon)
    records = []
    for patch_indices in groups:
        component_patches = [patches[index] for index in patch_indices]
        shape = Part.makeCompound([patch["shape"] for patch in component_patches])
        loops = [
            _wire_descriptor(wire)
            for patch in component_patches
            for wire in patch["shape"].Wires
        ]
        loops.sort(
            key=lambda loop: (-loop["enclosed_area_mm2"], loop["geometry_digest"])
        )
        for loop_index, loop in enumerate(loops):
            loop["kind"] = "outer" if loop_index == 0 else "hole"
        records.append(
            {
                "shape": shape,
                "patch_indices": patch_indices,
                "geometry_digest": _digest(shape),
                "area_mm2": float(sum(patch["area_mm2"] for patch in component_patches)),
                "boundary_loops": loops,
                "source_face_linkage": sorted(
                    {
                        json.dumps(link, sort_keys=True)
                        for patch in component_patches
                        for link in patch["source_face_linkage"]
                    }
                ),
            }
        )
    records.sort(key=lambda component: component["geometry_digest"])
    for component_index, component in enumerate(records, start=1):
        component["component_id"] = "Component_" + str(component_index)
        component["source_face_linkage"] = [
            json.loads(value) for value in component["source_face_linkage"]
        ]
        for patch_index in component["patch_indices"]:
            patches[patch_index]["component_id"] = component["component_id"]
    boundary_count = sum(len(component["boundary_loops"]) for component in records)
    hole_count = sum(
        sum(loop["kind"] == "hole" for loop in component["boundary_loops"])
        for component in records
    )
    public = []
    for component in records:
        public.append(
            {
                key: value
                for key, value in component.items()
                if key not in {"shape", "patch_indices"}
            }
        )
    return {
        "patch_count": len(patches),
        "component_count": len(records),
        "connectedness": "connected" if len(records) == 1 else "disconnected",
        "boundary_component_count": boundary_count,
        "hole_count": hole_count,
        "first_betti_number": hole_count,
        "annular_or_multiply_connected": hole_count > 0,
        "components": public,
    }, records


def _public_patches(patches):
    return [
        {key: value for key, value in patch.items() if key != "shape"}
        for patch in patches
    ]


def _remaining(first_group, second_group, patches, area_epsilon):
    patch_compound = Part.makeCompound([patch["shape"] for patch in patches])
    result = {"Side_1": [], "Side_2": []}
    records = []
    for role, group in (("Side_1", first_group), ("Side_2", second_group)):
        for member in group["members"]:
            linked = []
            face_label = member["descriptor"]["human_face_label"]
            for patch in patches:
                if any(link[role] == face_label for link in patch["source_face_linkage"]):
                    linked.append(patch["shape"])
            tool = Part.makeCompound(linked) if linked else Part.Shape()
            remainder = member["shape"].cut(tool) if linked else member["shape"].copy()
            faces = [face for face in remainder.Faces if face.Area > area_epsilon]
            for face in faces:
                result[role].append(face)
                records.append(
                    {
                        "role": role,
                        "source_face_set": group["face_set_id"],
                        "source_member_face": face_label,
                        "source_member_geometry_digest": member["descriptor"][
                            "geometry_digest"
                        ],
                        "result_digest": _digest(face),
                        "area_mm2": float(face.Area),
                        "operation_kind": "FACE_CUT_REMAINDER",
                    }
                )
    return result, records, patch_compound


def _spatial_partition(group, common_shape, remaining_shapes, area_epsilon):
    source = Part.makeCompound([member["shape"] for member in group["members"]])
    remaining = Part.makeCompound(remaining_shapes) if remaining_shapes else Part.Shape()
    pieces = [common_shape]
    if remaining_shapes:
        pieces.append(remaining)
    result = Part.makeCompound(pieces)
    overlap = common_shape.common(remaining).Area if remaining_shapes else 0.0
    missing = source.cut(result).Area
    outside = result.cut(source).Area
    return {
        "common_remaining_overlap_area_mm2": float(overlap),
        "coverage_missing_area_mm2": float(missing),
        "outside_area_mm2": float(outside),
        "source_area_mm2": float(source.Area),
        "result_area_mm2": float(result.Area),
        "within_area_epsilon": bool(
            overlap <= area_epsilon
            and missing <= area_epsilon
            and outside <= area_epsilon
        ),
    }


def _export_brep(output, name, shape):
    path = output / (name + ".brep")
    shape.exportBrep(str(path))
    return path.name


def _export_step(output, name, objects):
    document = FreeCAD.newDocument("Export06C_" + name)
    try:
        features = []
        for object_name, label, shape in objects:
            feature = document.addObject("Part::Feature", object_name)
            feature.Label = label
            feature.Shape = shape
            features.append(feature)
        document.recompute()
        path = output / (name + ".step")
        Import.export(features, str(path))
        return path.name
    finally:
        FreeCAD.closeDocument(document.Name)


def _reimport_corrected(path, rules, reverse=False):
    document = FreeCAD.newDocument("ReimportCorrected06C")
    try:
        Import.insert(str(path), document.Name)
        first, second = _roles(document, reverse)
        first_sets = _face_sets(first, "Side_1", 1.0, rules["linear_epsilon_mm"], reverse)
        second_sets = _face_sets(second, "Side_2", -1.0, rules["linear_epsilon_mm"], reverse)
        matches = []
        for first_set in first_sets:
            for second_set in second_sets:
                gap = second_set["support_coordinate_mm"] - first_set["support_coordinate_mm"]
                if abs(gap) > rules["linear_epsilon_mm"]:
                    continue
                _, patches = _common_patches(
                    first_set, second_set, rules["area_epsilon_mm2"], reverse
                )
                if sum(patch["area_mm2"] for patch in patches) > rules["area_epsilon_mm2"]:
                    matches.append((first_set, second_set, gap, patches))
        if len(matches) != 1:
            raise RuntimeError(
                "corrected STEP did not contain one semantic zero-gap FaceSet pair"
            )
        first_set, second_set, gap, patches = matches[0]
        topology, _ = _topology(patches, rules["linear_epsilon_mm"])
        common_area = float(sum(patch["area_mm2"] for patch in patches))
        remaining, _, _ = _remaining(
            first_set, second_set, patches, rules["area_epsilon_mm2"]
        )
        return {
            "roles": ["Side_1", "Side_2"],
            "residual_gap_mm": float(gap),
            "support_coordinates_mm": {
                "Side_1": float(first_set["support_coordinate_mm"]),
                "Side_2": float(second_set["support_coordinate_mm"]),
            },
            "common_area_mm2": common_area,
            "patch_count": topology["patch_count"],
            "component_count": topology["component_count"],
            "boundary_component_count": topology["boundary_component_count"],
            "hole_count": topology["hole_count"],
            "coverage": {
                "Side_1": common_area / first_set["total_area_mm2"],
                "Side_2": common_area / second_set["total_area_mm2"],
            },
            "remaining_area_mm2": {
                role: float(sum(face.Area for face in remaining[role]))
                for role in ("Side_1", "Side_2")
            },
            "solid_counts": [len(first.Solids), len(second.Solids)],
            "valid": bool(first.isValid() and second.isValid()),
            "closed": bool(_closed(first) and _closed(second)),
            "volumes_mm3": [float(first.Volume), float(second.Volume)],
        }
    finally:
        FreeCAD.closeDocument(document.Name)


def _reimport_fused(path):
    document = FreeCAD.newDocument("ReimportFused06C")
    try:
        Import.insert(str(path), document.Name)
        objects = _objects(document)
        solids = [solid for _, shape in objects for solid in shape.Solids]
        return {
            "solid_count": len(solids),
            "valid": bool(len(solids) == 1 and solids[0].isValid()),
            "closed": bool(len(solids) == 1 and _closed(solids[0])),
            "volume_mm3": float(sum(solid.Volume for solid in solids)),
        }
    finally:
        FreeCAD.closeDocument(document.Name)


def _add_group(document, name, parent=None):
    group = document.addObject("App::DocumentObjectGroup", name)
    group.Label = name.replace("_", " ")
    if parent is not None:
        parent.addObject(group)
    return group


def _add_feature(document, group, name, label, shape, visible=False):
    feature = document.addObject("Part::Feature", name)
    feature.Label = label
    feature.Shape = shape
    group.addObject(feature)
    if feature.ViewObject is not None:
        feature.ViewObject.Visibility = visible
    return feature


def _debug_document(
    path,
    scenario_id,
    first,
    second,
    status,
    candidate_pairs,
    selected,
    corrected,
    patches,
    components,
    remaining,
    fused,
):
    document = FreeCAD.newDocument("PlanarMultipatch06CDebug")
    try:
        originals = _add_group(document, "Originals")
        show_originals = status != "SUPPORTED_UNIQUE_INTERFACE_FACESET"
        _add_feature(document, originals, "Original_Side_1", "Original Side_1", first, show_originals)
        _add_feature(document, originals, "Original_Side_2", "Original Side_2", second, show_originals)
        if status == "SUPPORTED_UNIQUE_INTERFACE_FACESET":
            corrected_group = _add_group(document, "Corrected_Assembly")
            _add_feature(document, corrected_group, "Corrected_Side_1", "Corrected Side_1", first)
            _add_feature(document, corrected_group, "Corrected_Side_2", "Corrected Side_2", corrected)
            selected_group = _add_group(document, "Selected_Interface_FaceSets")
            _add_feature(
                document,
                selected_group,
                "Selected_Side_1_FaceSet",
                "Selected Side_1 FaceSet",
                Part.makeCompound([member["shape"] for member in selected["first"]["members"]]),
            )
            _add_feature(
                document,
                selected_group,
                "Selected_Side_2_FaceSet",
                "Selected Side_2 FaceSet",
                Part.makeCompound([member["shape"] for member in selected["moved_second"]["members"]]),
            )
            common_group = _add_group(document, "Common_Patches")
            for index, patch in enumerate(patches, start=1):
                label = "Annular Common" if scenario_id == "P11" else "Common " + str(index)
                _add_feature(document, common_group, "Common_" + str(index), label, patch["shape"])
            component_group = _add_group(document, "Components")
            for index, component in enumerate(components, start=1):
                _add_feature(
                    document,
                    component_group,
                    "Component_" + str(index),
                    "Component " + str(index),
                    component["shape"],
                )
            if scenario_id == "P11":
                boundary_group = _add_group(document, "Boundary_Loops")
                wires = patches[0]["shape"].Wires
                descriptors = [(_wire_descriptor(wire), wire) for wire in wires]
                descriptors.sort(key=lambda item: -item[0]["enclosed_area_mm2"])
                for index, (_, wire) in enumerate(descriptors):
                    name = "Outer" if index == 0 else "Hole"
                    _add_feature(document, boundary_group, name, name, wire)
            remaining_group = _add_group(document, "Remaining")
            for role in ("Side_1", "Side_2"):
                if remaining[role]:
                    _add_feature(
                        document,
                        remaining_group,
                        role + "_Remaining",
                        role + " Remaining",
                        Part.makeCompound(remaining[role]),
                    )
                else:
                    empty = document.addObject("App::FeaturePython", role + "_Remaining_EMPTY")
                    empty.Label = role + " Remaining EMPTY"
                    empty.addProperty("App::PropertyBool", "EMPTY", "06C")
                    empty.EMPTY = True
                    remaining_group.addObject(empty)
            fused_group = _add_group(document, "Fused_Result")
            _add_feature(document, fused_group, "Fused_Solid", "Fused Result", fused, True)
        else:
            candidate_group = _add_group(document, "Candidate_Interface_FaceSets")
            for index, pair in enumerate(candidate_pairs, start=1):
                feature = _add_feature(
                    document,
                    candidate_group,
                    "Candidate_Set_" + str(index),
                    "Candidate Set " + str(index),
                    Part.makeCompound(
                        [member["shape"] for member in pair["second"]["members"]]
                    ),
                    False,
                )
                feature.addProperty("App::PropertyBool", "DISPLAY_ONLY", "06C")
                feature.addProperty("App::PropertyBool", "NOT_EXECUTED", "06C")
                feature.DISPLAY_ONLY = True
                feature.NOT_EXECUTED = True
            rejection_group = _add_group(document, "Rejection_Evidence")
            evidence = document.addObject("App::FeaturePython", "Ambiguity_Rejection")
            evidence.Label = "UNSUPPORTED_AMBIGUOUS_INTERFACE_SET"
            evidence.addProperty("App::PropertyString", "Status", "06C")
            evidence.addProperty("App::PropertyInteger", "CandidateCount", "06C")
            evidence.Status = status
            evidence.CandidateCount = len(candidate_pairs)
            rejection_group.addObject(evidence)
            if evidence.ViewObject is not None:
                evidence.ViewObject.Visibility = True
        document.recompute()
        document.saveAs(str(path))
    finally:
        FreeCAD.closeDocument(document.Name)
    reopened = FreeCAD.openDocument(str(path))
    try:
        groups = [
            obj.Name
            for obj in reopened.Objects
            if obj.TypeId == "App::DocumentObjectGroup"
        ]
        visible = [
            obj.Name
            for obj in reopened.Objects
            if obj.ViewObject is not None and obj.ViewObject.Visibility
        ]
        if "Originals" not in groups:
            raise RuntimeError("debug FCStd lost Originals group")
        if status == "SUPPORTED_UNIQUE_INTERFACE_FACESET" and "Fused_Result" not in groups:
            raise RuntimeError("debug FCStd lost Fused_Result group")
        if status != "SUPPORTED_UNIQUE_INTERFACE_FACESET" and "Corrected_Assembly" in groups:
            raise RuntimeError("rejected debug FCStd contains a corrected-success group")
        return {"reopened": True, "groups": groups, "visible_objects": visible}
    finally:
        FreeCAD.closeDocument(reopened.Name)


def _generate(request):
    scenario_id = request["scenario_id"]
    vector = FreeCAD.Vector
    if scenario_id == "P10":
        first = Part.makeBox(60.0, 40.0, 5.0, vector(0.0, 0.0, 0.0))
        left = Part.makeBox(12.0, 16.0, 15.0, vector(6.0, 12.0, 5.05))
        right = Part.makeBox(12.0, 16.0, 15.0, vector(42.0, 12.0, 5.05))
        bridge = Part.makeBox(48.0, 8.0, 5.0, vector(6.0, 16.0, 15.05))
        second = left.fuse(right).fuse(bridge).removeSplitter()
        construction = {
            "Side_1": {"kind": "box", "bounds_mm": [0, 60, 0, 40, 0, 5]},
            "Side_2": {
                "kind": "connected_fused_feet_bridge",
                "left_foot_bounds_mm": [6, 18, 12, 28, 5.05, 20.05],
                "right_foot_bounds_mm": [42, 54, 12, 28, 5.05, 20.05],
                "upper_bridge_bounds_mm": [6, 54, 16, 24, 15.05, 20.05],
            },
        }
    elif scenario_id == "P11":
        first = Part.makeBox(60.0, 60.0, 5.0, vector(-30.0, -30.0, 0.0))
        outer = Part.makeCylinder(20.0, 10.0, vector(0.0, 0.0, 5.05))
        inner = Part.makeCylinder(10.0, 10.0, vector(0.0, 0.0, 5.05))
        second = outer.cut(inner)
        construction = {
            "Side_1": {"kind": "box", "bounds_mm": [-30, 30, -30, 30, 0, 5]},
            "Side_2": {
                "kind": "direct_analytic_annular_cylinder",
                "outer_radius_mm": 20.0,
                "inner_radius_mm": 10.0,
                "height_mm": 10.0,
                "base_z_mm": 5.05,
                "transformGeometry_used": False,
            },
        }
    elif scenario_id == "P12":
        first = Part.makeBox(60.0, 40.0, 5.0, vector(0.0, 0.0, 0.0))
        left = Part.makeBox(12.0, 16.0, 15.0, vector(6.0, 12.0, 5.05))
        right = Part.makeBox(12.0, 16.0, 15.0, vector(42.0, 12.0, 5.08))
        bridge = Part.makeBox(48.0, 8.0, 5.08, vector(6.0, 16.0, 15.0))
        second = left.fuse(right).fuse(bridge).removeSplitter()
        construction = {
            "Side_1": {"kind": "box", "bounds_mm": [0, 60, 0, 40, 0, 5]},
            "Side_2": {
                "kind": "connected_unequal_support_feet_bridge",
                "left_foot_bounds_mm": [6, 18, 12, 28, 5.05, 20.05],
                "right_foot_bounds_mm": [42, 54, 12, 28, 5.08, 20.08],
                "upper_bridge_bounds_mm": [6, 54, 16, 24, 15.0, 20.08],
            },
        }
    else:
        raise ValueError("unknown 06C scenario " + scenario_id)
    if len(second.Solids) != 1 or not second.isValid() or not _closed(second):
        raise RuntimeError("generated Side_2 is not one valid closed connected solid")
    document = FreeCAD.newDocument("PlanarMultipatch06CGenerator")
    try:
        first_object = document.addObject("Part::Feature", "Side_1")
        second_object = document.addObject("Part::Feature", "Side_2")
        first_object.Label = "Side_1"
        second_object.Label = "Side_2"
        first_object.Shape = first
        second_object.Shape = second
        document.recompute()
        step_path = Path(request["step_path"])
        step_path.parent.mkdir(parents=True, exist_ok=True)
        Import.export([first_object, second_object], str(step_path))
        return {
            "status": "SUCCEEDED",
            "scenario_id": scenario_id,
            "step_path": str(step_path),
            "construction": construction,
            "solid_evidence": {
                "Side_1": {"solid_count": len(first.Solids), "valid": bool(first.isValid()), "closed": bool(_closed(first))},
                "Side_2": {"solid_count": len(second.Solids), "valid": bool(second.isValid()), "closed": bool(_closed(second))},
            },
        }
    finally:
        FreeCAD.closeDocument(document.Name)


def _analyze(request):
    rules = request["rules"]
    policy = request["policy"]
    reverse = request.get("traversal_order") == "reverse"
    output = Path(request["output_dir"])
    output.mkdir(parents=True, exist_ok=True)
    document = FreeCAD.newDocument("PlanarMultipatch06CAnalysis")
    try:
        Import.insert(request["step_path"], document.Name)
        first, second = _roles(document, reverse)
        first_sets, second_sets, candidates = _candidate_pairs(
            first, second, policy, rules, reverse
        )
        public_candidates = [candidate["record"] for candidate in candidates]
        face_set_evidence = {
            "raw_face_set_count": {
                "Side_1": len(first_sets),
                "Side_2": len(second_sets),
            },
            "raw_face_sets": {
                "Side_1": [_public_face_set(group) for group in first_sets],
                "Side_2": [_public_face_set(group) for group in second_sets],
            },
            "eligible_face_set_pair_count": len(candidates),
            "candidate_face_set_pair_count": len(candidates),
            "candidate_pairs": public_candidates,
            "selection_policy": "execute_only_when_exactly_one_pair_satisfies_the_contract",
        }
        base_motion = {
            "motion_authorized": False,
            "executed_translation_mm": [0.0, 0.0, 0.0],
            "executed_translation_norm_mm": 0.0,
            "tangential_translation_norm_mm": 0.0,
            "rigid_side_2_transform": True,
            "rotation_executed": False,
            "scale_executed": False,
            "deformation_executed": False,
        }
        if len(candidates) > 1:
            status = "UNSUPPORTED_AMBIGUOUS_INTERFACE_SET"
            operation = {
                "schema_version": 1,
                "scenario_id": request["scenario_id"],
                "status": status,
                "face_sets": face_set_evidence,
                "motion": base_motion,
                "partition": {},
                "topology": {},
                "fuse": {"executed": False},
                "provenance": {
                    "roles": {"Side_1": "Side_1", "Side_2": "Side_2"},
                    "face_sets": public_candidates,
                    "operation_kind": "DIRECT_BREP_PROSPECTIVE_FACESET_COMMON",
                    "native_history_claimed": False,
                },
            }
            if request.get("create_view"):
                operation["view_reopen"] = _debug_document(
                    output / "operation_debug.FCStd",
                    request["scenario_id"],
                    first,
                    second,
                    status,
                    candidates,
                    None,
                    None,
                    [],
                    [],
                    {"Side_1": [], "Side_2": []},
                    Part.Shape(),
                )
            return operation
        if not candidates:
            numeric_policy = all(
                type(policy.get(name)) in (int, float)
                and not isinstance(policy.get(name), bool)
                and math.isfinite(float(policy[name]))
                and float(policy[name]) >= 0.0
                for name in ("tauE_mm", "max_translation_mm")
            )
            if policy.get("policy_valid") is not True or not numeric_policy:
                status = "MOTION_NOT_AUTHORIZED"
            elif policy.get("allow_motion") is not True:
                status = "MOTION_NOT_AUTHORIZED"
            else:
                permissive = dict(policy)
                permissive.update(
                    {
                        "policy_valid": True,
                        "allow_motion": True,
                        "tauE_mm": 1.0e9,
                        "max_translation_mm": 1.0e9,
                    }
                )
                _, _, geometric_candidates = _candidate_pairs(
                    first, second, permissive, rules, reverse
                )
                gaps = [candidate["record"]["gap_mm"] for candidate in geometric_candidates]
                if gaps and all(
                    gap > float(policy["tauE_mm"]) + rules["linear_epsilon_mm"]
                    for gap in gaps
                ):
                    status = "ENGINEERING_TOLERANCE_EXCEEDED"
                elif gaps and all(
                    gap
                    > float(policy["max_translation_mm"])
                    + rules["linear_epsilon_mm"]
                    for gap in gaps
                ):
                    status = "TRANSLATION_BUDGET_EXCEEDED"
                else:
                    status = "NO_POSITIVE_AREA_INTERFACE"
            return {
                "schema_version": 1,
                "scenario_id": request["scenario_id"],
                "status": status,
                "face_sets": face_set_evidence,
                "motion": base_motion,
                "partition": {},
                "topology": {},
                "fuse": {"executed": False},
                "provenance": {
                    "roles": {"Side_1": "Side_1", "Side_2": "Side_2"},
                    "operation_kind": "DIRECT_BREP_PROSPECTIVE_FACESET_COMMON",
                    "native_history_claimed": False,
                },
            }
        selected = candidates[0]
        gap = selected["record"]["gap_mm"]
        if selected["record"]["gap_spread_mm"] > rules["linear_epsilon_mm"]:
            return {
                "schema_version": 1,
                "scenario_id": request["scenario_id"],
                "status": "UNSUPPORTED_NONCOPLANAR_INTERFACE_FACESET",
                "face_sets": face_set_evidence,
                "motion": base_motion,
                "partition": {},
                "topology": {},
                "fuse": {"executed": False},
                "provenance": {"native_history_claimed": False},
            }
        corrected = second.copy()
        corrected.translate(FreeCAD.Vector(0.0, 0.0, -gap))
        corrected_second = _translated_group(
            corrected,
            -1.0,
            selected["first"]["support_coordinate_mm"],
            rules,
            reverse,
        )
        raw, patches = _common_patches(
            selected["first"], corrected_second, rules["area_epsilon_mm2"], reverse
        )
        topology, component_shapes = _topology(patches, rules["linear_epsilon_mm"])
        remaining, remaining_provenance, common_shape = _remaining(
            selected["first"], corrected_second, patches, rules["area_epsilon_mm2"]
        )
        common_area = float(sum(patch["area_mm2"] for patch in patches))
        carrier_areas = {
            "Side_1": float(selected["first"]["total_area_mm2"]),
            "Side_2": float(corrected_second["total_area_mm2"]),
        }
        remaining_areas = {
            role: float(sum(face.Area for face in remaining[role]))
            for role in ("Side_1", "Side_2")
        }
        spatial = {
            "Side_1": _spatial_partition(
                selected["first"], common_shape, remaining["Side_1"], rules["area_epsilon_mm2"]
            ),
            "Side_2": _spatial_partition(
                corrected_second, common_shape, remaining["Side_2"], rules["area_epsilon_mm2"]
            ),
        }
        fused = first.copy().fuse(corrected.copy()).removeSplitter()
        material_common = first.common(corrected)
        boundary_overlap = float(
            sum(
                patch["shape"].common(face).Area
                for patch in patches
                for face in fused.Faces
            )
        )
        corrected_step = _export_step(
            output,
            "corrected_assembly",
            (("Side_1", "Side_1", first), ("Side_2", "Side_2", corrected)),
        )
        fused_step = _export_step(
            output, "fused", (("Fused_Result", "Fused_Result", fused),)
        )
        artifacts = {
            "corrected_assembly_step": corrected_step,
            "fused_step": fused_step,
            "common_brep": _export_brep(output, "common", common_shape),
        }
        for role in ("Side_1", "Side_2"):
            if remaining[role]:
                artifacts[role.lower() + "_remaining_brep"] = _export_brep(
                    output,
                    role.lower() + "_remaining",
                    Part.makeCompound(remaining[role]),
                )
            else:
                artifacts[role.lower() + "_remaining_brep"] = "EMPTY"
        patch_provenance = []
        for patch in patches:
            patch_provenance.append(
                {
                    "Side_1_occurrence": "Side_1",
                    "Side_2_occurrence": "Side_2",
                    "Side_1_FaceSet": selected["first"]["face_set_id"],
                    "Side_2_FaceSet": selected["second"]["face_set_id"],
                    "source_face_member_pair": patch["source_face_linkage"],
                    "actual_common_digest": patch["geometry_digest"],
                    "component_id": patch["component_id"],
                    "operation_kind": "DIRECT_BREP_FACE_COMMON",
                }
            )
        selected_public = dict(selected["record"])
        selected_public["selection_reason"] = "SUPPORTED_UNIQUE_INTERFACE_FACESET"
        face_set_evidence["selected_pair"] = selected_public
        motion = dict(base_motion)
        motion.update(
            {
                "motion_authorized": True,
                "executed_translation_mm": [0.0, 0.0, float(-gap)],
                "executed_translation_norm_mm": float(abs(gap)),
                "normal_component_mm": float(-gap),
            }
        )
        operation = {
            "schema_version": 1,
            "scenario_id": request["scenario_id"],
            "status": "SUPPORTED_UNIQUE_INTERFACE_FACESET",
            "face_sets": face_set_evidence,
            "motion": motion,
            "partition": {
                "raw_common_face_count": len(raw),
                "common_area_mm2": common_area,
                "common_patches": _public_patches(patches),
                "carrier_area_mm2": carrier_areas,
                "coverage": {
                    role: common_area / carrier_areas[role]
                    for role in ("Side_1", "Side_2")
                },
                "remaining_area_mm2": remaining_areas,
                "remaining_empty": {
                    role: not bool(remaining[role]) for role in ("Side_1", "Side_2")
                },
                "spatial_validation": spatial,
                "member_level_partition": remaining_provenance,
            },
            "topology": topology,
            "fuse": {
                "executed": True,
                "solid_count": len(fused.Solids),
                "valid": bool(fused.isValid()),
                "closed": bool(_closed(fused)),
                "volume_conservation_error_mm3": float(
                    abs(fused.Volume - (first.Volume + corrected.Volume - material_common.Volume))
                ),
                "boundary_overlap_area_mm2": boundary_overlap,
            },
            "provenance": {
                "roles": {"Side_1": "Side_1", "Side_2": "Side_2"},
                "face_sets": selected_public,
                "common_patches": patch_provenance,
                "remaining_patches": remaining_provenance,
                "operation_kind": "DIRECT_BREP_FACESET_COMMON_AND_MEMBER_FACE_CUT_REMAINDER",
                "native_history_claimed": False,
            },
            "artifacts": artifacts,
            "step_reimport": {
                "corrected_assembly": _reimport_corrected(
                    output / corrected_step, rules, reverse
                ),
                "fused": _reimport_fused(output / fused_step),
            },
        }
        if request.get("create_view"):
            operation["view_reopen"] = _debug_document(
                output / "operation_debug.FCStd",
                request["scenario_id"],
                first,
                second,
                operation["status"],
                candidates,
                selected,
                corrected,
                patches,
                component_shapes,
                remaining,
                fused,
            )
        return operation
    finally:
        FreeCAD.closeDocument(document.Name)


def _main():
    response_path = Path(os.environ["DMSLICER_FREECAD_RESPONSE"])
    try:
        request = json.loads(
            Path(os.environ["DMSLICER_FREECAD_REQUEST"]).read_text(encoding="utf-8")
        )
        response = _generate(request) if request["action"] == "generate" else {
            "status": "SUCCEEDED",
            "operation": _analyze(request),
        }
    except Exception:
        response = {"status": "FAILED", "traceback": traceback.format_exc()}
    response_path.write_text(json.dumps(response, sort_keys=True), encoding="utf-8")


_main()
