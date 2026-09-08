# 03A Contact Canonical — implementation note

Scope: semantic-free, two-body STEP/B-rep analysis for the first six frozen Level A cases. Input is only the tracked STEP, its two imported occurrences, and explicit mm/mm²/mm³ tolerances. Expected truth is read only after actual evidence is written.

| Frozen case | Relation | Geometry definition | Analytic truth | Main files |
|---|---|---|---|---|
| A01 | `full_full`, 2D | Equal prisms with coincident end faces | common rectangle area; both coverages 1 | `freecad_contact_03a.py`, `contact_canonical_03a.py` |
| A02 | `partial_partial`, 2D | A01 prisms with tangential x offset | overlap rectangle area; partial coverages | same |
| A03 | `small_face_contained_in_large_face`, 2D | Small prism end face inside large prism end face | small rectangle area; one coverage 1 | same |
| A04 | `point_touch`, 0D | Sphere tangent to finite plate | one tangent point | same |
| A05 | `edge_touch`, 1D | Two prisms sharing only one edge | shared edge length | same |
| A06 | `solid_material_interference`, 3D | Offset prisms with positive box overlap | common-solid volume | same |

All raw coordinates are uniformly normalized so the current pair bounding-box diagonal is 100 mm. The concrete raw dimensions and scale are stored beside each fixture in `benchmarks/contact_canonical_03a/<case>/parameters.json`; expected measures are independently calculated from the frozen analytic constructions. Debug files retain the imported bodies and the actual B-rep result, not a shape reconstructed from expected data.
