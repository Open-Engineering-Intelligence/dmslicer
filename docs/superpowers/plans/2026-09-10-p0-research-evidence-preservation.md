# P0 Research Evidence Preservation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Preserve provenance-qualified DM-Slicer research evidence, publish curated append-only evidence Releases, isolate the Human Inspection policy integration, and report worktree custody without deleting historical material.

**Architecture:** Public Git documents contain sanitized manifests and reports; private local custody contains absolute source mappings and verified copies; GitHub Releases contain curated evidence bound to supported implementation commits. All result domains and confidence levels remain separate, and unsupported provenance blocks only the affected Release.

**Tech Stack:** Git, Git worktrees, PowerShell 7, SHA-256, JSON, ZIP, GitHub CLI, Markdown

**Spec:** `docs/superpowers/specs/2026-09-10-p0-research-evidence-preservation-design.md`

## Global Constraints

- Work only in the isolated `<p0-worktree>` for preservation-branch files.
- Use `<private-custody-root>/dmslicer/p0-20260910` for private custody; never add it to Git.
- Do not start 07A, delete worktrees, clean `outputs/` or `work/`, overwrite artifacts, force push, rebase, or merge 02C–06D/DOC01.
- Do not modify `docs/research_v2/`.
- Unknown historical fields remain JSON `null` with confidence `U`.
- SHA-256 proves byte integrity only, never geometry equivalence.
- A pytest pass never becomes a scientific experiment pass.

---

### Task 1: Establish public evidence structure and manifest contract

**Files:**
- Create: `docs/evidence_preservation/README.md`
- Create: `docs/evidence_preservation/evidence_manifest.schema.json`

**Interfaces:**
- Consumes: approved design spec and the GH/L/CHAT/U vocabulary
- Produces: the required JSON structure used by every Goal manifest

- [ ] **Step 1: Write the public/private and confidence contract**

Create `README.md` with the public path-safety rules, result-domain separation, append-only Release rule, and navigation for every report.

- [ ] **Step 2: Define the manifest schema**

Create a JSON Schema requiring identity, inputs, environment, execution, tolerances, artifact inventory, failure/fix history, actual geometry criteria, four result domains, confidence labels, Release state, and supersession metadata.

- [ ] **Step 3: Validate the schema parses**

Run:

```powershell
Get-Content docs/evidence_preservation/evidence_manifest.schema.json -Raw | ConvertFrom-Json | Out-Null
```

Expected: exit code 0.

### Task 2: Generate the real branch dependency DAG

**Files:**
- Create: `docs/evidence_preservation/BRANCH_DEPENDENCY_DAG.md`

**Interfaces:**
- Consumes: local and remote Goal refs plus Git parent/merge-base commands
- Produces: ancestry facts used by manifests and future integration decisions

- [ ] **Step 1: Capture every Goal tip, parent, main merge-base, and prior-Goal ancestry result**

Run `git rev-parse`, `git show -s --format=%P`, `git merge-base`, and `git merge-base --is-ancestor` for 02C–06D and DOC01.

- [ ] **Step 2: Record the 03A packaging fork explicitly**

Prove that `a1fc48b` and 03B both descend from `bd831be`, while `a1fc48b` is not an ancestor of 03B or later branches.

- [ ] **Step 3: Write the DAG and integration dependency table**

Include a Mermaid graph, the command-backed matrix, and explicit prohibition on deriving ancestry from Goal numbering.

- [ ] **Step 4: Re-run the ancestry commands used by every positive/negative claim**

Expected: every table value matches fresh Git exit codes and SHAs.

### Task 3: Build the P0 source inventory and private custody index

**Files:**
- Create: `docs/evidence_preservation/P0_PRESERVATION_INVENTORY.md`
- Create outside Git: `<private-custody-root>/dmslicer/p0-20260910/LOCAL_CUSTODY_INVENTORY.json`

**Interfaces:**
- Consumes: historical worktree outputs, historical Codex task artifacts, tracked fixtures, and audit findings
- Produces: exact source classifications and private absolute-path custody mappings

- [ ] **Step 1: Inventory 04A A02/A08 first**

Enumerate BREP, FCStd, STEP, validation, repeatability, summary, and VIEW_INDEX files in the historical 04A task directory; record sizes and SHA-256 without changing them.

- [ ] **Step 2: Inventory remaining P0 evidence**

Enumerate 03C A12 pre-fix, probe, and analytic-fix evidence; 05B/05C mismatch and recovery evidence; 06A/06B JUnit, rejection, failure, BREP, and FCStd evidence; 06C BREP, validator, JUnit, reviewer/fix evidence; and 06D BREP, FCStd, STEP, JUnit, VIEW_INDEX, HUMAN_REVIEW, and reviewer evidence.

