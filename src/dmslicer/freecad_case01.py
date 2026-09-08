"""FreeCADCmd-side adapter for the CASE01 STEP/B-rep workflow.

This module is executed inside FreeCAD's embedded Python interpreter.  It only
exchanges JSON DTOs with the host interpreter; persistent identifiers are built
on the host from the raw B-rep facts emitted here.
"""

import itertools
import json
import os
import sys
import tempfile
import traceback
from pathlib import Path

import FreeCAD
import Import
import Part

AREA_EPSILON_MM2 = 1e-8


def _box(shape):
    bound_box = shape.BoundBox
    return {
        "xmin": float(bound_box.XMin),
        "xmax": float(bound_box.XMax),
        "ymin": float(bound_box.YMin),
        "ymax": float(bound_box.YMax),
        "zmin": float(bound_box.ZMin),
        "zmax": float(bound_box.ZMax),
    }


def _center_of_mass(shape):
    if hasattr(shape, "CenterOfMass"):
        return [float(component) for component in shape.CenterOfMass]
    return None


def _surface_type(face):
    surface = face.Surface
    return getattr(surface, "TypeId", type(surface).__name__)


def _face_record(face, index):
    return {
        "index": index,
        "surface_type": _surface_type(face),
        "area_mm2": float(face.Area),
        "center_of_mass_mm": _center_of_mass(face),
        "bounding_box_mm": _box(face),
        "edge_count": len(face.Edges),
        "wire_count": len(face.Wires),
    }


def _solid_record(shape, semantic, source_ordinal, source_occurrence_locator):
    faces = [_face_record(face, index) for index, face in enumerate(shape.Faces)]
    return {
        "semantic_id": semantic["semantic_id"],
        "source_label": semantic["source_label"],
        "semantic_role": semantic["semantic_role"],
        "material_key": semantic["material_key"],
        "participation_policy": semantic["participation_policy"],
        "source_boundary": semantic.get("source_boundary"),
        "source_occurrence_locator": source_occurrence_locator,
        "source_ordinal": source_ordinal,
        "shape_type": shape.ShapeType,
        "volume_mm3": float(shape.Volume),
        "area_mm2": float(shape.Area),
        "center_of_mass_mm": _center_of_mass(shape),
        "bounding_box_mm": _box(shape),
        "face_count": len(shape.Faces),
        "edge_count": len(shape.Edges),
        "validation": {
            "is_valid": bool(shape.isValid()),
            "shell_closed": bool(shape.Shells) and all(shell.isClosed() for shell in shape.Shells),
            "solid_count": len(shape.Solids),
            "positive_volume": bool(shape.Volume > 0.0),
        },
        "faces": faces,
    }


def _aabb_gap(box_a, box_b):
    axis_gaps = []
    for lower, upper in (("x", "x"), ("y", "y"), ("z", "z")):
        axis_gaps.append(
            max(
                0.0,
                box_a[f"{lower}min"] - box_b[f"{upper}max"],
                box_b[f"{lower}min"] - box_a[f"{upper}max"],
            )
        )
    return sum(value * value for value in axis_gaps) ** 0.5


def _shape_summary(shape):
    summary = {
        "shape_type": shape.ShapeType,
        "solid_count": len(shape.Solids),
        "face_count": len(shape.Faces),
        "edge_count": len(shape.Edges),
        "area_mm2": float(shape.Area),
        "volume_mm3": float(shape.Volume),
        "is_valid": bool(shape.isValid()),
        "shell_closed": all(shell.isClosed() for shell in shape.Shells),
        "center_of_mass_mm": _center_of_mass(shape),
    }
    if shape.isNull():
        summary["bounding_box_mm"] = None
    else:
        summary["bounding_box_mm"] = _box(shape)
    return summary


