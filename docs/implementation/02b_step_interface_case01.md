# CASE01 STEP Interface Engine Implementation Plan

**Goal:** Deliver only the CASE01 STEP → FreeCADCmd B-rep → evidence chain for A, G, B.

**Architecture:** The host-side Python package creates a deterministic JSON request and invokes FreeCADCmd with a small adapter script. The adapter generates/imports STEP, extracts B-rep facts, identifies coincident planar source faces by B-rep common area, and emits JSON-only DTOs. The host publishes the required evidence files and compares two independent analysis processes.

**Constraints:** FreeCAD/Part is the geometry authority; no mesh/UI/solver/slicing code; `docs/research_v2/` is immutable. CASE01 coordinates follow this Goal (`x=0..30`), a +15 mm translation from the frozen illustrative fixture; record it as an implementation deviation without editing the freeze.

## Files

- Create `src/dmslicer/__init__.py`, `identity.py`, `runner.py`, `evidence.py`, `__main__.py`: deterministic identities, FreeCADCmd invocation, result validation, artifact publishing and the headless CLI.
- Create `src/dmslicer/freecad_case01.py`: headless FreeCAD adapter for capability probing, STEP generation/import, B-rep analysis, explicit geometric provenance and JSON response.
- Create `benchmarks/interface_case01/case01.step` and `expected.json`: tracked three-solid STEP and semantic truth/tolerance manifest.
- Create `tests/test_case01.py`: targeted import, relation, patch, area, provenance, identity and cross-process assertions.
- Create `outputs/step_interface_case01/`: generated probe/run evidence (not source code).

## Execution

1. Probe actual FreeCADCmd capabilities and save `capability_probe.json`, including Boolean history availability. If history is unavailable, use explicit geometric matching only when both source faces contain the same B-rep common-area face, with matching area and fingerprints; label the method/status.
2. Generate A `[0,10]`, G `[10,20]`, B `[20,30]` boxes with Part; export `case01.step`; discard generation objects; re-import the STEP before all analysis.
3. Build document, region and source-face IDs from the STEP SHA-256 plus canonical, orientation-independent B-rep fingerprints; construct each patch ID from the ordered region/face IDs plus common-face fingerprint. No ordinal, object address or UUID is a persistent ID.
4. For every region pair, record AABB candidate evidence, then verify B-rep face common areas. Accept A-G/G-B as `FACE_CONTACT`, dimension 2, 400 mm², one connected patch; record A-B as `DISJOINT`.
5. Serialize `manifest.json`, `regions.json`, `relations.json`, `interface_patches.json`, `provenance.json` and `repeatability.json` under `outputs/step_interface_case01/`. `manifest.json` includes input hash, Git state, versions, tolerance and run timing.
6. Run the adapter twice in independent FreeCADCmd processes and compare IDs, relation/dimension/area and provenance mappings. Run the targeted tests; retain only CASE01 changes.
