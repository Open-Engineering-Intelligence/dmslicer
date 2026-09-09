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
- The evidence-backed FreeCAD implementation now covers CASE01, selected canonical
  relation/topology cases, bounded partition/union operations, and the 05A--05C
  tolerance pilots through the fixed documentation baseline
  `fa4436a2784574ffa336e87a9df898c35780a587`.
- This is not a complete geometry engine: general assembly handling, a second
  backend, gradient fields, slicing, toolpaths, and G-code remain unimplemented or
  design-only.

Start with the [workflow and backend portability map](docs/workflow/README.md).
Its status labels distinguish implementation, recorded validation, available
evidence, limitations, plans, and work not re-verified in the current checkout.

The earlier AMF-based prototype is preserved separately as a frozen research baseline. This repository does not inherit the legacy Git history. Legacy algorithms and results may inform research comparisons, but they are not the implementation of this repository.

No license has been selected for this repository.
