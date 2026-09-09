# DM-Slicer backend-porting pitfalls

These are traceable review rules, not a replacement for the historical
diagnoses. Apply only the entries relevant to the selected `G*` steps. A repair
commit proves a scoped repository change; it does not create a universal CAD
law. Validation recorded by older documents was not rerun for DOC01.

## PIT-001 — Expected truth leaks into actual geometry

- **Symptom:** changing `expected.json` changes selected faces, measured geometry,
  constructed patches, or operation results.
- **Affected stages:** G02--G06.
- **Evidence-supported cause:** actual and expected pipelines were not kept
  independent. The exact origin of any new occurrence is `NOT_CONFIRMED` until
  traced.
- **Scope:** general/project.
- **Preventive check:** write and persist actual evidence before reading expected;
  mutate expected and confirm only the validation verdict changes.
- **Test index:** `tests/test_case01.py::test_expected_truth_mutations_cannot_change_frozen_geometry`;
  analogous mutation tests in `test_contact_canonical_03a.py`, `03b.py`, `03c.py`,
  `test_contact_partition_union_04a.py`, and `test_contact_scale_covariance_pilot_05b.py`.
- **Repair/evidence commits:** truth isolation `07655b8`; stage implementations
  preserve the same property.
- **Boundary:** expected values may validate actual output after it is frozen; they
  may not select or manufacture actual geometry.

## PIT-002 — Minimum plane distance is mistaken for interface signed offset

- **Symptom:** A01 penetration is reported as a positive gap or the measured
  offset comes from a non-nominal supporting-plane pair.
- **Affected stages:** G02, G03.
- **Evidence-supported cause:** minimization over all qualifying horizontal
  supporting planes selected the closest unrelated pair.
- **Scope:** project/FreeCAD calling path; the conceptual distinction is general.
- **Preventive check:** bind corresponding interface roles first, then measure the
  signed offset of that pair; retain candidate audit records.
- **Test index:** `test_a01_role_constrained_measurement_uses_tracked_penetration_interface`,
  `test_a01_role_constrained_measurement_uses_archived_minus_four_interface`, and
  role rejection tests in `tests/test_contact_tolerance_pilot_05a.py`.
- **Repair/evidence commits:** diagnosis `52db2a8`; repairs `0d681a9`, `fa4436a`;
  tracked evidence `artifacts/reference_results/05c_a01_candidate_probe.json`.
- **Boundary:** this proves the A01 role-constrained repair, not a general automatic
  correspondence algorithm.

## PIT-003 — Support-surface Axis is mistaken for outward face normal

- **Symptom:** the sign or side of a planar/cylindrical offset is reversed even
  though support surfaces appear parallel or coaxial.
- **Affected stages:** G01--G03.
- **Evidence-supported cause:** a geometric support Axis is unoriented with respect
  to the trimmed face and its body; face orientation/outward normal carries the
  missing sign.
- **Scope:** general B-rep concept; FreeCAD mapping is binding-specific.
- **Preventive check:** record support Axis, face orientation, and evaluated outward
  normal separately; use the contract-required one.
- **Test index:** A01 role/source and measured-offset tests in
  `tests/test_contact_tolerance_pilot_05a.py`.
- **Repair/evidence commits:** `0d681a9`, `fa4436a`; diagnosis in
  `docs/analysis/05c_a01_candidate_probe.md`.
- **Boundary:** the exact normal-evaluation API must be reprobed for each backend.

## PIT-004 — Full sphere, hemisphere, shell, and fill intent are conflated

- **Symptom:** a result with the right radii is accepted even though the wrong half
  is filled, an intended cavity disappears, or an exposed sphere face is described
  as an internal cavity wall.
- **Affected stages:** G04--G06.
- **Evidence-supported cause:** construction labels and weak radius/volume checks
  did not encode the target material/void region.
- **Scope:** project case semantics; target-property principle is general.
- **Preventive check:** define the target with independent reference solids,
  bidirectional material differences, internal/external samples, and boundary
  properties.
- **Test index:** `test_u01_rejects_half_shell_plus_full_core_with_same_radii`,
  `test_u03_rejects_filled_lower_cavity` in `tests/test_shell_fill_04a2.py`.
- **Repair/evidence commit:** `1935427`.
- **Boundary:** these negative candidates cover U01/U03, not every shell topology.

## PIT-005 — Valid, closed, connected, or equal-volume is treated as target shape

- **Symptom:** an operation passes while required material is missing, extra
  material exists, a cavity is wrong, or a final-gate field is merely recorded.
- **Affected stages:** G05, G06.
- **Evidence-supported cause:** proxy shape-health properties were substituted for
  target-shape acceptance.
- **Scope:** general.
- **Preventive check:** combine health properties with bidirectional reference
  differences, material/void samples, intended boundary properties, and all
  operation-specific required fields in the final verdict.
- **Test index:** shell-fill negative candidates; 04A
  `test_production_validation_rejects_excess_volume_error` and
  `test_production_validation_rejects_invalid_or_disconnected_union`.
- **Repair/evidence commit:** `1935427`.
- **Boundary:** the required target properties are case-specific; no single metric
  is sufficient universally.

