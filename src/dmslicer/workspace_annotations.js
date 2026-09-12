/* Human annotations only. Never constructs geometry, MaterialRegion or a field. */
const WorkspaceAnnotations = (() => {
 const copy=value=>JSON.parse(JSON.stringify(value));
 const now=()=>new Date().toISOString();
 const require=(value,message)=>{if(!value)throw Error(message)};
 const object=v=>v!==null&&typeof v==='object'&&!Array.isArray(v);
 const canonical=v=>JSON.stringify(sort(v));
 function sort(v){return Array.isArray(v)?v.map(sort):object(v)?Object.fromEntries(Object.keys(v).sort().map(k=>[k,sort(v[k])])):v}
 const types=['Unassigned','Source','Gradient','Isolator'];
 const activation={MaterialRegion:false,InterfaceSourceBoundary:false,volumetric_field:false};
 const hex=v=>typeof v==='string'&&/^#[0-9a-fA-F]{6}$/.test(v);
 function geometryRole(e){
  if(e.entity_kind==='INTERFACE')return 'Interface';
  if(e.entity_kind==='PATCH')return 'Patch';
  return ({input:'Input',fused_result:'Fused output',corrected:'Corrected geometry',remaining:'Remaining geometry'})[e.scene_role]||'Input';
 }
 function source(c){return copy({case_id:c.case_id,provenance:c.provenance.source_evidence||c.provenance,package_case:c.provenance.package_case||null})}
 function library(){return {schema:'dmslicer.material-library.v1',version:0,materials:[['PLA','#6daba3'],['ABS','#dcaa6c'],['PETG','#709abe'],['TPO','#b898bb']].map(([id,color])=>({id,name:id,category:'预置聚合物',color,description:'用户指定的常用材料名称；颜色为显示设计值，未提供物性数据。',properties:{},provenance:{kind:'UI_PRESET',basis:'User requested PLA, ABS, PETG, TPO; no physical values supplied'}})),history:[]}}
 function create(c,materials=library()){
  validateLibrary(materials);
  require(typeof c.case_id==='string'&&c.case_id.length>0&&object(c.provenance)&&Object.keys(c.provenance.source_evidence||c.provenance).length>0,'Source provenance required');
  const refs=new Set();for(const e of c.scene.entities){require(typeof e.entity_ref==='string'&&e.entity_ref.length>0&&!refs.has(e.entity_ref),'Unique object reference required');refs.add(e.entity_ref);if(e.identity_status==='STABLE_REFERENCE')require(object(e.reference_provenance)&&Object.keys(e.reference_provenance).length>0,'Stable reference provenance required')}
  return {schema:'dmslicer.workspace-annotation.v2',source:source(c),created_at:now(),saved_at:null,
   material_library:copy(materials),material_library_version:materials.version,activation:copy(activation),decisions:[],active_relations:[],isolator_material_requirement:'UNDECIDED',
   objects:c.scene.entities.filter(e=>e.identity_status==='STABLE_REFERENCE').map(e=>({entity_ref:e.entity_ref,
    reference_provenance:copy(e.reference_provenance),source_geometry:copy(e.source||null),geometry_role:geometryRole(e),semantic_type:'Unassigned',material_id:null,gradient_group_id:null,isolator_instance:null,display_override:null}))};
 }
 function validateMaterial(m){
  require(object(m)&&typeof m.id==='string'&&/^[a-zA-Z][a-zA-Z0-9._-]{0,79}$/.test(m.id),'Invalid stable material key');
  require(typeof m.name==='string'&&m.name.trim().length>0&&m.name.length<=200,'Material name required (max 200)');
  require(hex(m.color),'Invalid material color');require(typeof m.description==='string'&&m.description.length<=4000,'Invalid description');
  require(m.category===undefined||typeof m.category==='string'&&m.category.length<=200,'Invalid category');
  require(object(m.properties)&&JSON.stringify(m.properties).length<=16000,'Properties must be a JSON object (max 16 KB)');
  require(canonical(m.properties)===canonical(JSON.parse(JSON.stringify(m.properties))),'Properties must be finite JSON');
  function quantities(v,basis){
   if(typeof v==='number')require(Number.isFinite(v)&&basis&&['unit','source','evidence'].every(k=>typeof basis[k]==='string'&&basis[k].trim()),'Numeric properties require finite value, unit, source and evidence');
   else if(Array.isArray(v))v.forEach(x=>quantities(x,basis));
   else if(object(v)){const range=Number.isFinite(v.min)&&Number.isFinite(v.max)&&v.min<=v.max&&['unit','source','evidence'].every(k=>typeof v[k]==='string'&&v[k].trim());for(const [k,x] of Object.entries(v))quantities(x,k==='value'?v:(range&&['min','max'].includes(k)?{unit:v.unit,source:v.source,evidence:v.evidence}:null));}
  }quantities(m.properties,null);
 }
 function validateLibrary(l){
  require(object(l)&&l.schema==='dmslicer.material-library.v1'&&Number.isInteger(l.version)&&l.version>=0,'Invalid material library version');
  require(Array.isArray(l.materials)&&l.materials.length<=1000&&Array.isArray(l.history),'Invalid material library');
  const ids=new Set();for(const m of l.materials){validateMaterial(m);require(!ids.has(m.id),'Duplicate material key');ids.add(m.id)}
 }
 function validate(c,w){
  require(w?.schema!=='dmslicer.workspace-annotation.v1','v1 annotation is ambiguous; review semantic types and recreate v2 explicitly');
  require(object(w)&&w.schema==='dmslicer.workspace-annotation.v2','Invalid workspace annotation schema');
  require(canonical(w.source)===canonical(source(c)),'Annotation source does not match this case');
  require(canonical(w.activation)===canonical(activation),'Semantic activation is unsupported');validateLibrary(w.material_library);
  require(w.isolator_material_requirement==='UNDECIDED','Isolator material requirement is undecided');
  require(Array.isArray(w.active_relations),'Invalid active relations');
  require(!w.active_relations.some(r=>r.source_ref===r.target_ref),'Self association is forbidden');
  require(w.active_relations.length===0,'Active relation generation is not implemented');
  require(w.material_library_version===w.material_library.version,'Library version mismatch');
  require(typeof w.created_at==='string'&&Number.isFinite(Date.parse(w.created_at))&&(w.saved_at===null||typeof w.saved_at==='string'&&Number.isFinite(Date.parse(w.saved_at))),'Invalid annotation timestamp');
  require(Array.isArray(w.decisions)&&w.decisions.every(d=>object(d)&&(d.actor==='human'||d.actor==='system'&&d.reason==='DEFAULT_GRADIENT_GROUP')&&typeof d.at==='string'&&Number.isFinite(Date.parse(d.at))),'Invalid decision history');
  const expected=create(c).objects,refs=new Map(expected.map(e=>[e.entity_ref,e]));
  require(Array.isArray(w.objects)&&w.objects.length===expected.length,'Missing/duplicate stable references');
  for(const o of w.objects){const e=refs.get(o.entity_ref);require(e,'Unknown/duplicate stable reference');refs.delete(o.entity_ref);
   require(canonical(o.reference_provenance)===canonical(e.reference_provenance),'Reference provenance mismatch');
   require(canonical(o.source_geometry)===canonical(e.source_geometry),'Object source geometry reference mismatch');
   require(!('semantic_role' in o),'Ambiguous legacy semantic_role is rejected');
   require(o.geometry_role===e.geometry_role,'Geometry role is read only');require(types.includes(o.semantic_type),'Invalid semantic type');
   if(e.geometry_role!=='Input')require(o.semantic_type==='Unassigned'&&o.material_id===null&&o.display_override===null,'Only input block/region annotations are supported');
   require(o.material_id===null||w.material_library.materials.some(m=>m.id===o.material_id),'Unknown material');
   if(o.semantic_type==='Source')require(o.material_id!==null,'Source requires material_id');
   if(o.semantic_type==='Gradient'){require(o.material_id===null,'Gradient material_id must be null');require(typeof o.gradient_group_id==='string'&&/^G(?:[1-9][0-9]*)?$/.test(o.gradient_group_id),'Gradient group must be G, G1, G2, ...')}
   else require(o.gradient_group_id===null,'Only Gradient has gradient_group_id');
   if(o.semantic_type==='Isolator')require(object(o.isolator_instance)&&o.isolator_instance.owner_entity_ref===o.entity_ref&&typeof o.isolator_instance.name==='string'&&o.isolator_instance.name.length>0,'Isolator owner must match stable object identity');
   else require(o.isolator_instance===null,'Only Isolator has isolator_instance');
   require(o.display_override===null||hex(o.display_override),'Invalid display override');
  }
  return w;
 }
 function decide(w,ref,field,value){
  const o=w.objects.find(o=>o.entity_ref===ref);require(o,'No stable reference for annotation');
  require(o.geometry_role==='Input','Only input block/region annotations are supported');
  require(['semantic_type','material_id','display_override','gradient_group_id'].includes(field),'Geometry role is read only');
  if(field==='semantic_type')require(types.includes(value),'Invalid semantic type');
  if(field==='material_id')require(value===null||w.material_library.materials.some(m=>m.id===value),'Unknown material');
  if(field==='material_id'&&o.semantic_type==='Gradient')require(value===null,'Gradient cannot have direct material assignment');
  if(field==='display_override')require(value===null||hex(value),'Invalid display override');
  if(field==='gradient_group_id')require(o.semantic_type==='Gradient'&&typeof value==='string'&&/^G(?:[1-9][0-9]*)?$/.test(value),'Gradient group must be G, G1, G2, ...');
  if(o[field]===value)return;
  function change(key,next,reason='EXPLICIT_HUMAN_CONFIGURATION'){if(canonical(o[key])===canonical(next))return;w.decisions.push({actor:'human',at:now(),entity_ref:ref,field:key,before:copy(o[key]),after:copy(next),reason,material_library_version:w.material_library.version});o[key]=next}
  change(field,value);
  if(field==='semantic_type'){
   if(value==='Gradient')change('material_id',null,'GRADIENT_REQUIRES_NULL_MATERIAL');
   change('gradient_group_id',value==='Gradient'?'G':null,'SEMANTIC_TYPE_TRANSITION');
   change('isolator_instance',value==='Isolator'?{owner_entity_ref:ref,name:'Isolator'}:null,'SEMANTIC_TYPE_TRANSITION');
  }
 }
 function applyAssignment(w,refs,draft){
  require(Array.isArray(refs)&&refs.length>0,'Select at least one object');
  require(object(draft)&&types.includes(draft.semantic_type),'Invalid assignment draft');
  const candidate=copy(w),unique=[...new Set(refs)];
  require(unique.length===refs.length,'Duplicate stable object reference');
  for(const ref of unique)require(candidate.objects.some(o=>o.entity_ref===ref),'Unknown stable object reference');
  if(draft.semantic_type==='Source')require(typeof draft.material_id==='string'&&draft.material_id.length>0,'Source requires material_id');
  if(draft.semantic_type==='Gradient')require(draft.material_id===undefined||draft.material_id===null,'Gradient cannot have direct material assignment');
  for(const ref of unique){
   decide(candidate,ref,'semantic_type',draft.semantic_type);
   if(draft.semantic_type==='Source')decide(candidate,ref,'material_id',draft.material_id);
   if(draft.semantic_type==='Gradient')decide(candidate,ref,'gradient_group_id',draft.gradient_group_id||'G');
   if(Object.prototype.hasOwnProperty.call(draft,'display_override'))decide(candidate,ref,'display_override',draft.display_override);
  }
  Object.assign(w,candidate);
  return w;
 }
 function putMaterial(w,data){
  validateMaterial(data);const l=w.material_library,old=l.materials.find(m=>m.id===data.id),at=now();
  const value={...copy(data),category:data.category||'自定义',updated_at:at};
  l.history.push({actor:'human',at,material_id:data.id,before:old?copy(old):null,after:copy(value),version:l.version+1});
  if(old)Object.assign(old,value);else l.materials.push(value);
  l.version++;w.material_library_version=l.version;
 }
 function materialDraft(material){
  validateMaterial(material);
  return copy(material);
 }
 function exportLibrary(l,libraryId){validateLibrary(l);require(typeof libraryId==='string'&&/^[a-zA-Z][a-zA-Z0-9._-]{0,79}$/.test(libraryId),'Invalid library_id');return {schema_version:'dmslicer.material-library-file.v1',library_id:libraryId,materials:copy(l.materials),exported_at:now()}}
 function importLibrary(text){require(typeof text==='string'&&text.length<=4*1024*1024,'Library limit: 4 MiB');const f=JSON.parse(text);require(object(f)&&f.schema_version==='dmslicer.material-library-file.v1'&&typeof f.library_id==='string'&&Array.isArray(f.materials)&&typeof f.exported_at==='string'&&Number.isFinite(Date.parse(f.exported_at)),'Invalid material library file');const l={schema:'dmslicer.material-library.v1',version:0,materials:f.materials,history:[]};validateLibrary(l);return l}
 function color(w,ref){const o=w?.objects.find(o=>o.entity_ref===ref);return o?.display_override||w?.material_library.materials.find(m=>m.id===o?.material_id)?.color||'#8ca3b3'}
 function restore(c,text){
  require(typeof text==='string'&&text.length<=4*1024*1024,'Annotation limit: 4 MiB');const value=JSON.parse(text);
  if(value?.schema==='dmslicer.workspace-annotation.v2'&&Array.isArray(value.objects)&&Array.isArray(value.decisions))for(const o of value.objects){
   if(o.semantic_type==='Gradient'&&o.gradient_group_id===undefined){o.gradient_group_id='G';value.decisions.push({actor:'system',at:now(),entity_ref:o.entity_ref,field:'gradient_group_id',before:null,after:'G',reason:'DEFAULT_GRADIENT_GROUP'})}
  }
  return validate(c,value);
 }
 function replaceLibrary(c,w,text){
  require(typeof text==='string'&&text.length<=4*1024*1024,'Library limit: 4 MiB');const l=JSON.parse(text);validateLibrary(l);
  const candidate=copy(w);candidate.material_library=l;candidate.material_library_version=l.version;validate(c,candidate);
  w.decisions.push({actor:'human',at:now(),field:'material_library',before:copy(w.material_library),after:copy(l)});
  w.material_library=l;w.material_library_version=l.version;
 }
 function key(c){return 'dmslicer.workspace.v2:'+canonical(source(c))}
 function save(c,w,storage){const snapshot=copy(w);snapshot.saved_at=now();validate(c,snapshot);storage.setItem(key(c),JSON.stringify(snapshot));w.saved_at=snapshot.saved_at;return snapshot}
 function connectionPolicy(w,a,b,geometry){
  require(a!==b,'Self connection is forbidden');const left=w.objects.find(o=>o.entity_ref===a),right=w.objects.find(o=>o.entity_ref===b);require(left&&right,'Stable object references required');
  let reason='NOT_TWO_GRADIENT_REGIONS',allowed=false;
  if(left.semantic_type==='Gradient'&&right.semantic_type==='Gradient'){
   if(left.gradient_group_id!==right.gradient_group_id)reason='DIFFERENT_GRADIENT_GROUP';
   else if(geometry?.status==='CONFIRMED'&&geometry.allows_connection===true&&typeof geometry.relation_ref==='string'&&geometry.relation_ref.length>0&&canonical([...(geometry.region_refs||[])].sort())===canonical([a,b].sort())){reason='SAME_GROUP_CONFIRMED_GEOMETRY';allowed=true}
   else reason='GEOMETRY_CONNECTION_NOT_CONFIRMED';
  }
  return {schema:'dmslicer.gradient-connection-policy.v1',source_ref:a,target_ref:b,gradient_groups:[left.gradient_group_id,right.gradient_group_id],geometry_evidence:copy(geometry||null),allowed,activated:false,reason};
 }
 return {create,geometryRole,types,library,validateLibrary,putMaterial,materialDraft,exportLibrary,importLibrary,decide,applyAssignment,color,validate,restore,replaceLibrary,key,save,connectionPolicy};
})();
if(typeof module!=='undefined')module.exports=WorkspaceAnnotations;
