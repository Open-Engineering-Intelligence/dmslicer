# Evidence Promotion Pipeline

Status: P2-MVP CAD evidence and local promotion closed loop implemented.

## Purpose

The P2-MVP pipeline turns an explicit set of temporary run files into a stable,
inspectable local evidence package. It validates before copying, recounts every
copied byte, refuses overwrite, preserves declared failure evidence, and records
what has and has not been proven.

The MVP flow is:

```text
outputs/ or work/
        -> individual-file allowlist
        -> request schema
        -> Git/path/content/result/retention policy checks
        -> byte-verified candidate package
        -> generated manifest schema
        -> evidence/<goal_id>/<implementation_commit>/<run_id>/
```

The following distinctions are invariants:

```text
Hash != Geometry
Geometry != Semantic
Semantic != UI
pytest != Scientific Result
local package creation != full preservation != publication
```

SHA-256 is used only for custody, copy verification, acquisition provenance,
off-host verification, and reproducibility lookup. A hash, stable fingerprint,
or serialized-file identity is never a geometry predicate.

## P2-MVP CAD boundary

P2-MVP opens a fixed FreeCAD fixture: a 40 × 30 × 12 mm block with a vertical
through-hole. It creates immutable original, UI-only, and hole-radius-mutated
FCStd/BREP/STEP files, then reopens them and writes separate
`geometry_semantic_snapshot`, `topology_snapshot`, and `ui_state_snapshot`
artifacts. Geometry authority comes from reopened Part shapes and actual B-rep
operations, never from a display mesh or file hash.

Case A changes only color, transparency, and visibility. Its expected statuses
are `GEOMETRY_EQUIVALENT`, `SEMANTIC_EQUIVALENT`, and `UI_DIFFERENT`; its byte
status may be either `BYTE_SAME` or `BYTE_DIFFERENT`. Case B changes the hole
radius from 4.0 mm to 5.0 mm and must report `GEOMETRY_DIFFERENT` with literal
area, volume, or bidirectional Boolean-difference reasons. Serialization/reopen
is compared through the same B-rep path and cannot become geometry-different
merely because bytes differ.

The fixture comparison records inclusive 0.001 mm, 0.001 mm², and 0.001 mm³
tolerances with their roles and source. Manifold inference remains `UNKNOWN`;
Hausdorff metrics, arbitrary subshape correspondence, registration, and general
CAD semantics remain deferred.

## Request contract

Requests validate against
`docs/evidence_preservation/schemas/promotion_request.schema.json` version
2.0.0. A request supplies, without inference:

- Goal ID, run ID, branch, full implementation commit, parent baseline, and merge base;
- a repository-relative staging root below `outputs/` or `work/`;
- an allowlist of individual source files and their public package paths;
- Python, pytest, FreeCAD, and OCCT versions for CAD-backed runs;
- commands, exit codes, and timestamps;
- every declared tolerance with value, unit, role, and source;
- eight independent result domains;
- retained failure, mismatch, rejection, and reviewer-finding references; and
- an empty off-host-copy list and `publication_authorized: false` in MVP.

This structurally complete example shows the required fields. The Git commits
must be replaced by commits that exist in the repository, and the selected file
must exist below the declared staging root:

```json
{
  "schema_version": "2.0.0",
  "goal_id": "P2-MVP",
  "run_id": "p2-mvp-local-001",
  "identity": {
    "branch": "feat/evidence-promotion-semantic-snapshot",
    "implementation_commit": "ea617b6b6fa8d074c1c89d6f61513fe4d892cef3",
    "parent_baseline": "ea617b6b6fa8d074c1c89d6f61513fe4d892cef3",
    "merge_base": "ea617b6b6fa8d074c1c89d6f61513fe4d892cef3"
  },
  "source": {
    "staging_root": "outputs/p2-mvp-local-001",
    "allowlist": [
      {
        "artifact_id": "validator-result",
        "source_path": "validator-result.json",
        "public_path": "artifacts/validator-result.json",
        "kind": "VALIDATOR",
        "validation_role": "software_validator_result",
        "retention_role": "STANDARD"
      }
    ]
  },
  "environment": {
    "python_version": "3.12.0",
    "pytest_version": "8.4.2",
    "freecad_version": null,
    "occt_version": null
  },
  "execution": [
    {
      "command": "py -3.12 -m pytest -q",
      "exit_code": 0,
      "timestamp": "2026-09-10T12:00:00+08:00"
    }
  ],
  "tolerances": [],
  "results": {
    "byte_identity_result": {"status": "BYTE_NOT_EVALUATED", "evidence_artifact_ids": []},
    "geometry_equivalence_result": {"status": "GEOMETRIC_EQUIVALENCE_NOT_PROVEN", "evidence_artifact_ids": []},
    "semantic_equivalence_result": {"status": "SEMANTIC_EQUIVALENCE_NOT_PROVEN", "evidence_artifact_ids": []},
    "ui_state_result": {"status": "UI_STATE_NOT_PROVEN", "evidence_artifact_ids": []},
    "pytest_result": {"status": "NOT_EVALUATED", "evidence_artifact_ids": []},
    "validator_result": {"status": "PASS", "evidence_artifact_ids": ["validator-result"]},
    "scientific_experiment_result": {"status": "NOT_EVALUATED", "evidence_artifact_ids": []},
    "human_inspection_result": {"status": "NOT_EVALUATED", "evidence_artifact_ids": []}
  },
  "history": {
    "failure_artifact_ids": [],
    "mismatch_artifact_ids": [],
    "rejection_artifact_ids": [],
    "reviewer_finding_artifact_ids": []
  },
  "custody": {"off_host_copies": [], "publication_authorized": false},
  "geometry_validation": {
    "status": "GEOMETRIC_EQUIVALENCE_NOT_PROVEN",
    "evidence_method": "NOT_EVALUATED_P2_MVP",
    "evidence_artifact_ids": [],
    "sha256_role": "file_and_copy_integrity_only_not_geometry_equivalence"
  }
}
```

