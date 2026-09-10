# P2 CAD human review guide

Human inspection status for this evidence run is `NOT_EVALUATED`. This file is
an inspection guide, not a recorded approval.

Open the three FCStd files listed in `VIEW_INDEX.md`. Confirm that the original
uses the neutral visible appearance; the UI-only variant has changed color,
60% transparency, and hidden visibility; and the geometry-changed variant has a
larger through-hole. The display view is supporting UI evidence only. Visual
inspection does not replace the reopened-shape, tolerance-aware B-rep validation
recorded in the comparison JSON files.

Case A should read `GEOMETRY_EQUIVALENT`, `SEMANTIC_EQUIVALENT`, and
`UI_DIFFERENT`. Case B should read `GEOMETRY_DIFFERENT` and identify actual
area, volume, or Boolean-difference measurements. Serialization/reopen should
remain `GEOMETRY_EQUIVALENT` irrespective of its byte status.

Known limitations: manifold inference is `UNKNOWN`; camera evidence is
`UNSUPPORTED`; general CAD entity correspondence, arbitrary deterministic
face/edge matching, Hausdorff metrics, best-fit registration, and universal
semantic bindings are deferred.
