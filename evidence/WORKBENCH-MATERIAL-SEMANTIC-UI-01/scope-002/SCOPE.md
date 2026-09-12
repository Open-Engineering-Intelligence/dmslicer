# 09B scope correction — supersedes design-001 where in conflict

Goal ID remains WORKBENCH-MATERIAL-SEMANTIC-UI-01. Formal task title: DM-Slicer｜09B 材料与语义配置工作区. Historical names: 08J → Workbench 材料与语义配置工作区 → 09B. User explicitly restricted scope after the first model GREEN and before UI verification. Previous unverified UI patch and browser test are preserved here; they are not accepted implementation evidence.

## Scope

Material library CRUD limited to add/edit, JSON extensible properties, explicit semantic roles and material assignments for stable block/region input objects, display color default/override, standalone annotation manifest with source references, timestamps, decision history, library version, export/import and local persistence. Extend existing workbench with minimal page tabs required for these forms. 09A receives only stable entity references, assignments and display configuration data; no geometry algorithms or shared mutable mesh.

## Acceptance Criteria

- Material key remains stable through rename/edit; name, color, description and JSON properties validated and saved independently.
- Geometry role stays read only; Semantic role defaults Unassigned and is explicitly human selected. Source / Gradient do not construct MaterialRegion / InterfaceSourceBoundary / volumetric field. No Phase II claim.
- Material and semantic role remain independent; color inherits material unless explicit recorded override. Adding a material returns to original object without auto assignment.
- Stable input block/region objects support configuration. Derived interface/patch/fused/corrected/remaining objects show geometry facts but cannot masquerade as input material regions; run-local objects have disabled persistent domain configuration.
- Save/export/import record source scope, stable entity reference and provenance, human decisions, library snapshot/version, override, time; source mismatch, invalid annotation, material edit/save failure preserve prior valid state. Full source facts remain in existing viewer evidence sections.
- Test-first model and actual browser checks cover add/edit/return, role/material/color independence, persistence recovery/error and stable handoff data; preserve failures and final manifest with recoverable local copies.

## Stop Conditions

Stop after scoped features, targeted regression/browser checks, local commits and evidence manifest/copies. No push/merge/release. No docs/research_v2 changes. No geometry/scientific rerun. No new geometry viewer main-interface design. Bulk object selection, per-object/bulk transparency and single evidence drawer are removed from 09B acceptance and left for 09A. Existing geometry controls remain baseline behavior; the previous browser acceptance steps for those controls are historical unimplemented 09A intent only.

## Phase model configuration

Architecture-boundary phase requested Astra / High; user requested Terra / Medium for subsequent UI implementation and browser tests. Request received in task delegation. This running tool interface does not expose a direct active-turn model setter, so actual model switch is not independently verified. Escalation to architecture review is reserved for substantive truth/semantic/persistence conflicts.

## Independent persistence and handoff

Material library: dmslicer.material-library.v1, user-supplied material IDs, version and history; dedicated browser key and export/import. Workspace: dmslicer.workspace-annotation.v1, source-scoped stable references, immutable geometry_role, explicit semantic/material/override, decisions, library snapshot. Neither file is a geometry result package. Source identity matching is provenance validation only, not geometry equivalence. Display color lookup consumes only the annotation and stable entity_ref. Existing viewer is kept for local preview, no geometry geometry_role mutation.
