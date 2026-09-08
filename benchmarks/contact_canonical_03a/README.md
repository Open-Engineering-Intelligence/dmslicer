# Canonical Contact Benchmark 03A

This directory is the authoritative fixture bundle for the completed planar/low-dimensional diagnostic subset of the Level A Contact Benchmark: A01–A06. Each case directory contains one tracked `fixture.step`, its analytic `expected.json`, and `parameters.json` describing the normalized construction. The fixture generator is `src/dmslicer/contact_canonical_03a.py`.

| Case | Canonical relation | Dimension | Analytic measure |
|---|---|---:|---|
| A01 | `full_full` | 2D | common area |
| A02 | `partial_partial` | 2D | common area |
| A03 | `small_face_contained_in_large_face` | 2D | common area |
| A04 | `point_touch` | 0D | point count |
| A05 | `edge_touch` | 1D | common length |
| A06 | `solid_material_interference` | 3D | common volume |

The governing research definitions remain the frozen files in `docs/benchmark_design/`. `expected.json` is independent analytic truth used only after the STEP-based actual analysis has been published; it must not select geometry, pairs, dimensions, or measures.

The versioned reference snapshot is `artifacts/reference_results/contact_canonical_03a.json`. FreeCAD models in `artifacts/freecad_debug/` are non-authoritative human-inspection artifacts, not geometry truth or production-test inputs.
