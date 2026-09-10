# Worktree custody and archivability

No worktree was deleted, moved, cleaned, or rewritten in this preservation phase.

P1 addendum: 03A, 03B, 04B, and 05A now have verified second local custody copies (808 files total), and exact 06D reviewer text has been recovered into the manifests. These remain local copies on the same host, not independent off-host protection, so the existing `NOT_ARCHIVABLE` decisions remain unchanged. The separate CAD evidence governance PR was merged to `main` at `cea98d726e9e3a2f69d648db7b2920a48df41b6d`; the older conflict-preserving human-inspection policy worktree was not modified or deleted.

## Classification rule

`ARCHIVABLE` requires a remote implementation commit, a complete Goal manifest, canonical evidence in a remote Release or approved persistent store, verified SHA-256, an independent local preservation copy, retained failures/mismatches and applicable review evidence, and no unresolved provenance blocker. Classification does not authorize deletion.

## Goal worktrees

| Worktree / branch | Remote source | Evidence state | Classification | Reason |
|---|---|---|---|---|
| 02C / `fix/case01-foundation` | exact tip remote | local custody only | `NOT_ARCHIVABLE` | final-HEAD bundle provenance gap |
| 03A / `feat/contact-canonical-planar-dimensions` | exact tip remote | manifest only | `NOT_ARCHIVABLE` | canonical output custody/Release incomplete; packaging is non-inherited sibling history |
| 03B / `feat/contact-canonical-analytic-curves` | exact tip remote | manifest only | `NOT_ARCHIVABLE` | canonical output custody/Release incomplete |
| 03C / `feat/contact-canonical-interface-topology` | exact tip remote | local custody only | `NOT_ARCHIVABLE` | post-fix run-to-commit binding unresolved |
| 04A / `feat/contact-partition-and-union` | exact tip remote | verified A02/A08 local custody | `NOT_ARCHIVABLE` | historical run-to-commit binding unresolved; fragile source retained |
| 04B / `feat/cylinder-partition-and-union` | exact tip remote | manifest only | `NOT_ARCHIVABLE` | canonical output custody/Release incomplete |
| 05A / `feat/contact-tolerance-pilot` | exact tip remote | manifest only | `NOT_ARCHIVABLE` | canonical output custody/Release incomplete |
| 05B / `feat/contact-scale-covariance-pilot` | exact tip remote | local custody only | `NOT_ARCHIVABLE` | result-to-final-commit binding unresolved |
| 05C / `feat/contact-fixed-tolerance-pilot` | exact tip remote | local custody only | `NOT_ARCHIVABLE` | evidence binds `0d681a9`, not final `fa4436a` |
| 06A / `feat/planar-gap-assembly-correction` | exact tip remote | local custody + published Release | `ARCHIVABLE` | all minimum evidence/custody conditions met |
| 06B / `feat/planar-partial-overlap-correction` | exact tip remote | local custody only | `NOT_ARCHIVABLE` | validator provenance points to 06A commit |
| 06C / `feat/planar-multipatch-interface-correction` | exact tip remote | local custody + published Release | `ARCHIVABLE` | reviewer/failure history and artifact-backed evidence preserved |
| 06D / `feat/orientation-invariant-planar-correction` | exact tip remote | local custody + published Release + self-contained review v2 | `ARCHIVABLE` | geometry target fixed to `b7054f3`; policy commit remains separate |

## Non-Goal and active worktrees

| Worktree / branch | Classification | Reason |
|---|---|---|
| repository checkout / `docs/contact-benchmark-design` | `NOT_ARCHIVABLE` | active checkout with pre-existing ignored/untracked work custody; intentionally untouched |
| DOC01 / `docs/geometry-portability-playbook` | `NOT_ARCHIVABLE` | outside this Release scope and not inherited by 06A–06D |
| preservation / `chore/p0-research-evidence-preservation` | `ACTIVE_RETAIN` | report/manifests committed; worktree remains the custody control checkout |
| policy / `policy/human-inspection-deliverables` | `BLOCKED_ACTIVE` | cherry-pick conflict intentionally preserved; no PR |

06A, 06C, and 06D meet `ARCHIVABLE` evidence conditions, but remain present because this phase explicitly prohibits worktree deletion.
