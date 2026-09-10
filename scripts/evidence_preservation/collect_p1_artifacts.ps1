param(
    [Parameter(Mandatory = $true)]
    [string]$CustodyRoot,
    [Parameter(Mandatory = $true)]
    [string]$P0Root,
    [Parameter(Mandatory = $true)]
    [string]$WorktreeRoot,
    [Parameter(Mandatory = $true)]
    [string]$LegacyAuditRoot,
    [Parameter(Mandatory = $true)]
    [string]$LegacyWorkRoot,
    [Parameter(Mandatory = $true)]
    [string]$SyncPlanRoot,
    [Parameter(Mandatory = $true)]
    [string]$Historical06DRoot,
    [string]$PublicOutput = "docs\evidence_preservation\artifact_reconciliation.json",
    [string]$PrivateInventoryName = "PRIVATE_ARTIFACT_INVENTORY.json",
    [string]$CopyInventoryName = "RISK_GOAL_COPY_INVENTORY.json",
    [switch]$CopyRiskGoals
)

$ErrorActionPreference = "Stop"

function Get-SharedFileSha256([string]$Path) {
    $stream = [System.IO.File]::Open($Path, [System.IO.FileMode]::Open, [System.IO.FileAccess]::Read,
        [System.IO.FileShare]::ReadWrite -bor [System.IO.FileShare]::Delete)
    try {
        $hasher = [System.Security.Cryptography.SHA256]::Create()
        try { return ([BitConverter]::ToString($hasher.ComputeHash($stream))).Replace("-", "").ToLowerInvariant() }
        finally { $hasher.Dispose() }
    } finally { $stream.Dispose() }
}

