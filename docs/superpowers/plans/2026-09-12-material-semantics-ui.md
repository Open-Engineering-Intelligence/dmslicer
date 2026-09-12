# Material and Semantics UI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build and validate the 09B material-library and object semantic-assignment prototype while keeping the 56810 DM-Slicer workbench unchanged.

**Architecture:** Reuse `workspace_annotations.js` as the domain model. Refactor the 09B controller into an explicit object-selection table and two dialogs inside its own review surface. Treat 56810 only as a protected interaction reference; integration into 56810 is outside this plan.

**Tech Stack:** Static HTML/CSS/JavaScript, CommonJS-compatible domain module, Python package server, Node test runner, browser acceptance script.

**Spec:** `docs/superpowers/specs/2026-09-12-material-semantics-ui-design.md`

## Global Constraints

- Consume `.dmslicer` packages; do not add an AMF import path.
- Do not copy or depend on PyVista or the reference application's renderer.
- STEP/B-rep remains geometry authority and display mesh remains display-only.
- Preserve the protected 56810 baseline branch `codex/09a-56810-stable-baseline`.
- Do not modify the 56810 source, service, or 09A branch in this plan.
- Do not modify `docs/research_v2/`, push, merge, release, or publish.
- Only stable input object references may receive persistent annotation.

---

### Task 1: Dialog-safe material and assignment drafts

**Files:**
- Modify: `src/dmslicer/workspace_annotations.js`
- Test: `tests/workspace_annotations.test.cjs`

**Interfaces:**
- Consumes: `create(caseData, library)`, `decide(workspace, entityRef, field, value)`, `putMaterial(workspace, material)`.
- Produces: `applyAssignment(workspace, entityRefs, draft)` and `materialDraft(material)`; both mutate only after full validation.

- [ ] **Step 1: Write failing atomicity tests**

```js
test('multi-object assignment is atomic', () => {
  const c=fixture(), w=W.create(c), before=JSON.stringify(w);
  assert.throws(()=>W.applyAssignment(w,['input-a','missing'],{semantic_type:'Source',material_id:'PLA'}));
  assert.equal(JSON.stringify(w),before);
});

test('Gradient assignment clears material for every selected input', () => {
  const c=fixture(), w=W.create(c);
  W.applyAssignment(w,['input-a','input-b'],{semantic_type:'Gradient',gradient_group_id:'G2',material_id:null});
  assert.deepEqual(w.objects.slice(0,2).map(o=>[o.semantic_type,o.material_id,o.gradient_group_id]),
    [['Gradient',null,'G2'],['Gradient',null,'G2']]);
});
```

- [ ] **Step 2: Run the focused tests and confirm RED**

Run: `node --test tests/workspace_annotations.test.cjs`

Expected: FAIL because `applyAssignment` is absent.

- [ ] **Step 3: Implement clone-validate-commit assignment**

```js
function applyAssignment(w,refs,draft){
  require(Array.isArray(refs)&&refs.length>0,'Select at least one object');
  const candidate=copy(w);
  for(const ref of refs){
    require(candidate.objects.some(o=>o.entity_ref===ref),'Unknown stable object reference');
    decide(candidate,ref,'semantic_type',draft.semantic_type);
    if(draft.semantic_type==='Source')decide(candidate,ref,'material_id',draft.material_id);
    if(draft.semantic_type==='Gradient')decide(candidate,ref,'gradient_group_id',draft.gradient_group_id||'G');
    if('display_override' in draft)decide(candidate,ref,'display_override',draft.display_override);
  }
  Object.assign(w,candidate);
  return w;
}
```

- [ ] **Step 4: Run tests and confirm GREEN**

Run: `node --test tests/workspace_annotations.test.cjs`

Expected: all existing tests and the two new tests PASS.

- [ ] **Step 5: Commit the domain change**

```powershell
git add src/dmslicer/workspace_annotations.js tests/workspace_annotations.test.cjs
git commit -m "feat(09b): add atomic object assignment drafts"
```

### Task 2: Object selection and assignment dialog

**Files:**
- Modify: `src/dmslicer/material_workspace.js`
- Modify: `src/dmslicer/geometry_import_viewer.html`
- Test: `tests/material_workspace_browser.cjs`

**Interfaces:**
- Consumes: `WorkspaceAnnotations.applyAssignment(workspace, entityRefs, draft)` and the active case entities supplied by the viewer.
- Produces: `openAssignmentDialog(entityRefs)`, `closeAssignmentDialog(mode)`, and a table whose selection is independent from geometry visibility.

- [ ] **Step 1: Add browser assertions for selection and conditional fields**

```js
await page.locator('.object-select').first().check();
await page.getByRole('button',{name:'编辑材料与语义'}).click();
await page.getByRole('dialog',{name:'编辑材料与语义'}).waitFor();
await page.locator('#assignment-type').selectOption('Source');
assert(await page.locator('#assignment-material').isVisible());
await page.locator('#assignment-type').selectOption('Gradient');
assert(await page.locator('#assignment-group').isVisible());
assert(await page.locator('#assignment-material').isDisabled());
```

- [ ] **Step 2: Run the browser test and confirm RED**

Run: `node tests/material_workspace_browser.cjs`

Expected: FAIL because the object table and assignment dialog do not exist.

- [ ] **Step 3: Replace per-row editors with a selection table and native dialog**

Add an object table with `.object-select` checkboxes and one `编辑材料与语义` button. Add a native `<dialog id="assignment-dialog">` containing selected count, semantic type, conditional material/group fields, display override, Cancel, and Save. Non-input or unstable-reference rows remain visible and disabled with a reason.

