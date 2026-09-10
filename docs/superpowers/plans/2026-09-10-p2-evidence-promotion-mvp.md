# P2 Evidence Promotion MVP Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a fail-closed, schema-backed CLI that promotes an explicit allowlist of local staging files into a stable, byte-verified evidence package while keeping geometry, semantics, UI, preservation, and publication claims explicitly separate.

**Architecture:** A small host-side Python package validates versioned request/manifest schemas, repository and path constraints, result domains, SHA usage, and failure retention before copying any file. Promotion uses a temporary sibling directory, verifies each copied byte stream, emits public-safe inventories and statuses, refuses overwrite, then atomically installs `evidence/<goal_id>/<implementation_commit>/<run_id>/`; FreeCAD/OCCT execution is deferred to phase 2.

**Tech Stack:** Python 3.12, pytest 8, JSON Schema draft 2020-12, `jsonschema`, `pathlib`, `shutil`, `hashlib`, `subprocess`, PowerShell, and GitHub Actions.

**Spec:** `docs/superpowers/specs/2026-09-10-p2-evidence-promotion-semantic-snapshot-design.md`

## Global Constraints

- Preserve schema v1.1.0 and every P0/P1 manifest byte-for-byte.
- SHA-256 means byte integrity only and never decides geometry equivalence.
- P2-MVP geometry status is `GEOMETRIC_EQUIVALENCE_NOT_PROVEN` with no geometry evidence.
- Every declared tolerance has value, unit, role, and source; an empty list is valid when geometry is not evaluated.
- Stable identity is `goal_id + implementation_commit + run_id`.
- Allowlist individual files below repository `outputs/` or `work/`; reject traversal, broad selection, symlink/reparse escape, duplicates, and overwrite.
- Preserve declared failures, mismatches, rejections, and reviewer findings.
- Local package creation success is independent of preservation and publication.
- Two same-host paths mean `LOCAL_TWO_PATHS_NOT_OFF_HOST_REDUNDANCY` and `NOT_FULLY_PRESERVED`.
- Do not implement FreeCAD/OCCT comparison, CAD snapshots, CAD fixtures, or Human Inspection CAD packages in MVP.
- Do not push, create a PR or Release, write external storage, or register an off-host copy without separate authorization.
- Do not modify `docs/research_v2/`, historical reports/manifests/outputs, or historical worktrees.
- Follow red-green-refactor for every production behavior.

---

### Task 1: Package foundation and versioned schema contracts

**Files:**
- Create: `pyproject.toml`
- Create: `src/dmslicer/__init__.py`
- Create: `src/dmslicer/evidence_promotion/__init__.py`
- Create: `src/dmslicer/evidence_promotion/models.py`
- Create: `docs/evidence_preservation/schemas/promotion_request.schema.json`
- Create: `docs/evidence_preservation/schemas/evidence_manifest.v2.schema.json`
- Create: `tests/conftest.py`
- Create: `tests/test_schema_contracts.py`

**Interfaces:**
- Produces: `write_json(path: Path, value: Mapping[str, Any]) -> None`.
- Produces: `read_json(path: Path) -> dict[str, Any]`.
- Produces: `schema_path(name: str) -> Path` and result/status constants.
- Produces: pytest factory `valid_request(repository_root: Path, staging_root: Path) -> dict[str, Any]`.

- [x] **Step 1: Write historical-compatibility and valid-request tests**

```python
def test_historical_manifests_remain_valid() -> None:
    schema = load_schema(HISTORICAL_SCHEMA)
    for manifest in sorted(HISTORICAL_MANIFESTS.glob("goal-*.json")):
        Draft202012Validator(schema).validate(read_json(manifest))


def test_valid_mvp_request_requires_unproven_geometry(valid_request) -> None:
    request = valid_request()
    Draft202012Validator(load_schema(PROMOTION_SCHEMA)).validate(request)
    assert request["results"]["geometry_equivalence_result"] == {
        "status": "GEOMETRIC_EQUIVALENCE_NOT_PROVEN",
        "evidence_artifact_ids": [],
    }
```

- [x] **Step 2: Write schema rejection tests**

