# P1 Historical Evidence Ingestion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Recover DM-Slicer historical conversation and workspace provenance into the P0 evidence system, preserve newly found research artifacts, and integrate the approved CAD evidence policy through a separate policy-only PR.

**Architecture:** The evidence branch stores only sanitized indexes, manifests, reports, and small governance scripts in Git while immutable local custody stores raw task records and artifact copies. A separate branch based on current `origin/main` modifies only `AGENTS.md`; Release and merge actions are gated independently.

**Tech Stack:** Git, Git worktrees, PowerShell 7, JSON Schema, SHA-256 for byte integrity, GitHub CLI, Codex task discovery/read APIs, Markdown

**Spec:** `docs/superpowers/specs/2026-09-10-p1-historical-evidence-ingestion-design.md`

## Global Constraints

- Evidence branch: `chore/p1-historical-evidence-ingestion`, based exactly on P0 `4f77c8ab8700a5cef9ef02667b6b7e4005472147`.
- Policy branch: `policy/cad-evidence-governance`, based on verified latest `origin/main`; its final diff contains only `AGENTS.md`.
- Do not start 07A; modify `docs/research_v2/`; rewrite P0; replace existing Release assets; delete worktrees/evidence; rebase; force-push; or batch-merge research branches.
- Preserve `GH`, `L`, `CHAT`, and `U` as separate confidence states; never infer missing execution facts.
- SHA-256 is restricted to byte integrity, exact-byte duplicate detection, and copy verification; it is never geometry-equivalence evidence.
- Geometry, semantic, UI/display, pytest, validator, scientific experiment, and human inspection results remain independent.
- Public outputs use aliases and stable URIs, never private absolute paths, usernames, credentials, tokens, or unnecessary host data.
- Copy operations must fail rather than overwrite and must retain both source and destination on verification failure.

---

### Task 1: Establish the P1 execution record and baseline

**Files:**
- Create: `docs/superpowers/specs/2026-09-10-p1-historical-evidence-ingestion-design.md`
- Create: `docs/superpowers/plans/2026-09-10-p1-historical-evidence-ingestion.md`

**Interfaces:**
- Consumes: the approved Goal objective and P0 evidence framework
- Produces: bounded scope, acceptance criteria, stop conditions, and an executable task sequence

- [ ] **Step 1: Verify roots, refs, remotes, worktrees, DAG, and existing Releases**

Run the Goal preflight commands plus `gh repo view`, `gh release list`, and `git ls-remote`. Require the canonical root and exact known P0/main/Release identities before writing evidence.

- [ ] **Step 2: Create isolated evidence and policy worktrees**

Create the named branches at their required commits. Abort on any pre-existing ambiguous path or branch; do not alter the dirty canonical checkout.

- [ ] **Step 3: Validate the inherited P0 baseline**

Parse the schema and all 13 manifests, validate each manifest with JSON Schema, run `git diff --check`, and record any missing validator dependency rather than silently skipping it.

- [ ] **Step 4: Commit the approved design and plan**

Stage only the two files in this task, inspect the staged diff, and commit them on the evidence branch.

### Task 2: Discover and privately preserve historical Codex task evidence

**Files:**
- Create outside Git: `P1_CUSTODY_ROOT/private_conversations/task-<stable-id>.json`
- Create outside Git: `P1_CUSTODY_ROOT/PRIVATE_CONVERSATION_INVENTORY.json`
- Create: `docs/evidence_preservation/conversation_evidence.json`
- Create: `docs/evidence_preservation/CONVERSATION_EVIDENCE_INDEX.md`

**Interfaces:**
- Consumes: Codex task listings, task pages, branch/commit/artifact reverse-search terms
- Produces: sanitized Goal/task provenance events and private raw-record custody hashes

- [ ] **Step 1: Enumerate candidate tasks by title, summary, project, branch, commit, artifact, and geometry terminology**

Use task discovery across available hosts/projects. Record total discovered, candidates, inaccessible tasks, and the exact inclusion reason; do not rely on titles alone.

- [ ] **Step 2: Read every candidate deeply enough to recover process history**

Collect task ID, title, Goal, branch, start/implementation/failure/fix commits, commands, exit codes, failures, diagnosis, reviewer findings, fixes, revalidation, repeatability, artifacts, and final conclusion. Page backward when earlier failure or review context is required.

- [ ] **Step 3: Preserve raw records privately and verify their bytes**

Write each fetched record once under a stable task-derived ID, compute SHA-256, and record its Goal relationship. If a destination exists, compare it and create a new version rather than overwrite.

- [ ] **Step 4: Build sanitized JSON and Markdown indexes**

Represent unsupported fields as `null/U`; retain failure-to-fix ordering; include artifact/Release references; exclude raw messages, private paths, user names, secrets, and host-only details.

- [ ] **Step 5: Validate index parity and public safety**

Require identical relevant-task counts and task IDs in Markdown and JSON, parse JSON, and scan both outputs for prohibited local-path and secret patterns.

### Task 3: Inventory and reconcile all historical workspaces

