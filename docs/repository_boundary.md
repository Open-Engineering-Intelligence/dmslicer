# Repository boundary

## Legacy repository: DMSlicer-AI-mod

The legacy repository is responsible for the historical research prototype, legacy AMF backend, and legacy mesh-heuristic baseline. It remains a separate, read-only reference for this repository.

## Current repository: dmslicer

This repository is responsible for the current research implementation. Its intended main line is:

```text
STEP/B-rep
→ interface detection
→ InterfaceSourceBoundary
→ GradientDomain
→ volumetric material field
→ field-aware slicing
```

Repository initialization does not imply that any stage in this chain has been implemented.

## Inheritance policy

Research ideas and explicit scientific provenance may be inherited. Git history is not inherited, and legacy code is not copied by default.

If a legacy module is later considered for migration, it must be evaluated module by module, record its precise origin, and be handled as an explicit migration task. Copying the entire legacy directory or silently treating it as current implementation is prohibited.