Remove `identity.implementation_commit`, set `run_id` to `../escape`, add a tolerance without `unit`, add an unknown property, and supply geometry PASS/evidence. Each case must raise `jsonschema.ValidationError` at the changed field.

- [x] **Step 3: Run tests and verify RED**

Run: `py -3.12 -m pytest tests/test_schema_contracts.py -q`

Expected: import/fixture failure because P2 helpers and schemas do not exist.

- [x] **Step 4: Implement package metadata, deterministic JSON helpers, constants, and schemas**

Use schema version `2.0.0`. The request requires `goal_id`, `run_id`, identity (`branch`, full `implementation_commit`, `parent_baseline`, `merge_base`), source staging root and allowlist, environment versions, execution records, tolerances, eight separate results, four history-reference arrays, custody, and geometry validation.

Each allowlist entry requires `artifact_id`, repository-relative `source_path`, package-relative `public_path`, `kind`, `validation_role`, and `retention_role`. The manifest adds generated byte metadata and separate `local_package_result`, `preservation_result`, and `publication_result`.

The MVP geometry contract is exactly:

```json
{
  "status": "GEOMETRIC_EQUIVALENCE_NOT_PROVEN",
  "evidence_method": "NOT_EVALUATED_P2_MVP",
  "evidence_artifact_ids": [],
  "sha256_role": "file_and_copy_integrity_only_not_geometry_equivalence"
}
```

- [x] **Step 5: Run schema tests and verify GREEN**

Run: `py -3.12 -m pytest tests/test_schema_contracts.py -q`

Expected: all pass; 13/13 historical manifests remain valid.

- [x] **Step 6: Commit**

```powershell
git add pyproject.toml src/dmslicer docs/evidence_preservation/schemas tests/conftest.py tests/test_schema_contracts.py
git commit -m "feat: define P2 MVP evidence contracts"
```

---

### Task 2: Byte-integrity layer

**Files:**
- Create: `src/dmslicer/evidence_promotion/integrity.py`
- Create: `tests/test_integrity.py`

**Interfaces:**
- Produces: `file_integrity(path: Path) -> dict[str, int | str]`.
- Produces: `compare_bytes(first: Path, second: Path) -> dict[str, Any]`.
- Produces: `copy_and_verify(source: Path, destination: Path) -> dict[str, Any]`.

- [x] **Step 1: Write failing same-byte and different-byte tests**

```python
def test_compare_bytes_reports_different_bytes_without_geometry_status(tmp_path: Path) -> None:
    first, second = tmp_path / "a.bin", tmp_path / "b.bin"
    first.write_bytes(b"first")
    second.write_bytes(b"second")
    result = compare_bytes(first, second)
    assert result["status"] == "BYTE_DIFFERENT"
    assert "geometry" not in result
```

Also assert equal bytes return `BYTE_SAME` with equal digests and sizes.

- [x] **Step 2: Write a failing verified-copy test**

Assert that `copy_and_verify` creates the destination, records equal source/destination SHA-256 and size, returns `BYTE_SAME`, and refuses an existing destination.

- [x] **Step 3: Run and verify RED**

Run: `py -3.12 -m pytest tests/test_integrity.py -q`

Expected: import failure because `integrity.py` does not exist.

- [x] **Step 4: Implement streaming SHA-256 and copy verification**

Read in 1 MiB blocks, use `shutil.copy2`, refuse an existing destination, and delete only a just-created incomplete copy if verification fails. Return byte-only fields and statuses.

- [x] **Step 5: Run focused and cumulative tests and verify GREEN**

Run: `py -3.12 -m pytest tests/test_integrity.py tests/test_schema_contracts.py -q`

- [x] **Step 6: Commit**

```powershell
git add src/dmslicer/evidence_promotion/integrity.py tests/test_integrity.py
git commit -m "feat: add byte integrity evidence"
```

---

### Task 3: Fail-closed request and policy validation

**Files:**
- Create: `src/dmslicer/evidence_promotion/policy.py`
- Create: `tests/test_policy.py`