## PIT-006 — A12 representation conversion and post-hoc threshold relaxation

- **Symptom:** analytic plane/circle geometry becomes B-spline geometry and the
  area deviates; an unsupported tolerance is proposed only after observing it.
- **Affected stages:** G01, G03, G06.
- **Evidence-supported cause:** `TopoShape.transformGeometry` in the A12 generator
  converted support/boundary representations before STEP export; STEP re-import
  was not the principal cause in that retained probe.
- **Scope:** confirmed for A12/FreeCAD path; broader transform behavior is
  `NOT_CONFIRMED`.
- **Preventive check:** construct normalized analytic geometry directly and retain
  pre/post-import surface-family checks; use pre-existing acceptance thresholds.
- **Test index:** A12 analytic representation and strict rejection tests in
  `tests/test_contact_canonical_03c.py`.
- **Repair/evidence commit:** `4a2aad8`.
- **Boundary:** do not generalize the `1e-8 mm²`/`1e-7` limits to arbitrary B-spline
  or external STEP inputs.

## PIT-007 — Periodic seams, degenerate edges, holes, and components are confused

- **Symptom:** one periodic contact becomes multiple semantic patches, or an
  annular hole/disconnected component count is inferred from raw edge/face count.
- **Affected stages:** G03, G04, G06.
- **Evidence-supported cause:** representation seams and raw topology enumeration
  were used as geometric patch topology.
- **Scope:** general B-rep issue; current checks cover selected analytic fixtures.
- **Preventive check:** group by actual geometric adjacency; derive component and
  boundary-loop topology from compound geometry; record seam/degenerate status.
- **Test index:** analytic component test in `test_contact_canonical_03b.py` and
  topology/A12 tests in `test_contact_canonical_03c.py`.
- **Repair/evidence commits:** `5e96906`, `1c227cf`, `4a2aad8`.
- **Boundary:** arbitrary non-manifold and degenerate external models remain
  `NOT_VERIFIED`.

## PIT-008 — Coverage denominator follows incidental face partitioning

- **Symptom:** coverage changes when the same semantic carrier is split into a
  different number of raw faces.
- **Affected stages:** G04, G06.
- **Evidence-supported cause:** raw face area/count was used without declaring the
  participating carrier region and matching rule.
- **Scope:** general.
- **Preventive check:** record numerator geometry, carrier denominator geometry,
  side, and aggregation rule; compare semantic coverage, not raw face counts.
- **Test index:** CASE01 patch coverage/repeatability tests; 03A planar coverage;
  U04--U06 coverage checks.
- **Repair/evidence commits:** `b646027`, `bd831be`, `5ce13c7`.
- **Boundary:** a full source-face denominator and a selected carrier-band
  denominator are different valid metrics when labeled explicitly.

## PIT-009 — Face number or enumeration order is treated as stable identity

- **Symptom:** results change after re-import, process restart, or harmless raw-face
  reorder despite equivalent geometry.
- **Affected stages:** G01, G02, G04, G07.
- **Evidence-supported cause:** ordinal identity or ordered serialization was used
  beyond its local audit role.
- **Scope:** general; FreeCAD `FaceN` is one instance.
- **Preventive check:** use input hash, occurrence locator, orientation-independent
  geometry fingerprints, semantic grouping, and unordered repeatability
  comparison. Keep source ordinal only as non-persistent trace evidence.
- **Test index:** CASE01 identity tests and
  `test_repeatability_snapshot_accepts_identical_records_and_unordered_output`;
  03C reverse raw-order topology tests.
- **Repair/evidence commits:** `e6d9a86`, `79f60fa`, `b646027`.
- **Boundary:** geometry fingerprints are not a proof of cross-kernel canonical
  identity; collisions/quantization remain an adapter concern.

## PIT-010 — Kernel tolerance, engineering tolerance, numeric epsilon, and movement budget are merged

- **Symptom:** changing one tolerance silently changes candidate generation,
  engineering classification, validation, and authorized geometry movement.
- **Affected stages:** G00--G06.
- **Evidence-supported cause:** the research contract identifies distinct `tauK`,
  `tauE`, metric epsilons, and action budgets; a single-value cause for any new
  adapter is `NOT_CONFIRMED` until traced.
- **Scope:** general/project contract.
- **Preventive check:** name, unit, source, consumer, and permission effect for each
  tolerance; record nominal and any fuzzy pass separately.
- **Test index:** inclusive `tauE` boundary test in 05A; fixed-`tauE` non-scaling
  test in 05C.
- **Repair/evidence commits:** `312bc7d`, `bb2eb89`; design source
  `docs/benchmark_design/tolerance_protocol.md`.
- **Boundary:** proximity acceptance never grants movement or topology repair.

## PIT-011 — Raw absolute error and scale-normalized error are conflated

- **Symptom:** a sample is called passing/failing without saying whether the limit
  applies in native units or after `s`, `s²`, `s³` normalization.
- **Affected stages:** G03, G06, G07.
- **Evidence-supported cause:** 05B's original `native_validation` did not compare
  same-scale area/volume under fixed absolute limits, yet its label invited an
  overbroad reading.
