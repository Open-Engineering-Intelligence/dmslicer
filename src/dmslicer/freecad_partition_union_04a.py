"""FreeCADCmd adapter for actual contact-face partition and solid union."""

import hashlib
import json
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


def _face_common(shape_a, shape_b, area_epsilon):
    records = []
    seen = set()
    for ia, face_a in enumerate(shape_a.Faces, 1):
        for ib, face_b in enumerate(shape_b.Faces, 1):
            for common in face_a.common(face_b).Faces:
                if common.Area <= area_epsilon:
                    continue
                digest = _digest(common)
                if digest in seen:
                    continue
                seen.add(digest)
                records.append({"id": f"C_{len(records) + 1}", "source_face_a": f"Face{ia}", "source_face_b": f"Face{ib}", "area_mm2": float(common.Area), "digest": digest, "shape": common})
    return records


def _patches_for_face(face, commons, area_epsilon):
    common_shape = Part.makeCompound(commons) if commons else Part.Shape()
    remainder = face.cut(common_shape) if commons else face
    return [candidate for candidate in remainder.Faces if candidate.Area > area_epsilon]


def _write_patch_exports(document, output, prefix, shapes):
    results = []
    for index, shape in enumerate(shapes, 1):
        name = f"{prefix}_{index}"
        brep_path = output / "patches" / f"{name}.brep"
        step_path = output / "patches" / f"{name}.step"
        brep_path.parent.mkdir(parents=True, exist_ok=True)
        shape.exportBrep(str(brep_path))
        obj = document.addObject("Part::Feature", f"Export_{name}")
        obj.Shape = shape
        Import.export([obj], str(step_path))
        document.removeObject(obj.Name)
        results.append({"id": name, "area_mm2": float(shape.Area), "brep_file": str(brep_path.relative_to(output)).replace("\\", "/"), "step_file": str(step_path.relative_to(output)).replace("\\", "/"), "digest": _digest(shape)})
    return results


def _add_string_properties(obj, values):
    for name, value in values.items():
        obj.addProperty("App::PropertyString", name, "04A operation")
        setattr(obj, name, str(value))


def _finalize_validation(facts, volume_epsilon):
    checks = (
        ("common_not_on_union_boundary", facts.get("common_not_on_union_boundary") is True),
        ("common_not_on_reimported_boundary", facts.get("common_not_on_reimported_boundary") is True),
        ("input_material_retained", facts.get("input_material_retained") is True),
        ("no_added_material", facts.get("no_added_material") is True),
        ("volume_error_mm3", facts.get("volume_error_mm3", float("inf")) <= volume_epsilon),
        ("solid_count", facts.get("solid_count") == 1),
        ("valid", facts.get("valid") is True),
        ("closed", facts.get("closed") is True),
        ("roundtrip_solid_count", facts.get("roundtrip_solid_count") == 1),
        ("roundtrip_valid", facts.get("roundtrip_valid") is True),
        ("roundtrip_volume_error_mm3", facts.get("roundtrip_volume_error_mm3", float("inf")) <= volume_epsilon),
    )
    failures = []
    for kind, passed in checks:
        if not passed:
            failure = {"kind": kind, "actual": facts.get(kind)}
            if kind in {"volume_error_mm3", "roundtrip_volume_error_mm3"}:
                failure["tolerance_mm3"] = volume_epsilon
            failures.append(failure)
    return {**facts, "status": "PASS" if not failures else "FAIL", "failures": failures}