**Interfaces:**
- Produces: `PolicyFinding(code: str, message: str, artifact_id: str | None)`.
- Produces: `ResolvedArtifact` with source/public paths and artifact metadata.
- Produces: `validate_request(request: Mapping[str, Any], repository_root: Path) -> dict[str, Any]`.
- Produces: `resolve_allowlisted_files(request, repository_root) -> list[ResolvedArtifact]`.

- [x] **Step 1: Write failing provenance and Git tests**

Cover valid request, missing/nonexistent implementation commit, invalid ancestry, invalid run ID, missing tolerance unit, and a result evidence ID absent from the allowlist. Assert stable codes `SCHEMA_INVALID`, `GIT_COMMIT_NOT_FOUND`, `GIT_ANCESTRY_INVALID`, and `EVIDENCE_REFERENCE_MISSING`.

- [x] **Step 2: Write failing path/allowlist tests**

Cover missing file, `../` traversal, absolute source/public paths, staging outside `outputs/` or `work/`, directory selection, duplicate public destination, reserved generated name, and symlink escape when supported. Assert `ALLOWLIST_SOURCE_MISSING`, `PATH_ESCAPE`, `BROAD_SELECTION`, or `PUBLIC_PATH_INVALID`.

- [x] **Step 3: Write failing sensitive-content tests**

Detect Windows/Linux home paths, Codex attachment/session paths, private-key headers, GitHub token syntax, and password/secret assignments in allowlisted public text/JSON. Ordinary SHA-256 values must remain allowed.

- [x] **Step 4: Write failing SHA-misuse regressions**

Set an evidence method or validation role to say a hash proves geometry equivalence and assert `SHA_GEOMETRY_MISUSE`. Separately set byte result to `BYTE_DIFFERENT` and confirm geometry stays `GEOMETRIC_EQUIVALENCE_NOT_PROVEN` without a geometry finding.

- [x] **Step 5: Write failing failure-retention tests**

Reference failure, mismatch, rejection, and reviewer artifact IDs in `history`. Each must be allowlisted with the matching `retention_role`; omission or wrong role yields `FAILURE_EVIDENCE_NOT_RETAINED`.

- [x] **Step 6: Run and verify RED**

Run: `py -3.12 -m pytest tests/test_policy.py -q`

Expected: import failure because `policy.py` does not exist.

- [x] **Step 7: Implement schema, Git, path, content, SHA, and retention checks**

Return deterministic `schema_version`, `status`, per-check status, and sorted findings. Resolve paths strictly, prove containment, reject symlink/reparse components and non-files, and scan only selected public text/JSON. Use argument-list subprocess calls for `git cat-file -e <sha>^{commit}` and `git merge-base --is-ancestor`; never invoke a shell.

- [x] **Step 8: Run focused and cumulative tests and verify GREEN**

Run: `py -3.12 -m pytest tests/test_policy.py tests/test_schema_contracts.py tests/test_integrity.py -q`

- [x] **Step 9: Commit**

```powershell
git add src/dmslicer/evidence_promotion/policy.py tests/test_policy.py
git commit -m "feat: enforce fail-closed evidence policy"
```

---

### Task 4: Transactional local evidence packaging

**Files:**
- Create: `src/dmslicer/evidence_promotion/promotion.py`
- Create: `tests/test_promotion.py`

**Interfaces:**
- Produces: `promote(request_path: Path, repository_root: Path, copy_function=copy_and_verify) -> dict[str, Any]`.
- Produces package: `manifest.json`, `copy_inventory.json`, `policy_report.json`, and allowlisted public files.

- [x] **Step 1: Write a failing successful-local-package test**

```python
def test_local_package_can_succeed_without_full_preservation(repo, request_file) -> None:
    result = promote(request_file, repo)
    assert result["local_package_status"] == "LOCAL_PACKAGE_CREATED"
    assert result["preservation_status"] == "NOT_FULLY_PRESERVED"
    assert result["publication_status"] == "PUBLICATION_NOT_AUTHORIZED"
    assert result["recoverable_copy_count"] == 2
    assert result["recoverable_copy_policy"] == "LOCAL_TWO_PATHS_NOT_OFF_HOST_REDUNDANCY"
```

Verify the exact stable path and that public files contain no absolute local paths.

- [x] **Step 2: Write failing no-overwrite and missing-file tests**

