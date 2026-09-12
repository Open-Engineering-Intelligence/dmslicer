const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const modelPath=require('node:path').resolve(__dirname,'../src/dmslicer/workspace_annotations.js');
const available=fs.existsSync(modelPath);
const W=available?require(modelPath):{};
function fixture(){return {case_id:'case-a',provenance:{source_evidence:{source_run_id:'run-source-a'}},scene:{entities:[
 {entity_ref:'input-a',entity_kind:'REGION',scene_role:'input',identity_status:'STABLE_REFERENCE',reference_provenance:{asset:'input.step'},display_name:'SOURCE red'},
 {entity_ref:'interface-ab',entity_kind:'INTERFACE',scene_role:'common_interface',identity_status:'STABLE_REFERENCE',reference_provenance:{asset:'interface.brep'}},
 {entity_ref:'patch-ab',entity_kind:'PATCH',scene_role:'common_interface',identity_status:'STABLE_REFERENCE',reference_provenance:{asset:'patch.brep'}},
 {entity_ref:'diagnostic-face',entity_kind:'MODEL',identity_status:'RUN_LOCAL_DIAGNOSTIC'}]}}}
test('annotation API is available before state consumers are wired',()=>assert.equal(typeof W.create,'function'));
const domainTest=(name,fn)=>test(name,{skip:!available},fn);
domainTest('defaults derive geometry only; names and colors never activate semantic entities',()=>{
 const c=fixture(),before=JSON.stringify(c),w=W.create(c);
 assert.deepEqual(w.objects.map(o=>[o.entity_ref,o.geometry_role,o.semantic_role,o.material_id,o.display_override]),[
 ['input-a','Input','Unassigned',null,null],['interface-ab','Interface','Unassigned',null,null],['patch-ab','Patch','Unassigned',null,null]]);
 assert.deepEqual(w.activation,{MaterialRegion:false,InterfaceSourceBoundary:false,volumetric_field:false});
 assert.equal(JSON.stringify(c),before);
});
domainTest('explicit role, material and override are independent through material edits and roundtrip',()=>{
 const c=fixture(),w=W.create(c);
 W.putMaterial(w,{id:'polymer-a',name:'Source',color:'#112233',description:'',properties:{density:{value:1.2,unit:'g/cm3'}}});
 W.decide(w,'input-a','material_id','polymer-a');
 assert.equal(w.objects[0].semantic_role,'Unassigned');assert.equal(W.color(w,'input-a'),'#112233');
 W.decide(w,'input-a','semantic_role','Gradient');W.decide(w,'input-a','display_override','#ff0000');
 W.putMaterial(w,{id:'polymer-a',name:'Renamed',color:'#336699',description:'changed',properties:{}});
 assert.equal(w.objects[0].material_id,'polymer-a');assert.equal(w.objects[0].semantic_role,'Gradient');
 assert.equal(W.color(w,'input-a'),'#ff0000');W.decide(w,'input-a','display_override',null);
 assert.equal(W.color(w,'input-a'),'#336699');assert.equal(w.material_library.version,2);
 const restored=W.restore(c,JSON.stringify(w));assert.equal(restored.objects[0].semantic_role,'Gradient');
 assert(restored.decisions.every(d=>d.actor==='human'&&d.at));assert.equal(restored.activation.MaterialRegion,false);
});
domainTest('restore refuses wrong source and changed reference provenance without mutating current state',()=>{
 const c=fixture(),w=W.create(c),raw=JSON.stringify(w);
 c.provenance.source_evidence.source_run_id='other';assert.throws(()=>W.restore(c,raw),/source/i);
 const other=fixture();other.scene.entities[0].reference_provenance.asset='another.step';assert.throws(()=>W.restore(other,raw),/reference/i);
 assert.equal(JSON.stringify(w),raw);
});
domainTest('invalid annotations never enter persistence',()=>{
 const c=fixture(),w=W.create(c);
 for(const [field,value] of [['semantic_role','SourceBoundary'],['material_id','absent'],['display_override','red'],['geometry_role','Patch']])assert.throws(()=>W.decide(w,'input-a',field,value));
 assert.throws(()=>W.decide(w,'diagnostic-face','semantic_role','Source'),/stable/i);
 for(const edit of [v=>v.objects.push(v.objects[0]),v=>v.objects.pop(),v=>v.objects[0].geometry_role='Patch',v=>v.activation.MaterialRegion=true,v=>v.material_library.version=-1,v=>v.objects[0].material_id='missing']){
  const value=JSON.parse(JSON.stringify(w));edit(value);assert.throws(()=>W.restore(c,JSON.stringify(value)));
 }
 assert.equal(w.decisions.length,0);
});
domainTest('library requires stable keys, valid colors and JSON properties; failed edits are atomic',()=>{
 const w=W.create(fixture()),before=JSON.stringify(w);
 for(const data of [{id:'',name:'x',color:'#123456',description:'',properties:{}},{id:'x',name:'',color:'#123456',description:'',properties:{}},{id:'x',name:'X',color:'red',description:'',properties:{}},{id:'x',name:'X',color:'#123456',description:'',properties:[]}])assert.throws(()=>W.putMaterial(w,data));
 assert.equal(JSON.stringify(w),before);
});
domainTest('selection and opacity operate on explicit sets; empty and filtered sets cannot leak',()=>{
 const c=fixture(),s=W.display(c.scene.entities);assert.equal(s.selected.size,4);
 W.select(s,'none');W.transparency(s,65);assert.equal(s.items.get('input-a').transparency,0);
 s.selected.add('interface-ab');W.transparency(s,65);assert.equal(s.items.get('interface-ab').transparency,65);assert.equal(s.items.get('patch-ab').transparency,0);
 W.select(s,'invert');W.show(s,false);assert.equal(s.items.get('interface-ab').visible,true);assert.equal(s.items.get('patch-ab').visible,false);
 assert.throws(()=>W.transparency(s,101));assert.throws(()=>W.transparency(s,NaN));
});
domainTest('failed save preserves draft, saved time and old persisted bytes',()=>{
 const c=fixture(),w=W.create(c),before=JSON.stringify(w);
 const store={setItem(){throw Error('Quota exceeded')}};
 assert.throws(()=>W.save(c,w,store),/Quota/);assert.equal(JSON.stringify(w),before);
 const data=new Map();W.save(c,w,{setItem:(k,v)=>data.set(k,v)});
 const saved=W.restore(c,[...data.values()][0]);assert(saved.saved_at);assert.equal(w.saved_at,saved.saved_at);
});
