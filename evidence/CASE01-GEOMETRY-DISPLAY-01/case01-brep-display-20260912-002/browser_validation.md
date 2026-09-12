# Browser validation

- Human observation: the user opened the MVP and confirmed the colored model,
  three Region controls, and two Patch visibility controls render and hide/show
  as expected.
- This run adds drag-to-rotate, wheel-to-zoom, and visible-triangle hit testing.
- Automated browser interaction remains unavailable for local `file://` pages
  under the browser automation URL policy. The human observation is recorded as
  `CHAT` provenance, not as an automated browser result.

Display semantics remain unchanged: original Region B-rep meshes are not cut
by Patch meshes; the two independently tessellated common-face Patches are
display-only overlays with authoritative references.
