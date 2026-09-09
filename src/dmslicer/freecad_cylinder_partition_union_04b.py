"""FreeCAD/OCC adapter for the bounded 04B cylindrical operations."""

import hashlib, json, math, os, sys, traceback
from pathlib import Path
import FreeCAD, Import, Part
sys.path.insert(0, str(Path(os.environ["DMSLICER_FREECAD_SCRIPT"]).parent))
from freecad_contact_03a import _objects


def _digest(shape): return "sha256:" + hashlib.sha256(shape.exportBrepToString().encode("utf-8")).hexdigest()
def _cylinder(radius, lower, upper): return Part.makeCylinder(radius, upper - lower, FreeCAD.Vector(0, 0, lower), FreeCAD.Vector(0, 0, 1), 360.0)
def _sleeve(outer, inner): return _cylinder(outer, 0, 40).cut(_cylinder(inner, 0, 40))
def _inputs(params): return _sleeve(float(params["outer_radius_mm"]), float(params["inner_radius_mm"])), _cylinder(float(params["inner_radius_mm"]), *params["core_z_mm"])
def _reference(case_id, outer, inner):
    annulus = _cylinder(outer, 20, 40).cut(_cylinder(inner, 20, 40))
    if case_id == "U04_cylinder_full_fill": return _cylinder(outer, 0, 40)
    if case_id == "U05_cylinder_short_core": return _cylinder(outer, 0, 20).fuse(annulus).removeSplitter()
    return _cylinder(inner, -80, 0).fuse(_cylinder(outer, 0, 20)).fuse(annulus).removeSplitter()
def _is_cylinder(face, radius, epsilon):
    surface = face.Surface
    return "cylinder" in type(surface).__name__.lower() and abs(float(surface.Radius) - radius) <= epsilon and getattr(surface, "Axis", FreeCAD.Vector()).z >= 1 - epsilon
def _common(first, second, epsilon):
    records, seen = [], set()
    for ia, face_a in first:
        for ib, face_b in second:
            for patch in face_a.common(face_b).Faces:
                if patch.Area <= epsilon or _digest(patch) in seen: continue
                seen.add(_digest(patch)); records.append({"id": f"C_{len(records)+1}", "source_face_side_1": f"Face{ia}", "source_face_side_2": f"Face{ib}", "area_mm2": float(patch.Area), "digest": _digest(patch), "shape": patch})
    return records
def _remaining(carriers, commons, epsilon):
    pieces, seen = [], set(); common = Part.makeCompound(commons)
    for _, face in carriers:
        for patch in face.cut(common).Faces:
            if patch.Area > epsilon and _digest(patch) not in seen: seen.add(_digest(patch)); pieces.append(patch)
    return pieces
def _exports(doc, output, prefix, shapes):
    rows = []
    for index, shape in enumerate(shapes, 1):
        name = f"{prefix}_{index}"; brep = output / "patches" / f"{name}.brep"; step = output / "patches" / f"{name}.step"; brep.parent.mkdir(parents=True, exist_ok=True); shape.exportBrep(str(brep)); obj = doc.addObject("Part::Feature", name); obj.Shape = shape; Import.export([obj], str(step)); doc.removeObject(obj.Name); rows.append({"id": name, "area_mm2": float(shape.Area), "digest": _digest(shape), "brep_file": str(brep.relative_to(output)).replace("\\", "/"), "step_file": str(step.relative_to(output)).replace("\\", "/")})
    return rows
def _props(obj, values):
    for name, value in values.items(): obj.addProperty("App::PropertyString", name, "04B cylinder fit"); setattr(obj, name, str(value))
