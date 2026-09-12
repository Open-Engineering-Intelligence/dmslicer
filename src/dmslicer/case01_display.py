"""Minimal CASE01 projection and display-only B-rep tessellation bridge."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from .geometry_contract.ids import component_id, interface_id, relation_id, snapshot_id
from .runner import TOLERANCES, _run_freecad, analyze_case01


def _relative_uri(path: Path, root: Path) -> str:
    return path.resolve().relative_to(root.resolve()).as_posix()


def _plane_parameters(box: Mapping[str, float]) -> dict[str, list[float]]:
    """CASE01-only axis-aligned plane projection from measured common-face bounds."""
    spans = {axis: box[f"{axis}max"] - box[f"{axis}min"] for axis in "xyz"}
    normal_axis = min(spans, key=spans.get)
    center = [(box[f"{axis}min"] + box[f"{axis}max"]) / 2.0 for axis in "xyz"]
    normal = {"x": [1.0, 0.0, 0.0], "y": [0.0, 1.0, 0.0], "z": [0.0, 0.0, 1.0]}[normal_axis]
    tangents = {"x": ([0.0, 1.0, 0.0], [0.0, 0.0, 1.0]), "y": ([1.0, 0.0, 0.0], [0.0, 0.0, 1.0]), "z": ([1.0, 0.0, 0.0], [0.0, 1.0, 0.0])}[normal_axis]
    return {"origin": center, "unit_normal": normal, "tangent_u": tangents[0], "tangent_v": tangents[1]}


def _scene_html(scene: Mapping[str, Any]) -> str:
    """Small self-contained 3D canvas inspector; its only identity input is entity_ref."""
    payload = json.dumps(scene, ensure_ascii=True).replace("<", "\\u003c")
    return f'''<!doctype html><meta charset="utf-8"><title>CASE01 B-rep display</title>
<style>body{{font:14px system-ui;display:grid;grid-template-columns:1fr 290px;margin:0}}canvas{{width:100%;height:100vh;background:#111}}aside{{padding:12px;overflow:auto}}button{{display:block;margin:5px 0;width:100%;text-align:left}}label{{display:block;margin:6px 0}}#trace{{white-space:pre-wrap}}</style>
<canvas id="scene" width="900" height="650"></canvas><aside><h1>CASE01 display-only B-rep mesh</h1><p>Selection resolves only through stable entity_refs.</p><div id="controls"></div><h2>Selection traceability</h2><pre id="trace">No entity selected.</pre></aside>
<script>const scene={payload}, canvas=document.querySelector('#scene'), ctx=canvas.getContext('2d'), controls=document.querySelector('#controls'), trace=document.querySelector('#trace');let selected=null,drag=null,azimuth=-.72,elevation=.44,zoom=15;
scene.entities.forEach((e,i)=>{{e.visible=true;e.color=e.entity_kind==='PATCH'?'#ffd166':['#4cc9f0','#80ed99','#f72585'][i%3];let l=document.createElement('label'),c=document.createElement('input');c.type='checkbox';c.checked=true;c.onchange=()=>{{e.visible=c.checked;draw()}};l.append(c,' ',e.display_name);controls.append(l);let b=document.createElement('button');b.textContent='Select '+e.display_name;b.onclick=()=>select(e);controls.append(b)}});
function view(p){{let ca=Math.cos(azimuth),sa=Math.sin(azimuth),ce=Math.cos(elevation),se=Math.sin(elevation),x=p[0]-15,y=p[1]-10,z=p[2]-10,rx=ca*x-sa*y,ry=sa*x+ca*y,sy=ce*z-se*ry,depth=se*z+ce*ry;return [450+rx*zoom,330-sy*zoom,depth]}}function project(p){{return view(p).slice(0,2)}}function select(e){{selected=e;trace.textContent=JSON.stringify({{display_name:e.display_name,entity_ref:e.entity_ref,entity_kind:e.entity_kind,mesh_provenance:e.mesh.provenance,linear_deflection_mm:e.mesh.linear_deflection_mm}},null,2);draw()}}
function normal(a,b,c){{let u=[b[0]-a[0],b[1]-a[1],b[2]-a[2]],v=[c[0]-a[0],c[1]-a[1],c[2]-a[2]],n=[u[1]*v[2]-u[2]*v[1],u[2]*v[0]-u[0]*v[2],u[0]*v[1]-u[1]*v[0]],m=Math.hypot(...n)||1;return n.map(x=>x/m)}}function shade(color,n){{let l=Math.abs(n[0]*-.4+n[1]*-.5+n[2]*.75),s=.30+.70*l,h=color.slice(1),r=parseInt(h.slice(0,2),16),g=parseInt(h.slice(2,4),16),b=parseInt(h.slice(4,6),16);return `rgb(${{Math.round(r*s)}},${{Math.round(g*s)}},${{Math.round(b*s)}})`}}function facetEdges(e){{let map=new Map;for(let t of e.mesh.triangles){{let n=normal(e.mesh.positions[t[0]],e.mesh.positions[t[1]],e.mesh.positions[t[2]]);for(let [a,b] of [[t[0],t[1]],[t[1],t[2]],[t[2],t[0]]){{let key=a<b?`${{a}}:${{b}}`:`${{b}}:${{a}}`,item=map.get(key)||{{a:a,b:b,normals:[]}};item.normals.push(n);map.set(key,item)}}}}return [...map.values()].filter(item=>item.normals.length===1||Math.abs(item.normals[0][0]*item.normals[1][0]+item.normals[0][1]*item.normals[1][1]+item.normals[0][2]*item.normals[1][2])<.999)}}
function draw(){{ctx.clearRect(0,0,canvas.width,canvas.height);let triangles=[];scene.entities.filter(e=>e.visible).forEach(e=>e.mesh.triangles.forEach(t=>{{let a=view(e.mesh.positions[t[0]]),b=view(e.mesh.positions[t[1]]),c=view(e.mesh.positions[t[2]]),n=normal(e.mesh.positions[t[0]],e.mesh.positions[t[1]],e.mesh.positions[t[2]]);triangles.push({{e:e,a:a,b:b,c:c,n:n,depth:(a[2]+b[2]+c[2])/3}})}}));triangles.sort((left,right)=>left.depth-right.depth);triangles.forEach(item=>{{ctx.fillStyle=shade(item.e.color,item.n);ctx.globalAlpha=item.e.entity_kind==='PATCH'?.82:1;ctx.beginPath();ctx.moveTo(item.a[0],item.a[1]);ctx.lineTo(item.b[0],item.b[1]);ctx.lineTo(item.c[0],item.c[1]);ctx.closePath();ctx.fill()}});scene.entities.filter(e=>e.visible&&e.entity_kind==='REGION').forEach(e=>{{ctx.globalAlpha=.6;ctx.strokeStyle='#bdefff';ctx.lineWidth=1;facetEdges(e).forEach(edge=>{{let a=project(e.mesh.positions[edge.a]),b=project(e.mesh.positions[edge.b]);ctx.beginPath();ctx.moveTo(...a);ctx.lineTo(...b);ctx.stroke()}})}});ctx.globalAlpha=1}}
function hitTest(x,y){{let hit=null;scene.entities.filter(e=>e.visible).forEach(e=>e.mesh.triangles.forEach(t=>{{let a=project(e.mesh.positions[t[0]]),b=project(e.mesh.positions[t[1]]),c=project(e.mesh.positions[t[2]]),s=(u,v,w)=>(u[0]-w[0])*(v[1]-w[1])-(u[1]-w[1])*(v[0]-w[0]),p=[x,y],d=s(a,b,c),u=s(p,b,c)/d,v=s(a,p,c)/d;if(d&&u>=0&&v>=0&&u+v<=1)hit=e}}));return hit}}
canvas.addEventListener('pointerdown',e=>{{drag=[e.clientX,e.clientY,0];canvas.setPointerCapture(e.pointerId)}});canvas.addEventListener('pointermove',e=>{{if(!drag)return;let dx=e.clientX-drag[0],dy=e.clientY-drag[1];if(dx||dy)drag[2]+=Math.abs(dx)+Math.abs(dy);azimuth+=dx*.01;elevation=Math.max(-1.4,Math.min(1.4,elevation+dy*.01));drag[0]=e.clientX;drag[1]=e.clientY;draw()}});canvas.addEventListener('pointerup',e=>{{if(drag&&drag[2]<5){{let box=canvas.getBoundingClientRect(),hit=hitTest((e.clientX-box.left)*canvas.width/box.width,(e.clientY-box.top)*canvas.height/box.height);if(hit)select(hit)}}drag=null}});canvas.addEventListener('wheel',e=>{{e.preventDefault();zoom=Math.max(4,Math.min(50,zoom*(e.deltaY>0?.9:1.1)));draw()}},{{passive:false}});draw();</script>'''


def snapshot_from_case01_result(result: Mapping[str, Any], *, step_path: Path, repository_root: Path) -> dict[str, Any]:
    """Project accepted CASE01 B-rep facts into the existing v0.1 public contract."""
    artifact_id = "artifact:case01-step"
    document_id = result["manifest"]["source_document_id"]
    provenance_id = "provenance:case01-direct-brep"
    tolerance_linear = "tolerance:case01-contact"
    tolerance_area = "tolerance:case01-area"
    regions = [{
        "region_id": region["region_id"], "source_document_id": document_id,
        "validity_state": "VALID", "frame_ref": "frame:case01-model",
        "geometry_ref": {"artifact_ref": artifact_id, "locator": {"scheme": "STEP_OCCURRENCE", "value": region["occurrence_key"]}},
        "label": region["semantic_id"],
    } for region in result["regions"]]
    relations = []
    for raw in result["relations"]:
        refs = sorted(raw["region_pair"])
        taxonomy = raw["relation_type"]
        relations.append({"relation_id": relation_id(refs, taxonomy, "CONFIRMED"), "region_refs": refs,
                          "taxonomy": taxonomy, "confirmation": "CONFIRMED",
                          "intersection_dimension": raw["intersection_dimension"] if raw["intersection_dimension"] is not None else -1,
                          "tolerance_refs": [tolerance_linear, tolerance_area] if raw["intersection_dimension"] == 2 else [tolerance_linear]})
    relation_by_pair = {tuple(item["region_refs"]): item for item in relations}
    interfaces, components, patches = [], [], []
    for raw in result["interface_patches"]:
        refs = sorted([raw["region_a_id"], raw["region_b_id"]])
        relation = relation_by_pair[tuple(refs)]
        iid = interface_id(relation["relation_id"])
        cid = component_id(iid, [raw["patch_id"]])
        patch = {"patch_id": raw["patch_id"], "interface_ref": iid, "component_ref": cid, "family": "PLANE",
                 "frame_ref": "frame:case01-model", "source_face_refs": sorted([raw["source_face_a_id"], raw["source_face_b_id"]]),
                 "area": {"value": raw["area_mm2"], "unit": "mm2"},
                 "geometry_ref": {"artifact_ref": artifact_id, "locator": {"scheme": "STEP_FACE", "value": raw["source_face_a_id"], "provenance_ref": provenance_id}},
                 "planar_parameters": _plane_parameters(raw["geometry"]["bounding_box_mm"])}
        patches.append(patch)
        interfaces.append({"interface_id": iid, "relation_ref": relation["relation_id"], "region_refs": refs, "patch_refs": [raw["patch_id"]]})
        components.append({"component_id": cid, "interface_ref": iid, "patch_refs": [raw["patch_id"]]})
    snapshot = {
        "contract": {"name": "dmslicer.geometry-snapshot", "version": "0.1.0"}, "snapshot_id": "",
        "source_documents": [{"source_document_id": document_id, "artifact_ref": artifact_id, "source_length_unit": "mm", "internal_length_unit": "mm"}],
        "model_frame": {"frame_id": "frame:case01-model", "length_unit": "mm", "origin": [0, 0, 0], "axes": {"x": [1, 0, 0], "y": [0, 1, 0], "z": [0, 0, 1]}},
        "regions": regions, "relations": relations,
        "artifact_references": [{"artifact_id": artifact_id, "kind": "STEP", "uri": _relative_uri(step_path, repository_root)}],
        "provenance_references": [{"provenance_id": provenance_id, "goal_id": "02C-CASE01", "implementation_commit": result["manifest"]["git"]["head"], "fixture_uri": _relative_uri(step_path, repository_root), "evidence_uri": "docs/research_v2/03_interface_engine_design.md"}],
        "tolerances": [{"tolerance_id": tolerance_linear, "role": "contact_classification", "value": TOLERANCES["candidate_tolerance_mm"], "unit": "mm", "source": "CASE01"}, {"tolerance_id": tolerance_area, "role": "interface_area_acceptance", "value": TOLERANCES["area_epsilon_mm2"], "unit": "mm2", "source": "CASE01"}],
        "interfaces": interfaces, "interface_components": components, "patches": patches,
    }
    # The placeholder id is excluded by the established canonical identity routine.
    snapshot["snapshot_id"] = snapshot_id(snapshot)
    return snapshot


def build_case01_display_bundle(step_path: Path, output_dir: Path, *, repository_root: Path) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    result = analyze_case01(step_path, output_dir / "analysis")
    snapshot = snapshot_from_case01_result(result, step_path=step_path, repository_root=repository_root)
    raw_scene = _run_freecad({"action": "tessellate", "step_path": str(step_path), "linear_deflection_mm": 0.25})
    region_ids = {region["occurrence_key"]: region["region_id"] for region in result["regions"]}
    patch_ids = {frozenset(patch["semantic_pair"]): patch["patch_id"] for patch in result["interface_patches"]}
    semantic_by_occurrence = {region["occurrence_key"]: region["semantic_id"] for region in result["regions"]}
    entities = []
    for entity in raw_scene["entities"]:
        if entity["entity_kind"] == "REGION":
            ref = region_ids[entity["occurrence_key"]]
        else:
            ref = patch_ids[frozenset(semantic_by_occurrence[key] for key in entity["occurrence_pair"])]
        if entity["entity_kind"] == "REGION":
            display_name = {"A": "A / SOURCE", "G": "G / GRADIENT", "B": "B / SOURCE"}[semantic_by_occurrence[entity["occurrence_key"]]]
        else:
            pair = frozenset(semantic_by_occurrence[key] for key in entity["occurrence_pair"])
            display_name = "A-G common face" if pair == {"A", "G"} else "G-B common face"
        entities.append({"entity_ref": ref, "entity_kind": entity["entity_kind"], "display_name": display_name, "mesh": entity["mesh"]})
    scene = {"kind": "DISPLAY_ONLY_BREP_TESSELLATION", "entities": entities}
    entity_index = {entity["entity_ref"]: {"entity_kind": entity["entity_kind"]} for entity in entities}
    (output_dir / "geometry_snapshot.json").write_text(json.dumps(snapshot, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (output_dir / "display_scene.json").write_text(json.dumps(scene, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (output_dir / "case01_3d.html").write_text(_scene_html(scene), encoding="utf-8")
    (output_dir / "display_manifest.json").write_text(json.dumps({
        "goal_id": "CASE01-GEOMETRY-DISPLAY-01", "input_artifact": _relative_uri(step_path, repository_root),
        "geometry_snapshot": "geometry_snapshot.json", "display_scene": "display_scene.json",
        "viewer": "case01_3d.html", "mesh_authority": "DISPLAY_ONLY", "mesh_source": "BREP_TESSELLATION",
        "entity_refs": sorted(entity_index), "limitations": ["CASE01 axis-aligned planar patch parameter projection only"],
    }, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return {"snapshot": snapshot, "scene": scene, "entity_index": entity_index}