def _debug(output, case_id, shape_a, shape_b, commons, remaining_a, remaining_b, union, metadata):
    doc = FreeCAD.newDocument("ContactPartitionUnion04A")
    try:
        originals = doc.addObject("App::DocumentObjectGroup", "Originals")
        partitions = doc.addObject("App::DocumentObjectGroup", "Partitions")
        union_group = doc.addObject("App::DocumentObjectGroup", "Union_Result")
        for name, shape in (("Original_Side_1", shape_a), ("Original_Side_2", shape_b)):
            obj = doc.addObject("Part::Feature", name); obj.Shape = shape
            if obj.ViewObject is not None:
                obj.ViewObject.Transparency = 82
            _add_string_properties(obj, {"SourceIDs": metadata["source_ids"], "OperationType": "original", "InputStepHash": metadata["step_hash"]})
            originals.addObject(obj)
        for name, shape, operation in [("Common_Interface", Part.makeCompound(commons), "actual_face_common"), ("Side_1_Remaining", Part.makeCompound(remaining_a), "face_cut_common"), ("Side_2_Remaining", Part.makeCompound(remaining_b), "face_cut_common")]:
            obj = doc.addObject("Part::Feature", name); obj.Shape = shape
            _add_string_properties(obj, {"SourceIDs": metadata["source_ids"], "OperationType": operation, "Area": shape.Area, "Empty": len(shape.Faces) == 0, "InputStepHash": metadata["step_hash"]})
            partitions.addObject(obj)
        fused = doc.addObject("Part::Feature", "Fused_Union"); fused.Shape = union
        _add_string_properties(fused, {"SourceIDs": metadata["source_ids"], "OperationType": "solid_fuse", "Volume": union.Volume, "SolidCount": len(union.Solids), "ShellCount": len(union.Shells), "Valid": union.isValid(), "Closed": all(shell.isClosed() for shell in union.Shells), "Validation": metadata["validation"], "InputStepHash": metadata["step_hash"]})
        union_group.addObject(fused)
        for obj in originals.Group + partitions.Group:
            obj.Visibility = False
        fused.Visibility = True
        originals.Visibility = False; partitions.Visibility = False; union_group.Visibility = True
        doc.recompute(); doc.saveAs(str(output / "operation_debug.FCStd"))
    finally:
        FreeCAD.closeDocument(doc.Name)
    reopened = FreeCAD.openDocument(str(output / "operation_debug.FCStd"))
    try:
        if not all(reopened.getObject(name) for name in ("Originals", "Partitions", "Union_Result", "Fused_Union")):
            raise RuntimeError("reopened debug model lacks required view groups")
    finally:
        FreeCAD.closeDocument(reopened.Name)