def _source_objects(document, semantics):
    semantic_by_label = {item["source_label"]: item for item in semantics}
    objects = []
    for obj in document.Objects:
        if obj.TypeId != "Part::Feature" or obj.Label not in semantic_by_label:
            continue
        if not hasattr(obj, "Shape") or len(obj.Shape.Solids) != 1:
            continue
        objects.append(
            (
                semantic_by_label[obj.Label],
                obj.Shape.Solids[0],
                len(objects),
                {"product_path": [obj.Name], "persistent_label": obj.Name, "display_label": obj.Label},
            )
        )
    labels = [semantic["source_label"] for semantic, _, _, _ in objects]
    expected_labels = sorted(semantic_by_label)
    if sorted(labels) != expected_labels or len(labels) != len(set(labels)):
        raise RuntimeError(
            "STEP import did not expose exactly one Part::Feature solid for every semantic source label: "
            + repr({"expected": expected_labels, "actual": labels})
        )
    return sorted(objects, key=lambda item: item[0]["semantic_id"])


def _face_contacts(shape_a, shape_b):
    contacts = []
    for index_a, face_a in enumerate(shape_a.Faces):
        for index_b, face_b in enumerate(shape_b.Faces):
            common = face_a.common(face_b)
            for common_face in common.Faces:
                if common_face.Area <= AREA_EPSILON_MM2:
                    continue
                contacts.append(
                    {
                        "source_face_index_a": index_a,
                        "source_face_index_b": index_b,
                        "area_mm2": float(common_face.Area),
                        "source_face_a_area_mm2": float(face_a.Area),
                        "source_face_b_area_mm2": float(face_b.Area),
                        "geometry": {
                            "surface_type": _surface_type(common_face),
                            "area_mm2": float(common_face.Area),
                            "center_of_mass_mm": _center_of_mass(common_face),
                            "bounding_box_mm": _box(common_face),
                            "edge_count": len(common_face.Edges),
                            "wire_count": len(common_face.Wires),
                        },
                    }
                )
    return contacts


def _generate(request):
    step_path = Path(request["step_path"])
    step_path.parent.mkdir(parents=True, exist_ok=True)
    document = FreeCAD.newDocument("CASE01Generator")
    try:
        shapes = {
            "A": Part.makeBox(10, 20, 20, FreeCAD.Vector(0, 0, 0)),
            "G": Part.makeBox(10, 20, 20, FreeCAD.Vector(10, 0, 0)),
            "B": Part.makeBox(10, 20, 20, FreeCAD.Vector(20, 0, 0)),
        }
        objects = []
        for label in ("A", "G", "B"):
            obj = document.addObject("Part::Feature", label)
            obj.Label = label
            obj.Shape = shapes[label]
            objects.append(obj)
        document.recompute()
        Import.export(objects, str(step_path))
        return {
            "status": "SUCCEEDED",
            "step_path": str(step_path),
            "generated_object_labels": [obj.Label for obj in objects],
            "generation_geometry": {
                "A": [0, 10, 0, 20, 0, 20],
                "G": [10, 20, 0, 20, 0, 20],
                "B": [20, 30, 0, 20, 0, 20],
            },
        }
    finally:
        FreeCAD.closeDocument(document.Name)