**Files:**
- Create outside Git: `P1_CUSTODY_ROOT/PRIVATE_ARTIFACT_INVENTORY.json`
- Create outside Git: `P1_CUSTODY_ROOT/reconciliation/goal-<id>.json`
- Create outside Git: `P1_CUSTODY_ROOT/reconciliation/goal-06d-focused.json`

**Interfaces:**
- Consumes: all formal Goal worktrees, historical Codex workspaces, P0 custody, repository outputs/work, and Release inventories
- Produces: logical-artifact classifications and copy candidates for every Goal

- [ ] **Step 1: Enumerate source roots without following reparse-point cycles**

Inventory regular files for 02C–06D and DOC01 with source alias, normalized relative path, extension, size, SHA-256, and source class. Retain errors and inaccessible paths in the inventory.

- [ ] **Step 2: Reconcile every Goal**

Classify logical artifacts only as `ONLY_IN_WORKTREE`, `ONLY_IN_CODEX_HISTORY`, `ONLY_IN_PRESERVATION`, `PRESENT_IN_RELEASE`, `IDENTICAL_DUPLICATE`, `DIVERGENT_REQUIRES_REVIEW`, `PROVENANCE_UNRESOLVED`, or `MISSING`. For CAD divergence, add a cause field restricted to serialization, UI-only, geometry, semantic, different run, different commit, or unknown, and use `unknown` unless artifact-backed evidence establishes more.

- [ ] **Step 3: Run the focused 06D formal-versus-historical reconciliation**

Compare D01/D02/D03, all controls, repeatability/second_process, HUMAN_REVIEW, BREP patches/remaining/common, corrected/fused STEP, FCStd, operation/provenance/covariance/validation JSON, facesets, components, and patches.

- [ ] **Step 4: Prioritize unresolved P0 and P1-risk evidence**

Explicitly inspect 02C final-tip binding; 03C A12 failure/diagnosis/fix; 04A A02/A08 context; 06D reviewer findings; and complete inventories for 03A, 03B, 04B, and 05A. Preserve 05B/05C/06B/06C failure and reviewer history.

- [ ] **Step 5: Reconcile inventory totals**

For every source alias, compare enumerated file count and byte total against an independent filesystem count. Fail the affected source closed on mismatch.

### Task 4: Ingest missing critical evidence into immutable P1 custody

**Files:**
- Create outside Git: `P1_CUSTODY_ROOT/canonical/goal-<id>/<run-id>/...`
- Update outside Git: `P1_CUSTODY_ROOT/PRIVATE_ARTIFACT_INVENTORY.json`

**Interfaces:**
- Consumes: Task 3 copy candidates and P0 allowlist policy
- Produces: stable source-to-copy mappings with byte-fidelity verification

- [ ] **Step 1: Build an explicit Goal/run allowlist**

Include only evidence needed for provenance, geometry/topology validation, controls, repeatability, failures, reviewer findings, diagnostics, JUnit, VIEW_INDEX, HUMAN_REVIEW, STEP, BREP, and FCStd. Exclude caches, regenerated junk, and unrelated source trees without deleting them.

- [ ] **Step 2: Copy into new versioned destinations**

Use literal paths and fail if a destination exists. Preserve source-relative structure and record goal_id, implementation_commit when known, run_id, source alias, size, and source SHA-256.

- [ ] **Step 3: Verify every copy**

Recompute destination SHA-256 and require equality with the source solely as copy-fidelity evidence. On mismatch retain both, mark `HASH_VERIFICATION_FAILED`, and exclude the file from Release staging.

- [ ] **Step 4: Evaluate recoverability**

Record copy locations and whether an independent off-host copy exists. Do not claim full preservation where only same-host source and custody copies exist.

### Task 5: Enrich the P0 evidence control plane

**Files:**
- Modify: `docs/evidence_preservation/evidence_manifest.schema.json` only if backward-compatible fields are required
- Modify: `docs/evidence_preservation/manifests/goal-02c.json` through `goal-06d.json`
- Modify: `docs/evidence_preservation/WORKTREE_CUSTODY_REPORT.md`
- Create: `docs/evidence_preservation/EVIDENCE_PROMOTION_CI_REQUIREMENTS.md`

**Interfaces:**
- Consumes: conversation index, reconciliation, custody copies, Git/GitHub facts
- Produces: enriched provenance chains, result-layer separation, and a bounded future CI design

- [ ] **Step 1: Extend manifests without replacing P0 facts**

Add recovered task references, run bindings, failure/diagnosis/reviewer/fix/revalidation events, stable custody IDs, geometry criteria, tolerance value/unit, snapshot roles, and confidence. Keep previous Release records append-only and all unknown values null/U.

- [ ] **Step 2: Re-evaluate blocked Releases**

Require a reliable implementation-commit → input → output → validation chain. Otherwise retain `RELEASE_BLOCKED_PROVENANCE` and state the exact missing link.

- [ ] **Step 3: Update custody classifications without deleting worktrees**

