# DM-Slicer backend contract

This contract defines the semantics a geometry backend adapter must preserve.
API names are mappings to those semantics, not the contract itself. A port is
complete only for capabilities that were probed, mapped, and independently
validated on the exact software/kernel/binding/version combination.

Baseline for the current mapping:
`fa4436a2784574ffa336e87a9df898c35780a587`. This document did not rerun
FreeCAD and does not validate a second backend.

## 1. Backend-neutral semantic model

### 1.1 Inputs and identity

An input record contains the original file hash, format, declared unit, import
settings, backend versions, and each imported occurrence's source label,
placement, and stable locator. `Solid`, `Shell`, `Face`, `Edge`, and `Vertex`
retain their topological type. A face record distinguishes its underlying
support surface from the face's trim, orientation, and outward normal.

Two occurrences may share identical geometry but are not the same region.
Persistent identity must not depend on object address, process counter,
enumeration order, `FaceN`, or a random UUID. A copy or transform must say
whether it creates a new value or mutates an existing object; DM-Slicer
operation paths preserve archived originals and operate on copies.

Assembly support means more than reading multiple solids. A backend claiming it
must preserve occurrence identity and placement, or declare the exact limited
fallback it implements. General assembly occurrence graphs are `NOT_VERIFIED`
in the current FreeCAD implementation.

### 1.2 Geometry facts

For a pair of imported regions, keep these layers separate:

1. Candidate evidence: broad-phase proximity or surface compatibility.
2. Exact geometry: `DISJOINT`, 0D point, 1D curve/edge, 2D face patch, or 3D
   material intersection, with applicable distance/length/area/volume.
3. Engineering state: exact, within-tolerance gap/penetration, beyond-tolerance,
   or unsupported, using a separately named `tauE`.
4. Semantics: material region, interface source boundary, gradient role, and any
   application decision.
5. Action authorization: whether cut/split/fuse/movement is permitted.

Candidate evidence is not a confirmed relation. Geometry truth is not semantic
activation, and neither authorizes an operation.

### 1.3 Common and remainder semantics

`face_common(Fa, Fb)` is the positive-area intersection of two trimmed faces.
It is not interchangeable with `solid_common(A, B)`, which may produce a 3D
material region, a lower-dimensional result, or an empty shape depending on the
backend. Record both when both are needed.

For each participating carrier face `F`, `common(F)` and `remainder(F)` must
satisfy, within declared units and tolerances:

- `area(F) ≈ area(common(F)) + area(remainder(F))`;
- positive-area overlap of common and remainder is zero;
- their union does not leave `F`;
- an empty remainder is an empty result, not a fabricated zero-area Face.

Raw common faces are evidence. Semantic patches/components are geometric groups
formed from adjacency and boundary topology. Periodic seams and degenerate edges
must not silently become semantic component boundaries. Coverage records its
denominator explicitly; a raw face partition is not automatically that
denominator.

### 1.4 Operations

`cut`, `split/general-fuse`, and `fuse` are optional capabilities. An adapter may
use them only when the task explicitly authorizes that operation. Detection-only
work bypasses operations.

An operation result is accepted by target properties, not by a weak proxy. At
minimum, record result topological type/count, validity, shell closedness,
connectedness, volume/material conservation, unexpected material, missing
material, internal/external boundary properties, and STEP re-import behavior
where applicable. A valid, closed, equal-volume result can still be the wrong
shape.

### 1.5 Provenance

Provenance capability is graded, not Boolean:

- `NATIVE_BOOLEAN_HISTORY`: source→result `Generated`/`Modified`/`Deleted` or
  equivalent is exposed and probed.
- `DIRECT_FACE_COMMON`: actual common geometry is derived from an explicit
  source-face pair and the linkage is recorded.
- `GEOMETRIC_MATCH`: a separately validated geometric matching fallback.
- `UNSUPPORTED`: the required source mapping cannot be established.

