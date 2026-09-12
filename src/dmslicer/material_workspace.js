// UI controller for separate, human-authored domain annotations and material library.
let annotation=null,annotationDirty=false,libraryDirty=false,returnRef=null,libraryState=WorkspaceAnnotations.library();
const libraryKey='dmslicer.material-library.v1';
function note(text){$('annotation-status').textContent=text;$('library-status').textContent=text}
function refreshAnnotationTrace(){
 $('annotation-trace').textContent=JSON.stringify(annotation?{...annotation,unsaved_changes:annotationDirty}: {state:'NO_CASE'},null,2);
}
function dirty(){annotationDirty=true;note('有未保存的配置修改');refreshAnnotationTrace();draw()}
function prepareAnnotation(c){
 let next=WorkspaceAnnotations.create(c,libraryState),message='未保存配置 · 本地缓存不是备份，请导出 JSON。';
 try{const text=localStorage.getItem(WorkspaceAnnotations.key(c));if(text){next=WorkspaceAnnotations.restore(c,text);message='已恢复此浏览器保存的配置；仅人工注释，未激活。'}}
 catch(e){message='配置读取失败：'+e.message+'。原保存内容未覆盖；当前使用未分配默认值。'}
 annotation=next;annotationDirty=false;note(message);renderAnnotations();renderLibrary();refreshAnnotationTrace();
}
function setTab(name){
 const geometry=name==='geometry';$('viewport').hidden=!geometry||$('mode').value==='evidence';$('inspector').hidden=!geometry;
 $('annotations-panel').hidden=name!=='annotations';$('library-panel').hidden=name!=='library';
 $('workspace').classList.toggle('form-mode',!geometry);$('geometry-toolbar').hidden=!geometry;
 for(const b of document.querySelectorAll('[role="tab"]')){b.setAttribute('aria-selected',String(b.dataset.tab===name));b.tabIndex=b.dataset.tab===name?0:-1}
 if(geometry)requestAnimationFrame(fit);
}
function make(tag,text,className){const e=document.createElement(tag);if(text!==undefined)e.textContent=text;if(className)e.className=className;return e}
function choice(values,value,className,label){const s=make('select',undefined,className);s.setAttribute('aria-label',label);for(const [v,label] of values){const o=make('option',label);o.value=v;s.append(o)}s.value=value;return s}
function renderAnnotations(){
 $('annotation-rows').replaceChildren();$('annotation-empty').hidden=entities.length>0;
 for(const e of entities){
  const record=annotation?.objects.find(o=>o.entity_ref===e.entity_ref),o=record?.geometry_role==='Input'?record:null,row=make('article',undefined,'annotation-row');row.dataset.ref=e.entity_ref;
  const identity=make('div',undefined,'annotation-identity');identity.append(make('strong',e.display_name),make('span',WorkspaceAnnotations.geometryRole(e)+' · Geometry role（只读）','muted'));
  const semantic=choice(WorkspaceAnnotations.roles.map(r=>[r,r]),o?.semantic_role||'Unassigned','semantic-role','Semantic role · '+e.display_name);
  semantic.disabled=!o;semantic.onchange=()=>{WorkspaceAnnotations.decide(annotation,e.entity_ref,'semantic_role',semantic.value);dirty()};
  const material=choice([['','未分配'],...annotation.material_library.materials.map(m=>[m.id,m.name])],o?.material_id||'','material-assignment','Material assignment · '+e.display_name);
  material.disabled=!o;material.onchange=()=>{WorkspaceAnnotations.decide(annotation,e.entity_ref,'material_id',material.value||null);dirty();renderAnnotations()};
  const add=make('button','添加材料');add.disabled=!o;add.onclick=()=>{returnRef=e.entity_ref;clearMaterialForm();setTab('library');$('material-id').focus()};
  const displayColor=make('input',undefined,'display-color');displayColor.type='color';displayColor.value=WorkspaceAnnotations.color(annotation,e.entity_ref);displayColor.disabled=!o?.display_override;displayColor.setAttribute('aria-label','Display color · '+e.display_name);
  displayColor.oninput=()=>{WorkspaceAnnotations.decide(annotation,e.entity_ref,'display_override',displayColor.value);dirty()};
  const enabled=make('input',undefined,'override-enabled');enabled.type='checkbox';enabled.checked=!!o?.display_override;enabled.disabled=!o;enabled.setAttribute('aria-label','显示覆盖 · '+e.display_name);
  enabled.onchange=()=>{WorkspaceAnnotations.decide(annotation,e.entity_ref,'display_override',enabled.checked?displayColor.value:null);dirty();renderAnnotations()};
  const colorLabel=make('label');colorLabel.append(enabled,document.createTextNode(' 显示覆盖'));const colorBox=make('div');colorBox.append(colorLabel,displayColor,make('span',o?.display_override?'已记录覆盖色':'默认材料色；未分配为中性灰','muted'));
  const semanticBox=make('label','Semantic role');semanticBox.append(semantic,make('span','人工配置 · 未激活','muted'));
  const materialBox=make('div');materialBox.append(make('label','Material assignment'),material,add);
  row.append(identity,semanticBox,materialBox,colorBox);
  if(!o)row.append(make('p',record?'派生几何只读；09B 仅配置输入 block/region。':'此对象只有运行内诊断引用，缺少稳定引用；领域配置不可用。','muted'));
  $('annotation-rows').append(row);
 }
 for(const id of ['save-workspace','export-workspace','import-workspace'])$(id).disabled=!annotation;
}
function activeLibrary(){return annotation?annotation.material_library:libraryState}
function clearMaterialForm(){for(const id of ['material-id','material-name','material-description'])$(id).value='';$('material-id').readOnly=false;$('material-color').value='#498b92';$('material-properties').value='{}'}
function renderLibrary(){
 const l=activeLibrary();$('library-version').textContent='材料库版本 '+l.version+' · '+l.materials.length+' 项';$('material-list').replaceChildren();
 for(const m of l.materials){const b=make('button',m.name+' · '+m.id);b.onclick=()=>{$('material-id').value=m.id;$('material-id').readOnly=true;$('material-name').value=m.name;$('material-color').value=m.color;$('material-description').value=m.description;$('material-properties').value=JSON.stringify(m.properties,null,2);$('material-name').focus()};$('material-list').append(b)}
 $('return-object').hidden=!returnRef;
}
function returnToObject(){setTab('annotations');const row=[...document.querySelectorAll('.annotation-row')].find(row=>row.dataset.ref===returnRef);row?.scrollIntoView({block:'center'});row?.querySelector('select')?.focus();returnRef=null}
function downloadJSON(value,name){const a=document.createElement('a'),url=URL.createObjectURL(new Blob([JSON.stringify(value,null,2)],{type:'application/json'}));a.href=url;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000)}
function initializeMaterialUI(){
 try{const text=localStorage.getItem(libraryKey);if(text){const value=JSON.parse(text);WorkspaceAnnotations.validateLibrary(value);libraryState=value}}
 catch(e){note('材料库读取失败：'+e.message+'。旧存储内容保留。')}
 for(const b of document.querySelectorAll('[role="tab"]')){
  b.onclick=()=>setTab(b.dataset.tab);
  b.onkeydown=e=>{const tabs=[...document.querySelectorAll('[role="tab"]')],i=tabs.indexOf(b);if(['ArrowLeft','ArrowRight','Home','End'].includes(e.key)){e.preventDefault();const n=e.key==='Home'?0:e.key==='End'?tabs.length-1:(i+(e.key==='ArrowRight'?1:tabs.length-1))%tabs.length;tabs[n].click();tabs[n].focus()}};
 }
 $('material-form').onsubmit=e=>{e.preventDefault();try{
  const target=annotation||{material_library:libraryState};
  if(!$('material-id').readOnly&&target.material_library.materials.some(m=>m.id===$('material-id').value.trim()))throw Error('材料键已存在；请从材料列表选择编辑。');
  WorkspaceAnnotations.putMaterial(target,{id:$('material-id').value.trim(),name:$('material-name').value.trim(),color:$('material-color').value,description:$('material-description').value,properties:JSON.parse($('material-properties').value)});
  libraryDirty=true;if(annotation)dirty();renderAnnotations();renderLibrary();note('材料已更新到草稿；请保存材料库 / 工作区配置。');clearMaterialForm();if(returnRef)returnToObject();
 }catch(err){note('材料保存失败：'+err.message+'。原材料保留。')}};
 $('new-material').onclick=()=>{clearMaterialForm();$('material-id').focus()};$('return-object').onclick=returnToObject;
 $('save-library').onclick=()=>{try{const l=activeLibrary();WorkspaceAnnotations.validateLibrary(l);localStorage.setItem(libraryKey,JSON.stringify(l));libraryState=JSON.parse(JSON.stringify(l));libraryDirty=false;note('材料库已保存到此浏览器；可导出作为备份。')}catch(e){note('材料库保存失败：'+e.message+'。草稿保留。')}};
 $('export-library').onclick=()=>{try{WorkspaceAnnotations.validateLibrary(activeLibrary());downloadJSON(activeLibrary(),'materials.json');note('已发起材料库文件下载，请确认文件已落盘。')}catch(e){note('材料库导出失败：'+e.message)}};
 $('import-library').onchange=async e=>{try{
  const file=e.target.files[0];if(!file)return;if(file.size>4*1024*1024)throw Error('Library limit: 4 MiB');const text=await file.text();
  if(annotation){WorkspaceAnnotations.replaceLibrary(current,annotation,text);dirty()}
  else{const value=JSON.parse(text);WorkspaceAnnotations.validateLibrary(value);libraryState=value}
  libraryDirty=true;renderAnnotations();renderLibrary();note('已导入材料库草稿；请保存材料库，工作区引用仍需独立保存。');
 }catch(err){note('材料库导入失败：'+err.message+'。原材料库与配置保留。')}finally{e.target.value=''}};
 $('save-workspace').onclick=()=>{try{WorkspaceAnnotations.save(current,annotation,localStorage);annotationDirty=false;note('已保存配置到此浏览器 · '+annotation.saved_at);refreshAnnotationTrace()}catch(e){note('配置保存失败：'+e.message+'。草稿保留，旧保存内容未覆盖。')}};
 $('export-workspace').onclick=()=>{try{WorkspaceAnnotations.validate(current,annotation);const snapshot=JSON.parse(JSON.stringify(annotation));snapshot.saved_at=new Date().toISOString();downloadJSON(snapshot,'workspace.annotation.json');note('已发起配置文件下载，请确认文件已落盘；浏览器草稿保存状态未改变。')}catch(e){note('配置导出失败：'+e.message)}};
 $('import-workspace').onchange=async e=>{try{const file=e.target.files[0];if(!file)return;if(file.size>4*1024*1024)throw Error('Annotation limit: 4 MiB');const next=WorkspaceAnnotations.restore(current,await file.text());annotation=next;dirty();renderAnnotations();renderLibrary();note('已导入配置草稿；材料库快照仅用于此工作区，全局材料库未覆盖。')}catch(err){note('配置导入失败：'+err.message+'。当前配置保留。')}finally{e.target.value=''}};
 window.addEventListener('beforeunload',e=>{if(annotationDirty||libraryDirty){e.preventDefault();e.returnValue=''}});
 clearMaterialForm();renderAnnotations();renderLibrary();
}