The second identical request returns `LOCAL_PACKAGE_BLOCKED` with `DESTINATION_EXISTS` and changes no existing byte. A missing source installs no final destination.

- [x] **Step 3: Write a failing copy-corruption transaction test**

Inject a copy function that writes altered bytes. Assert `COPY_VERIFY_FAILED`, no final destination, unchanged source failure artifacts, and a non-overwriting report under `work/evidence-promotion-failures/<goal>/<commit>/<run>/`.

- [x] **Step 4: Write a failing generated-manifest test**

Validate the output against manifest v2. Assert eight domain results are independent, byte results derive from copy records, geometry remains unproven, and package/preservation/publication results are separate objects.

- [x] **Step 5: Run and verify RED**

Run: `py -3.12 -m pytest tests/test_promotion.py -q`

Expected: import failure because `promotion.py` does not exist.

- [x] **Step 6: Implement staging, recount, manifest generation, and atomic install**

Stage under `work/evidence-promotion-staging/`, copy every resolved file, verify digests/sizes, write deterministic generated records, validate manifest v2, and rename on the same volume into the new stable destination. Refuse overwrite. On failure, retain a structured report without deleting or changing source evidence.

- [x] **Step 7: Run focused and cumulative tests and verify GREEN**

Run: `py -3.12 -m pytest tests/test_promotion.py tests/test_policy.py tests/test_integrity.py tests/test_schema_contracts.py -q`

- [x] **Step 8: Commit**

```powershell
git add src/dmslicer/evidence_promotion/promotion.py tests/test_promotion.py
git commit -m "feat: promote allowlisted local evidence"
```

---

### Task 5: CLI, documentation, and local CI gate

**Files:**
- Create: `src/dmslicer/evidence_promotion/cli.py`
- Create: `src/dmslicer/evidence_promotion/__main__.py`
- Create: `tests/test_cli.py`
- Create: `scripts/evidence_preservation/run_p2_mvp_checks.ps1`
- Create: `.github/workflows/evidence-promotion.yml`
- Create: `docs/evidence_preservation/EVIDENCE_PROMOTION_PIPELINE.md`

**Interfaces:**
- Produces: `python -m dmslicer.evidence_promotion validate --repository-root ROOT --request FILE`.
- Produces: `python -m dmslicer.evidence_promotion promote --repository-root ROOT --request FILE`.

- [ ] **Step 1: Write failing CLI tests**

Use subprocess with `sys.executable`. Assert valid `validate` exits 0, policy failure exits 2, `promote` exits 0 for a created/not-fully-preserved package, and malformed JSON reports a concise error without a traceback or secret echo.

- [ ] **Step 2: Run and verify RED**

Run: `py -3.12 -m pytest tests/test_cli.py -q`

Expected: module execution failure because CLI files do not exist.

- [ ] **Step 3: Implement the CLI**

Use `argparse`. Emit UTF-8 JSON to stdout. Return 0 only for validation PASS or `LOCAL_PACKAGE_CREATED`; return 2 for input, policy, or packaging failure. Do not expose private absolute paths in normal output.

- [ ] **Step 4: Write the pipeline documentation**

Document `outputs/work -> allowlist -> manifest -> policy checks -> local stable evidence`; explain `Hash != Geometry`, `Geometry != Semantic`, `Semantic != UI`, and `pytest != Scientific Result`; give a complete request and CLI example; explain local PASS versus incomplete preservation; and state all phase-2 and authorization boundaries.

- [ ] **Step 5: Add local and GitHub Actions checks**

The PowerShell script runs `py -3.12 -m pytest -q` and the module help. The workflow uses Python 3.12, `pip install -e .`, and `pytest -q`; it also fails if `docs/research_v2/` differs from the base.

- [ ] **Step 6: Run and verify GREEN**

Run: `py -3.12 -m pytest -q`

Run: `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/evidence_preservation/run_p2_mvp_checks.ps1`

- [ ] **Step 7: Commit**

```powershell
git add src/dmslicer/evidence_promotion/cli.py src/dmslicer/evidence_promotion/__main__.py tests/test_cli.py scripts/evidence_preservation/run_p2_mvp_checks.ps1 .github/workflows/evidence-promotion.yml docs/evidence_preservation/EVIDENCE_PROMOTION_PIPELINE.md
git commit -m "feat: expose P2 MVP promotion gate"
```