These levels are not interchangeable. Missing native history must stay visible
even when direct-face-common evidence is sufficient for a narrowed task.

### 1.6 Export, errors, and unsupported states

Export records format, parameters, result hash, and producing versions. Re-import
is a new validation step. The contract distinguishes:

- `EMPTY`: operation succeeded with an empty geometric result;
- `UNSUPPORTED`: required semantics or binding are absent;
- `INVALID_INPUT` / `INVALID_RESULT`;
- `AMBIGUOUS`: available evidence conflicts or cannot select uniquely;
- `TIMEOUT`;
- `BACKEND_ERROR`: exception/crash with captured diagnostics;
- `NOT_AUTHORIZED`: operation permission is absent;
- `NOT_VERIFIED`: capability was not exercised.

None of these may be silently converted to a passing empty patch.

## 2. Minimum capability checklist

| Capability | Required observation |
|---|---|
| Runtime identity | software, kernel, binding, versions, process mode |
| STEP input | import Solid/Face, multi-solid behavior, units, placement, occurrence labels |
| Topology | traverse types, trims, orientation, outward normal, validity, closedness |
| Measurements | distance, length, area, volume with explicit units |
| Relations | solid common, section/dimension evidence, face common |
| Partition | face cut and common/remainder property checks |
| Optional operations | `cut`, `split/general-fuse`, `fuse`, copy/mutation semantics |
| Provenance | native history status and any narrower source mapping method |
| Durability | export, re-import, hash, independent-process replay |
| Failure behavior | empty, unsupported, invalid, ambiguous, timeout, exception |

## 3. Current FreeCAD mapping

The mapping below describes only capabilities demonstrated by reachable code and
tests at the baseline. Historical validation was not rerun for DOC01.

| Contract capability | FreeCAD/Part mapping in this repository | Status and boundary |
|---|---|---|
| Headless process | host Python invokes `FreeCADCmd` adapters through `src/dmslicer/runner.py` and stage runners | `IMPLEMENTED`; exact executable/version is recorded at run time |
| STEP import/export | `Import.open`, `Import.export` in `freecad_case01.py` and operation adapters | `IMPLEMENTED` for tracked fixtures; general assembly semantics `NOT_VERIFIED` |
| Solid/face traversal | `TopoShape.Solids`, `.Faces`, bounding boxes, surface records | `IMPLEMENTED` for selected valid B-rep inputs |
| Identity | file SHA-256 plus geometry fingerprints and occurrence locator in `identity.py` | `IMPLEMENTED`; not a claim of cross-kernel canonical topology identity |
| Validity/closedness | `isValid`, solid/shell counts and closed-shell checks in adapters | `IMPLEMENTED` for operation suites |
| Solid common/section | `shape.common`, `shape.section` | capability probe `AVAILABLE`; case coverage is limited |
| Face common | `face_a.common(face_b)` | capability probe `AVAILABLE`; main provenance path for selected contacts |
| Face remainder | `face.cut(common)` | `IMPLEMENTED` in 04A/04A2/04B limited cases |
| General fuse | `shape.generalFuse([other])` | probe `AVAILABLE`; do not infer full history from returned pieces |
| Direct fuse | copied shapes, `.fuse(...).removeSplitter()` | `IMPLEMENTED` for explicitly scoped operation/pilot cases |
| Native Boolean history | probe checks exposed `BRepAlgoAPI_Common`, `BRepAlgoAPI_BuilderAlgo`, `BOPAlgo_Splitter` and history methods | `NOT_AVAILABLE` in the recorded actual FreeCAD Python binding; OCCT C++ availability does not upgrade this |
| Direct-face provenance | source pair plus actual face-common geometry, fingerprints, coverage | `IMPLEMENTED`; distinct from native Boolean history |
| Analytic/topology measures | plane/cylinder/sphere/cone families, area/volume, component and boundary-loop logic | `IMPLEMENTED` only for A01--A09, A11--A12 and U01--U06 scopes described in stage docs |
| Export/re-import/repeatability | STEP/BREP/FCStd outputs in operation adapters; semantic snapshot comparison across processes | `IMPLEMENTED` for selected suites; generated `outputs/` are not durable unless separately archived |

