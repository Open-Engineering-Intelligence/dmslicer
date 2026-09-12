const {test}=require('node:test');
const assert=require('node:assert/strict');
const W=require('../src/dmslicer/workspace_annotations.js');
function fixture(){return {case_id:'case-a',provenance:{source_evidence:{source_run_id:'run-source-a'}},scene:{entities:[
 {entity_ref:'input-a',entity_kind:'REGION',scene_role:'input',identity_status:'STABLE_REFERENCE',reference_provenance:{asset:'input.step'},display_name:'SOURCE red'},
 {entity_ref:'input-b',entity_kind:'REGION',scene_role:'input',identity_status:'STABLE_REFERENCE',reference_provenance:{asset:'input.step'},display_name:'Gradient'},
 {entity_ref:'interface-ab',entity_kind:'INTERFACE',scene_role:'common_interface',identity_status:'STABLE_REFERENCE',reference_provenance:{asset:'interface.brep'}},
 {entity_ref:'patch-ab',entity_kind:'PATCH',scene_role:'common_interface',identity_status:'STABLE_REFERENCE',reference_provenance:{asset:'patch.brep'}},
 {entity_ref:'diagnostic-face',entity_kind:'MODEL',identity_status:'RUN_LOCAL_DIAGNOSTIC'}]}}}
