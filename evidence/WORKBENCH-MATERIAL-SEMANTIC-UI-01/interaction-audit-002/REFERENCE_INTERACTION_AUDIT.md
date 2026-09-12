# 09B interaction audit — 2026-09-12

`evidence_confidence`: `CHAT`. The task owner manually exercised `localhost:8501` and reviewed its source. This record preserves the reported findings without copying the reference implementation.

- Reuse only layout intent: object list selection plus adjacent/detail configuration; local property name/unit/value/add-property interaction.
- Library requires non-destructive Add/Edit through one prefilled editor. Reference Edit temporarily removes a material and can lose it on exit; 09B rejects that behavior.
- Color is an explicit material field and an object-row entry point to current material/display color configuration.
- Replace Initialize with confirmation or undoable reset of selected annotation drafts only. Do not unload the case or affect geometry state.
- Keep all objects re-editable; do not hide completed items in a processing-only selector.
- Apply is atomic draft-to-selected-objects; Save persists the whole workspace. Show/visibility is unrelated.
- Preserve established Source, Gradient, Isolator and Unassigned semantic rules. No geometry relation activation.
- Keep composition/property editor state structurally separate from color state; the reference's `#000000` composition leak is a preserved negative case.
- 56811 is independent development/review preview. 56810 remains frozen.

The normative implementation detail is [the interaction design](../../../docs/implementation/material_semantic_interaction_design.md).
