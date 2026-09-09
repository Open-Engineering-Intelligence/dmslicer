---
name: dmslicer-backend-port
description: Use when migrating DM-Slicer geometry capabilities to a new CAD API or backend, reproducing an existing capability in another kernel or binding, or establishing cross-backend equivalence validation.
---

# DM-Slicer Backend Port

## Overview

Port observable geometry semantics and evidence, not function names. Treat
geometry facts, material semantics, and permission to modify geometry as separate
records. This skill does not replace a geometry kernel, authorize movement or
shape changes, merge branches, hide missing capabilities, or replay all project
history.

## Workflow

1. Read the requested capability and operation permission. Load only the relevant
   `G00`--`G07` entries from `docs/workflow/workflow.json`.
2. Read the matching semantics in `docs/workflow/backend_contract.md` and only
   applicable `PIT-*` rules in `docs/workflow/pitfalls.md`.
3. Record target software, kernel, binding, and versions; consult that exact
   version's official API documentation.
4. Run a minimal capability probe. Mark each result `AVAILABLE`, `PARTIAL`,
   `UNSUPPORTED`, or `NOT_VERIFIED`; do not infer binding support from kernel docs.
5. Map the smallest adapter slice. Reuse immutable inputs, independent truth, and
   acceptance properties; classify FreeCAD-specific test code before adapting it.
6. Write actual evidence before reading expected truth. Compare relations,
   dimensions, applicable measures, common/remainder properties, topology,
   coverage denominators, material/void, and required provenance.
7. Run export/re-import and independent replay where required. Apply only limited,
   evidence-supported corrections, then report supported, unsupported, and
   unverified capabilities separately.

## Capability decision

| Probe result | Decision |
|---|---|
| Required semantic capability available | Map and validate the smallest slice |
| Native history absent but direct-face provenance satisfies declared scope | Label the narrower provenance mode and its boundary |
| Required capability absent | Report `UNSUPPORTED`; narrow scope or stop |
| Mesh approximation only | Use only when explicitly allowed; do not claim B-rep equivalence |

## Common mistakes

- Treating the same OCCT kernel through two applications as independent-kernel evidence.
- Comparing FaceN, raw face count, STEP bytes, or B-rep serialization hashes.
- Running Fuse during detection without explicit operation authorization.
- Calling an old FreeCAD report or static document check a new-backend pass.

## Invocation and loading check

Invoke explicitly with: `$dmslicer-backend-port Port G03--G04 to <backend> and
report unsupported capabilities.` Confirm the loaded instructions mention
`docs/workflow/workflow.json`; if not, stop and load this `SKILL.md` before API
mapping. Start with `docs/workflow/README.md` when historical stage context is
needed.