- [ ] **Step 3: Classify evidence state**

Use only `PRESERVED`, `SINGLE_COPY`, `MISSING`, `UNRECOVERABLE`, or `RELEASE_BLOCKED_PROVENANCE`, with an evidence basis and confidence for each row.

- [ ] **Step 4: Validate the private inventory is outside Git and valid JSON**

Run `git -C <p0-worktree> status --short` and confirm the private custody file is not listed; parse it with `ConvertFrom-Json`.

### Task 4: Copy and verify canonical P0 evidence

**Files:**
- Create outside Git: goal-specific trees under `<private-custody-root>/dmslicer/p0-20260910/canonical/` named `goal-03c`, `goal-04a`, `goal-05b`, `goal-05c`, `goal-06a`, `goal-06b`, `goal-06c`, and `goal-06d`
- Update outside Git: `<private-custody-root>/dmslicer/p0-20260910/LOCAL_CUSTODY_INVENTORY.json`

**Interfaces:**
- Consumes: Task 3 source list
- Produces: versioned preserved copies and exact source-to-copy verification

- [ ] **Step 1: Create new custody directories without overwrite semantics**

Fail the affected copy if its destination already exists; never delete or replace the destination.

- [ ] **Step 2: Copy 04A A02/A08 and verify every file**

Use `Copy-Item -LiteralPath` and compare `Get-FileHash -Algorithm SHA256` for source and copy.

- [ ] **Step 3: Copy all other selected P0 files and verify every file**

Preserve source-relative structure and record size, source SHA-256, copy SHA-256, and equality.

- [ ] **Step 4: Fail closed on verification differences**

Record the affected artifact as `HASH_VERIFICATION_FAILED`, preserve both files, and exclude it from public Release staging.

### Task 5: Create and validate all Goal evidence manifests

**Files:**
- Create: `docs/evidence_preservation/manifests/goal-02c.json`
- Create: `docs/evidence_preservation/manifests/goal-03a.json`
- Create: `docs/evidence_preservation/manifests/goal-03b.json`
- Create: `docs/evidence_preservation/manifests/goal-03c.json`
- Create: `docs/evidence_preservation/manifests/goal-04a.json`
- Create: `docs/evidence_preservation/manifests/goal-04b.json`
- Create: `docs/evidence_preservation/manifests/goal-05a.json`
- Create: `docs/evidence_preservation/manifests/goal-05b.json`
- Create: `docs/evidence_preservation/manifests/goal-05c.json`
- Create: `docs/evidence_preservation/manifests/goal-06a.json`
- Create: `docs/evidence_preservation/manifests/goal-06b.json`
- Create: `docs/evidence_preservation/manifests/goal-06c.json`
- Create: `docs/evidence_preservation/manifests/goal-06d.json`

**Interfaces:**
- Consumes: schema, DAG, custody inventory, Git history, tracked evidence, and historical task confidence boundaries
- Produces: sanitized public Goal-to-commit-to-input-to-output-to-validation-to-review chains

- [ ] **Step 1: Populate identity and ancestry only from Git**

Use full SHAs for branch tips, implementation/fix/policy commits, merge-bases, and parents. Where artifact-to-commit binding is not established, leave the commit field `null`, confidence `U`, and Release state blocked.

- [ ] **Step 2: Populate environment and execution without inference**

Use values only if explicitly recorded inside preserved evidence; otherwise use `null/U`. Do not use filesystem modification time as execution timestamp.

- [ ] **Step 3: Populate artifacts and tolerances**

Use repository-relative paths, planned Release asset names, SHA-256, explicit tolerance units, and actual geometry criteria. Do not expose private source paths.

- [ ] **Step 4: Preserve failure and mismatch facts**

Record 03C A12 pre-fix failure, 05B `16/90` and `1/90`, 05C retained area exceedance, 06B early failures, and 06C reviewer/hash-policy history independently of pytest results.

- [ ] **Step 5: Validate all 13 manifests**

Parse every file, assert all schema-required top-level fields, verify allowed confidence/status enums, and scan for prohibited local path/user/secret patterns.

### Task 6: Build and isolate-test the 06D V2 human-review package

**Files:**
- Create outside Git: `<private-custody-root>/dmslicer/p0-20260910/release_staging/goal-06d-evidence-b7054f3/goal-06d-human-review-v2-b7054f3.zip`

**Interfaces:**
- Consumes: preserved 06D D01/D02/D03 FCStd, corrected/fused STEP, VIEW_INDEX facts, and reviewer/failure history
- Produces: a self-contained review package referenced by the 06D manifest

- [ ] **Step 1: Assemble a new versioned package directory**

Write package-relative `README.md`, `VIEW_INDEX.md`, and `REVIEWER_AND_FAILURE_NOTES.md`; copy the three FCStd and six corrected/fused STEP files. Do not read from or modify the old ZIP.