`Part.OCC_VERSION` identifies the embedded OCCT version. It does not prove that
an OCCT API is exposed through the current FreeCAD Python binding.

## 4. Second-backend integration order

1. Record software, B-rep/mesh kernel, language binding, exact versions, license,
   process boundary, and supported file formats.
2. Select the smallest relevant `G*` subset and operation permission. Do not load
   every historical report.
3. Run G00 capability probes, including copy/mutation and failure behavior.
4. Implement G01 import, units, placement, occurrence, validity, and identity.
5. Map G02/G03 candidate, correspondence, relation, dimension, and measurement
   semantics using the smallest fixture subset that exercises the needed types.
6. Map G04 common/remainder/topology/provenance. If face-level history is absent,
   record `UNSUPPORTED` or a narrower labeled provenance mode.
7. Map G05 only when the task authorizes operations and the probe supports them.
8. Reuse independent truth and acceptance properties in G06; classify existing
   test code as portable truth/input, portable property, adapter-required test,
   or backend/version-internal test.
9. Run G07 export/re-import and independent-process evidence capture. Publish
   supported and unsupported capabilities without inflating coverage.

Function-name substitution is not a port. Each stage must establish observable
semantic equivalence.

## 5. Backend classes and claim limits

| Backend class | What it can establish | Required limitation |
|---|---|---|
| Same OCCT kernel, different application/binding | Independent calling-layer and integration evidence | Not independent-kernel validation; binding exposure and defaults may still differ |
| Different B-rep kernel | Stronger cross-kernel evidence when the same independent truth/properties pass | Topological decomposition and face counts may legitimately differ |
| Mesh-only or approximate geometry | Approximate task-specific comparison if explicitly authorized and separately toleranced | Must not claim preserved B-rep truth, exact topology, or Boolean provenance; no silent conversion |

## 6. Cross-backend comparison rules

Use the same immutable inputs where both backends can consume them, plus an
independent analytic or construction-derived truth. Compare, as applicable:

- relation and intersection dimension;
- distance/length/area/volume with declared absolute and normalized tolerances;
- common and remainder geometry properties;
- component count, connectedness, boundary components and holes;
- coverage with explicit denominators;
- material region and void/cavity properties;
- positive and reverse differences against the independent reference;
- required provenance mode and completeness;
- export/re-import and independent-process stability.

Do **not** require matching `FaceN`, traversal order, raw face count, STEP bytes,
or serialized B-rep hashes. An original file hash identifies the exact input; it
does not define geometric equivalence. A semantic patch may span different raw
face decompositions in two correct backends.

## 7. Reusing the current tests

Classify before reuse:

| Reuse class | Examples | Porting action |
|---|---|---|
| Input and parsing truth | tracked STEP, `parameters.json`, independently authored `expected.json` | Reuse if the target importer supports the format and provenance is retained |
| Acceptance property | expected mutation cannot alter actual; dimension/area/coverage; negative shape candidates | Re-express against a backend-neutral result DTO |
| Adapter-required test | tests that launch `FreeCADCmd` or call current stage runners | Replace the adapter/process layer while preserving the property |
| Backend/version-internal test | FreeCAD object labels, exposed symbols, raw analytic representation details | Keep as FreeCAD regression; do not call it portable |

The current pytest collection is therefore source material for a portable suite,
not an already portable cross-backend conformance package.

## 8. Explicit future boundary

General geometry-backend portability, full assembly graphs, arbitrary external
STEP, gradient fields, volumetric field solving, slicing, toolpaths, and G-code
remain `DESIGN_ONLY`, `PLANNED`, or `NOT_VERIFIED`. The independently developed
06A branch is outside this documentation baseline and is not evidence of a
completed generic movement or correction capability.
