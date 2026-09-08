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