---

### Task 6: Artifact-backed local acceptance run and completion audit

**Files:**
- Create: `evidence/P2-MVP/<implementation_commit>/p2-mvp-acceptance-001/manifest.json`
- Create: `evidence/P2-MVP/<implementation_commit>/p2-mvp-acceptance-001/copy_inventory.json`
- Create: `evidence/P2-MVP/<implementation_commit>/p2-mvp-acceptance-001/policy_report.json`
- Create: `evidence/P2-MVP/<implementation_commit>/p2-mvp-acceptance-001/artifacts/pytest.xml`
- Create: `evidence/P2-MVP/<implementation_commit>/p2-mvp-acceptance-001/artifacts/validator-result.json`
- Create: `evidence/P2-MVP/<implementation_commit>/p2-mvp-acceptance-001/artifacts/ACCEPTANCE_SUMMARY.md`
- Modify: `docs/evidence_preservation/EVIDENCE_PROMOTION_PIPELINE.md`

**Interfaces:**
- Consumes: committed MVP code, schemas, CLI, and complete tests.
- Produces: stable proof of local package success with incomplete preservation/publication.

- [ ] **Step 1: Record the implementation commit**

Run: `git rev-parse HEAD`. Use the full commit in the request and destination; do not rewrite it after evidence generation.

- [ ] **Step 2: Generate fresh staging evidence**

Run pytest with JUnit output under `outputs/p2-mvp-acceptance-001/pytest.xml`. Create validator JSON there with exact command, exit code, timestamp, versions, implementation commit, separate result domains, `GEOMETRIC_EQUIVALENCE_NOT_PROVEN`, and no FreeCAD claim. Create a factual `ACCEPTANCE_SUMMARY.md` in the same staging root before promotion. The summary records code commit, branch, commands, test count, schemas, SHA role, copy policy, and every deferred/not-authorized item. Create an explicit three-file allowlist and reference JUnit from `pytest_result`.

- [ ] **Step 3: Validate and locally promote**

```powershell
$env:PYTHONPATH = "src"
py -3.12 -m dmslicer.evidence_promotion validate --repository-root . --request outputs/p2-mvp-acceptance-001/request.json
py -3.12 -m dmslicer.evidence_promotion promote --repository-root . --request outputs/p2-mvp-acceptance-001/request.json
```

Expected: `LOCAL_PACKAGE_CREATED`, `NOT_FULLY_PRESERVED`, `PUBLICATION_NOT_AUTHORIZED`, and `GEOMETRIC_EQUIVALENCE_NOT_PROVEN`.

- [ ] **Step 4: Verify the immutable package and update pipeline documentation**

Revalidate all package JSON against schema, recompute every copied digest, and confirm every public path is relative. Add the immutable package path and local acceptance command to `EVIDENCE_PROMOTION_PIPELINE.md`. After the atomic install, do not edit any file inside the stable package. Do not claim CAD validation, full preservation, hosted CI success, remote SHA, or PR state.

- [ ] **Step 5: Run the complete verification matrix**

```powershell
py -3.12 -m pytest -q
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/evidence_preservation/run_p2_mvp_checks.ps1
git diff origin/main -- docs/research_v2
git diff --check origin/main...HEAD
git status --short
```

Validate both P2 schemas, the generated manifest, and all 13 historical manifests. Recount all promoted files and scan the package for absolute paths/secrets.

- [ ] **Step 6: Commit stable acceptance evidence**

```powershell
git add evidence/P2-MVP docs/evidence_preservation/EVIDENCE_PROMOTION_PIPELINE.md
git commit -m "evidence: record P2 MVP local promotion"
```

- [ ] **Step 7: Perform final local completion audit**

```powershell
git branch --show-current
git rev-parse HEAD
git status --short --branch
git log --oneline origin/main..HEAD
```

Confirm no push, PR, Release, external-storage write, historical-file change, or phase-2 CAD implementation occurred. Report remote SHA and PR as `NOT_AUTHORIZED/NOT_CREATED`.