Recompute 02C–06D, DOC01, P0, P1, and policy worktree custody. `ARCHIVABLE` remains a non-deletion state.

- [ ] **Step 4: Define the future promotion gate**

Document allowlisting, commit/run/version/command/tolerance fields, stable URIs, two recoverable copies, sensitivity scans, duplicate handling, failure retention, SHA-256 misuse detection, and geometry/semantic/UI separation. Stop at requirements unless a small existing script can be safely extended.

- [ ] **Step 5: Validate schemas and public safety**

Parse every JSON, validate all Goal manifests against the schema, scan public files for private paths/secrets, and run `git diff --check`.

### Task 6: Publish only provenance-qualified supplemental evidence

**Files:**
- Modify: `docs/evidence_preservation/RELEASE_UPLOAD_INVENTORY.md`
- Modify: `docs/evidence_preservation/SENSITIVITY_DUPLICATION_CHECK.md`
- Create outside Git: `P1_CUSTODY_ROOT/release_staging/<versioned-release>/...`

**Interfaces:**
- Consumes: eligible manifest chains and verified custody copies
- Produces: append-only supplemental Releases or explicit blockers

- [ ] **Step 1: Prove existing Releases are unchanged**

Query names, tags, target commits, asset names, sizes, and GitHub digests for the three P0 Releases and compare with the P0 upload inventory.

- [ ] **Step 2: Gate each supplemental candidate**

Require supported implementation commit, input, output, validation, retained failures/reviews, sensitivity pass, non-duplicate purpose, manifest validity, and versioned supplement metadata linking the prior Release.

- [ ] **Step 3: Publish eligible supplements without replacement**

Use a new versioned tag/name and upload only allowlisted assets. If no Goal passes, publish none and retain blockers.

- [ ] **Step 4: Verify GitHub state after publication**

Read back target, assets, sizes, digests, and URLs; compare them with staging and record the result. Do not equate matching digests with geometry equivalence.

### Task 7: Create and gate the repository policy PR

**Files:**
- Modify in policy worktree only: `AGENTS.md`

**Interfaces:**
- Consumes: current `main:AGENTS.md` and the approved governance sections
- Produces: one clean policy commit/PR or a recorded blocker

- [ ] **Step 1: Rebuild the policy from current main**

Preserve every existing main rule and add only `CAD hashes and geometric equivalence` plus `Research evidence persistence and output paths`. Do not cherry-pick `b42ba9e`, import Completion Git Policy, or modify any other file.

- [ ] **Step 2: Run policy static gates**

Require `git diff --name-only origin/main...HEAD` to equal `AGENTS.md`; inspect the full diff; verify all numbered main rules remain; scan for prohibited weakening language; and confirm no 06D implementation ancestry enters the branch.

- [ ] **Step 3: Commit and push the policy branch**

Commit only `AGENTS.md`, run fresh gates, then push without force.

- [ ] **Step 4: Create the PR with accurate provenance**

Explain that `b42ba9e` is a historical precursor and this PR is a clean reconstruction following the P0 audit and CAD hash/geometry findings. State that the PR is not a cherry-pick.

- [ ] **Step 5: Merge only if every gate passes**

Check base/head SHAs, changed files, checks, conflicts, review findings, and mergeability. Merge only when all are clean; otherwise leave the PR open and record the blocker. Verify final `main:AGENTS.md` after any merge.

### Task 8: Write the P1 report, commit, push, and verify end state

**Files:**
- Create: `docs/evidence_preservation/P1_HISTORICAL_EVIDENCE_REPORT.md`
- Modify: `docs/evidence_preservation/README.md`

**Interfaces:**
- Consumes: all discovery, custody, manifest, Release, policy, and verification records
- Produces: the required A–J report and final auditable branch state

- [ ] **Step 1: Write report sections A–J**

Report task counts/access, recovered chains/findings, per-Goal workspace classifications, copied counts/bytes/hash verification, geometry/semantic evidence maturity, manifest changes, Release outcomes, P1-risk Goal custody, policy PR/merge state, and every remaining U/CHAT-only/blocked/unrecoverable gap.

- [ ] **Step 2: Verify report totals against machine-readable records**

Recompute counts and bytes from JSON rather than copying narrative totals. Require report/JSON parity for tasks, copies, Goal classifications, Releases, and blockers.

- [ ] **Step 3: Run final evidence verification**

Parse and schema-validate all JSON; compare custody hashes; rescan public files; run `git diff --check`; inspect both worktree statuses and diffs; query GitHub Releases/PR/main; and confirm every historical worktree still exists.

- [ ] **Step 4: Commit and push the evidence branch**

Stage only public sanitized evidence documents, manifests, and bounded scripts. Inspect the staged file list and diff, commit with the verified totals, and push without force.

- [ ] **Step 5: Record final immutable identities**

Capture the evidence commit, policy commit/PR/merge (or blocker), Release URLs (or blockers), P1 custody run ID, remaining single-location risks, and explicit confirmation that 07A was not started and no worktree was deleted.