def _run(request):
    output = Path(request["output_dir"]); output.mkdir(parents=True, exist_ok=True)
    doc = FreeCAD.newDocument("ContactPartitionUnion04AAnalysis")
    try:
        Import.insert(request["step_path"], doc.Name)
        sources = _objects(doc)
        if len(sources) != 2:
            raise RuntimeError(f"expected two imported single-solid bodies, found {len(sources)}")
        (label_a, shape_a), (label_b, shape_b) = sources
        epsilon = float(request["tolerances"]["area_epsilon_mm2"])
        volume_epsilon = float(request["tolerances"]["volume_epsilon_mm3"])
        commons = _face_common(shape_a, shape_b, epsilon)
        if not commons:
            raise RuntimeError("no actual positive-area common face was found")
        material_common = shape_a.common(shape_b)
        if material_common.Volume > volume_epsilon:
            raise RuntimeError("fixture has material interference; 04A only accepts nominal surface contact")
        remaining_a, remaining_b = [], []
        partition_data = {}
        for side, shape, face_key in (("side_1", shape_a, "source_face_a"), ("side_2", shape_b, "source_face_b")):
            face_ids = sorted({record[face_key] for record in commons}, key=lambda value: int(value[4:]))
            entries = []
            all_remaining = []
            for face_id in face_ids:
                face = shape.Faces[int(face_id[4:]) - 1]
                matched = [record["shape"] for record in commons if record[face_key] == face_id]
                remaining = _patches_for_face(face, matched, epsilon)
                all_remaining.extend(remaining)
                contact_area, remaining_area = sum(piece.Area for piece in matched), sum(piece.Area for piece in remaining)
                coverage_gap = face.cut(Part.makeCompound(matched + remaining)).Area
                overlap = Part.makeCompound(matched).common(Part.makeCompound(remaining)).Area if remaining else 0.0
                entries.append({"source_face_id": face_id, "source_area_mm2": float(face.Area), "common_patch_ids": [record["id"] for record in commons if record[face_key] == face_id], "common_area_mm2": float(contact_area), "remaining_area_mm2": float(remaining_area), "remaining_empty": not remaining, "area_conserved": abs(face.Area - contact_area - remaining_area) <= epsilon and coverage_gap <= epsilon and overlap <= epsilon, "coverage_gap_mm2": float(coverage_gap), "positive_overlap_mm2": float(overlap), "remaining_shapes": remaining})
            if side == "side_1": remaining_a = all_remaining
            else: remaining_b = all_remaining
            partition_data[side] = {"faces": entries, "area_conserved": all(entry["area_conserved"] for entry in entries), "remaining_shapes": all_remaining}
        common_shapes = [record["shape"] for record in commons]
        common_exports = _write_patch_exports(doc, output, "common", common_shapes)
        for record, exported in zip(commons, common_exports): record.update(exported)
        for side, prefix in (("side_1", "side_1_remaining"), ("side_2", "side_2_remaining")):
            exported = _write_patch_exports(doc, output, prefix, partition_data[side]["remaining_shapes"])
            partition_data[side]["remaining_patches"] = exported
            for entry in partition_data[side]["faces"]: del entry["remaining_shapes"]
            del partition_data[side]["remaining_shapes"]
        union = shape_a.fuse(shape_b).removeSplitter()
        fused_path = output / "fused.step"
        fused_obj = doc.addObject("Part::Feature", "FusedExport"); fused_obj.Shape = union; Import.export([fused_obj], str(fused_path)); doc.removeObject(fused_obj.Name)
        roundtrip = FreeCAD.newDocument("ContactPartitionUnion04ARoundtrip")
        try:
            Import.insert(str(fused_path), roundtrip.Name)
            imported = _objects(roundtrip)
            if len(imported) != 1: raise RuntimeError(f"fused STEP reimport has {len(imported)} solids")
            reimported = imported[0][1]
            common_on_boundary = any(patch["shape"].common(face).Area > epsilon for patch in commons for face in union.Faces)
            reimported_common = any(patch["shape"].common(face).Area > epsilon for patch in commons for face in reimported.Faces)
            facts = {"common_not_on_union_boundary": not common_on_boundary, "common_not_on_reimported_boundary": not reimported_common, "input_material_retained": shape_a.cut(union).Volume <= volume_epsilon and shape_b.cut(union).Volume <= volume_epsilon, "no_added_material": union.cut(shape_a.fuse(shape_b)).Volume <= volume_epsilon, "volume_error_mm3": float(abs(union.Volume - (shape_a.Volume + shape_b.Volume - material_common.Volume))), "solid_count": len(union.Solids), "valid": union.isValid(), "closed": all(shell.isClosed() for shell in union.Shells), "roundtrip_solid_count": len(reimported.Solids), "roundtrip_valid": reimported.isValid(), "roundtrip_volume_error_mm3": float(abs(reimported.Volume - union.Volume))}
            validation = _finalize_validation(facts, volume_epsilon)
        finally:
            FreeCAD.closeDocument(roundtrip.Name)
        metadata = {"source_ids": json.dumps({"side_1": label_a, "side_2": label_b}), "step_hash": request["step_hash"], "validation": validation["status"]}
        _debug(output, request["case_id"], shape_a, shape_b, common_shapes, remaining_a, remaining_b, union, metadata)
        for record in commons: del record["shape"]
        operation = {"case_id": request["case_id"], "analysis_input": "reimported_step", "source_ids": {"side_1": label_a, "side_2": label_b}, "input_unchanged": True, "input_step_sha256": request["step_hash"], "common_patches": commons, "partitions": partition_data, "union": {"volume_mm3": float(union.Volume), "solid_count": len(union.Solids), "shell_count": len(union.Shells), "valid": union.isValid(), "closed": all(shell.isClosed() for shell in union.Shells), "digest": _digest(union)}, "a08_prerequisites": {"checked_from_brep": request["case_id"] == "A08", "two_valid_closed_solids": shape_a.isValid() and shape_b.isValid() and all(shell.isClosed() for shell in shape_a.Shells + shape_b.Shells), "material_interference_volume_mm3": float(material_common.Volume)}}
        return {"operation": operation, "validation": validation}
    finally:
        FreeCAD.closeDocument(doc.Name)


def _main():
    response_path = Path(os.environ["DMSLICER_FREECAD_RESPONSE"])
    try:
        request = json.loads(Path(os.environ["DMSLICER_FREECAD_REQUEST"]).read_text(encoding="utf-8"))
        response = ({"validation": _finalize_validation(request["facts"], float(request["volume_epsilon_mm3"]))}
                    if request.get("action") == "validate" else _run(request))
        response["status"] = "SUCCEEDED"
    except Exception:
        response = {"status": "FAILED", "traceback": traceback.format_exc()}
    response_path.write_text(json.dumps(response, sort_keys=True), encoding="utf-8")


_main()
