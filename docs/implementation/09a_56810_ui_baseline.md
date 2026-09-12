# 09A 56810 UI baseline

## Purpose

Preserve the working geometry workbench served on port 56810 before the 09A
interaction changes are applied. This snapshot protects the current camera,
rendering, fit, boundary, picking, and comparison behavior.

## Protected revision

- Baseline branch: `codex/09a-56810-stable-baseline`
- Baseline commit: `146dd8dd934dc81f475d33b5cbbb242cde21fa2c`
- Entry point: `src/dmslicer/geometry_import_viewer.html`
- File SHA-256: `EA48BA19EDD256B54ED8E5E3202C9E5E6D7DB73725C26401DBBD7E8044CD77C6`
- Runtime command: `python -u -m dmslicer.geometry_import --serve --port 56810`

The SHA-256 value records file byte integrity only. It is not evidence of
geometric equivalence.

## Restore procedure

To inspect the protected version without disturbing ongoing work, create a
separate worktree from the baseline branch:

```powershell
git worktree add ..\dmslicer-56810-restore codex/09a-56810-stable-baseline
```

To restore only the viewer entry point onto the current branch:

```powershell
git restore --source codex/09a-56810-stable-baseline -- src/dmslicer/geometry_import_viewer.html
```

Do not move or rewrite the baseline branch. All 09A changes must be developed
on a separate branch and reviewed as a diff from this baseline.