def _debug(output, operation, sleeve, core, commons, remainder_1, remainder_2, union):
    doc = FreeCAD.newDocument("CylinderFit04BDebug")
    try:
        originals = doc.addObject("App::DocumentObjectGroup", "Originals"); partitions = doc.addObject("App::DocumentObjectGroup", "Partitions"); result = doc.addObject("App::DocumentObjectGroup", "Union_Result")
        for name, shape in (("Side_1_Sleeve", sleeve), ("Side_2_Core", core)):
            obj=doc.addObject("Part::Feature", name); obj.Shape=shape; originals.addObject(obj); obj.Visibility=False
        for name, shape, state in (("Common_Interface", Part.makeCompound(commons), "NON_EMPTY"), ("Side_1_Remaining", Part.makeCompound(remainder_1), "EMPTY" if not remainder_1 else "NON_EMPTY"), ("Side_2_Remaining", Part.makeCompound(remainder_2), "EMPTY" if not remainder_2 else "NON_EMPTY")):
            obj=doc.addObject("Part::Feature", name); obj.Shape=shape; _props(obj, {"ResultState": state, "AreaMm2": shape.Area}); partitions.addObject(obj); obj.Visibility=False
        fused=doc.addObject("Part::Feature", "Fused_Union"); fused.Shape=union; _props(fused, {"VolumeMm3": union.Volume, "Validation": "pending"}); result.addObject(fused); fused.Visibility=True
        originals.Visibility=False; partitions.Visibility=False; result.Visibility=True; doc.recompute(); doc.saveAs(str(output / "operation_debug.FCStd"))
    finally: FreeCAD.closeDocument(doc.Name)
    reopened=FreeCAD.openDocument(str(output / "operation_debug.FCStd"))
    try: return {"reopened": all(reopened.getObject(name) for name in ("Originals", "Partitions", "Union_Result", "Fused_Union")), "visibility_state_saved": bool(reopened.getObject("Union_Result").Visibility and not reopened.getObject("Originals").Visibility)}
    finally: FreeCAD.closeDocument(reopened.Name)
def _generate(request):
    sleeve, core = _inputs(request["parameters"]); doc=FreeCAD.newDocument("CylinderFit04BGenerator")
    try:
        one=doc.addObject("Part::Feature", "Side_1_Sleeve"); one.Label="Side_1_Sleeve"; one.Shape=sleeve; two=doc.addObject("Part::Feature", "Side_2_Core"); two.Label="Side_2_Core"; two.Shape=core; doc.recompute(); Import.export([one, two], request["step_path"]); return {"valid_closed": [sleeve.isValid() and all(x.isClosed() for x in sleeve.Shells), core.isValid() and all(x.isClosed() for x in core.Shells)]}
    finally: FreeCAD.closeDocument(doc.Name)