- **Scope:** general dimensional analysis; counts are specific to 05B.
- **Preventive check:** report native absolute and scale-normalized results as
  separate verdicts with length/area/volume normalization dimensions.
- **Test index:** all normalization and separate-pass/fail tests in
  `tests/test_contact_scale_covariance_pilot_05b.py`.
- **Repair/evidence commit:** `1de21fd`.
- **Boundary:** the documented revalidation reused saved actual records and did not
  rerun FreeCAD.

## PIT-012 — Out-of-domain input is counted as method failure

- **Symptom:** an impossible A07 construction is generated anyway or is counted as
  a measured algorithm mismatch.
- **Affected stages:** G01, G03, G06.
- **Evidence-supported cause:** construction-domain validity and analysis outcome
  were not represented as separate states.
- **Scope:** general; current formula is A07-specific.
- **Preventive check:** evaluate and retain `CONSTRUCTIBLE` versus
  `OUT_OF_CONSTRUCTION_DOMAIN` before generation; keep excluded rows in the plan
  denominator without inventing measurements.
- **Test index:** `test_a07_domain_rejects_non_positive_and_outer_radius_bore` and
  `test_manifest_has_all_planned_rows_and_keeps_domain_exclusions` in 05C tests.
- **Repair/evidence commit:** `bb2eb89`.
- **Boundary:** unsupported backend capability is also not a method-accuracy
  failure; report it separately.

## PIT-013 — A required check is recorded but not wired into final FAIL

- **Symptom:** evidence contains a failed volume/validity/closedness/connectivity or
  provenance field while top-level status remains PASS.
- **Affected stages:** G05, G06.
- **Evidence-supported cause:** the 04A final status gate omitted required shape
  properties before the 04A2 repair.
- **Scope:** general status-aggregation rule; confirmed repair is project-specific.
- **Preventive check:** enumerate required checks, derive final status exclusively
  from that set, emit structured `failures`, and mutation-test each gate input.
- **Test index:** production validation rejection tests in
  `tests/test_contact_partition_union_04a.py`.
- **Repair/evidence commit:** `1935427`.
- **Boundary:** informational fields need not fail the run, but must be declared
  informational rather than silently excluded.

## PIT-014 — Cross-stage inputs, fixed hashes, and ignored outputs lose provenance

- **Symptom:** a test expects a hash no reachable commit contains; a later stage
  references mutable earlier outputs; or a report points only to missing ignored
  `outputs/` files.
- **Affected stages:** G01, G06, G07.
- **Evidence-supported cause:** CASE01 had an invalid fixed hash constant; 05B had
  to distinguish tracked 05A inputs from generated scale inputs. Ignored-output
  disappearance has multiple possible causes and is otherwise `NOT_CONFIRMED`.
- **Scope:** project/reproducibility.
- **Preventive check:** trace bytes to a reachable blob, record repository-relative
  source path and SHA-256, archive the minimum immutable bundle, and label any
  uncommitted evidence `LOCAL_ONLY`.
- **Test index:** CASE01 fixture-integrity assertion; 05B tracked-input preservation;
  05C materialization preservation.
- **Repair/evidence commits:** `e50e1b8`, `2fe54de`, `fa4436a`.
- **Boundary:** a summary hash authenticates a referenced artifact but does not
  replace the artifact's measurements.

## PIT-015 — Duplicate backend/test launches and stale evidence are called new validation

- **Symptom:** multiple FreeCAD/pytest processes are started accidentally, or a
  historical log/summary is reported as if it were produced in the current run.
- **Affected stages:** G00, G06, G07.
- **Evidence-supported cause:** current stage runners deliberately launch two
  independent FreeCAD processes for repeatability; the specific cause of any
  accidental duplicate launch is `NOT_CONFIRMED` until process/request evidence is
  inspected.
- **Scope:** general operations/project runners.
- **Preventive check:** assign a run ID and expected process count, capture command
  and versions, wait for the intended process, and distinguish `CURRENT_RUN`,
  `DOCUMENTED_VALIDATION`, and saved-actual-only revalidation.
- **Test index:** suite repeatability tests across CASE01, 03A--03C, 04A2, 04B;
  `test_revalidation_reports_missing_actual_as_incomplete` for saved-record checks.
- **Repair/evidence commits:** repeatability foundation `b646027`; 05B reporting
  correction `1de21fd`; 05C evidence classification `5dd0359`.
- **Boundary:** two deliberately independent analyses are required evidence, not a
  duplicate-run bug; DOC01 itself runs neither FreeCAD nor the full regression.

## Porting review checklist

| Before accepting a capability | Applicable rules |
|---|---|
| Import/identity | PIT-006, PIT-009, PIT-014 |
| Candidate/correspondence | PIT-002, PIT-003, PIT-009 |
| Relation/measurement | PIT-007, PIT-010, PIT-011, PIT-012 |
| Patch/provenance | PIT-001, PIT-007, PIT-008, PIT-009 |
| Geometry operation | PIT-004, PIT-005, PIT-010, PIT-013 |
| Evidence/replay | PIT-001, PIT-011, PIT-014, PIT-015 |
