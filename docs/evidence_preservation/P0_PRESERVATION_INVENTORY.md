# P0 Preservation Inventory

Inventory date: 2026-09-10. Source aliases are resolved only in the private local custody inventory; no private absolute path is published here.

## Preservation totals

The first custody pass copied and SHA-256-verified 1,513 files totaling 6,567,706 bytes. All 1,513 source/copy pairs matched. This is a verified local preservation copy; independent remote preservation is recorded separately by the Release gate.

| Goal | Source alias | Files | Bytes | BREP | FCStd | STEP | XML | JSON | Preservation / Release state |
|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| 02C | `WT_02C` | 23 | 145,097 | 0 | 0 | 0 | 0 | 23 | `RELEASE_BLOCKED_PROVENANCE`; copied locally without rebinding |
| 03C | `WT_03C` | 51 | 496,411 | 0 | 9 | 2 | 0 | 25 | `RELEASE_BLOCKED_PROVENANCE`; pre/post-fix evidence retained |
| 04A | `CODEX_TASK_04A` | 58 | 254,177 | 15 | 6 | 21 | 0 | 15 | `RELEASE_BLOCKED_PROVENANCE`; highest-risk source copied first |
| 05B | `WT_05B` | 470 | 719,099 | 0 | 4 | 0 | 1 | 452 | `RELEASE_BLOCKED_PROVENANCE`; mismatch evidence retained |
| 05C | `WT_05C`, `WT_05C_REPO` | 605 | 1,983,271 | 0 | 6 | 58 | 3 | 523 | `RELEASE_BLOCKED_PROVENANCE`; failure/recovery evidence retained |
| 06A | `WT_06A` | 47 | 202,276 | 0 | 2 | 8 | 2 | 30 | `PUBLISHED`; rejection evidence retained |
| 06B | `WT_06B`, `WT_06B_WORK` | 49 | 257,748 | 10 | 6 | 8 | 5 | 19 | `RELEASE_BLOCKED_PROVENANCE`; four early/fix JUnit files retained |
| 06C | `WT_06C` | 81 | 930,413 | 14 | 3 | 8 | 1 | 50 | `PUBLISHED`; artifact-backed evidence retained |
| 06D | `WT_06D` | 129 | 1,579,214 | 38 | 3 | 22 | 1 | 57 | `PUBLISHED`; old ZIP retained unchanged; v2 review asset added |

Counts include only the explicitly selected custody trees. They do not count source code, unrelated tracked fixtures, caches, or repository-wide files.

## Priority evidence decisions

### 04A

- Preserved the complete A02/A08 historical task output: BREP, FCStd, STEP, operation/validation JSON, repeatability runs, summary, and VIEW_INDEX.
- The source was the only located historical task copy of these A02/A08 outputs before this operation.
- No JUnit was present in this evidence tree.

### 03C

- Preserved the top-level A12 pre-fix output, `a12_error_probe/`, `probe_failure.txt`, diagnostic measurements/report, and `a12_analytic_geometry_fix_20260909/`.
- The pre-fix result remains distinguishable from the analytic-geometry fix result.
- No formal stage JUnit was found; this remains an evidence limitation, not a reason to rerun.

### 05B

- Preserved the complete local output, including JUnit and native/normalized scale validation evidence.
- Scientific facts remain: native mismatch `16/90`; normalized mismatch `1/90`.
- The historical pytest result is recorded independently and does not erase either mismatch.

### 05C

- Preserved the full output plus the tracked failure breakdown and candidate-probe JSON/Markdown evidence.
- Preserved candidate probe, 21-case recovery, all three JUnit XML files, and the retained `A01_delta_p0tauE_s100` area-method exceedance.
- Intermediate failed/incomplete acceptance evidence remains in custody; it was not filtered to present a falsely clean history.

### 06A and 06B

- 06A: preserved the complete correction output, two FCStd, eight STEP, two XML, validation, and rejection-scenario evidence.
- 06B: preserved the complete output plus `06b_initial.xml`, `06b_second.xml`, `06b_targeted.xml`, and `06b_third.xml` from the work directory.
- The early 06B failures remain separate from later passing evidence.

### 06C

- Preserved all 14 BREP, three FCStd, eight STEP, artifact-backed validation, and final JUnit.
- Git commit history remains the authority for the reviewer-driven fixes and hash-policy change; a derived reviewer/fix note is added to the public manifest and Release staging rather than rewriting historical output.
- Hashes are retained only for byte integrity. The recorded geometry validation criteria must use actual B-rep operations and measures.

### 06D

- Preserved all 38 BREP, three FCStd, 22 STEP, final JUnit, VIEW_INDEX, HUMAN_REVIEW documents, and the old `06D_HUMAN_REVIEW.zip` without modification.
- The old ZIP is retained as historical evidence even though it is not self-contained.
- A new V2 package is created separately and bound to geometry implementation commit `b7054f3`; policy commit `b42ba9e` is not treated as an experiment run.

## Remaining single-copy or fragile evidence

These are not deleted or declared safe merely because they were outside the P0 copy whitelist:

| Goal | Evidence | State | Reason |
|---|---|---|---|
| 03A | additional local outputs and packaging artifacts not included in this P0 custody copy | `SINGLE_COPY` | P1 evidence; `a1fc48b` is not inherited by later branches |
| 03B | local outputs, FCStd, validation, and VIEW_INDEX | `SINGLE_COPY` | P1 evidence; no formal JUnit located |
| 04B | local cylinder-fit outputs and regression evidence | `SINGLE_COPY` | P1 evidence; not selected into first P0 custody pass |
| 05A | original/fix/rerun tolerance-pilot outputs | `SINGLE_COPY` | P1 evidence; no formal JUnit located |
| 06C | exact full reviewer conversation wording | `SINGLE_COPY` / `CHAT` | code/fix history is local/GitHub, but reviewer prose requires task-record custody |
| 06D | exact wording of two historical reviewer findings | `SINGLE_COPY` / `CHAT` | final task summary did not enumerate both findings |

## Missing or not fully recoverable evidence

- 02C has no located JUnit, BREP, FCStd, or VIEW_INDEX for the final branch tip.
- 02C's existing evidence bundle is not rebound to final commit `b646027`; no rerun or inferred binding is performed.
- 03C has no formal JUnit for the analytic-geometry fix.
- 04A A02/A08 historical task output has no JUnit in the located tree.
- 06D reviewer findings are not completely recoverable from the final summary alone; any exact prose remains `CHAT` unless recovered directly from the reviewer task.
- No Goal is reclassified as currently scientifically validated by this preservation copy operation.

## Custody records

The private custody inventory contains exact absolute source paths and 1,513 source-to-copy mappings. An initial 04A-only inventory remains as an execution trace; the complete inventory is the append-only V2 file that declares it supersedes the partial record. Neither private file is tracked by Git or included in public Release assets.