def _analyze(request):
    step_path = request["step_path"]
    semantics = request["semantics"]
    candidate_tolerance = float(request["tolerances"]["candidate_tolerance_mm"])
    near_miss_band = float(request["tolerances"]["near_miss_max_gap_mm"])
    document = Import.open(step_path) or FreeCAD.ActiveDocument
    if document is None:
        raise RuntimeError("Import.open did not create an active FreeCAD document")
    try:
        source_objects = _source_objects(document, semantics)
        regions = [_solid_record(shape, semantic, source_ordinal, locator) for semantic, shape, source_ordinal, locator in source_objects]
        region_by_semantic = {record["semantic_id"]: record for record in regions}
        shape_by_semantic = {semantic["semantic_id"]: shape for semantic, shape, _, _ in source_objects}

        candidates = []
        relations = []
        patches = []
        for semantic_a, semantic_b in itertools.combinations(sorted(region_by_semantic), 2):
            record_a = region_by_semantic[semantic_a]
            record_b = region_by_semantic[semantic_b]
            shape_a = shape_by_semantic[semantic_a]
            shape_b = shape_by_semantic[semantic_b]
            bounds_gap = _aabb_gap(record_a["bounding_box_mm"], record_b["bounding_box_mm"])
            candidates.append(
                {
                    "semantic_pair": [semantic_a, semantic_b],
                    "broad_phase_method": "AABB",
                    "bounds_gap_mm": bounds_gap,
                    "candidate_tolerance_mm": candidate_tolerance,
                    "status": "EVALUATED" if bounds_gap <= candidate_tolerance else "FILTERED_OUT",
                }
            )

            solid_common = shape_a.common(shape_b)
            contacts = _face_contacts(shape_a, shape_b)
            section = shape_a.section(shape_b)
            distance_mm = float(shape_a.distToShape(shape_b)[0])
            evidence = {
                "method": "face_common_brep" if contacts else "solid_common_section_distance_brep",
                "solid_common": _shape_summary(solid_common),
                "section": _shape_summary(section),
                "minimum_distance_mm": distance_mm,
                "face_common_count": len(contacts),
            }
            if solid_common.Volume > AREA_EPSILON_MM2:
                relation_type = "VOLUME_OVERLAP"
                dimension = 3
            elif contacts:
                coverage_a = max(contact["area_mm2"] / contact["source_face_a_area_mm2"] for contact in contacts)
                coverage_b = max(contact["area_mm2"] / contact["source_face_b_area_mm2"] for contact in contacts)
                relation_type = (
                    "FULL_FACE_OVERLAP"
                    if abs(1.0 - coverage_a) <= 1e-9 and abs(1.0 - coverage_b) <= 1e-9
                    else "PARTIAL_FACE_OVERLAP"
                )
                dimension = 2
            elif distance_mm > near_miss_band:
                relation_type = "DISJOINT"
                dimension = None
            elif section.Edges:
                relation_type = "TOUCH_EDGE"
                dimension = 1
            else:
                relation_type = "NEAR_MISS"
                dimension = None

            if candidates[-1]["status"] == "EVALUATED" and contacts:
                candidates[-1]["status"] = "CONFIRMED"

            relations.append(
                {
                    "semantic_pair": [semantic_a, semantic_b],
                    "relation_type": relation_type,
                    "intersection_dimension": dimension,
                    "confirmed": True,
                    "coverage_a": coverage_a if contacts else None,
                    "coverage_b": coverage_b if contacts else None,
                    "evidence": evidence,
                }
            )
            for contact in contacts:
                patches.append(
                    {
                        "semantic_pair": [semantic_a, semantic_b],
                        "source_face_index_a": contact["source_face_index_a"],
                        "source_face_index_b": contact["source_face_index_b"],
                        "relation_type": relation_type,
                        "intersection_dimension": 2,
                        "area_mm2": contact["area_mm2"],
                        "coverage_a": contact["area_mm2"] / contact["source_face_a_area_mm2"],
                        "coverage_b": contact["area_mm2"] / contact["source_face_b_area_mm2"],
                        "geometry": contact["geometry"],
                        "extraction_method": "face_common_brep",
                    }
                )

        return {
            "status": "SUCCEEDED",
            "analysis_input": "reimported_step",
            "imported_solid_count": len(regions),
            "freecad_version": list(FreeCAD.Version()),
            "opencascade_version": getattr(Part, "OCC_VERSION", None),
            "regions": regions,
            "candidates": candidates,
            "relations": relations,
            "patches": patches,
        }
    finally:
        FreeCAD.closeDocument(document.Name)


