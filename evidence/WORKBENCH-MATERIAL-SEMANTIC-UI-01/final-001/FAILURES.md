# Preserved failure and correction timeline

| Evidence | Finding | Resolution |
|---|---|---|
| ../design-001/model-red*.txt | Initial annotation implementation absent | Model test-first implementation; original broader selection prototype later removed from09B scope |
| ../browser-red-001 | Original viewer had no bulk selection UI | Superseded by user scope move to09A; not claimed fixed in09B |
| ../browser-scope-002 | Existing service had old Python renderer loaded | Restarted only owned 56811 test service; preserved failure |
| ../browser-scope-003 | Test incorrectly expected stable Interface in C02 | Inspected real package identities; core configuration tested on stable CASE01, diagnostic cases disabled |
| ../browser-scope-004 | Browser rejected HTML pattern regex; test sample-loading race | Removed redundant browser pattern, kept model key validation; await actual sample response/state |
| ../browser-library-red-006 | Duplicate new material silently edited existing record | Require explicit existing-material edit path |
| ../browser-library-red-007 | Standalone library import absent | Added validated explicit import with orphan-reference rejection |
| ../scope-002/asset-provenance-red.txt | Object asset reference changes not checked | Match source_geometry and reference_provenance on restore |
| ../browser-provenance-red-009 | Missing annotation provenance could break geometry viewer | Graceful read-only annotation fallback, preserved geometry view |
| ../scope-002/v2-red.txt and ../browser-v2-red-010 | User semantic-type/group correction superseded v1 implementation | v2 Source/Gradient/Isolator rules, presets and group policy; explicit v1 rejection |
| ../scope-002/default-group-red.txt | Missing explicit Gradient group not defaulted on v2 import | Normalize to G with recorded system default decision |
| ../browser-review-red-012 | Imported file replaced unsaved draft | Dirty draft import rejection |
| ../browser-race-red-013 | Deferred file read could attach A annotation after opening B | Recheck case and draft revision; also guard library/package awaits |
| ../scope-002/affected-regression-002.xml | Three historical sample packages absent from new checkout | Restore only exact allowlisted package bytes; 22 regression tests passed |
| manifest-generation-failure.txt | Windows default GBK decoder rejected UTF-8 JSON | Explicit UTF-8 reads in task-local manifest builder |

Checkpoint commits: abc532d (initial RED and prototype); aa6f76b (pre-v2 implementation checkpoint); f1d9887 (final implementation and persistence fixes). Failure test/source snapshots, JSON checks and screenshots remain preserved. No failed research experiment was rerun or relabeled green; this is software/UI evidence only.

One combined background-start-and-test shell command was rejected by automatic approval review with only "blocked by policy". The task used a tool-managed foreground service and separately executed tests. No rejected action was retried with bypass permissions.