- [ ] **Step 2: Confirm the package file whitelist**

Require exactly the three documentation files plus three FCStd and six STEP files, with no absolute path references.

- [ ] **Step 3: Create the V2 ZIP and record its SHA-256**

Use a new destination name and fail if it already exists.

- [ ] **Step 4: Validate outside the source worktree**

Extract into a new directory under the private custody root, parse every Markdown link in `VIEW_INDEX.md`, reject absolute or parent-traversal paths, and require every referenced human-review file to exist inside the extraction root.

### Task 7: Gate and publish curated Evidence Releases

**Files:**
- Create: `docs/evidence_preservation/RELEASE_UPLOAD_INVENTORY.md`
- Create: `docs/evidence_preservation/SENSITIVITY_DUPLICATION_CHECK.md`
- Create outside Git: one staged directory and `SHA256SUMS.txt` per eligible Release

**Interfaces:**
- Consumes: public manifests, canonical preserved files, 06D V2 package, and Release gate rules
- Produces: published append-only Releases or explicit per-Goal blockers

- [ ] **Step 1: Determine each supported implementation commit**

Require evidence internal provenance or unambiguous historical Git/task evidence; do not bind an artifact to a branch tip merely because the file resides in that worktree.

- [ ] **Step 2: Curate assets and remove duplicate garbage only from staging selection**

Keep canonical validation, failure/mismatch, reviewer, and human-review evidence. Exclude caches and redundant reruns without deleting sources.

- [ ] **Step 3: Run upload manifest gates**

Record asset name, source alias, byte size, SHA-256, target Release, supported commit, duplication decision, and sensitivity scan. A failed gate marks only that Goal blocked.

- [ ] **Step 4: Publish eligible Releases**

Use versioned tag/Release names, target the supported implementation commit, upload the public manifest and staged assets, and never replace an existing asset.

- [ ] **Step 5: Verify each published Release from GitHub**

Read back tag target, asset names, sizes, and download metadata; compare them with the upload inventory and record the public URL.

### Task 8: Integrate Human Inspection policy through an isolated PR

**Files:**
- Create on separate branch: only `AGENTS.md` via cherry-pick of `b42ba9e`
- Create/update: `docs/evidence_preservation/HUMAN_INSPECTION_POLICY_PR.md`

**Interfaces:**
- Consumes: current remote main and source policy commit `b42ba9e`
- Produces: a policy-only PR and merge evidence, or an explicit blocker

- [ ] **Step 1: Fetch and create the policy branch from current `origin/main`**

Record the exact base SHA before mutation.

- [ ] **Step 2: Cherry-pick `b42ba9e` without broadening the change**

If a conflict occurs, abort only the policy integration and record the blocker.

- [ ] **Step 3: Verify the complete diff**

Require `git diff --name-only origin/main...HEAD` to contain only `AGENTS.md`; inspect the full diff and assert no implementation/output/evidence content.

- [ ] **Step 4: Push, create PR, and wait for checks/reviews**

Do not enable automatic merge before confirming checks and unresolved-review state.

- [ ] **Step 5: Merge only when every authorized gate passes**

Record PR URL and merge commit. Otherwise leave the PR unmerged and record the exact blocker.

### Task 9: Classify worktree custody and write the final A–J report

**Files:**
- Create: `docs/evidence_preservation/WORKTREE_CUSTODY_REPORT.md`
- Create: `docs/evidence_preservation/P0_PRESERVATION_REPORT.md`

**Interfaces:**
- Consumes: all earlier verification results, Release states, policy PR state, and the DAG
- Produces: the required final decision record

- [ ] **Step 1: Evaluate every worktree against all ARCHIVABLE criteria**

Mark only `ARCHIVABLE` or `NOT_ARCHIVABLE`, list every failed criterion, and do not delete a worktree.

- [ ] **Step 2: Write A–J preservation results**

Answer preserved evidence, single-copy evidence, incomplete recovery, manifests, Release readiness, 06D package, policy PR, DAG, non-deletable worktrees, and archivable worktrees.

- [ ] **Step 3: Add requested execution totals**

Include Releases created/blocked, PR URL/merge commit, preserved count/bytes, remaining single-copy artifacts, manifest validation, isolated package validation, DAG conclusions, and custody status.

- [ ] **Step 4: Run final verification**

Parse all JSON, run `git diff --check`, rescan public files for prohibited paths/secrets, compare custody hashes, inspect Git status, query Releases/PR/main, and confirm every historical worktree still appears in `git worktree list --porcelain`.

- [ ] **Step 5: Commit the preservation documentation**

Commit only public sanitized documentation and manifests on `chore/p0-research-evidence-preservation`; do not add custody binaries or absolute-path inventories.
