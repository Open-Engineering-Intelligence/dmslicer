# Task 1–3 test record

`goal_id`: `WORKBENCH-MATERIAL-SEMANTIC-UI-01`  
`implementation_commit`: recorded by the follow-on commit  
`evidence_confidence`: `L` for commands and browser execution; `CHAT` for the reference-page audit.

## Preserved RED cases

- `node --test tests/workspace_annotations.test.cjs` initially failed because `materialDraft` did not exist (`TypeError: W.materialDraft is not a function`). The output remains in `work/09b-task2-model-red.txt` as temporary process material.
- `node tests/material_semantic_preview_browser.cjs` against the old 56811 service failed with `09B preview has no geometry canvas`, actual canvas count `1`. The output remains in `work/09b-task2-ui-red.txt` as temporary process material.

## GREEN commands

- `node --test tests/workspace_annotations.test.cjs`: 14 passed, 0 failed.
- `DMS_WORKBENCH_URL=http://127.0.0.1:56811/ node tests/material_semantic_preview_browser.cjs`: exit 0. The check loads CASE01, asserts zero canvases, selects objects, exercises Source/Gradient conditional controls, material-dialog return to assignment, and confirmed reset.
- `GET http://127.0.0.1:56811/samples`: five frozen sample entries returned.

The browser run tests annotation UI only. It makes no geometry-equivalence, CAD, STEP/B-rep, or field-activation claim.
