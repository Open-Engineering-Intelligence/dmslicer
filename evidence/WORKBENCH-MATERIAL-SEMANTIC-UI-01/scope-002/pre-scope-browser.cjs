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
 await page.addInitScript(()=>{window.paint=[];const fill=CanvasRenderingContext2D.prototype.fill;CanvasRenderingContext2D.prototype.fill=function(...args){window.paint.push(this.globalAlpha);return fill.apply(this,args)}});
 async function check(name,fn){await fn();checks.push({name,status:'PASS'})}
 async function range(locator,value){await locator.fill(String(value));await locator.dispatchEvent('input')}
 async function sample(key){await page.locator('#samples').selectOption(key);await page.locator('#status').filter({hasText:'已打开'}).waitFor()}
 try{
  await page.goto(url);await page.waitForFunction(()=>document.documentElement.dataset.ready==='true');
  await sample('c02');
  await check('page identity and default selection',async()=>{
   assert((await page.title()).includes('DM-Slicer'));assert.equal(page.url(),url);
   const n=await page.locator('.entity').count();assert(n>=5);
   assert.equal(await page.locator('.entity .select-object:checked').count(),n);
   assert.equal(await page.locator('#evidence-drawer').getAttribute('open'),null);
  });
  await check('empty selection disables batch; inversion scopes Canvas alpha and individual ranges',async()=>{
   await page.getByRole('button',{name:'全不选',exact:true}).click();assert(await page.locator('#opacity').isDisabled());
   await page.locator('.select-object').first().check();await range(page.locator('#opacity'),65);
   assert.equal(await page.locator('.entity-opacity').first().inputValue(),'65');assert.equal(await page.locator('.entity-opacity').nth(1).inputValue(),'0');
   await page.getByRole('button',{name:'反选',exact:true}).click();await range(page.locator('#opacity'),20);
   assert.equal(await page.locator('.entity-opacity').first().inputValue(),'65');assert.equal(await page.locator('.entity-opacity').nth(1).inputValue(),'20');
   await page.getByRole('button',{name:'隐藏所选',exact:true}).click();assert(await page.locator('.visibility').first().isChecked());assert.equal(await page.locator('.visibility:checked').count(),1);
   await page.getByRole('button',{name:'显示所选',exact:true}).click();await page.getByRole('button',{name:'全选',exact:true}).click();assert((await page.locator('#opacity-state').textContent()).includes('混合'));
   await range(page.locator('.entity-opacity').first(),35);assert.equal(await page.locator('.entity-opacity').nth(1).inputValue(),'20');
   await page.evaluate(()=>window.paint=[]);await range(page.locator('#opacity'),40);
   const alphas=await page.evaluate(()=>window.paint);assert(alphas.length>0);assert(alphas.every(x=>Math.abs(x-.6)<1e-6));
   await page.locator('#filter').fill('不存在');assert((await page.locator('#selection-summary').textContent()).includes('6 / 6'));assert.equal(await page.locator('.entity').count(),0);
   await page.locator('#filter').fill('');
  });
  await check('interface and patch independent; one collapsed evidence drawer',async()=>{
   const i=page.locator('.entity[data-kind="INTERFACE"]'),p=page.locator('.entity[data-kind="PATCH"]');assert(await i.count());assert(await p.count());
   await i.locator('.select-object').uncheck();assert(await p.locator('.select-object').first().isChecked());
   await i.locator('.visibility').uncheck();assert(await p.locator('.visibility').first().isChecked());
   await page.locator('.object-focus').first().click();assert.equal(await page.locator('.select-object:checked').count(),1);
   assert.equal(await page.locator('#evidence-drawer').getAttribute('open'),null);
   await page.locator('#evidence-drawer summary').click();assert((await page.locator('#trace').textContent()).includes('entity_ref'));
   assert((await page.locator('#contents').textContent()).includes('PRESENT_BYTE_CHECKED'));assert((await page.locator('#facts').textContent()).length>20);
   await page.locator('#evidence-drawer summary').click();await page.screenshot({path:path.join(output,'geometry.png')});
  });
  await check('material add returns to source row without assignment; role material color independent',async()=>{
   await page.getByRole('tab',{name:'材料与语义配置',exact:true}).click();
   const row=page.locator('.annotation-row').first();assert.equal(await row.locator('.semantic-role').inputValue(),'Unassigned');
   await row.getByRole('button',{name:'添加材料',exact:true}).click();
   await page.locator('#material-id').fill('test-polymer');await page.locator('#material-name').fill('Source 红材料');await page.locator('#material-color').fill('#112233');
   await page.locator('#material-description').fill('人工测试材料');await page.locator('#material-properties').fill('{"density":{"value":1.2,"unit":"g/cm3"}}');
   await page.getByRole('button',{name:'保存材料',exact:true}).click();assert(await page.locator('#annotations-panel').isVisible());
   assert.equal(await row.locator('.material-assignment').inputValue(),'');await row.locator('.material-assignment').selectOption('test-polymer');
   assert.equal(await row.locator('.semantic-role').inputValue(),'Unassigned');assert.equal(await row.locator('.display-color').inputValue(),'#112233');
   await row.locator('.semantic-role').selectOption('Gradient');await row.locator('.override-enabled').check();await row.locator('.display-color').fill('#ff0000');await row.locator('.display-color').dispatchEvent('input');
   assert.equal(await row.locator('.material-assignment').inputValue(),'test-polymer');assert((await page.locator('#activation-state').textContent()).includes('未激活'));
   await page.screenshot({path:path.join(output,'annotations.png')});
  });
  let exported;
  await check('explicit save and portable export preserve fields and decisions',async()=>{
   await page.locator('#save-workspace').click();assert((await page.locator('#annotation-status').textContent()).includes('已保存'));
   const promise=page.waitForEvent('download');await page.locator('#export-workspace').click();const download=await promise;exported=path.join(output,'workspace.annotation.json');await download.saveAs(exported);
   const w=JSON.parse(fs.readFileSync(exported));assert.equal(w.objects[0].semantic_role,'Gradient');assert.equal(w.objects[0].material_id,'test-polymer');assert.equal(w.objects[0].display_override,'#ff0000');assert.equal(w.activation.InterfaceSourceBoundary,false);assert(w.decisions.length>=3);assert.equal(w.material_library.version,1);
   await page.reload();await page.waitForFunction(()=>document.documentElement.dataset.ready==='true');await sample('c02');await page.getByRole('tab',{name:'材料与语义配置',exact:true}).click();assert.equal(await page.locator('.semantic-role').first().inputValue(),'Gradient');
  });
  await check('save failure retains draft and recovery; imported data source checked',async()=>{
   await page.locator('.semantic-role').first().selectOption('Source');
   await page.evaluate(()=>{window.realSet=Storage.prototype.setItem;Storage.prototype.setItem=function(){throw Error('QA quota failure')}});
   await page.locator('#save-workspace').click();assert((await page.locator('#annotation-status').textContent()).includes('失败'));assert.equal(await page.locator('.semantic-role').first().inputValue(),'Source');
   await page.screenshot({path:path.join(output,'save-failure.png')});await page.evaluate(()=>Storage.prototype.setItem=window.realSet);
   await page.locator('#save-workspace').click();assert((await page.locator('#annotation-status').textContent()).includes('已保存'));
   await page.locator('#import-workspace').setInputFiles(exported);assert.equal(await page.locator('.semantic-role').first().inputValue(),'Gradient');await page.locator('#save-workspace').click();
   await sample('case01');await page.locator('#import-workspace').setInputFiles(exported);assert((await page.locator('#annotation-status').textContent()).includes('失败'));assert.equal(await page.locator('.semantic-role').first().inputValue(),'Unassigned');
  });
  await check('five source packages and narrow layout remain readable',async()=>{
   for(const key of ['case01','c02','u05','s04','pmulti']){
    await sample(key);await page.getByRole('tab',{name:'几何查看',exact:true}).click();await page.locator('#mode').selectOption('comparison');assert(Number(await page.locator('#scene').getAttribute('data-panel-count'))>=5);
   }
   await page.setViewportSize({width:760,height:1050});await page.screenshot({path:path.join(output,'narrow.png')});
   assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));await page.getByRole('tab',{name:'材料库',exact:true}).click();assert(await page.locator('#material-form').isVisible());
   await page.screenshot({path:path.join(output,'library-narrow.png')});assert.deepEqual(errors,[]);
  });
  fs.writeFileSync(path.join(output,'checks.json'),JSON.stringify({status:'PASS',url,viewports:[[1500,1000],[760,1050]],browser:'Playwright Chrome; Browser plugin not available',checks,errors,human_review:'PENDING'},null,2));
  console.log('PASS: material workspace browser acceptance');
 }catch(e){await page.screenshot({path:path.join(output,'failure.png')});fs.writeFileSync(path.join(output,'checks.json'),JSON.stringify({status:'FAIL',checks,errors,failure:String(e),stack:e.stack},null,2));throw e}
 finally{await browser.close()}
})().catch(e=>{console.error(e);process.exit(1)});
