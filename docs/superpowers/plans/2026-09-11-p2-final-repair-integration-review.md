# P2 Final Repair & Integration Review Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Repair the two CAD promotion regressions, bind fresh FreeCAD Case A/B/reopen evidence to the final implementation commit, and reconcile the canonical P2 branch with PR #3 without expanding P2 scope.

**Architecture:** Preserve fail-closed promotion and immutable destinations. Align the per-artifact CAD evidence schema, allowlist kinds, and policy expectations; then commit executable logic before generating a new immutable evidence package. Keep byte, geometry, semantic, UI, pytest, validator, scientific, human-review, preservation, and publication results independent.

**Tech Stack:** Python 3.12, pytest 8.4.2, JSON Schema draft 2020-12, Git, GitHub CLI, FreeCADCmd 1.1.1, OCCT 7.8.1, PowerShell.

**Spec:** `C:/Users/ufo00/.codex/attachments/179d8ec1-a616-4db6-b975-92e19e8a7cf5/pasted-text-1.txt`

## Global Constraints

- Do not modify `docs/research_v2/` or start 07A/07B.
- Existing destination must refuse overwrite and leave source evidence untouched.
- SHA-256 records byte integrity only and never decides geometry equivalence.
- Every tolerance records an explicit value and unit.
- Commit executable fixes before generating final scientific evidence.
- Preserve the preliminary package and mark it preliminary/rejected without rewriting its historical claims.
- Run the inherited full suite once, only after targeted tests and real FreeCAD experiments pass.
- Do not rebase published history, force-push, merge PR #3, merge to main, delete evidence, or delete worktrees.

---

### Task 1: Repair the CAD promotion contract mismatch

**Files:**
- Modify: `tests/conftest.py`
- Modify: `docs/evidence_preservation/schemas/cad_evidence.schema.json`
- Modify: `tests/test_cad_evidence_schema.py`
- Test: `tests/test_promotion.py`

**Interfaces:**
- Consumes: per-artifact `artifact_type` values used by `policy._cad_evidence_findings`.
- Produces: schema-valid `geometry_semantic_snapshot`, `ui_state_snapshot`, and `geometry_comparison` artifacts with specialized allowlist kinds.

- [ ] **Step 1: Preserve the observed RED evidence**

```powershell
py -3.12 -m pytest tests/test_promotion.py::test_promotes_case_a_and_case_b_without_collapsing_results -vv
py -3.12 -m pytest tests/test_promotion.py::test_second_cad_promotion_refuses_overwrite -vv
```

Expected: first promotion is blocked by `CAD_EVIDENCE_SCHEMA_INVALID` and `RESULT_EVIDENCE_MISMATCH`, not by a pre-existing stable destination.

- [ ] **Step 2: Add direct schema regressions for each per-artifact envelope**

```python
validator.validate(_geometry_snapshot("original"))
validator.validate(_ui_snapshot("original", changed=False))
validator.validate(_geometry_comparison())
```

Also retain the existing missing-unit and SHA-as-geometry rejection tests.

- [ ] **Step 3: Verify the new schema tests fail for the contract mismatch**

```powershell
py -3.12 -m pytest tests/test_cad_evidence_schema.py -vv
```

- [ ] **Step 4: Apply the minimal contract repair**

Update the schema to accept the existing legacy aggregate shape and the three policy-consumed envelopes selected by `artifact_type`. Require `schema_version`, the discriminator, identity fields, measured value+unit objects, explicit tolerances, checks, reasons, and the safe SHA role for comparisons. In `valid_cad_request`, map kinds exactly as follows:

```python
{
    "case-a-comparison": "COMPARISON_JSON",
    "original-geometry-snapshot": "GEOMETRY_SNAPSHOT",
    "ui-geometry-snapshot": "GEOMETRY_SNAPSHOT",
    "original-ui-snapshot": "UI_SNAPSHOT",
    "ui-changed-snapshot": "UI_SNAPSHOT",
}
```

Set the appended Case B kind to `COMPARISON_JSON`.

- [ ] **Step 5: Verify the two original failures and all promotion tests are GREEN**

```powershell
py -3.12 -m pytest tests/test_promotion.py::test_promotes_case_a_and_case_b_without_collapsing_results -vv
py -3.12 -m pytest tests/test_promotion.py::test_second_cad_promotion_refuses_overwrite -vv
py -3.12 -m pytest tests/test_promotion.py -q
```

- [ ] **Step 6: Run the P2 focused set**

```powershell
py -3.12 -m pytest tests/test_cad_evidence.py tests/test_cad_demo.py tests/test_cad_evidence_schema.py tests/test_promotion.py tests/test_schema_contracts.py tests/test_policy.py tests/test_cli.py -q
```

- [ ] **Step 7: Commit the implementation repair**

```powershell
git add tests/conftest.py tests/test_cad_evidence_schema.py docs/evidence_preservation/schemas/cad_evidence.schema.json docs/superpowers/plans/2026-09-11-p2-final-repair-integration-review.md
git commit -m "fix: align CAD promotion evidence contracts"
git rev-parse HEAD
```

---

### Task 2: Generate final FreeCAD Case A/B/reopen evidence

