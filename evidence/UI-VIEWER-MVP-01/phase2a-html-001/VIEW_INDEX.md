# UI-VIEWER-MVP-01 — Phase 2A visual checkpoint

Scope: approved ViewerModel to one self-contained static HTML document. Only
render.py, viewer.html and test_render.py were added to product/test source.
The Phase 1 model and __init__.py are unchanged. No CLI, packaging work, search,
filters, CAD/mesh rendering or future-stage architecture was implemented.

Acceptance: readable Snapshot/Decision diagnostics, separate taxonomy and
confirmation, explicit membership and stable-ID navigation, separate partitions,
selection highlights only for enabled overlays, safe JSON embedding and no
external resources. Stop: human visual review of the four pages below.

## Open these four pages

Each page can be opened directly from disk in a JavaScript-enabled browser.
The banner always states CONTRACT TOPOLOGY / NON-GEOMETRIC VIEW. Left navigation
and main content scroll independently. Click an entity ID, then click a reference
or an entry under “Referenced by”; “Overview & diagnostics” returns to the overview.
The Decision fields appear below the overview. No depicted layout represents CAD
location, and no action changes the embedded Snapshot or its semantic bindings.

1. [planar_full](pages/planar_full.html): inspect three regions, two full-overlap
   interfaces and the DISJOINT relation. Taxonomy and confirmation occupy separate
   columns; the latter relation reads “Confirmed to be disjoint.” Follow a region
   to its declared relation and back. The mock Decision is REJECTED due to missing
   selection semantics, while the Snapshot remains VALID.
2. [planar_partial](pages/planar_partial.html): immediately compare three distinct
   rows: COMMON 480 mm2 and two REMAINING 320 mm2 partitions. Inspect each source
   locator. Left navigation marks Target region, Selected interface and Selected
   patch. Click patch:e1-common and follow component_ref/interface_ref. The Decision
   section labels expected partition references “Expected / NOT_EXECUTED.”
3. [planar_multipatch](pages/planar_multipatch.html): inspect two separate components
   and patches beneath one interface. Boundaries and Surface Partitions are ABSENT.
   The original mock's empty expected_partition_refs produces a visible Decision
   schema diagnostic; the VALID Snapshot still has full navigation and no selection
   highlighting. No contract/mock/canonical fixture was repaired.
4. [ambiguous_relation](pages/ambiguous_relation.html): inspect AMBIGUOUS taxonomy and
   confirmation. Interfaces/components/patches are ABSENT, and no interface is
   fabricated. The Decision is REJECTED / AMBIGUOUS_INTERFACE.

Artifact/provenance URIs are deliberately plain text. Displayed resolution states
are saved model observations, not current file checks. Internal artifact IDs can
open their metadata; they do not open or read the referenced CAD files.

## Verification

Final requested suite: **127 passed, 0 failed, 0 skipped**: 25 renderer tests,
55 Phase 1 model tests and 47 frozen contract/consumer tests. JUnit is retained in
test_reports/regression-02.xml. Browser tests use an existing Node/Playwright
installation, configured through DMSLICER_TEST_NODE and NODE_PATH; no package or
browser is downloaded by the tests. Browser plugin not available; used bundled
Playwright 1.62.1 / Chromium 151.0.7922.34 with a 1360 x 900 desktop viewport.

Checks passed: page identity, nonblank content, zero console/page errors, zero
external resource requests, stable-ID and reverse-reference navigation, selection
and no-selection states, INVALID/UNAVAILABLE navigation suppression, hostile
script strings displayed as text, and exact Unicode-ID fragment round trips.
Final first-screen screenshots of all four pages and the partial patch detail were
visually inspected. Mobile and other browser engines were not evaluated in this
minimal engineering-viewer phase. No CAD or scientific experiment was performed.

## Preserved development failures

- red-01.xml: seven expected failures before the renderer existed.
- render-01.xml: browser test stdout was decoded using the Windows default GBK;
  the test subprocess now explicitly uses UTF-8. This did not require a model fix.
- render-02.xml: test row selection included nested tables and detail assertions
  raced hash navigation. Tests now select top-level partition rows and wait for
  the target ID. Detail placement and compact source summaries improve readability.
- review-red-01.xml: code review identified encodeURIComponent rejecting a lone
  surrogate in an otherwise schema-accepted identifier. The before-fix page is
  retained under failure/surrogate-id-before-fix.html (a failure reproduction, not
  one of the four review pages). Fragment encoding now wraps the exact ID in JSON
  before URI encoding and decodes reciprocally. No normalization or model-contract
  change was made. The reviewer confirmed the fix with no further findings.

This checkpoint is local. It does not claim off-host preservation, CAD geometric
equivalence, or completion of the later CLI/packaging phases. Wait for human visual
review before proceeding.
