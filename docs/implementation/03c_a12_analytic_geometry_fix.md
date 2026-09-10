# 03C A12 analytic-geometry fixture fix

Scope: correct only the A12 canonical fixture-generation path.  The prior
fixture was generated from the `1c227cf` implementation baseline by uniformly
scaling raw shapes with `TopoShape.transformGeometry`.  The retained diagnostic
probe localized the principal area deviation to that operation: it converted
the A12 plane and circular boundaries to B-spline geometry before STEP export.
STEP re-import was not the principal source of the deviation.

The repaired A12 branch derives `lambda = 100 / sqrt(50^2 + 50^2 + 15^2)` from
the unchanged raw parameters, then directly constructs the plate dimensions,
washer radii, height, and placement at normalized dimensions.  It does not
hard-code a printed lambda value and does not modify analyzer selection,
common, identity, provenance, or topology grouping behavior.

| Item | Before | After |
|---|---:|---:|
| `fixture.step` SHA-256 | `4afdb043c6bfa95de82bab806ae2feb2844600d930e41e832b6874b46672f1d3` | `2f5103a555ceae4faad2666e82c8a7c67d59f8b92d0d78e2ec1e3f2c42d5574a` |
| A12 actual area (mm²) | `1803.7424900293495` | direct construction is verified against the unchanged analytic `1803.7852556496418` value |
| Contact representation | `BSplineSurface` / two `BSplineCurve` boundaries | `Plane` / two `Circle` boundaries before export and after STEP re-import |

The analytic truth, coverage, relation, and topology truth remain unchanged.
The unsupported `validation_tolerances` metadata (`0.05 mm²`, `1e-4`) is
removed.  Validation now uses the pre-existing 03A/03B comparison semantics:
an explicit absolute area difference no greater than `1e-8 mm²` and an
explicit absolute coverage difference no greater than `1e-7`; no relative
tolerance is applied.  These values are the analytic canonical benchmark
acceptance baseline, not a general claim for arbitrary B-spline or external
STEP input.

The repair evidence and reopenable debug model are published under
`outputs/contact_canonical_03c/a12_analytic_geometry_fix_20260909/`.
