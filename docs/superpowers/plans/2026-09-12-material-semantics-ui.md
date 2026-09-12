# Material and Semantics UI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a material-library and object semantic-assignment workflow to the 56810 DM-Slicer workbench while retaining its existing `.dmslicer` geometry viewer.

**Architecture:** Reuse `workspace_annotations.js` as the domain model. Refactor the 09B controller into an explicit object-selection table and two dialogs, then mount that controller as the peer Material and semantics page in the 56810 shell. The geometry page remains the sole owner of package import, canvas, camera, picking, and geometry evidence.

**Tech Stack:** Static HTML/CSS/JavaScript, CommonJS-compatible domain module, Python package server, Node test runner, browser acceptance script.

**Spec:** `docs/superpowers/specs/2026-09-12-material-semantics-ui-design.md`

## Global Constraints

- Consume `.dmslicer` packages; do not add an AMF import path.
- Do not copy or depend on PyVista or the reference application's renderer.
- STEP/B-rep remains geometry authority and display mesh remains display-only.
- Preserve the protected 56810 baseline branch `codex/09a-56810-stable-baseline`.
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

### Task 4: Integrate the peer page into the protected 56810 workbench

**Files:**
- Modify: `src/dmslicer/geometry_import_viewer.html`
- Add or modify: `src/dmslicer/material_workspace.js`
- Add or modify: `src/dmslicer/workspace_annotations.js`
- Modify: `tests/test_unified_workbench.py`
- Modify: `tests/geometry_view_ui_browser.cjs`
- Modify: `tests/material_workspace_browser.cjs`

**Interfaces:**
- Consumes: active `current` case, `entities`, `selected`, `WorkspaceAnnotations`, and the Task 2/3 UI controller.
- Produces: peer pages `geometry` and `materials`, a shared dirty-state guard, and a single 56810 user entry point.

- [ ] **Step 1: Add failing integration checks**

```python
def test_material_page_reuses_geometry_context(viewer_html):
    assert 'data-page="geometry"' in viewer_html
    assert 'data-page="materials"' in viewer_html
    assert viewer_html.count('id="scene"') == 1
    assert '.AMF' not in viewer_html
    assert 'PyVista' not in viewer_html
```

Browser checks must open a sample, select a geometry object, switch pages, verify the same case/object appears in the object table, switch back, and verify camera/visibility state is unchanged.

- [ ] **Step 2: Run integration checks and confirm RED**

Run: `py -3.12 -m pytest tests/test_unified_workbench.py -q`

Run: `node tests/geometry_view_ui_browser.cjs`

- [ ] **Step 3: Add the shared shell and peer-page lifecycle**

Add top-level page controls for Geometry and Material and semantics. `openCase(c)` prepares annotation context once. Page switching only changes visibility/focus and never calls `openCase`, `fit`, or package fetch. Keep one `canvas#scene` in the geometry page.

- [ ] **Step 4: Apply material preview colors as display-only inputs**

Where a geometry entity has an annotation, call `WorkspaceAnnotations.color(annotation, entity_ref)` for preview fill. Do not write color into package data, geometry evidence, or persistent geometry identity.

- [ ] **Step 5: Run the full focused regression**

Run: `node --test tests/workspace_annotations.test.cjs`

Run: `py -3.12 -m pytest tests/test_geometry_case_viewer.py tests/test_result_package.py tests/test_geometry_import.py tests/test_case01_result_package.py tests/test_result_labels.py tests/test_unified_workbench.py -q`

Run: `node tests/geometry_view_ui_browser.cjs`

Run: `node tests/material_workspace_browser.cjs`

Expected: all checks PASS; browser inspection confirms one geometry canvas and two peer pages.

- [ ] **Step 6: Record evidence and commit**

Update the 09A/09B review index with commands, exit codes, screenshots, failure and fix commits, and the protected baseline. Keep geometry validation results separate from UI and browser results.

```powershell
git add src/dmslicer tests docs/implementation evidence
git commit -m "feat(workbench): integrate material semantics workflow"
```