const material=()=>({id:'mat-a',name:'Material A',category:'Custom',color:'#112233',description:'',properties:{density:{value:1.2,unit:'g/cm3',source:'TEST ONLY',evidence:'synthetic test fixture; not an actual material property'}}});
test('v2 defaults do not infer semantic types from source names; four presets contain no physical values',()=>{
 const c=fixture(),before=JSON.stringify(c),w=W.create(c);assert.equal(w.schema,'dmslicer.workspace-annotation.v2');
 assert.deepEqual(w.objects.map(o=>[o.entity_ref,o.geometry_role,o.semantic_type,o.material_id,o.gradient_group_id,o.isolator_instance]),[
 ['input-a','Input','Unassigned',null,null,null],['input-b','Input','Unassigned',null,null,null],['interface-ab','Interface','Unassigned',null,null,null],['patch-ab','Patch','Unassigned',null,null,null]]);
 assert.deepEqual(w.material_library.materials.map(m=>m.id),['PLA','ABS','PETG','TPO']);assert(w.material_library.materials.every(m=>Object.keys(m.properties).length===0&&m.category));
 assert.deepEqual(w.activation,{MaterialRegion:false,InterfaceSourceBoundary:false,volumetric_field:false});assert.deepEqual(w.active_relations,[]);assert.equal(JSON.stringify(c),before);
});
test('Source requires existing material when persisting, while incomplete draft is editable',()=>{
 const c=fixture(),w=W.create(c);W.decide(w,'input-a','semantic_type','Source');assert.throws(()=>W.validate(c,w),/Source.*material/i);
 W.decide(w,'input-a','material_id','PLA');W.validate(c,w);assert.equal(w.objects[0].semantic_type,'Source');
 assert.throws(()=>W.decide(w,'input-a','material_id','absent'),/material/i);
});
test('Gradient cannot hold material; switching records cleared assignment and keeps display override separate',()=>{
 const c=fixture(),w=W.create(c);W.decide(w,'input-a','material_id','PLA');W.decide(w,'input-a','display_override','#ff0000');
 W.decide(w,'input-a','semantic_type','Gradient');const o=w.objects[0];assert.equal(o.material_id,null);assert.equal(o.gradient_group_id,'G');assert.equal(o.display_override,'#ff0000');
 assert(w.decisions.some(d=>d.field==='material_id'&&d.before==='PLA'&&d.after===null));assert.throws(()=>W.decide(w,'input-a','material_id','ABS'),/Gradient/i);
 const raw=JSON.parse(JSON.stringify(w));raw.objects[0].material_id='PLA';assert.throws(()=>W.restore(c,JSON.stringify(raw)),/Gradient/i);
 W.decide(w,'input-a','gradient_group_id','G2');assert.equal(W.restore(c,JSON.stringify(w)).objects[0].gradient_group_id,'G2');
 const absent=JSON.parse(JSON.stringify(w));delete absent.objects[0].gradient_group_id;const defaulted=W.restore(c,JSON.stringify(absent));assert.equal(defaulted.objects[0].gradient_group_id,'G');assert(defaulted.decisions.some(d=>d.reason==='DEFAULT_GRADIENT_GROUP'));
 assert.equal(w.material_library.materials.some(m=>m.id==='G2'),false);assert.equal(w.activation.volumetric_field,false);
});
test('same group requires confirmed connection; different groups preserve geometry contact but block semantics',()=>{
 const w=W.create(fixture());W.decide(w,'input-a','semantic_type','Gradient');W.decide(w,'input-b','semantic_type','Gradient');
 const g={relation_ref:'relation-a-b',region_refs:['input-a','input-b'],status:'CONFIRMED',allows_connection:true},before=JSON.stringify(g);
 const yes=W.connectionPolicy(w,'input-a','input-b',g);assert.equal(yes.allowed,true);assert.equal(yes.activated,false);assert.equal(yes.reason,'SAME_GROUP_CONFIRMED_GEOMETRY');
 W.decide(w,'input-b','gradient_group_id','G1');const no=W.connectionPolicy(w,'input-a','input-b',g);assert.equal(no.allowed,false);assert.equal(no.reason,'DIFFERENT_GRADIENT_GROUP');assert.deepEqual(no.geometry_evidence,g);
 W.decide(w,'input-a','gradient_group_id','G2');assert.equal(W.connectionPolicy(w,'input-a','input-b',g).allowed,false);
 W.decide(w,'input-a','gradient_group_id','G1');assert.equal(W.connectionPolicy(w,'input-a','input-b',{...g,status:'CANDIDATE'}).allowed,false);assert.equal(W.connectionPolicy(w,'input-a','input-b',{...g,allows_connection:false}).allowed,false);
 assert.throws(()=>W.connectionPolicy(w,'input-a','input-a',g),/self/i);assert.equal(W.connectionPolicy(w,'input-a','input-b',{...g,region_refs:['input-a','unrelated']}).allowed,false);
 assert.equal(JSON.stringify(g),before);assert.deepEqual(w.active_relations,[]);
});
test('Isolator identity is object scoped, material requirement remains undecided and self links are rejected',()=>{
 const c=fixture(),w=W.create(c);W.decide(w,'input-a','material_id','PETG');W.decide(w,'input-a','semantic_type','Isolator');W.decide(w,'input-b','semantic_type','Isolator');
 assert.equal(w.isolator_material_requirement,'UNDECIDED');assert.equal(w.objects[0].material_id,'PETG');assert.equal(w.objects[1].material_id,null);
 assert.equal(w.objects[0].isolator_instance.owner_entity_ref,'input-a');assert.equal(w.objects[1].isolator_instance.owner_entity_ref,'input-b');
 assert.equal(w.objects[0].isolator_instance.name,w.objects[1].isolator_instance.name);assert.notDeepEqual(w.objects[0].isolator_instance,w.objects[1].isolator_instance);W.validate(c,w);
 const raw=JSON.parse(JSON.stringify(w));raw.active_relations=[{source_ref:'input-a',target_ref:'input-a'}];assert.throws(()=>W.restore(c,JSON.stringify(raw)),/self/i);
 raw.active_relations=[];raw.objects[1].isolator_instance.owner_entity_ref='input-a';assert.throws(()=>W.restore(c,JSON.stringify(raw)),/owner/i);
});
test('material color follows edits except explicit override, never changes semantic type',()=>{
 const c=fixture(),w=W.create(c);W.putMaterial(w,material());W.decide(w,'input-a','material_id','mat-a');W.decide(w,'input-a','semantic_type','Source');assert.equal(W.color(w,'input-a'),'#112233');
 W.decide(w,'input-a','display_override','#ff0000');W.putMaterial(w,{...material(),name:'Renamed',color:'#336699'});assert.equal(W.color(w,'input-a'),'#ff0000');assert.equal(w.objects[0].semantic_type,'Source');
 W.decide(w,'input-a','display_override',null);assert.equal(W.color(w,'input-a'),'#336699');assert.equal(w.material_library.version,2);W.validate(c,w);
});
test('all numeric properties require unit, source and traceable basis; invalid edits are atomic',()=>{
 const w=W.create(fixture()),before=JSON.stringify(w);
 for(const properties of [{density:1.2},{density:{value:1.2,unit:'g/cm3'}},{density:{value:1.2,unit:'g/cm3',source:'datasheet'}},{density:{value:NaN,unit:'x',source:'s',evidence:'e'}},[]])assert.throws(()=>W.putMaterial(w,{...material(),properties}));
 assert.equal(JSON.stringify(w),before);W.putMaterial(w,material());assert.equal(w.material_library.materials.at(-1).properties.density.value,1.2);
});
test('v1 and forged annotations are explicitly rejected; current state stays intact',()=>{
 const c=fixture(),w=W.create(c),before=JSON.stringify(w);const old=JSON.parse(before);old.schema='dmslicer.workspace-annotation.v1';assert.throws(()=>W.restore(c,JSON.stringify(old)),/v1.*ambiguous/i);
 for(const edit of [v=>v.objects.push(v.objects[0]),v=>v.objects.pop(),v=>v.objects[0].geometry_role='Patch',v=>v.activation.MaterialRegion=true,v=>v.material_library.version=-1,v=>v.objects[0].material_id='missing',v=>v.objects[2].semantic_type='Source',v=>v.objects[0].semantic_role='Gradient']){const value=JSON.parse(before);edit(value);assert.throws(()=>W.restore(c,JSON.stringify(value)))}
 assert.throws(()=>W.decide(w,'diagnostic-face','semantic_type','Source'),/stable/i);assert.throws(()=>W.decide(w,'interface-ab','semantic_type','Source'),/input/i);assert.equal(JSON.stringify(w),before);
});
test('source context, asset and provenance must match exactly, not a geometry equivalence test',()=>{
 const c=fixture(),w=W.create(c),raw=JSON.stringify(w);c.provenance.source_evidence.source_run_id='other';assert.throws(()=>W.restore(c,raw),/source/i);
 const other=fixture();other.scene.entities[0].reference_provenance.asset='another.step';assert.throws(()=>W.restore(other,raw),/reference/i);
 const changed=fixture();changed.scene.entities[0].source={asset:'other.step'};assert.throws(()=>W.restore(changed,raw),/source/i);
 const missing=fixture();delete missing.scene.entities[0].reference_provenance;assert.throws(()=>W.create(missing),/provenance/i);
});
test('save validates first; storage failure preserves old bytes, draft and saved timestamp',()=>{
 const c=fixture(),w=W.create(c),before=JSON.stringify(w);assert.throws(()=>W.save(c,w,{setItem(){throw Error('Quota exceeded')}}),/Quota/);assert.equal(JSON.stringify(w),before);
 const data=new Map();W.save(c,w,{setItem:(k,v)=>data.set(k,v)});assert.equal(W.restore(c,[...data.values()][0]).saved_at,w.saved_at);
 W.decide(w,'input-a','semantic_type','Source');assert.throws(()=>W.save(c,w,{setItem(){assert.fail('must validate before writing')}}),/material/i);
});
test('library replacement retains assignments and former revision; orphan material references rejected atomically',()=>{
 const c=fixture(),w=W.create(c);W.putMaterial(w,material());W.decide(w,'input-a','material_id','mat-a');const before=JSON.stringify(w);
 assert.throws(()=>W.replaceLibrary(c,w,JSON.stringify({schema:'dmslicer.material-library.v1',version:0,materials:[],history:[]})),/material/i);assert.equal(JSON.stringify(w),before);
 const l=JSON.parse(JSON.stringify(w.material_library));l.materials.find(m=>m.id==='mat-a').name='Imported';W.replaceLibrary(c,w,JSON.stringify(l));assert.equal(w.objects[0].material_id,'mat-a');assert.equal(w.decisions.at(-1).before.materials.find(m=>m.id==='mat-a').name,'Material A');
});
test('multi-object assignment is atomic when one stable reference is missing',()=>{
 const c=fixture(),w=W.create(c),before=JSON.stringify(w);
 assert.throws(()=>W.applyAssignment(w,['input-a','missing'],{semantic_type:'Source',material_id:'PLA'}),/applyAssignment|Unknown stable/i);
 assert.equal(JSON.stringify(w),before);
});
test('Gradient assignment clears material for every selected input',()=>{
 const c=fixture(),w=W.create(c);
 W.applyAssignment(w,['input-a','input-b'],{semantic_type:'Gradient',gradient_group_id:'G2',material_id:null});
 assert.deepEqual(w.objects.slice(0,2).map(o=>[o.semantic_type,o.material_id,o.gradient_group_id]),[['Gradient',null,'G2'],['Gradient',null,'G2']]);
});
test('material draft is an independent copy for non-destructive edit',()=>{
 const w=W.create(fixture()),original=w.material_library.materials[0],draft=W.materialDraft(original);
 assert.deepEqual(draft,original);draft.name='Changed only in dialog draft';draft.color='#000000';draft.properties={composition:[{material_id:'ABS',fraction:1}]};
 assert.equal(original.name,'PLA');assert.equal(original.color,'#6daba3');assert.deepEqual(original.properties,{});
});