**Files:**
- Create: `outputs/<new-run-id>/...` staging artifacts
- Create through promotion: `evidence/P2-MVP/<final-implementation-sha>/<new-run-id>/...`
- Modify only if required by executable evidence generation: existing P2 scripts/modules covered by targeted tests

**Interfaces:**
- Consumes: committed implementation SHA and `C:/Program Files/FreeCAD 1.1/bin/freeCADCmd.exe` through the host request/worker/JSON boundary.
- Produces: real FCStd/BREP/STEP files, opening/closing geometry-semantic/topology/UI snapshots, measurement-backed Case A/B/reopen comparisons, VIEW_INDEX, HUMAN_REVIEW, JUnit, validator output, request, manifest, inventory, and policy report.

- [ ] **Step 1: Record the exact implementation identity**

```powershell
git rev-parse HEAD
git merge-base feat/cylindrical-interface-repairability HEAD
```

- [ ] **Step 2: Execute real Case A, Case B, and reopen on that commit**

```powershell
py -3.12 -m pytest tests/test_cad_demo.py -q --junitxml=outputs/<new-run-id>/artifacts/pytest.xml
```

Generate fixtures and comparison JSON using the existing host-side Python to FreeCADCmd worker boundary. Case A must report geometry and semantic equivalent with UI different; Case B must report geometry different with measured reasons; reopen must independently compare B-reps.

- [ ] **Step 3: Build and validate the final request**

Set `implementation_commit` to the exact Step 1 SHA. Reference the real comparison/snapshot artifacts from their separate result domains and record `NOT_FULLY_PRESERVED` when copies remain same-host.

```powershell
$env:PYTHONPATH = "src"
py -3.12 -m dmslicer.evidence_promotion validate --repository-root . --request outputs/<new-run-id>/request.json
```

- [ ] **Step 4: Promote once into a new immutable destination**

```powershell
py -3.12 -m dmslicer.evidence_promotion promote --repository-root . --request outputs/<new-run-id>/request.json
```

Expected: `LOCAL_PACKAGE_CREATED`. A second identical call must return only `DESTINATION_EXISTS` and leave package bytes unchanged.

- [ ] **Step 5: Verify artifact completeness and content**

Recompute inventory hashes as byte-integrity checks, validate all JSON schemas, inspect Case A/B/reopen measurements, and confirm original/UI-only/geometry-changed/reopened FCStd plus applicable BREP/STEP, snapshots, comparisons, VIEW_INDEX, and HUMAN_REVIEW are present.

- [ ] **Step 6: Commit final canonical evidence without changing executable logic**

```powershell
git add evidence/P2-MVP/<final-implementation-sha>/<new-run-id>
git commit -m "evidence: record final P2 FreeCAD validation"
```

---

### Task 3: Run the final regression and reviewer gate

**Files:**
- Inspect: all files changed from `feat/cylindrical-interface-repairability...HEAD`
- Preserve: failing and preliminary evidence already committed

- [ ] **Step 1: Run the single inherited full regression**

```powershell
py -3.12 -m pytest -q
```

Record collected, passed, failed, skipped, exit code, and every skip reason.

- [ ] **Step 2: Run repository integrity checks**

```powershell
git diff --check feat/cylindrical-interface-repairability...HEAD
git diff --exit-code feat/cylindrical-interface-repairability...HEAD -- docs/research_v2
git status --short
```

- [ ] **Step 3: Review only the P2 final-risk checklist**

Inspect SHA/geometry separation, placeholder evidence, implementation SHA freshness, overwrite protection, result-domain separation, preliminary disposition, sensitive paths/secrets, and scope creep. Fix Critical/Important findings with targeted RED/GREEN tests and regenerate evidence if executable logic changes.

---

### Task 4: Reconcile and publish the canonical branch and PR #3

**Files:**
- Inspect/remove only if unnecessary: `.github/workflows/evidence-promotion.yml` feature diff
- Update remotely: PR #3 body

- [ ] **Step 1: Classify the workflow diff**

```powershell
git diff --name-status origin/feat/evidence-promotion-semantic-snapshot..HEAD -- .github/workflows
git diff origin/feat/evidence-promotion-semantic-snapshot..HEAD -- .github/workflows/evidence-promotion.yml
```

If not required for P2, remove the feature-branch workflow change with a normal forward commit; do not rewrite history.

- [ ] **Step 2: Push the canonical branch without force**

```powershell
git push origin feat/evidence-promotion-semantic-snapshot
```

If GitHub rejects workflow modification permission, retain `GIT_PUSH_SCOPE_BLOCKED` and do not expose or persist credentials.

- [ ] **Step 3: Update PR #3 only after successful push**

Use `gh pr edit 3 --body-file <public-safe-body-file>` with actual Case A/B/reopen, promotion, preservation, and test results. Do not claim off-host preservation or publication.

- [ ] **Step 4: Verify the final remote gate**

```powershell
git fetch origin --prune
gh pr view 3 --json url,state,baseRefName,headRefName,headRefOid,body
git status --short --branch
```

Confirm PR #3 is OPEN and unmerged, base is `feat/cylindrical-interface-repairability`, head is the canonical P2 branch containing every accepted commit, and the working tree is clean. Stop without starting the next research Goal.
