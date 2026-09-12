const {chromium}=require('playwright');
const assert=require('node:assert/strict');
(async()=>{
 const browser=await chromium.launch({headless:true,channel:'chrome'}),page=await browser.newPage();
 try{
  await page.goto(process.env.DMS_WORKBENCH_URL||'http://127.0.0.1:56811/');
  await page.waitForFunction(()=>document.documentElement.dataset.ready==='true');
  await page.locator('#samples').selectOption('case01');
  assert.equal(await page.locator('canvas').count(),0,'09B preview has no geometry canvas');
  await page.locator('.object-select').first().check();
  await page.getByRole('button',{name:'编辑材料与语义'}).click();
  await page.getByRole('dialog',{name:'编辑材料与语义'}).waitFor();
  await page.locator('#assignment-type').selectOption('Source');
  assert(await page.locator('#assignment-material').isVisible());
  await page.locator('#assignment-material').selectOption('PLA');
  await page.locator('#assignment-type').selectOption('Gradient');
  assert(await page.locator('#assignment-group').isVisible());
  assert(await page.locator('#assignment-material').isDisabled());
  assert.equal(await page.locator('#assignment-material').inputValue(),'');
  await page.locator('#assignment-add').click();
  await page.getByRole('dialog',{name:'材料属性'}).waitFor();
  await page.locator('#material-id').fill('custom-a');
  await page.locator('#material-name').fill('Custom A');
  await page.locator('#material-color').fill('#123456');
  await page.getByRole('button',{name:'保存材料'}).click();
  assert(await page.getByRole('dialog',{name:'编辑材料与语义'}).isVisible());
  assert.equal(await page.locator('#assignment-material').inputValue(),'');
  await page.getByRole('button',{name:'取消'}).click();
  await page.getByRole('button',{name:'重置所选'}).click();
  await page.getByRole('button',{name:'确认重置'}).click();
 }finally{await browser.close();}
})().catch(error=>{console.error(error);process.exitCode=1});
