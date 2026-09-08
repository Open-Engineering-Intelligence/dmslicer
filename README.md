# DM-Slicer

DM-Slicer is a research repository for topology-aware and field-aware slicing for multi-material and functionally graded additive manufacturing.

The current research chain is:

```text
STEP/B-rep
→ interface topology
→ grading source boundaries
→ volumetric material field
→ slicing
```

## Current status

- Repository initialized.
- Research contract frozen in `docs/research_v2/`.
- STEP Interface Engine implementation has not started in this repository yet.

The earlier AMF-based prototype is preserved separately as a frozen research baseline. This repository does not inherit the legacy Git history. Legacy algorithms and results may inform research comparisons, but they are not the implementation of this repository.

No license has been selected for this repository.

## Canonical Contact Benchmark

The repository includes a verified A01–A06 canonical Contact subset. These cases are bounded diagnostics, not a claim that all CAD contacts are solved or that industrial validation is complete.

| Case | Relation | Dimension | Expected → actual | Absolute error |
|---|---|---:|---:|---:|
| A01 | full planar (`full_full`) | 2D | 3333.333333333333 → 3333.333333333383 mm² | 4.96e-11 mm² |
| A02 | partial planar (`partial_partial`) | 2D | 1515.151515151515 → 1515.151515151559 mm² | 4.41e-11 mm² |
| A03 | face containment | 2D | 666.666666666667 → 666.666666666659 mm² | 7.28e-12 mm² |
| A04 | point touch | 0D | 1 → 1 point | 0 |
| A05 | edge touch | 1D | 42.640143271122 → 42.640143271122 mm | 7.82e-14 mm |
| A06 | volumetric interference | 3D | 29259.210532767505 → 29259.210532641297 mm³ | 1.26e-7 mm³ |

- Fixtures and analytic truth: `benchmarks/contact_canonical_03a/`
- Verified reference results: `artifacts/reference_results/contact_canonical_03a.json`
- FreeCAD inspection artifacts: `artifacts/freecad_debug/`
- Reproduction instructions: `docs/reproducing_contact_benchmarks.md`

Tracked STEP, frozen benchmark specification, and analytic expected truth are authoritative. The FreeCAD artifacts and runtime outputs are inspection aids, not geometry truth.
