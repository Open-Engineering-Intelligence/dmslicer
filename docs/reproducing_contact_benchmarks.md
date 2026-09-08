# Reproducing the A01–A06 canonical contact benchmark

This repository currently publishes the verified A01–A06 canonical Contact subset only. It does not claim coverage of curved cases, tolerance sweeps, or general CAD contact analysis.

## Verified environment

The checked run used Python 3.12, FreeCAD 1.1.1, and OCCT 7.8.1 through `FreeCADCmd --safe-mode`. Other environments may produce different STEP serialization or numerical rounding; this document makes no cross-platform equivalence claim.

## Inputs and truth

- Authoritative STEP inputs, analytic expected truth, and construction parameters: `benchmarks/contact_canonical_03a/`.
- Frozen benchmark definitions: `docs/benchmark_design/`.
- Fixture/analysis entry points: `src/dmslicer/contact_canonical_03a.py` and `src/dmslicer/freecad_contact_03a.py`.

The authoritative sources are the tracked STEP files, the frozen benchmark specification, and the analytic `expected.json` files. Expected truth is validation input only: actual B-rep evidence is produced first from the reimported STEP.

## Commands

Set `PYTHONPATH=src` before running these commands.

```powershell
# Analyze one tracked case and write ignored run evidence.
py -3.12 -m dmslicer analyze-contact-canonical benchmarks/contact_canonical_03a/A01/fixture.step outputs/contact_canonical_03a/A01

# Analyze all six cases and run two-process repeatability checks.
py -3.12 -m dmslicer run-contact-canonical-suite benchmarks/contact_canonical_03a outputs/contact_canonical_03a

# Run the test suite.
py -3.12 -m pytest -q
```

Generated runtime evidence belongs under the ignored `outputs/contact_canonical_03a/` directory. It is not a versioned research input.

## Inspecting the FreeCAD artifacts

Open `artifacts/freecad_debug/A01.FCStd` through `A06.FCStd` in FreeCAD. Each contains `Body_1`, `Body_2`, and `Actual_Result`; the latter is the result shape produced by the verified analysis. These FCStd files are **non-authoritative human-inspection artifacts**. They, screenshots, and runtime outputs must not be used as geometry truth or as production-test inputs.

`artifacts/reference_results/contact_canonical_03a.json` is a compact, path-free verified reference result. It is a release/review aid, not production input.
