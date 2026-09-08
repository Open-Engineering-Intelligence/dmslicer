# 03C Contact Canonical Interface Topology — implementation note

Scope: semantic-free, two-body STEP/B-rep analysis for the frozen Level A
topology diagnostics A11 and A12.  The analyzer receives only two solids
re-imported from each tracked STEP fixture; expected truth is loaded only after
actual geometry and topology evidence has been written.

| Frozen case | New factor | Bodies / solids | Independent truth | Planned files |
|---|---|---:|---|---|
| A11 | Two disconnected planar interface components for one body-pair | 2 / 2 connected solids | Two disjoint `a_f × b_f` planar rectangles, `component_count=2`, two outer boundary loops, zero holes, total area `2a_fb_f` | `contact_canonical_03c.py`, `freecad_contact_03c.py`, `__main__.py`, `test_contact_canonical_03c.py`, tracked A11 fixture/expected/parameters |
| A12 | One connected planar annular interface with one hole | 2 / 2 connected solids | Annulus `π(r_o²-r_i²)`, `component_count=1`, two boundary loops (outer and hole), `hole_count=1` | same, plus tracked A12 fixture/expected/parameters |

The implementation retains every positive-area direct face-common result as
raw evidence.  It groups those results into contract patches/components from
actual geometric adjacency, derives boundary loops from the compound boundary
(not from edge counts or seam heuristics), deduplicates area by actual patch
geometry, and records the complete many-to-many source-face linkage for each
component.  Debug geometry is the actual analysis result; expected values never
select or construct output geometry.
