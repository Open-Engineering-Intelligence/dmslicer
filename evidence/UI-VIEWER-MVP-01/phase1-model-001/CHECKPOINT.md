# UI-VIEWER-MVP-01 — Phase 1 model checkpoint

## Scope, acceptance and stop

Scope: read-only GeometrySnapshot v0.1 projection, optional SlicerDecision v0.1
overlay, deterministic JSON model and model tests. Baseline:
`1ca211ccf78e31d05920d1769957b63bb5e20782`. Branch:
`feat/ui-viewer-mvp-01`.

Acceptance: public Snapshot validation precedes entity projection; invalid
Decision cannot damage a valid Snapshot view; absent collections remain distinct
from empty collections; entity IDs and explicit references drive navigation;
input data is never modified; CAD contents and geometry runtimes are not used.

Stop: human review of Phase 1. No render.py, HTML, CLI, search, filters, JSON CLI
export, future-stage implementation or plugin architecture has been added.

## Implemented boundary

`dmslicer.viewer.build_viewer_model(snapshot, decision=None, *, repository_root)`
returns an independent JSON-serializable dictionary. `validation.snapshot` is
the public Snapshot validator result; `validation.decision` is public Decision
schema validation; `validation.overlay` separately reports the approved Viewer
association and entity-reference checks. These results are not CAD validation.

The overlay checks input Snapshot ID, provenance reference, selected interface,
selected patch existence/membership, target region existence, and expected
partition references. They do not decide eligibility or activate semantics.

The authoritative baseline Decision schema constrains `decision_id` syntax.
The baseline identity helper and test mock generate IDs, but no explicit
consumer-side recomputation requirement was found. This Viewer does not recompute
Decision IDs. Likewise, the architecture specification's SlicerDecision section
and public schema do not prescribe equality between `local_frame_ref` and a
patch frame. The Viewer does not impose that equality, reinterpret strategy or
geometry family, normalize direction vectors, or impose new selection policy.
These deliberate non-rejections are covered by model tests.

Artifact/provenance records keep raw relative URIs and separate resolution
statuses. The model generates no hrefs, absolute resolved paths or HTML.
Resolution uses filesystem metadata and resolved root containment, including
Windows junctions. Any later renderer must independently recheck containment
before generating a link; a saved status does not guarantee later availability.

## Results and preserved discrepancies

Final targeted run: **102 passed, 0 failed, 0 skipped**: 55 Viewer model tests
plus 47 frozen Geometry contract/consumer tests. See `test_reports/regression-03.xml`.
No scientific experiment, CAD equivalence test or HTML/browser test was run.

| Case | Regions / relations / interfaces / patches / components | Overlay |
|---|---|---|
| planar_full | 3 / 3 / 2 / 2 / 2 | Disabled: REJECTED / MISSING_SEMANTIC_BINDING |
| planar_partial | 2 / 1 / 1 / 1 / 1 | Enabled; COMMON 480 mm2, REMAINING 320 + 320 mm2 remain separate |
| planar_multipatch | 2 / 1 / 1 / 2 / 2 | Disabled: supplied mock Decision fails schema |
| ambiguous_relation | 2 / 1 / 0 / 0 / 0 | Disabled: REJECTED / AMBIGUOUS_INTERFACE |

All four Snapshots are valid. All four omit boundaries; zero displayed boundaries
means absent contract data, not a geometric assertion. The multipatch fixture
also omits surface partitions. Its frozen mock returns DECIDED with
`expected_partition_refs=[]`, which the unchanged public schema rejects. The
model keeps both patches and components and exposes the Decision issue at
`expected_partition_refs`. No canonical file, schema or mock was changed.

The first test-first run had 44 expected missing-implementation failures
(`test_reports/red-01.xml`). A later expanded run had 3 test-fixture failures,
97 passes and one skipped symlink test (`test_reports/regression-01.xml`). Root
cause: the frozen mock aliases its direction list to the Snapshot normal;
mutating that test Decision also invalidated its input Snapshot. The test now
deep-copies the mock output before mutation. The mock remains unchanged.
The Windows symlink privilege was unavailable, so the final test uses a real
directory junction fallback and passes without a skip.

Independent code review found one P2 failure: an artifact URI containing NUL
can make the public validator raise a path exception before returning issues.
`test_reports/review-red-01.xml` preserves the failing reproduction. The Viewer
now catches expected filesystem/path failures at the public-validator call and
returns `validation.snapshot.status=UNAVAILABLE` with a
`VALIDATION_UNAVAILABLE` diagnostic, empty entity collections and disabled
overlay. This is not a new contract validity rule or a public-validator change.
The final regression above includes this fix.

`case_summary.json` contains the actual seven-case model summaries and validation
diagnostics. It is checkpoint evidence, not a new product JSON-export feature.

## Preservation limits

This is a local Phase 1 review checkpoint, not completion of the whole Viewer
Goal. File hashes in the manifest record byte integrity only. FreeCAD/OCCT and
geometry tolerances are not applicable: this consumer performs no geometry
calculation. No external synchronization is authorized by this checkpoint.
The manifest records the implementation commit and local evidence copies; it
does not claim off-host preservation or authorize deleting historical worktrees.
