"""FreeCADCmd diagnostic for the existing 05C A01 candidate-plane measurement."""
import hashlib,json,os
from pathlib import Path
import FreeCAD,Import,Part
req=json.loads(Path(os.environ['DMSLICER_PROBE_REQUEST']).read_text())
out=Path(os.environ['DMSLICER_PROBE_RESPONSE'])
def plane(f): return f.Surface if 'plane' in type(f.Surface).__name__.lower() else None
def faces(label,shape):
 r=[]
 for i,f in enumerate(shape.Faces,1):
  p=plane(f); ok=bool(p and abs(p.Axis.z)>=1-1e-7); n=None
  if ok:
   try:n=f.normalAt(0,0)
   except:n=None
  r.append({'body':label,'face':'Face%d'%i,'area_mm2':float(f.Area),'bbox':[f.BoundBox.XMin,f.BoundBox.YMin,f.BoundBox.ZMin,f.BoundBox.XMax,f.BoundBox.YMax,f.BoundBox.ZMax],'plane_position':[p.Position.x,p.Position.y,p.Position.z] if p else None,'plane_axis':[p.Axis.x,p.Axis.y,p.Axis.z] if p else None,'face_orientation':str(f.Orientation),'face_normal_at_uv0':[n.x,n.y,n.z] if n else None,'passes_production_filter':ok,'filter_reason':'planar and abs(Axis.z)>=1-1e-7' if ok else 'not a qualifying horizontal supporting plane','shape':f})
 return r
for sample in req['samples']:
 doc=FreeCAD.newDocument('A01CandidateProbe')
 try:
  Import.insert(sample['step_path'],doc.Name); objs=sorted([(x.Label,x.Shape.Solids[0]) for x in doc.Objects if x.TypeId=='Part::Feature' and len(x.Shape.Solids)==1])
  (la,a),(lb,b)=objs; fa,fb=faces(la,a),faces(lb,b); cand=[]
  for x in fa:
   if not x['passes_production_filter']:continue
   pa=a.Faces[int(x['face'][4:])-1].Surface; normal=pa.Axis.normalize()
   for y in fb:
    if not y['passes_production_filter']:continue
    pb=b.Faces[int(y['face'][4:])-1].Surface; signed=(pb.Position-pa.Position).dot(normal); cand.append({'first_face':x['face'],'second_face':y['face'],'normal':[normal.x,normal.y,normal.z],'signed_offset_mm':signed,'absolute_offset_mm':abs(signed),'comparison_tuple':[abs(signed),signed],'traversal_index':len(cand)})
  cand.sort(key=lambda z:(z['absolute_offset_mm'],z['signed_offset_mm'])); mn=cand[0]['comparison_tuple']; same=[z for z in cand if z['comparison_tuple']==mn]
  production=min((abs(z['signed_offset_mm']),z['signed_offset_mm']) for z in cand)[1]
  nominal={'first_face':'Face6','second_face':'Face5','signed_offset_mm':None}
  # explicit face-role reference: lower top is max z; upper bottom is min z
  top=max([x for x in fa if x['passes_production_filter']],key=lambda x:x['plane_position'][2]); bottom=min([x for x in fb if x['passes_production_filter']],key=lambda x:x['plane_position'][2]); nominal={'first_face':top['face'],'second_face':bottom['face'],'signed_offset_mm':bottom['plane_position'][2]-top['plane_position'][2]}
  vol=float(a.common(b).Volume); result={'sample_id':sample['sample_id'],'step_sha256':'sha256:'+hashlib.sha256(Path(sample['step_path']).read_bytes()).hexdigest(),'production_return_mm':production,'faces':[ {k:v for k,v in z.items() if k!='shape'} for z in fa+fb],'candidates':cand,'minimum_tuple':list(mn),'equal_minimum_candidates':same,'nominal_reference':nominal,'common_volume_mm3':vol}
  if sample['sample_id']==req['primary']:
   for name,sh in [('Actual_Input_1',a),('Actual_Input_2',b),('Production_Minimum_Candidates',Part.makeCompound([a.Faces[int(z['first_face'][4:])-1] for z in same]+[b.Faces[int(z['second_face'][4:])-1] for z in same])),('Nominal_Contact_Reference',Part.makeCompound([a.Faces[int(top['face'][4:])-1],b.Faces[int(bottom['face'][4:])-1]]))]:
    o=doc.addObject('Part::Feature',name);o.Shape=sh;o.addProperty('App::PropertyString','ProbeRole');o.ProbeRole=name
   doc.recompute();doc.saveAs(req['fcstd_path'])
  req.setdefault('results',[]).append(result)
 finally:FreeCAD.closeDocument(doc.Name)
out.write_text(json.dumps(req,indent=2))
