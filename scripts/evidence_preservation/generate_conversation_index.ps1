param(
    [string]$InputPath = "docs\evidence_preservation\conversation_evidence.json",
    [string]$OutputPath = "docs\evidence_preservation\CONVERSATION_EVIDENCE_INDEX.md"
)

$ErrorActionPreference = "Stop"
$doc = Get-Content -Raw -LiteralPath $InputPath | ConvertFrom-Json
$roots = @($doc.records | Where-Object task_kind -eq "root" | Sort-Object updated_at)
$lines = [System.Collections.Generic.List[string]]::new()
$lines.Add("# Conversation Evidence Index")
$lines.Add("")
$lines.Add("This is the public, sanitized index for read-only DM-Slicer Codex task custody. Raw JSONL exports, exact local source paths, and full task text remain in the private P1 custody root. A conversation is `CHAT` provenance: it can recover a claim or review chain, but it does not replace artifact-backed validation or establish a current geometry PASS.")
$lines.Add("")
$lines.Add("## Discovery result")
$lines.Add("")
$lines.Add("- Session-index entries searched: $($doc.discovery.session_index_entries).")
$lines.Add("- Root tasks selected: $($doc.discovery.root_candidate_count).")
$lines.Add("- Root plus reviewer/subagent tasks: $($doc.discovery.related_task_count).")
$lines.Add("- Fully readable: $($doc.discovery.fully_read_count).")
$lines.Add("- Metadata-only or otherwise inaccessible: $($doc.discovery.inaccessible_count).")
$lines.Add("- Selection: title search, explicit reverse-search identity, and descendant reviewer/subagent relationships.")
$lines.Add("")
$lines.Add("## Root task inventory")
$lines.Add("")
$lines.Add("| Goal(s) | Task ID | Title | Access | Implementation / gap |")
$lines.Add("|---|---|---|---|---|")
foreach ($record in $roots) {
    $goals = (@($record.related_goal_ids) -join ", ") -replace '\|', '\|'
    $title = ([string]$record.task_title) -replace '\|', '\|'
    $implementation = if ($record.implementation_commit) { ([string]$record.implementation_commit).Substring(0, [Math]::Min(12, ([string]$record.implementation_commit).Length)) } elseif ($record.unresolved_gaps.Count -gt 0) { "gap retained" } else { "not asserted" }
    $lines.Add("| $goals | ``$($record.task_id)`` | $title | ``$($record.access_status)`` | $implementation |")
}
$lines.Add("")
$lines.Add("## Recovered high-value chains")
$lines.Add("")
$lines.Add("- **02C:** the first closeout reported 23 passing tests but lacked repeatability and final provenance linkage. A later task reported 32 passing tests and two-process repeatability at `b646027`; the older evidence bundle remains bound to `79f60fa`, so the Release stays blocked.")
$lines.Add("- **03C/A12:** the diagnostic task localized the 0.0427656319 mm^2 error to `transformGeometry` before STEP export; the STEP roundtrip added only about 1.16e-8 mm^2. Direct normalized construction retained Plane/Circle and reduced the error to about 4.46e-11 mm^2. This does not repair the missing post-fix run-to-commit binding.")
$lines.Add("- **04A:** the task reported 83 tests with no failures/errors/skips at `1935427`, and historical A02/A08 CAD evidence was recovered. Because the historical outputs do not bind their execution explicitly to that commit, the Release stays blocked.")
$lines.Add("- **06A/06B:** one root task contains both phases. 06B was completed in later turns at `c23cc83`; there is no missing synthetic 06B root task.")
$lines.Add("- **06D review:** reviewer task `01a0887c-0ff5-7303-83ac-7de7484077e5` reported Critical 0 and Important 2. One finding showed covariance checks did not consume measured base normal/direction/translation and could pass corrupted base references. The other showed incomplete solid/face topology and boundary/surface-family checks in inverse-transform B-rep validation. Review preceded the single geometry commit; both fixes were incorporated into `b7054f3`, with no separately identifiable pre-fix commit.")
$lines.Add("")
$lines.Add("## Access limitations")
$lines.Add("")
$lines.Add("Two root tasks contain only session metadata: `01a07ec5-8f10-7302-89cf-d4ce461fa7f4` and `01a08363-8d56-75e1-9a9d-51047fb9a9f5`. Their contents are not reconstructed. No missing field is inferred from timestamps, adjacent commits, or task naming.")
$lines.Add("")
$lines.Add("The machine-readable companion is `conversation_evidence.json`. Each record includes its private archive ID and byte-integrity hash without exposing the local custody path.")

$lines | Set-Content -LiteralPath $OutputPath -Encoding utf8NoBOM
Write-Output "Wrote $OutputPath with $($roots.Count) root tasks."
