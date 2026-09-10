# Contact Canonical Interface Topology Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add the frozen A11 and A12 two-body STEP diagnostics with actual topology evidence, independent validation, repeatability, and debug models.

**Architecture:** A focused 03C host module creates tracked fixtures and validates separate expected truth only after a FreeCADCmd adapter has re-imported STEP and produced raw direct-common faces.  The adapter groups actual faces into component geometry, extracts boundary loops from the resulting topology, preserves all source-face links, and saves actual debug geometry.

**Tech Stack:** Python, pytest, FreeCADCmd, OpenCascade B-rep, STEP, JSON evidence.

**Spec:** `docs/implementation/03c_contact_canonical_interface_topology.md`

## Global Constraints

- Only frozen A11 and A12 are in scope; do not alter A01--A09 or freeze documents.
- Inputs to analysis are tracked STEP re-imports with exactly two connected solids.
- Expected data is read only after actual evidence has been written.
- Preserve raw faces, contract patches, components, boundary/hole data, deduplicated areas, and all direct-common source links.
- Generate a reopenable `debug.FCStd`, use two independent FreeCADCmd processes, retain existing regressions, and never push or merge.

---

### Task 1: Add failing topology-contract tests

**Files:**
- Create: `tests/test_contact_canonical_03c.py`
- Modify: `src/dmslicer/__main__.py`

**Interfaces:**
- Consumes: CLI command conventions from 03A/03B.
- Produces: tests for A11/A12 fixture shape, actual topology, expected isolation, linkage mutation, and repeatability.

- [ ] **Step 1: Write failing tests**

```python
assert relation["raw_common_face_count"] >= relation["patch_count"]
assert relation["component_count"] == expected_components
assert relation["boundary_component_count"] == expected_boundaries
assert relation["hole_count"] == expected_holes
assert relation["components"]
```

- [ ] **Step 2: Run tests to verify the new CLI is absent**

Run: `pytest tests/test_contact_canonical_03c.py -q`
Expected: FAIL because the 03C command/module does not exist.

- [ ] **Step 3: Add only enough CLI plumbing to reach the test's intended missing-analysis failure**

```python
topology_generate = commands.add_parser("generate-contact-canonical-interface-topology")
```

- [ ] **Step 4: Re-run the test and preserve a meaningful RED failure**

Run: `pytest tests/test_contact_canonical_03c.py -q`
Expected: FAIL because fixture/analyzer behavior is unimplemented.

- [ ] **Step 5: Commit after the analyzer reaches GREEN with Task 2**

### Task 2: Implement actual A11/A12 fixture generation and topology evidence

**Files:**
- Create: `src/dmslicer/contact_canonical_03c.py`
- Create: `src/dmslicer/freecad_contact_03c.py`
- Modify: `src/dmslicer/__main__.py`
- Create: `benchmarks/contact_canonical_03c/A11/fixture.step`
- Create: `benchmarks/contact_canonical_03c/A11/parameters.json`
- Create: `benchmarks/contact_canonical_03c/A11/expected.json`
- Create: `benchmarks/contact_canonical_03c/A12/fixture.step`
- Create: `benchmarks/contact_canonical_03c/A12/parameters.json`
- Create: `benchmarks/contact_canonical_03c/A12/expected.json`

**Interfaces:**
- Consumes: `Path` fixture root and output root.
- Produces: `generate_contact_canonical_interface_topology`, `analyze_contact_canonical_interface_topology`, `run_contact_canonical_interface_topology_repeatability`, and `run_contact_canonical_interface_topology_suite`.

- [ ] **Step 1: Implement raw-face collection and direct-common provenance**

```python
for face_a in shape_a.Faces:
    for face_b in shape_b.Faces:
        common = face_a.common(face_b)
        for face in common.Faces:
            if face.Area > area_epsilon:
                raw_faces.append({"shape": face, "source_face_a": ..., "source_face_b": ...})
```

- [ ] **Step 2: Build actual components and boundary loops from B-rep geometry**

```python
component_shape = Part.makeCompound(component_faces)
boundary_edges = component_shape.Edges
# Group boundary edges by actual shared vertices and report closed-loop geometry.
```

- [ ] **Step 3: Write actual evidence before loading expected truth**

```python
write_json(output_dir / "actual.json", actual)
validation = _validate(actual, read_json(expected_path))
```

- [ ] **Step 4: Generate the tracked fixtures and run the topology test suite**

Run: `pytest tests/test_contact_canonical_03c.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

Run: `git add src/dmslicer tests/test_contact_canonical_03c.py benchmarks/contact_canonical_03c docs/implementation/03c_contact_canonical_interface_topology.md docs/superpowers/plans/2026-09-08-contact-canonical-interface-topology.md && git commit -m "feat: add canonical contact topology diagnostics"`

### Task 3: Publish durable evidence and verify all regressions

**Files:**
- Create: `outputs/contact_canonical_03c/VIEW_INDEX.md`
- Create: `outputs/contact_canonical_03c/summary.json`
- Create: `outputs/contact_canonical_03c/A11/*`
- Create: `outputs/contact_canonical_03c/A12/*`

**Interfaces:**
- Consumes: tracked fixture paths and completed 03C commands.
- Produces: reopenable debug files, validation, repeatability, and view instructions.

- [ ] **Step 1: Run the full 03C suite against tracked STEP fixtures**

Run: `python -m dmslicer run-contact-canonical-interface-topology-suite benchmarks/contact_canonical_03c outputs/contact_canonical_03c`
Expected: A11 and A12 validation and repeatability PASS.

- [ ] **Step 2: Run all tests and diff validation**

Run: `pytest -q && git diff --check`
Expected: all existing and new tests PASS; no whitespace errors.

- [ ] **Step 3: Inspect worktree cleanliness and commit durable evidence**

Run: `git add outputs/contact_canonical_03c && git commit -m "test: publish 03c topology evidence" && git status --short`
Expected: clean worktree.
