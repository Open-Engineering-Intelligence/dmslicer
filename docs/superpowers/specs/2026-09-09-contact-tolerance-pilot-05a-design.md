# Contact Tolerance Pilot 05A Design

## Scope

This is a deliberately limited `LEVEL_B_PILOT`, not complete Level B.  It runs
only canonical A01 (full planar contact) and A07 (coaxial shaft--bore contact),
at nominal scale 1 with `tauE = 0.1 mm`.  Each case has the frozen 15-point
signed-offset sequence, for 30 samples total.  A01 uses a rigid normal pose;
A07 regenerates only the bore radius and remains coaxial.

## Evidence boundary

Sample generation writes a tracked STEP file, construction parameters, and an
independent expected-truth record.  Analysis accepts only the imported STEP,
the explicit geometry selection/configuration, and numeric tolerances.  It
never reads the expected file, its directory name, or the configured delta.
Validation is a separate final comparison of actual evidence with expected
truth.  This makes deliberate mutations of either side detectable.

## Recorded state

Every actual record keeps separate geometric facts (distance, common material
volume, current intersection dimension, and positive common area), engineering
classification from measured offset and inclusive `tauE`, and raw direct-Fuse
facts from independent input copies.  `tauK` is reported as `NOT_AVAILABLE`
when FreeCAD/OCC cannot expose an imported value.  A 2D metric is present only
when a positive-area current common region exists.

## Implementation boundaries

`contact_tolerance_pilot_05a.py` owns host orchestration, independent truth,
validation, aggregation, repeatability, and the CLI-facing suite.  Its
FreeCADCmd companion owns geometry construction, STEP reimport, bounded
plane/cylinder measurement, direct Fuse observation, and three representative
FCStd views per case.  Existing canonical fixtures and production operations
remain unchanged.  The output bundle is generated under
`outputs/contact_tolerance_pilot_05a/` and stays untracked under artifact
policy.

## Acceptance

The tracked pilot fixture directory contains exactly thirty parameter/expected/
STEP bundles.  A suite run produces per-sample actual and validation JSON,
CSV and JSON summary, six FCStd files, a Chinese view index, conclusion,
negative validation checks, and two-process comparison.  The nominal controls
must validate, but an honest method mismatch or direct-Fuse failure remains a
reported result rather than a fabricated pass.

## Stop conditions

No rotation, tangential motion, scale sweep, fuzzy fuse, snapping, repair,
NURBS, multi-body, gradient, field, or slicing work is included.
