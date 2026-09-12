// Run against the loopback workbench. Browser plugin not available; bundled Playwright.
const {chromium}=require('playwright');
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
(async()=>{
 const output=path.resolve(process.env.DMS_BROWSER_OUTPUT),url=process.env.DMS_WORKBENCH_URL;
 fs.mkdirSync(output,{recursive:false});
 const browser=await chromium.launch({headless:true,channel:'chrome'});
 const page=await browser.newPage({viewport:{width:1500,height:1000},acceptDownloads:true});
 const errors=[],checks=[];
 page.on('pageerror',e=>errors.push(String(e)));page.on('console',m=>{if(m.type()==='error')errors.push(m.text())});
 await page.addInitScript(()=>{window.paint=[];const fill=CanvasRenderingContext2D.prototype.fill;CanvasRenderingContext2D.prototype.fill=function(...args){window.paint.push({alpha:this.globalAlpha,color:this.fillStyle});return fill.apply(this,args)}});
 async function check(name,fn){await fn();checks.push({name,status:'PASS'})}
 async function range(locator,value){await locator.fill(String(value));await locator.dispatchEvent('input')}
 async function sample(key){const label=await page.locator('#samples option[value="'+key+'"]').textContent();const response=page.waitForResponse(r=>r.url().endsWith('/package')&&r.request().method()==='POST');await page.locator('#samples').selectOption(key);await response;await page.locator('#status').filter({hasText:'已打开 '+label+'.dmslicer'}).waitFor()}
 try{
  await page.goto(url);await page.waitForFunction(()=>document.documentElement.dataset.ready==='true');
  await sample('case01');
  await check('page identity; existing geometry and evidence remain readable',async()=>{
   assert((await page.title()).includes('DM-Slicer'));assert.equal(page.url(),url);
   assert.equal(await page.locator('#controls .entity').count(),5);
   await page.locator('#mode').selectOption('evidence');assert((await page.locator('#contents').textContent()).includes('PRESENT_BYTE_CHECKED'));
   assert((await page.locator('#facts').textContent()).length>20);await page.locator('#mode').selectOption('overlay');
   await page.screenshot({path:path.join(output,'geometry.png')});
  });
  await check('material add returns to source row without assignment; role material color independent',async()=>{
   await page.getByRole('tab',{name:'材料与语义配置',exact:true}).click();
   const row=page.locator('.annotation-row').first();assert(await page.locator('.annotation-row').filter({hasText:'Patch · Geometry role'}).locator('.semantic-type').first().isDisabled());assert.equal(await row.locator('.semantic-type').inputValue(),'Unassigned');
   await row.getByRole('button',{name:'添加材料',exact:true}).click();
   await page.locator('#material-id').fill('test-polymer');await page.locator('#material-name').fill('Source 红材料');await page.locator('#material-color').fill('#112233');
   await page.locator('#material-description').fill('人工测试材料');await page.locator('#material-properties').fill('{"density":{"value":1.2,"unit":"g/cm3","source":"QA synthetic fixture","evidence":"TEST ONLY; no physical material claim"}}');
   await page.getByRole('button',{name:'保存材料',exact:true}).click();assert(await page.locator('#annotations-panel').isVisible());
   assert.equal(await row.locator('.material-assignment').inputValue(),'');await row.locator('.material-assignment').selectOption('test-polymer');
   assert.equal(await row.locator('.semantic-type').inputValue(),'Unassigned');assert.equal(await row.locator('.display-color').inputValue(),'#112233');
   await row.locator('.semantic-type').selectOption('Source');await row.locator('.override-enabled').check();await row.locator('.display-color').fill('#ff0000');await row.locator('.display-color').dispatchEvent('input');
   assert.equal(await row.locator('.material-assignment').inputValue(),'test-polymer');assert((await page.locator('#activation-state').textContent()).includes('未激活'));
   await page.screenshot({path:path.join(output,'annotations.png')});
   await page.getByRole('tab',{name:'几何查看',exact:true}).click();await page.evaluate(()=>window.paint=[]);await page.locator('#fit').click();
   assert((await page.evaluate(()=>window.paint)).some(p=>/^#[0-9a-f]{2}0000$/i.test(p.color)&&p.color!=='#000000'),'Display consumes red override by stable reference');
   await page.screenshot({path:path.join(output,'color-preview.png')});await page.getByRole('tab',{name:'材料与语义配置',exact:true}).click();
  });
  let exported;
  await check('explicit save and portable export preserve fields and decisions',async()=>{
   await page.locator('#save-workspace').click();assert((await page.locator('#annotation-status').textContent()).includes('已保存'));
   await page.getByRole('tab',{name:'材料库',exact:true}).click();await page.locator('#save-library').click();await page.getByRole('tab',{name:'材料与语义配置',exact:true}).click();
   const promise=page.waitForEvent('download');await page.locator('#export-workspace').click();const download=await promise;exported=path.join(output,'workspace.annotation.json');await download.saveAs(exported);
   const w=JSON.parse(fs.readFileSync(exported));assert.equal(w.objects[0].semantic_type,'Source');assert.equal(w.objects[0].material_id,'test-polymer');assert.equal(w.objects[0].display_override,'#ff0000');assert.equal(w.activation.InterfaceSourceBoundary,false);assert(w.decisions.length>=3);assert.equal(w.material_library.version,1);
   await page.reload();await page.waitForFunction(()=>document.documentElement.dataset.ready==='true');await sample('case01');await page.getByRole('tab',{name:'材料与语义配置',exact:true}).click();assert.equal(await page.locator('.semantic-type').first().inputValue(),'Source');
  });
  await check('save failure retains draft and recovery; imported data source checked',async()=>{
   await page.locator('.semantic-type').first().selectOption('Isolator');
   await page.evaluate(()=>{window.realSet=Storage.prototype.setItem;Storage.prototype.setItem=function(){throw Error('QA quota failure')}});
   await page.locator('#save-workspace').click();assert((await page.locator('#annotation-status').textContent()).includes('失败'));assert.equal(await page.locator('.semantic-type').first().inputValue(),'Isolator');
   await page.screenshot({path:path.join(output,'save-failure.png')});await page.evaluate(()=>Storage.prototype.setItem=window.realSet);
   await page.locator('#save-workspace').click();assert((await page.locator('#annotation-status').textContent()).includes('已保存'));
   await page.locator('#import-workspace').setInputFiles(exported);await page.locator('#annotation-status').filter({hasText:'已导入'}).waitFor();assert.equal(await page.locator('.semantic-type').first().inputValue(),'Source');await page.locator('#save-workspace').click();
   await sample('c02');await page.locator('#import-workspace').setInputFiles(exported);await page.locator('#annotation-status').filter({hasText:'导入失败'}).waitFor();assert((await page.locator('#annotation-status').textContent()).includes('失败'));assert.equal(await page.locator('.semantic-type').first().inputValue(),'Unassigned');
  });
  await check('five source packages and narrow layout remain readable',async()=>{
   for(const key of ['case01','c02','u05','s04','pmulti']){
    await sample(key);await page.getByRole('tab',{name:'几何查看',exact:true}).click();await page.locator('#mode').selectOption('comparison');assert(Number(await page.locator('#scene').getAttribute('data-panel-count'))>=5);
   }
   await page.setViewportSize({width:760,height:1050});await page.screenshot({path:path.join(output,'narrow.png')});
   assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));await page.getByRole('tab',{name:'材料库',exact:true}).click();assert(await page.locator('#material-form').isVisible());
   await page.screenshot({path:path.join(output,'library-narrow.png')});assert.deepEqual(errors,[]);
  });
  await check('library edits retain key and assignments; duplicate add rejected; keyboard tabs reachable',async()=>{
   await sample('case01');await page.getByRole('tab',{name:'材料与语义配置',exact:true}).click();
   await page.locator('.override-enabled').first().uncheck();await page.getByRole('tab',{name:'材料库',exact:true}).click();
   await page.locator('#material-list button').filter({hasText:'test-polymer'}).click();assert(await page.locator('#material-id').getAttribute('readonly')!==null);
   await page.locator('#material-name').fill('聚合物 A（编辑）');await page.locator('#material-color').fill('#336699');await page.locator('#material-description').fill('修订说明');await page.locator('#material-properties').fill('{"density":{"value":1.3,"unit":"g/cm3","source":"QA synthetic fixture","evidence":"TEST ONLY; no physical material claim"}}');
   await page.getByRole('button',{name:'保存材料',exact:true}).click();
   await page.getByRole('tab',{name:'材料与语义配置',exact:true}).click();
   assert.equal(await page.locator('.material-assignment').first().inputValue(),'test-polymer');assert.equal(await page.locator('.semantic-type').first().inputValue(),'Source');assert.equal(await page.locator('.display-color').first().inputValue(),'#336699');
   await page.getByRole('tab',{name:'材料库',exact:true}).click();await page.locator('#new-material').click();await page.locator('#material-id').fill('test-polymer');await page.locator('#material-name').fill('不应覆盖');await page.getByRole('button',{name:'保存材料',exact:true}).click();
   assert((await page.locator('#library-status').textContent()).includes('已存在'));
   await page.locator('#new-material').click();await page.locator('#material-id').fill('bad-json');await page.locator('#material-name').fill('坏属性');await page.locator('#material-properties').fill('[]');await page.getByRole('button',{name:'保存材料',exact:true}).click();assert((await page.locator('#library-status').textContent()).includes('失败'));assert.equal(await page.locator('#material-list button').count(),5);
   await page.locator('#save-library').click();await page.getByRole('tab',{name:'材料与语义配置',exact:true}).click();await page.locator('#save-workspace').click();
   await page.getByRole('tab',{name:'材料与语义配置',exact:true}).focus();await page.keyboard.press('ArrowRight');assert(await page.locator('#library-panel').isVisible());
  });
  await check('standalone library export/import validates before replacing domain snapshot',async()=>{
   const promise=page.waitForEvent('download');await page.locator('#export-library').click();const d=await promise,filename=path.join(output,'materials.json');await d.saveAs(filename);
   const lib=JSON.parse(fs.readFileSync(filename));assert.equal(lib.version,2);assert.equal(lib.materials.find(m=>m.id==='test-polymer').name,'聚合物 A（编辑）');assert.equal(lib.materials.find(m=>m.id==='test-polymer').properties.density.value,1.3);
   await page.locator('#import-library').setInputFiles(filename);await page.locator('#library-status').filter({hasText:'已导入材料库'}).waitFor();
   const invalid=path.join(output,'invalid-library.json');fs.writeFileSync(invalid,JSON.stringify({...lib,materials:[]}));
   await page.locator('#import-library').setInputFiles(invalid);await page.locator('#library-status').filter({hasText:'导入失败'}).waitFor();assert.equal(await page.locator('#material-list button').count(),5);
   await page.locator('#save-library').click();await page.getByRole('tab',{name:'材料与语义配置',exact:true}).click();await page.locator('#save-workspace').click();
   await page.setViewportSize({width:390,height:844});await page.screenshot({path:path.join(output,'annotations-mobile.png')});assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
   await page.setViewportSize({width:1500,height:1000});await page.screenshot({path:path.join(output,'annotations-final.png')});assert.deepEqual(errors,[]);
  });
  await check('Source required material, Gradient group isolation, Isolator owner and v1 rejection',async()=>{
   const rows=page.locator('.annotation-row');await rows.nth(1).locator('.semantic-type').selectOption('Source');await page.locator('#save-workspace').click();assert((await page.locator('#annotation-status').textContent()).includes('Source requires material'));
   await rows.nth(1).locator('.material-assignment').selectOption('PLA');await rows.nth(1).locator('.semantic-type').selectOption('Gradient');assert(await rows.nth(1).locator('.material-assignment').isDisabled());assert.equal(await rows.nth(1).locator('.material-assignment').inputValue(),'');
   assert.equal(await rows.nth(1).locator('.gradient-group').inputValue(),'G');await rows.nth(1).locator('.gradient-group').fill('G1');await rows.nth(1).locator('.gradient-group').dispatchEvent('change');
   await rows.nth(2).locator('.semantic-type').selectOption('Gradient');await rows.nth(2).locator('.gradient-group').fill('G2');await rows.nth(2).locator('.gradient-group').dispatchEvent('change');
   await page.locator('#save-workspace').click();const promise=page.waitForEvent('download');await page.locator('#export-workspace').click();const download=await promise,typed=path.join(output,'typed-groups.annotation.json');await download.saveAs(typed);const v=JSON.parse(fs.readFileSync(typed));
   assert.equal(v.schema,'dmslicer.workspace-annotation.v2');assert.equal(v.objects[1].gradient_group_id,'G1');assert.equal(v.objects[2].gradient_group_id,'G2');assert.equal(v.objects[1].material_id,null);assert.deepEqual(v.active_relations,[]);
   await page.screenshot({path:path.join(output,'semantic-types-groups.png')});
   await rows.nth(1).locator('.semantic-type').selectOption('Isolator');await rows.nth(2).locator('.semantic-type').selectOption('Isolator');await page.locator('#save-workspace').click();
   const isoPromise=page.waitForEvent('download');await page.locator('#export-workspace').click();const isoDownload=await isoPromise,isoPath=path.join(output,'isolators.annotation.json');await isoDownload.saveAs(isoPath);const iso=JSON.parse(fs.readFileSync(isoPath));assert.equal(iso.isolator_material_requirement,'UNDECIDED');assert.notEqual(iso.objects[1].isolator_instance.owner_entity_ref,iso.objects[2].isolator_instance.owner_entity_ref);assert.equal(iso.objects[1].isolator_instance.name,iso.objects[2].isolator_instance.name);
   const old=path.join(output,'legacy-v1.json');fs.writeFileSync(old,JSON.stringify({...iso,schema:'dmslicer.workspace-annotation.v1'}));await page.locator('#import-workspace').setInputFiles(old);await page.locator('#annotation-status').filter({hasText:'v1'}).waitFor();assert.equal(await rows.nth(1).locator('.semantic-type').inputValue(),'Isolator');
   await page.locator('#import-workspace').setInputFiles(typed);await page.locator('#annotation-status').filter({hasText:'已导入'}).waitFor();await page.locator('#save-workspace').click();assert.equal(await rows.nth(1).locator('.gradient-group').inputValue(),'G1');
  });
  await check('import cannot silently discard unsaved annotation or library draft',async()=>{
   await page.locator('.gradient-group').first().fill('G3');await page.locator('.gradient-group').first().dispatchEvent('change');
   await page.locator('#import-workspace').setInputFiles(exported);await page.locator('#annotation-status').filter({hasText:'未保存'}).waitFor();assert.equal(await page.locator('.gradient-group').first().inputValue(),'G3');await page.locator('#save-workspace').click();
   await page.getByRole('tab',{name:'材料库',exact:true}).click();await page.locator('#material-list button').filter({hasText:'test-polymer'}).click();await page.locator('#material-name').fill('保留未保存材料');await page.getByRole('button',{name:'保存材料',exact:true}).click();
   await page.locator('#import-library').setInputFiles(path.join(output,'materials.json'));await page.locator('#library-status').filter({hasText:'未保存'}).waitFor();assert((await page.locator('#material-list').textContent()).includes('保留未保存材料'));
   await page.locator('#save-library').click();await page.getByRole('tab',{name:'材料与语义配置',exact:true}).click();await page.locator('#save-workspace').click();
  });
  await check('deferred annotation read cannot attach to a subsequently opened case',async()=>{
   await page.evaluate(()=>{window.originalText=File.prototype.text;File.prototype.text=function(){const file=this;return new Promise(resolve=>{window.completeImport=()=>window.originalText.call(file).then(resolve)})}});
   await page.locator('#import-workspace').setInputFiles(exported);await sample('c02');await page.evaluate(()=>window.completeImport());
   await page.locator('#annotation-status').filter({hasText:'导入失败'}).waitFor();assert(await page.locator('.semantic-type').first().isDisabled());assert.equal(await page.locator('#controls .entity').count(),6);
   await page.evaluate(()=>File.prototype.text=window.originalText);await sample('case01');
  });
  await check('package response cannot replace an annotation edited during upload',async()=>{
   let release,started;const waiting=new Promise(resolve=>started=resolve),gate=new Promise(resolve=>release=resolve);
   await page.route('**/package',async route=>{const response=await route.fetch();started();await gate;await route.fulfill({response})},{times:1});
   await page.locator('#samples').selectOption('c02');await waiting;await page.locator('.semantic-type').first().selectOption('Isolator');release();
   await page.locator('#status').filter({hasText:'状态已变化'}).waitFor();assert.equal(await page.locator('#controls .entity').count(),5);assert.equal(await page.locator('.semantic-type').first().inputValue(),'Isolator');await page.locator('#save-workspace').click();
  });
  await check('missing annotation provenance degrades to read-only without breaking geometry viewer',async()=>{
   const fixture={schema:'dmslicer.display-catalog.v1',cases:[{case_id:'ui-provenance-fixture',label:'Synthetic UI boundary fixture',provenance:{},scene:{kind:'DISPLAY_ONLY_BREP_TESSELLATION',entities:[{entity_ref:'fixture-input-a',display_name:'Synthetic input',entity_kind:'REGION',scene_role:'input',identity_status:'STABLE_REFERENCE',reference_provenance:{},mesh:{provenance:'BREP_TESSELLATION',linear_deflection_mm:.25,positions:[[0,0,0],[1,0,0],[0,1,0]],triangles:[[0,1,2]]}}]}}]};
   await page.route('**/package',route=>route.fulfill({json:fixture}),{times:1});await sample('case01');
   assert(await page.locator('.semantic-type').first().isDisabled());assert(await page.locator('#save-workspace').isDisabled());assert((await page.locator('#annotation-status').textContent()).includes('不可用'));
   await page.getByRole('tab',{name:'几何查看',exact:true}).click();assert.equal(await page.locator('#controls .entity').count(),1);assert.deepEqual(errors,[]);
  });
  fs.writeFileSync(path.join(output,'checks.json'),JSON.stringify({status:'PASS',url,viewports:[[1500,1000],[760,1050],[390,844]],browser:'Playwright Chrome; Browser plugin not available',checks,errors,human_review:'PENDING'},null,2));
  console.log('PASS: material workspace browser acceptance');
 }catch(e){await page.screenshot({path:path.join(output,'failure.png')});fs.writeFileSync(path.join(output,'checks.json'),JSON.stringify({status:'FAIL',checks,errors,failure:String(e),stack:e.stack},null,2));throw e}
 finally{await browser.close()}
})().catch(e=>{console.error(e);process.exit(1)});