- [ ] **Step 4: Wire Save through `applyAssignment` and preserve drafts on failure**

```js
$('assignment-form').onsubmit=e=>{
  e.preventDefault();
  try{
    WorkspaceAnnotations.applyAssignment(annotation,selectedObjectRefs(),readAssignmentDraft());
    dirty(); renderObjectTable(); $('assignment-dialog').close('saved');
  }catch(err){$('assignment-error').textContent=err.message;}
};
```

- [ ] **Step 5: Run model and browser checks**

Run: `node --test tests/workspace_annotations.test.cjs`

Run: `node tests/material_workspace_browser.cjs`

Expected: Source, Gradient, Isolator, Unassigned, one-object, multi-object, cancel, and failed-save cases PASS.

- [ ] **Step 6: Commit the object workflow**

```powershell
git add src/dmslicer/material_workspace.js src/dmslicer/geometry_import_viewer.html tests/material_workspace_browser.cjs
git commit -m "feat(09b): add object material semantics dialog"
```

### Task 3: Material library dialog and return flow

**Files:**
- Modify: `src/dmslicer/material_workspace.js`
- Modify: `src/dmslicer/geometry_import_viewer.html`
- Test: `tests/material_workspace_browser.cjs`

**Interfaces:**
- Consumes: `WorkspaceAnnotations.putMaterial(workspace, material)`.
- Produces: `openMaterialDialog(materialId, returnContext)`; new material creation returns to the unchanged assignment draft without auto-assignment.

- [ ] **Step 1: Add failing browser assertions**

```js
await page.getByRole('button',{name:'添加材料'}).click();
await page.getByRole('dialog',{name:'材料属性'}).waitFor();
await page.locator('#material-id').fill('custom-a');
await page.locator('#material-name').fill('Custom A');
await page.getByRole('button',{name:'保存材料'}).click();
assert(await page.getByRole('dialog',{name:'编辑材料与语义'}).isVisible());
assert.equal(await page.locator('#assignment-material').inputValue(),'');
```

- [ ] **Step 2: Run the browser test and confirm RED**

Run: `node tests/material_workspace_browser.cjs`

Expected: FAIL because the library still uses a persistent inline editor.

- [ ] **Step 3: Move add/edit fields into one material dialog**

The library page keeps the material table and one primary `添加材料` button. Row selection enables `编辑材料`. Both open `<dialog id="material-dialog">`. Saving validates through `putMaterial`; closing returns to the assignment dialog when `returnContext==='assignment'` and leaves its draft untouched.

- [ ] **Step 4: Verify add, edit, duplicate-id, invalid-property and return behavior**

Run: `node tests/material_workspace_browser.cjs`

Expected: all material library and assignment return checks PASS.

- [ ] **Step 5: Commit the library workflow**

```powershell
git add src/dmslicer/material_workspace.js src/dmslicer/geometry_import_viewer.html tests/material_workspace_browser.cjs
git commit -m "feat(09b): move material editing into dialog"
```

### Task 4: Verify the standalone 09B review surface

**Files:**
- Modify: `tests/material_workspace_browser.cjs`
- Modify: `docs/implementation/workbench_material_semantics.md`
- Modify: `evidence/WORKBENCH-MATERIAL-SEMANTIC-UI-01/final-001/VIEW_INDEX.md`

**Interfaces:**
- Consumes: the Task 2/3 09B controller and `.dmslicer` sample cases with stable object references.
- Produces: a reviewable 09B preview and evidence showing that 56810 was not modified.

- [ ] **Step 1: Add failing review-surface checks**

```js
assert.equal(await page.locator('canvas#scene').count(),0);
assert.equal(await page.getByText(/AMF|PyVista/).count(),0);
assert(await page.getByRole('button',{name:'编辑材料与语义'}).isVisible());
assert(await page.getByRole('button',{name:'添加材料'}).isVisible());
assert.equal(await page.getByLabel('Process').count(),0);
```

The browser check opens a sample, selects one and multiple stable input objects,
uses both dialogs, and verifies that invalid drafts do not mutate saved state.
It must also verify that Edit is non-destructive, completed objects remain
editable, reset preserves the active case, the material swatch opens a color
control, and composition state never inherits a previous property value.

- [ ] **Step 2: Run the review checks and confirm RED**

Run: `node tests/material_workspace_browser.cjs`

- [ ] **Step 3: Complete the 09B review layout**

Use the reference application's useful hierarchy—object selection, an explicit
edit action, and a separate material library—without reproducing its code or
renderer. Keep the object table and material library independently usable.

- [ ] **Step 4: Prove the 56810 baseline remains untouched**

Compare the 56810 viewer entry point with
`codex/09a-56810-stable-baseline` and record the result. Any difference created
by this Goal is a failure and must be reverted without moving the baseline.

- [ ] **Step 5: Run the full focused regression**

Run: `node --test tests/workspace_annotations.test.cjs`

Run: `node tests/material_workspace_browser.cjs`

Expected: all 09B checks PASS; browser inspection confirms the two dialogs and
no copied geometry viewer.

- [ ] **Step 6: Record evidence and commit**

Update the 09B review index with commands, exit codes, screenshots, failure and
fix commits, and the protected 56810 comparison. Keep geometry validation
results separate from UI and browser results.

```powershell
git add src/dmslicer tests docs/implementation evidence
git commit -m "feat(09b): complete material semantics review surface"
```
