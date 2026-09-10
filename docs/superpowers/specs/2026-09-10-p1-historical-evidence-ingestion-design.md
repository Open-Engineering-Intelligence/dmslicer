# P1 Historical Evidence Ingestion and CAD Evidence Governance Design

## Scope

P1 extends the P0 evidence framework without rerunning P0, rewriting frozen research documents, starting 07A, or altering existing evidence Releases. It has two isolated delivery tracks:

1. An evidence branch that discovers historical Codex task and filesystem evidence, preserves missing artifacts, enriches schema-compatible manifests, and reports unresolved provenance honestly.
2. A policy branch based on current `origin/main` that changes only `AGENTS.md` and integrates the approved CAD hash, geometry-equivalence, and research-evidence custody rules.

## Evidence architecture

Public Git content is a sanitized control plane: task identities, Goal mappings, findings, commit relations, artifact IDs, stable URIs, confidence, and unresolved gaps. Exact local source locations, raw task exports, source-to-copy mappings, and custody hashes remain in private versioned custody storage. Public files never expose usernames, credentials, temporary paths, or unnecessary host details.

Historical facts use `GH`, `L`, `CHAT`, and `U` confidence. Task statements do not become current validation. Unknown fields stay `null` or `U`. Failures, mismatches, rejected hypotheses, reviewer findings, pre-fix artifacts, and later verification remain distinct events in the provenance chain.

SHA-256 proves exact-byte identity and copy fidelity only. CAD byte divergence is classified separately from geometry, semantic, and UI/display equivalence. Geometry claims require artifact-backed B-rep/topology comparisons with explicit value-and-unit tolerances. JSON snapshots record evidence; they do not replace comparison.

## Discovery and reconciliation

Task discovery searches titles, summaries, task bodies, branch names, commits, worktree/output paths, geometry terms, validator/reviewer terms, and all Goals from 02C through 06D plus DOC01. Relevant tasks are read deeply enough to recover the failure-to-revalidation chain; raw conversations are not published.

Filesystem discovery covers every formal Goal worktree, P0 preservation custody, repository `outputs/` and `work/`, and all historical Codex workspaces. Logical artifacts are compared by normalized relative path, size, SHA-256, source class, and run/commit context. Exact-byte duplicates are labeled `IDENTICAL_DUPLICATE`; divergent CAD bytes are never labeled geometry-different without geometry evidence.

Missing important artifacts are copied, never moved or overwritten, into a new P1 custody run. Every source/copy pair is hash-verified. Final evidence must have a stable manifest and at least two recoverable copies before it is described as fully preserved.

## Deliverables

- `docs/evidence_preservation/CONVERSATION_EVIDENCE_INDEX.md`
- `docs/evidence_preservation/conversation_evidence.json`
- `docs/evidence_preservation/P1_HISTORICAL_EVIDENCE_REPORT.md`
- `docs/evidence_preservation/EVIDENCE_PROMOTION_CI_REQUIREMENTS.md`
- P1-enriched Goal manifests and custody reports, retaining P0 history
- private P1 custody inventory and immutable copied artifacts
- supplemental append-only Releases only where provenance and sensitivity gates pass
- a separate policy-only PR for `AGENTS.md`, merged only when every authorized gate passes

## Acceptance criteria

- Canonical root, refs, worktrees, and existing Releases are command-verified.
- All discoverable relevant tasks are classified as fully read or inaccessible, with Goal distribution and unresolved gaps.
- All Goals 02C–06D and DOC01 receive historical workspace reconciliation; 06D formal-versus-Codex evidence receives a complete focused reconciliation.
- All ingested files have matching source/copy SHA-256 values, used only for copy fidelity.
- Every public JSON file parses, every Goal manifest validates against the inherited schema, and public outputs pass sensitive-path/secret scans.
- Existing Releases remain unchanged and supplemental Releases, if any, point to supported implementation commits.
- The policy diff contains only `AGENTS.md`, preserves current main rules, and does not import historical implementation ancestry.
- No worktree or historical evidence is deleted, moved, overwritten, rebased, or force-pushed.

## Stop conditions

Keep unsupported provenance as `CHAT`, `U`, `MISSING`, or `RELEASE_BLOCKED_PROVENANCE`. Do not publish or merge when the applicable gate fails. Record the blocker and continue independent safe work. Do not build a large evidence service, database, plugin framework, or 07A implementation.