function Add-InventoryFile(
    [System.Collections.Generic.List[object]]$Records,
    [string]$GoalId,
    [string]$SourceId,
    [string]$SourceClass,
    [string]$Root,
    [System.IO.FileInfo]$File,
    [string]$LogicalPath
) {
    $Records.Add([pscustomobject][ordered]@{
        goal_id = $GoalId
        source_id = $SourceId
        source_class = $SourceClass
        source_root = $Root
        source_path = $File.FullName
        logical_path = $LogicalPath.Replace("\", "/")
        size_bytes = $File.Length
        sha256 = Get-SharedFileSha256 $File.FullName
        classification = $null
        divergence_cause = $null
    })
}

$worktrees = [ordered]@{
    "02C" = Join-Path $WorktreeRoot "dmslicer-02c"
    "03A" = Join-Path $WorktreeRoot "dmslicer-03a"
    "03B" = Join-Path $WorktreeRoot "dmslicer-03b"
    "03C" = Join-Path $WorktreeRoot "dmslicer-03c"
    "04A" = Join-Path $WorktreeRoot "dmslicer-04a"
    "04B" = Join-Path $WorktreeRoot "dmslicer-04b"
    "05A" = Join-Path $WorktreeRoot "dmslicer-05a"
    "05B" = Join-Path $WorktreeRoot "dmslicer-05b"
    "05C" = Join-Path $WorktreeRoot "dmslicer-05c"
    "06A" = Join-Path $WorktreeRoot "dmslicer-06a"
    "06B" = Join-Path $WorktreeRoot "dmslicer-06b"
    "06C" = Join-Path $WorktreeRoot "dmslicer-06c"
    "06D" = Join-Path $WorktreeRoot "dmslicer-06d"
    "DOC01" = Join-Path $WorktreeRoot "dmslicer-doc01"
}
$historicalRoots = @(
    [pscustomobject]@{ goal_id = "LEGACY"; source_id = "CODEX_LEGACY_AUDIT"; root = $LegacyAuditRoot },
    [pscustomobject]@{ goal_id = "LEGACY"; source_id = "CODEX_LEGACY_WORK"; root = $LegacyWorkRoot },
    [pscustomobject]@{ goal_id = "LEGACY"; source_id = "CODEX_SYNC_PLAN"; root = $SyncPlanRoot },
    [pscustomobject]@{ goal_id = "06D"; source_id = "CODEX_TASK_06D"; root = $Historical06DRoot }
)
$riskGoals = @("03A", "03B", "04B", "05A")
$records = [System.Collections.Generic.List[object]]::new()
$copyRecords = [System.Collections.Generic.List[object]]::new()

foreach ($goal in $worktrees.Keys) {
    $root = $worktrees[$goal]
    if (-not (Test-Path -LiteralPath $root)) { continue }
    $files = Get-ChildItem -LiteralPath $root -File -Recurse | Where-Object {
        $_.FullName -match "\\(outputs|work)\\" -or ($goal -eq "DOC01" -and $_.FullName -match "\\docs\\workflow\\")
    }
    foreach ($file in $files) {
        $relative = [IO.Path]::GetRelativePath($root, $file.FullName)
        Add-InventoryFile $records $goal "WT_$goal" "WORKTREE" $root $file $relative
        if ($CopyRiskGoals -and $riskGoals -contains $goal) {
            $destination = Join-Path $CustodyRoot ("canonical\goal-{0}\{1}" -f $goal.ToLowerInvariant(), $relative)
            if (Test-Path -LiteralPath $destination) { throw "Refusing to overwrite preserved artifact: $destination" }
            New-Item -ItemType Directory -Path (Split-Path -Parent $destination) -Force | Out-Null
            Copy-Item -LiteralPath $file.FullName -Destination $destination
            $copyHash = Get-SharedFileSha256 $destination
            $sourceHash = Get-SharedFileSha256 $file.FullName
            if ($copyHash -ne $sourceHash) { throw "Copy verification failed: $($file.FullName)" }
            $copyRecords.Add([pscustomobject][ordered]@{
                goal_id = $goal; source_path = $file.FullName; preserved_path = $destination
                size_bytes = $file.Length; source_sha256 = $sourceHash; preserved_sha256 = $copyHash; verified = $true
            })
        }
    }
}

foreach ($historical in $historicalRoots) {
    if (-not (Test-Path -LiteralPath $historical.root)) { continue }
    foreach ($file in Get-ChildItem -LiteralPath $historical.root -File -Recurse) {
        $relative = [IO.Path]::GetRelativePath($historical.root, $file.FullName)
        if ($historical.goal_id -eq "06D") { $relative = Join-Path "outputs" $relative }
        Add-InventoryFile $records $historical.goal_id $historical.source_id "CODEX_HISTORY" $historical.root $file $relative
    }
}

$p0InventoryPath = Join-Path $P0Root "LOCAL_CUSTODY_INVENTORY.v2.json"
$p0Inventory = Get-Content -Raw -LiteralPath $p0InventoryPath | ConvertFrom-Json
foreach ($entry in $p0Inventory.entries) {
    $preserved = Join-Path $P0Root $entry.preserved_relative_path
    if (Test-Path -LiteralPath $preserved) {
        $file = Get-Item -LiteralPath $preserved
        $logical = ($entry.preserved_relative_path -replace '^canonical/goal-[^/]+/', '')
        Add-InventoryFile $records $entry.goal_id "P0_CUSTODY" "PRESERVATION" $P0Root $file $logical
    }
    if ($entry.source_root_id -like "CODEX*") {
        if (Test-Path -LiteralPath $entry.source_absolute_path) {
            $file = Get-Item -LiteralPath $entry.source_absolute_path
            Add-InventoryFile $records $entry.goal_id $entry.source_root_id "CODEX_HISTORY" (Split-Path -Parent $entry.source_absolute_path) $file $entry.source_relative_path
        }
    }
}

$p1CanonicalRoot = Join-Path $CustodyRoot "canonical"
if (Test-Path -LiteralPath $p1CanonicalRoot) {
    foreach ($goalDirectory in Get-ChildItem -LiteralPath $p1CanonicalRoot -Directory -Filter "goal-*") {
        $goal = $goalDirectory.Name.Substring(5).ToUpperInvariant()
        foreach ($file in Get-ChildItem -LiteralPath $goalDirectory.FullName -File -Recurse) {
            $relative = [IO.Path]::GetRelativePath($goalDirectory.FullName, $file.FullName)
            Add-InventoryFile $records $goal "P1_CUSTODY" "PRESERVATION" $goalDirectory.FullName $file $relative
        }
    }
}

$releaseRoot = Join-Path $P0Root "release_staging"
if (Test-Path -LiteralPath $releaseRoot) {
    foreach ($releaseDir in Get-ChildItem -LiteralPath $releaseRoot -Directory) {
        $goal = if ($releaseDir.Name -match '^goal-(06[acd])-') { $Matches[1].ToUpperInvariant() } else { $null }
        if ($null -eq $goal) { continue }
        foreach ($file in Get-ChildItem -LiteralPath $releaseDir.FullName -File -Recurse) {
            $relative = [IO.Path]::GetRelativePath($releaseDir.FullName, $file.FullName)
            Add-InventoryFile $records $goal ("RELEASE_{0}" -f $releaseDir.Name) "RELEASE" $releaseDir.FullName $file $relative
        }
    }
}

$releaseHashes = @{}
foreach ($record in $records | Where-Object source_class -eq "RELEASE") { $releaseHashes["$($record.goal_id)|$($record.sha256)"] = $true }
$pathGroups = $records | Group-Object { "$($_.goal_id)|$($_.logical_path)" }
foreach ($group in $pathGroups) {
    $distinctHashes = @($group.Group.sha256 | Sort-Object -Unique)
    foreach ($record in $group.Group) {
        if ($record.source_class -eq "RELEASE" -or $releaseHashes.ContainsKey("$($record.goal_id)|$($record.sha256)")) {
            $record.classification = "PRESENT_IN_RELEASE"
        } elseif ($distinctHashes.Count -gt 1) {
            $record.classification = "DIVERGENT_REQUIRES_REVIEW"
            $record.divergence_cause = if ($record.logical_path -match '\.(FCStd|step|stp|brep)$') { "unknown; CAD byte divergence is not geometry evidence" } else { "unknown" }
        } elseif ($group.Count -gt 1) {
            $record.classification = "IDENTICAL_DUPLICATE"
        } else {
            $record.classification = switch ($record.source_class) {
                "WORKTREE" { "ONLY_IN_WORKTREE" }
                "CODEX_HISTORY" { "ONLY_IN_CODEX_HISTORY" }
                "PRESERVATION" { "ONLY_IN_PRESERVATION" }
                default { "UNCLASSIFIED" }
            }
        }
    }
}

$privateInventory = [ordered]@{
    schema_version = 1; goal_id = "P1"; run_id = Split-Path -Leaf $CustodyRoot
    generated_at = (Get-Date).ToUniversalTime().ToString("o")
    record_count = $records.Count; total_bytes = ($records | Measure-Object size_bytes -Sum).Sum
    records = $records
}
$privateInventoryPath = Join-Path $CustodyRoot $PrivateInventoryName
if (Test-Path -LiteralPath $privateInventoryPath) { throw "Refusing to overwrite private artifact inventory: $privateInventoryPath" }
$privateInventory | ConvertTo-Json -Depth 12 | Set-Content -LiteralPath $privateInventoryPath -Encoding utf8NoBOM

if ($CopyRiskGoals) {
    $copyInventoryPath = Join-Path $CustodyRoot $CopyInventoryName
    if (Test-Path -LiteralPath $copyInventoryPath) { throw "Refusing to overwrite risk copy inventory: $copyInventoryPath" }
    [ordered]@{
        schema_version = 1; goal_id = "P1"; generated_at = (Get-Date).ToUniversalTime().ToString("o")
        copied_file_count = $copyRecords.Count; copied_bytes = ($copyRecords | Measure-Object size_bytes -Sum).Sum; records = $copyRecords
    } | ConvertTo-Json -Depth 10 | Set-Content -LiteralPath $copyInventoryPath -Encoding utf8NoBOM
}

$publicRecords = foreach ($record in $records) {
    [pscustomobject][ordered]@{
        goal_id = $record.goal_id; source_id = $record.source_id; source_class = $record.source_class
        logical_path = $record.logical_path; size_bytes = $record.size_bytes; sha256 = "sha256:$($record.sha256)"
        classification = $record.classification; divergence_cause = $record.divergence_cause
    }
}
$public = [ordered]@{
    schema_version = 1; goal_id = "P1"; generated_at = (Get-Date).ToUniversalTime().ToString("o")
    classification_note = "SHA-256 is used only for byte-integrity and byte-duplicate classification, never geometric equivalence."
    record_count = $publicRecords.Count
    by_classification = @($publicRecords | Group-Object classification | Sort-Object Name | ForEach-Object { [ordered]@{ classification = $_.Name; count = $_.Count } })
    records = $publicRecords
}
$publicDirectory = Split-Path -Parent $PublicOutput
if (-not (Test-Path -LiteralPath $publicDirectory)) { New-Item -ItemType Directory -Path $publicDirectory -Force | Out-Null }
$public | ConvertTo-Json -Depth 10 | Set-Content -LiteralPath $PublicOutput -Encoding utf8NoBOM

Write-Output "Artifact records: $($records.Count)"
Write-Output "Artifact bytes: $($privateInventory.total_bytes)"
Write-Output "Risk files copied: $($copyRecords.Count)"
Write-Output "Private inventory: $privateInventoryPath"
Write-Output "Public reconciliation: $PublicOutput"