def _capability_probe(_request):
    document = FreeCAD.newDocument("CASE01CapabilityProbe")
    temporary_directory = tempfile.TemporaryDirectory()
    try:
        a = document.addObject("Part::Feature", "A")
        g = document.addObject("Part::Feature", "G")
        a.Label = "A"
        g.Label = "G"
        a.Shape = Part.makeBox(10, 20, 20, FreeCAD.Vector(0, 0, 0))
        g.Shape = Part.makeBox(10, 20, 20, FreeCAD.Vector(10, 0, 0))
        document.recompute()
        step_path = Path(temporary_directory.name) / "capability.step"
        Import.export([a, g], str(step_path))
        face_a = [face for face in a.Shape.Faces if abs(face.BoundBox.XMin - 10.0) <= 1e-9 and abs(face.BoundBox.XMax - 10.0) <= 1e-9][0]
        face_g = [face for face in g.Shape.Faces if abs(face.BoundBox.XMin - 10.0) <= 1e-9 and abs(face.BoundBox.XMax - 10.0) <= 1e-9][0]
        common = a.Shape.common(g.Shape)
        section = a.Shape.section(g.Shape)
        general_fuse = a.Shape.generalFuse([g.Shape])
        face_common = face_a.common(face_g)
        probe_facts = {
            "shape_traversal": _shape_summary(a.Shape),
            "face_properties": _face_record(a.Shape.Faces[0], 0),
            "solid_common": _shape_summary(common),
            "section": _shape_summary(section),
            "face_common": _shape_summary(face_common),
            "general_fuse": {
                "result": _shape_summary(general_fuse[0]),
                "map_argument_count": len(general_fuse[1]),
                "map_piece_counts": [len(pieces) for pieces in general_fuse[1]],
            },
        }
        FreeCAD.closeDocument(document.Name)
        document = None
        imported = Import.open(str(step_path)) or FreeCAD.ActiveDocument
        imported_features = [
            obj for obj in imported.Objects
            if obj.TypeId == "Part::Feature" and hasattr(obj, "Shape") and len(obj.Shape.Solids) == 1
        ]
        imported_count = len(imported_features)
        FreeCAD.closeDocument(imported.Name)
        return {
            "schema_version": 1,
            "status_values": ["AVAILABLE", "PARTIAL", "NOT_AVAILABLE", "NOT_VERIFIED"],
            "executable_path": os.path.abspath(sys.executable),
            "freecad_version": list(FreeCAD.Version()),
            "python_version": sys.version,
            "part_module": {"status": "AVAILABLE", "value": {"module": Part.__name__}},
            "opencascade": {"status": "AVAILABLE", "value": {"Part_OCC_VERSION": getattr(Part, "OCC_VERSION", None)}},
            "shape_traversal": {"status": "AVAILABLE", "value": probe_facts["shape_traversal"]},
            "face_properties": {"status": "AVAILABLE", "value": probe_facts["face_properties"]},
            "step_export": {"status": "AVAILABLE", "value": {"bytes": step_path.stat().st_size}},
            "step_import": {"status": "AVAILABLE", "value": {"imported_leaf_solid_count": imported_count}},
            "solid_common": {"status": "AVAILABLE", "value": probe_facts["solid_common"]},
            "section": {"status": "AVAILABLE", "value": probe_facts["section"]},
            "face_common": {"status": "AVAILABLE", "value": probe_facts["face_common"]},
            "general_fuse": {
                "status": "AVAILABLE",
                "value": {
                    **probe_facts["general_fuse"],
                },
            },
            "native_boolean_history": {
                "status": "NOT_AVAILABLE",
                "checked_symbols": {
                    name: hasattr(Part, name)
                    for name in ("BRepAlgoAPI_Common", "BRepAlgoAPI_BuilderAlgo", "BOPAlgo_Splitter")
                },
                "result": "No Python binding for Generated, Modified, or Deleted was exposed by this actual probe.",
            },
        }
    finally:
        if document is not None:
            FreeCAD.closeDocument(document.Name)
        temporary_directory.cleanup()


def _run(request):
    action = request["action"]
    if action == "generate":
        return _generate(request)
    if action == "analyze":
        return _analyze(request)
    if action == "capability_probe":
        return _capability_probe(request)
    raise RuntimeError(f"Unknown CASE01 FreeCAD action: {action}")


def main():
    request_path = Path(os.environ["DMSLICER_FREECAD_REQUEST"])
    response_path = Path(os.environ["DMSLICER_FREECAD_RESPONSE"])
    try:
        response = _run(json.loads(request_path.read_text(encoding="utf-8")))
    except Exception as error:
        response = {
            "status": "FAILED",
            "error_type": type(error).__name__,
            "message": str(error),
            "traceback": traceback.format_exc(),
        }
    response_path.parent.mkdir(parents=True, exist_ok=True)
    response_path.write_text(json.dumps(response, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if response["status"] == "FAILED":
        raise RuntimeError(response["message"])


if __name__ == "__main__":
    main()
