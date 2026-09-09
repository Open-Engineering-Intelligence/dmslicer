# AGENTS.md

## Repository purpose

This is a research-first repository. Every change must preserve the distinction between research hypotheses, geometric evidence, semantic decisions, and implemented behavior.

## Geometry and semantics

1. Never treat a derived display mesh as geometry truth.
2. Keep STEP/B-rep geometry authority distinct from every derived mesh used for display, sampling, acceleration, or export.
3. Legacy AMF algorithms are baselines and historical references only.
4. A candidate relation is not a confirmed geometry relation.
5. Geometry truth is not semantic activation.
6. `MaterialRegion` is not `InterfaceSourceBoundary`.
7. A gradient semantic role is not a volumetric field.

## Provenance and reproducibility

8. Stable provenance is mandatory for imported and derived entities.
9. Every tolerance must be explicit, carry a unit, and be recorded in the relevant manifest.
10. Do not use random UUIDs, process counters, or list indexes as persistent geometry identities.
11. Every implementation must emit machine-readable evidence sufficient to inspect its inputs, configuration, decisions, and outputs.
12. Every research claim must map to a test, benchmark, or experiment.

## Scope discipline

13. Do not perform unrelated refactors.
14. Do not build large plugin, service, repository, adapter, factory, or event-bus abstractions merely because they may be useful later.
15. Every Goal must define explicit Scope, Acceptance Criteria, and Stop Conditions.

## Frozen research contract

16. Treat `docs/research_v2/` as DESIGN FREEZE input and do not modify it by default.
17. Record design deviations in new evidence documents; do not silently rewrite the frozen contract to match an implementation.
18. Any future legacy-code migration must be evaluated module by module, preserve explicit source provenance, and be authorized as a dedicated migration task. Never copy the legacy source tree wholesale.

## External actions

Without separate authorization, do not push, merge, release, publish a package, configure a GitHub remote, or create a GitHub repository.

## Completion Git Policy

1. Every completed and verified Goal must leave its working tree clean.
2. Every formal source, test, documentation, or fixture change must be recorded in a local Git commit.
3. This repository has ongoing authorization for remote synchronization: after completing a stage or Goal, push the current feature branch to `origin`.
4. Never merge `main` automatically.
5. Never force-push.
6. Whether generated outputs are committed remains governed by `.gitignore` and the repository artifact policy; remote synchronization does not mean uploading every file.
7. If a task fails or reaches a STOP condition, do not present unverified results as a completed commit. A WIP branch may be preserved when needed, but it must be labeled explicitly.
8. Every completion report must include the branch, local HEAD, remote branch SHA, push status, and working tree status.

## Incremental knowledge capture

Use `docs/workflow/README.md` as the human entry point and
`docs/workflow/workflow.json` as the machine-readable capability index.

At the close of every completed and verified stage, assess whether the following
records require an incremental update:

1. **Stage record:** Update the corresponding stage index when the stage adds,
   repairs, or verifies a capability.
2. **Pitfall record:** Add or update a `PIT-*` record only when a new issue has
   cross-task reuse value and is supported by evidence. Do not duplicate an
   existing pitfall or create one from speculation.
3. **Workflow or Skill:** Update the workflow contract or backend-porting Skill
   only when the general execution process, acceptance contract, or backend
   migration method changes materially. Ordinary feature implementation must not
   rewrite the complete playbook.

Preserve historical reports. Record later corrections through explicit commit
and evidence references instead of silently rewriting frozen history.

If a stage is incomplete, preserve a clearly labeled checkpoint and do not claim
completion. Chat transcripts are not archival records by default; preserve only
final design decisions, implementation facts, verification evidence, and
reusable lessons.