def _analyze(request):
    output=Path(request["output_dir"]); output.mkdir(parents=True, exist_ok=True); params=request["parameters"]; eps=float(request["tolerances"]["area_epsilon_mm2"]); linear=float(request["tolerances"]["linear_epsilon_mm"]); volume_eps=float(request["tolerances"]["volume_epsilon_mm3"]); outer=float(params["outer_radius_mm"]); inner=float(params["inner_radius_mm"]); doc=FreeCAD.newDocument("CylinderFit04BAnalysis")
    try:
        Import.insert(request["step_path"], doc.Name); sources=_objects(doc)
        if len(sources)!=2: raise RuntimeError("expected exactly two imported solids")
        (sleeve_label,sleeve),(core_label,core)=sources; carrier_1=[(i,f) for i,f in enumerate(sleeve.Faces,1) if _is_cylinder(f,inner,linear)]; carrier_2=[(i,f) for i,f in enumerate(core.Faces,1) if _is_cylinder(f,inner,linear)]
        if not carrier_1 or not carrier_2: raise RuntimeError("designated cylindrical carrier region not found")
        common=_common(carrier_1,carrier_2,eps); commons=[x["shape"] for x in common]
        if not commons: raise RuntimeError("no positive-area cylindrical common region")
        rem_1,rem_2=_remaining(carrier_1,commons,eps),_remaining(carrier_2,commons,eps); denominators=[sum(f.Area for _,f in carrier_1),sum(f.Area for _,f in carrier_2)]; common_area=sum(f.Area for f in commons)
        partitions=[]
        for carriers, remainder in ((carrier_1,rem_1),(carrier_2,rem_2)):
            carrier=Part.makeCompound([f for _,f in carriers]); rem=Part.makeCompound(remainder); overlap=Part.makeCompound(commons).common(rem).Area if remainder else 0; gap=carrier.cut(Part.makeCompound(commons+remainder)).Area; partitions.append({"carrier_area_mm2":float(carrier.Area),"common_area_mm2":float(common_area),"remaining_area_mm2":float(rem.Area),"area_error_mm2":float(abs(carrier.Area-common_area-rem.Area)),"coverage_gap_mm2":float(gap),"positive_overlap_mm2":float(overlap),"area_conserved":abs(carrier.Area-common_area-rem.Area)<=eps and gap<=eps and overlap<=eps})
        overlap_volume=sleeve.common(core).Volume
        if overlap_volume>volume_eps: raise RuntimeError("inputs have material interference")
        union=sleeve.fuse(core).removeSplitter(); export=doc.addObject("Part::Feature","FusedExport"); export.Shape=union; Import.export([export],str(output/"fused.step")); doc.removeObject(export.Name)
        rt=FreeCAD.newDocument("CylinderFit04BRoundtrip")
        try:
            Import.insert(str(output/"fused.step"),rt.Name); imported=_objects(rt); roundtrip=imported[0][1] if len(imported)==1 else Part.Shape(); common_boundary=any(p.common(f).Area>eps for p in commons for f in union.Faces); checks={"input_solids_valid_closed":sleeve.isValid() and core.isValid() and all(x.isClosed() for x in sleeve.Shells+core.Shells),"material_intersection_volume_mm3":float(overlap_volume),"partition_area_conserved":all(x["area_conserved"] for x in partitions),"solid_count":len(union.Solids),"valid":union.isValid(),"closed":all(x.isClosed() for x in union.Shells),"common_not_on_boundary":not common_boundary,"volume_error_mm3":float(abs(union.Volume-(sleeve.Volume+core.Volume-overlap_volume))),"roundtrip_solid_count":len(roundtrip.Solids),"roundtrip_valid":roundtrip.isValid(),"roundtrip_volume_error_mm3":float(abs(roundtrip.Volume-union.Volume)),"roundtrip_shape_match":union.cut(roundtrip).Volume<=volume_eps and roundtrip.cut(union).Volume<=volume_eps}
        finally: FreeCAD.closeDocument(rt.Name)
        for record, exported in zip(common,_exports(doc,output,"common",commons)): record.update(exported); del record["shape"]
        operation={"schema_version":1,"case_id":request["case_id"],"analysis_input":"reimported_step","side_order":{"side_1":"sleeve","side_2":"core"},"source_ids":{"side_1":sleeve_label,"side_2":core_label},"input_step_sha256":request["step_hash"],"common_area_mm2":float(common_area),"common_patches":common,"coverage_denominators_mm2":denominators,"coverage":[float(common_area/x) for x in denominators],"partitions":{"side_1":{"status":"EMPTY" if not rem_1 else "NON_EMPTY","remaining_patches":_exports(doc,output,"side_1_remaining",rem_1),**partitions[0]},"side_2":{"status":"EMPTY" if not rem_2 else "NON_EMPTY","remaining_patches":_exports(doc,output,"side_2_remaining",rem_2),**partitions[1]}},"union":{"volume_mm3":float(union.Volume),"solid_count":len(union.Solids),"shell_count":len(union.Shells),"valid":union.isValid(),"closed":all(x.isClosed() for x in union.Shells),"digest":_digest(union)},"checks":checks}
        operation["debug"]=_debug(output,operation,sleeve,core,commons,rem_1,rem_2,union); return {"operation":operation,"checks":checks}
    finally: FreeCAD.closeDocument(doc.Name)
def _candidate(request):
    outer=float(request["parameters"]["outer_radius_mm"]); inner=float(request["parameters"]["inner_radius_mm"]); kind=request["candidate_kind"]
    if kind=="full_outer_cylinder": return _cylinder(outer,0,40)
    if kind=="truncated_to_sleeve": return _cylinder(outer,0,20).fuse(_cylinder(outer,20,40).cut(_cylinder(inner,20,40))).removeSplitter()
    raise ValueError(f"unsupported candidate: {kind}")