## Commands

From the repository root after installing the package with
`py -3.12 -m pip install -e .`:

```powershell
py -3.12 -m dmslicer.evidence_promotion demo --output-root outputs/p2-cad-demo
py -3.12 -m dmslicer.evidence_promotion validate --repository-root . --request outputs/p2-cad-demo/promotion_request.json
py -3.12 -m dmslicer.evidence_promotion promote --repository-root . --request outputs/p2-cad-demo/promotion_request.json
```

The `demo` command requires a local GUI-capable FreeCAD plus FreeCADCmd/OCCT.
It accepts only a repository-local `outputs/` or `work/` target and creates the
explicit allowlist request used by the next two commands. Case B's expected
`GEOMETRY_DIFFERENT` scientific result does not make the command fail.

`validate` exits 0 only when all request policies pass. `promote` exits 0 when
the local package is safely created. A malformed, unsafe, incomplete, or
overwriting request exits 2 and emits structured JSON without echoing the
request's sensitive value.

## Fail-closed gates

The validator checks:

1. request schema and version;
2. implementation, parent, and merge-base commits plus ancestry;
3. staging-root and individual-file containment;
4. no absolute source/public path, traversal, symlink/reparse escape, broad
   directory selection, duplicate destination, or generated-name collision;
5. no obvious private path, Codex path, private key, token, or credential value
   in selected public text/JSON;
6. every result evidence reference exists in the allowlist;
7. no hash/digest presented as geometry proof; and
8. every declared failure, mismatch, rejection, and reviewer finding is
   selected with the matching retention role.

Copying then verifies the source and destination size and SHA-256 independently.
The package is built in a temporary sibling and installed only after the
generated manifest validates. An existing stable destination is never changed.
On failure, selected source evidence remains untouched and a structured failure
report is retained under `work/evidence-promotion-failures/`.

## Separate result and custody statuses

The generated manifest retains these independent result objects:

- `byte_identity_result`;
- `geometry_equivalence_result`;
- `semantic_equivalence_result`;
- `ui_state_result`;
- `pytest_result`;
- `validator_result`;
- `scientific_experiment_result`; and
- `human_inspection_result`.

Successful local creation with no authorized off-host copy reports:

```text
local_package_status: LOCAL_PACKAGE_CREATED
recoverable_copy_count: 2
recoverable_copy_policy: LOCAL_TWO_PATHS_NOT_OFF_HOST_REDUNDANCY
preservation_status: NOT_FULLY_PRESERVED
publication_status: PUBLICATION_NOT_AUTHORIZED
```

This is a successful local operation and an incomplete preservation state at
the same time. Two paths on one host are not independent protection. P2-MVP
does not authorize or create a push, PR, Release, external-storage object, or
off-host custody record.

## P2-MVP acceptance evidence

The CAD closed-loop package created from implementation commit
`fbedef574580bf860f8c08e2a8d4cb18f6070515` is:

```text
evidence/P2-EVIDENCE-PROMOTION-SEMANTIC-SNAPSHOT/fbedef574580bf860f8c08e2a8d4cb18f6070515/p2-cad-closed-loop-001/
```

Its manifest independently records Case A geometry/semantic/UI results, Case B
geometry-different measurement evidence, serialization/reopen equivalence,
104 focused tests, FreeCAD 1.1.1, OCCT 7.8.1, and human inspection as
`NOT_EVALUATED`. The 25 promoted artifacts passed byte recount, CAD schema, and
relative-link verification. Local custody remains `NOT_FULLY_PRESERVED` and
publication remains unauthorized.

The current immutable local acceptance package is:

```text
evidence/P2-MVP/8d9df8403cb3505037724d13f465531b277515f9/p2-mvp-acceptance-002/
```

It was created with:

```powershell
$env:PYTHONPATH = "src"
py -3.12 -m dmslicer.evidence_promotion validate --repository-root . --request outputs/p2-mvp-acceptance-002/request.json
py -3.12 -m dmslicer.evidence_promotion promote --repository-root . --request outputs/p2-mvp-acceptance-002/request.json
```

The package binds the run to implementation commit
`8d9df8403cb3505037724d13f465531b277515f9`, contains a public-safe 65-test
JUnit result, retains negative policy evidence, and independently recounts all
four selected source/copy pairs. Its local package status is PASS while
preservation remains incomplete and publication unauthorized. It contains no
CAD validation or Human Inspection claim.

The earlier immutable package at
`evidence/P2-MVP/219e893392e80766469790e3bc1b99d3d39fd345/p2-mvp-acceptance-001/`
is retained as historical evidence. Run 002 supersedes it for completion
because it also covers host-independent Windows/POSIX path parsing and
public-safe JUnit case labels; no file in run 001 was changed or deleted.

## Verification

Run the complete local gate:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/evidence_preservation/run_p2_mvp_checks.ps1
```

The GitHub Actions workflow runs only `-m "not freecad"` portable tests and
checks that `docs/research_v2/` is unchanged from
`feat/cylindrical-interface-repairability`. It does not claim a FreeCAD run.
The local PowerShell gate runs the CAD tests and complete inherited suite. The
presence of the workflow is not evidence that hosted CI ran; hosted status is
reported only after an authorized push or PR causes an actual run.
