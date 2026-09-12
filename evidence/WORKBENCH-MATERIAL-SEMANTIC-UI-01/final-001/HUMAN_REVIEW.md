# 09B human review

Status: agent screenshot review completed; user visual acceptance PENDING. No geometry/scientific validation claim.

Current implementation: f1d988768db31e726eeeb99e98d12eea86b80c0a. Latest specification: ../scope-002/SEMANTIC_TYPES_V2.md. Earlier broader geometry redesign and v1/tag concepts are historical records, not current acceptance.

Independent code reviewer identified two P2 issues: importing over a dirty draft and an async file-read race attaching case A configuration while case B was displayed. Browser tests first reproduced both; fixes reject dirty imports and check case/draft revision after asynchronous reads, including package loading. Independent follow-up confirmed both resolved, 11 model tests passed and 12 browser checks passed, with no further important issue. Reviewer used read-only probes; no source changes by reviewer.

Agent inspected desktop semantic controls, Gradient G1/G2 groups, disabled direct Gradient material, library editor, and 390/760px layouts. Fields wrap without horizontal document overflow; long object source references remain in evidence records. Typed material category/description/properties and colors are editable. Default four materials contain no physical values. Synthetic QA properties are clearly marked TEST ONLY and are not reference material data.

User review targets: material creation and return to original object; Source material requirement; Gradient group identity and forbidden direct material; Isolator stable owner and unresolved material requirement; exported v2 configuration; browser save failure and dirty-import messages. The local preview is http://127.0.0.1:56811/ with the five frozen sample copies from this run.

Scientific boundary: CASE01 editable references are inherited as provided; no new identity generation or B-rep comparison. Other four samples' run-local identities remain uneditable for domain configuration. Same-group connection policy is conditional eligibility only, never active merging; no Source/boundary relation editor or field solver was added. Source package geometry facts remain unchanged.

Evidence custody is local only. Consult custody-verification.json for two-copy integrity results; it does not establish independent disaster recovery or remote preservation. No historical worktree deletion is recommended.