def _validate_shape(candidate,request,actual=None):
    expected=request["expected"]; params=request["parameters"]; eps=float(expected["tolerances"]["volume_epsilon_mm3"]); outer=float(params["outer_radius_mm"]); inner=float(params["inner_radius_mm"]); reference=_reference(request["case_id"],outer,inner); minus=float(candidate.cut(reference).Volume); missing=float(reference.cut(candidate).Volume); samples={"z10_axis_material":candidate.isInside(FreeCAD.Vector(0,0,10),1e-7,True),"z30_axis_empty":not candidate.isInside(FreeCAD.Vector(0,0,30),1e-7,True),"z30_radial25_material":candidate.isInside(FreeCAD.Vector(25,0,30),1e-7,True)}
    if request["case_id"]=="U06_cylinder_unequal_overlap": samples.update({"zminus40_axis_material":candidate.isInside(FreeCAD.Vector(0,0,-40),1e-7,True),"zminus40_radial25_empty":not candidate.isInside(FreeCAD.Vector(25,0,-40),1e-7,True)})
    if request["case_id"] == "U04_cylinder_full_fill":
        samples = {"z10_axis_material": samples["z10_axis_material"], "z30_axis_material": candidate.isInside(FreeCAD.Vector(0,0,30),1e-7,True), "z30_radial25_material": samples["z30_radial25_material"]}
    facts={"actual_minus_reference_mm3":minus,"reference_minus_actual_mm3":missing,"analytic_volume_error_mm3":float(abs(candidate.Volume-expected["union_volume_mm3"])),"solid_count":len(candidate.Solids),"valid":candidate.isValid(),"closed":all(x.isClosed() for x in candidate.Shells),**samples}
    if actual: facts.update(actual)
    required={"shape_actual_minus_reference":minus<=eps,"shape_reference_minus_actual":missing<=eps,"analytic_volume":facts["analytic_volume_error_mm3"]<=eps,"solid_count":facts["solid_count"]==1,"valid":facts["valid"] is True,"closed":facts["closed"] is True,**samples}
    if actual: required.update({"input_solids_valid_closed":actual["input_solids_valid_closed"] is True,"material_intersection":actual["material_intersection_volume_mm3"]<=eps,"partition_area_conserved":actual["partition_area_conserved"] is True,"common_not_on_boundary":actual["common_not_on_boundary"] is True,"volume_conservation":actual["volume_error_mm3"]<=eps,"roundtrip_shape":actual["roundtrip_shape_match"] is True})
    failures=[{"kind":key,"actual":facts.get(key)} for key,value in required.items() if value is not True]; return {**facts,"checks":required,"status":"PASS" if not failures else "FAIL","failures":failures}
def _validate(request):
    doc=FreeCAD.newDocument("CylinderFit04BValidate")
    try:
        Import.insert(request["fused_step"],doc.Name); sources=_objects(doc)
        if len(sources)!=1: raise RuntimeError("expected one fused STEP solid")
        validation=_validate_shape(sources[0][1],request,request["actual_checks"]); debug=FreeCAD.openDocument(request["debug_path"])
        try: debug.getObject("Fused_Union").Validation=validation["status"]; debug.recompute(); debug.save()
        finally: FreeCAD.closeDocument(debug.Name)
        return {"validation":validation}
    finally: FreeCAD.closeDocument(doc.Name)
def _main():
    response_path=Path(os.environ["DMSLICER_FREECAD_RESPONSE"])
    try:
        request=json.loads(Path(os.environ["DMSLICER_FREECAD_REQUEST"]).read_text(encoding="utf-8")); action=request["action"]
        if action=="generate": response=_generate(request)
        elif action=="analyze": response=_analyze(request)
        elif action=="validate": response=_validate(request)
        elif action=="validate_candidate": response={"validation":_validate_shape(_candidate(request),request)}
        else: raise ValueError(f"unknown action: {action}")
        response["status"]="SUCCEEDED"
    except Exception: response={"status":"FAILED","traceback":traceback.format_exc()}
    response_path.write_text(json.dumps(response,sort_keys=True),encoding="utf-8")
_main()
