param(
    [Parameter(Mandatory = $true)]
    [string]$CustodyRoot,
    [Parameter(Mandatory = $true)]
    [string]$CodexRoot,
    [string]$PublicOutput = "docs\evidence_preservation\conversation_evidence.json"
)

$ErrorActionPreference = "Stop"

function Get-GoalId([string]$title, [string]$id) {
    if ($id -eq "01a07fc7-ebb6-7963-8df1-b0c62e7be72a") { return "02C" }
    if ($id -eq "01a08331-eab2-7693-975a-acc0fa432065") { return "03C" }
    if ($id -eq "01a08980-5bae-7921-9526-da11bd01d7bf") { return "POLICY" }
    foreach ($goal in @("02A", "02B", "02R2", "02R", "02V", "02C", "03P", "03A", "03B", "03C", "04A", "04B", "05A", "05B", "05C", "06A", "06B", "06C", "06D", "DOC01")) {
        if ($title -match [regex]::Escape($goal)) { return $goal }
    }
    if ($title -match "历史证据完整性") { return "AUDIT" }
    if ($title -match "P0 Research Evidence") { return "P0" }
    if ($title -match "Policy|Agent 治理") { return "POLICY" }
    return "LEGACY"
}

function Get-ParentThreadId($meta) {
    if ($null -ne $meta.source -and $null -ne $meta.source.subagent -and $null -ne $meta.source.subagent.thread_spawn) {
        return $meta.source.subagent.thread_spawn.parent_thread_id
    }
    return $null
}

function Get-RootThreadId([string]$id, $metadataById) {
    $cursor = $id
    $seen = [System.Collections.Generic.HashSet[string]]::new([System.StringComparer]::OrdinalIgnoreCase)
    while ($null -ne $cursor -and $seen.Add($cursor)) {
        if ($null -eq $metadataById[$cursor]) { return $cursor }
        $parent = Get-ParentThreadId $metadataById[$cursor]
        if ($null -eq $parent) { return $cursor }
        $cursor = $parent
    }
    return $id
}

function Get-SharedFileSha256([string]$path) {
    $stream = [System.IO.File]::Open(
        $path,
        [System.IO.FileMode]::Open,
        [System.IO.FileAccess]::Read,
        [System.IO.FileShare]::ReadWrite -bor [System.IO.FileShare]::Delete
    )
    try {
        $hasher = [System.Security.Cryptography.SHA256]::Create()
        try {
            return ([System.BitConverter]::ToString($hasher.ComputeHash($stream))).Replace("-", "").ToLowerInvariant()
        } finally {
            $hasher.Dispose()
        }
    } finally {
        $stream.Dispose()
    }
}

$indexPath = Join-Path $CodexRoot "session_index.jsonl"
$indexRows = Get-Content -LiteralPath $indexPath | ForEach-Object { $_ | ConvertFrom-Json }
$latest = @{}
foreach ($row in $indexRows) { $latest[$row.id] = $row }

$explicitRootIds = @(
    "01a07fc6-057c-7550-9034-af5db17c9370",
    "01a08980-5bae-7921-9526-da11bd01d7bf"
)
$excludedRootIds = @("01a0898e-c850-7402-97b8-eafb8a05739b")
$rootRows = @($latest.Values | Where-Object {
    (($_.thread_name -match "(?i)DM-Slicer|DMSlicer|CASE01|A12") -or ($explicitRootIds -contains $_.id)) -and
    -not ($excludedRootIds -contains $_.id)
} | Sort-Object updated_at)

$sessionFiles = @(
    Get-ChildItem -LiteralPath (Join-Path $CodexRoot "sessions") -Filter "*.jsonl" -File -Recurse
    Get-ChildItem -LiteralPath (Join-Path $CodexRoot "archived_sessions") -Filter "*.jsonl" -File
)
$sessionById = @{}
$metadataById = @{}
foreach ($file in $sessionFiles) {
    $firstLine = Get-Content -LiteralPath $file.FullName -TotalCount 1
    if ([string]::IsNullOrWhiteSpace($firstLine)) { continue }
    try { $record = $firstLine | ConvertFrom-Json } catch { continue }
    if ($record.type -ne "session_meta") { continue }
    $id = $record.payload.id
    if ([string]::IsNullOrWhiteSpace($id)) { continue }
    $sessionById[$id] = $file.FullName
    $metadataById[$id] = $record.payload
}

$selectedIds = [System.Collections.Generic.HashSet[string]]::new([System.StringComparer]::OrdinalIgnoreCase)
foreach ($row in $rootRows) { [void]$selectedIds.Add($row.id) }

$changed = $true
while ($changed) {
    $changed = $false
    foreach ($id in @($metadataById.Keys)) {
        $parent = Get-ParentThreadId $metadataById[$id]
        if ($null -ne $parent -and $selectedIds.Contains($parent) -and -not $selectedIds.Contains($id)) {
            [void]$selectedIds.Add($id)
            $changed = $true
        }
    }
}

$goalById = @{}
foreach ($row in $rootRows) { $goalById[$row.id] = Get-GoalId $row.thread_name $row.id }
foreach ($id in @($selectedIds)) {
    if ($null -ne $goalById[$id]) { continue }
    $ancestor = $id
    $seen = [System.Collections.Generic.HashSet[string]]::new([System.StringComparer]::OrdinalIgnoreCase)
    while ($null -ne $ancestor -and $seen.Add($ancestor)) {
        if ($null -ne $goalById[$ancestor]) {
            $goalById[$id] = $goalById[$ancestor]
            break
        }
        $ancestor = if ($null -ne $metadataById[$ancestor]) { Get-ParentThreadId $metadataById[$ancestor] } else { $null }
    }
    if ($null -eq $goalById[$id]) { $goalById[$id] = "LEGACY" }
}

$conversationDirectory = Join-Path $CustodyRoot "private_conversations"
New-Item -ItemType Directory -Path $conversationDirectory -Force | Out-Null
$privatePath = Join-Path $CustodyRoot "PRIVATE_CONVERSATION_INVENTORY.json"
if (Test-Path -LiteralPath $privatePath) {
    throw "Refusing to overwrite private conversation inventory: $privatePath"
}
$privateRecords = @()
$publicRecords = @()

foreach ($id in @($selectedIds | Sort-Object)) {
    $isRoot = $null -ne $latest[$id]
    $title = if ($isRoot) { $latest[$id].thread_name } else { "review/subagent task" }
    $updatedAt = if ($isRoot) { $latest[$id].updated_at } else { $metadataById[$id].timestamp }
    $source = $sessionById[$id]
    $parent = if ($null -ne $metadataById[$id]) { Get-ParentThreadId $metadataById[$id] } else { $null }
    $archiveId = "codex-task-$id"
    $sha256 = $null
    $copySha256 = $null
    $copyVerified = $false
    $accessStatus = "not_located"
    $destination = $null

    if ($null -ne $source) {
        $destination = Join-Path $conversationDirectory ("task-{0}.jsonl" -f $id)
        if (Test-Path -LiteralPath $destination) {
            throw "Refusing to overwrite existing conversation custody file: $destination"
        }
        Copy-Item -LiteralPath $source -Destination $destination
        $sha256 = Get-SharedFileSha256 $source
        $copySha256 = Get-SharedFileSha256 $destination
        $copyVerified = $sha256 -eq $copySha256
        if (-not $copyVerified) { throw "Conversation copy verification failed for $id" }
        $recordCount = 0
        Get-Content -LiteralPath $destination | ForEach-Object {
            $_ | ConvertFrom-Json | Out-Null
            $recordCount++
        }
        $accessStatus = if ($recordCount -le 2) { "metadata_only" } else { "fully_read" }
    }

    $privateRecords += [ordered]@{
        task_id = $id
        parent_task_id = $parent
        task_title = $title
        source_path = $source
        custody_path = $destination
        archive_id = $archiveId
        source_sha256 = $sha256
        copy_sha256 = $copySha256
        copy_verified = $copyVerified
        access_status = $accessStatus
    }
    $rootThreadId = Get-RootThreadId $id $metadataById
    $relatedGoalIds = if ($rootThreadId -eq "01a085f9-f7d8-7db2-a268-12822b3de6e6") {
        @("06A", "06B")
    } else {
        @($goalById[$id])
    }
    $publicRecords += [ordered]@{
        goal_id = $goalById[$id]
        related_goal_ids = $relatedGoalIds
        thread_id = $id
        task_id = $id
        parent_task_id = $parent
        task_title = $title
        task_kind = if ($null -eq $parent) { "root" } else { "review_or_subagent" }
        updated_at = $updatedAt
        access_status = $accessStatus
        private_archive = [ordered]@{
            archive_id = $archiveId
            sha256 = if ($null -eq $sha256) { $null } else { "sha256:$sha256" }
            confidence = if ($copyVerified) { "L" } else { "U" }
        }
        branch = $null
        initial_commit = $null
        implementation_commit = $null
        failure_commit = $null
        reviewer_finding = @()
        diagnosis = @()
        fix_commit = $null
        validation = @()
        artifact_references = @()
        release_references = @()
        confidence = if ($copyVerified) { @("CHAT", "L") } else { @("U") }
        unresolved_gaps = @()
    }
}

$privateInventory = [ordered]@{
    schema_version = 1
    goal_id = "P1"
    run_id = Split-Path -Leaf $CustodyRoot
    generated_at = (Get-Date).ToUniversalTime().ToString("o")
    root_candidate_count = $rootRows.Count
    selected_task_count = $privateRecords.Count
    fully_read_count = @($privateRecords | Where-Object access_status -eq "fully_read").Count
    inaccessible_count = @($privateRecords | Where-Object access_status -ne "fully_read").Count
    records = $privateRecords
}
$privateInventory | ConvertTo-Json -Depth 12 | Set-Content -LiteralPath $privatePath -Encoding utf8NoBOM

$public = [ordered]@{
    schema_version = 1
    goal_id = "P1"
    generated_at = (Get-Date).ToUniversalTime().ToString("o")
    discovery = [ordered]@{
        session_index_entries = $indexRows.Count
        root_candidate_count = $rootRows.Count
        related_task_count = $publicRecords.Count
        fully_read_count = @($publicRecords | Where-Object access_status -eq "fully_read").Count
        inaccessible_count = @($publicRecords | Where-Object access_status -ne "fully_read").Count
        selection_basis = @("title", "explicit reverse-search identity", "descendant reviewer/subagent relationship")
    }
    records = $publicRecords
}
$publicDirectory = Split-Path -Parent $PublicOutput
if (-not (Test-Path -LiteralPath $publicDirectory)) { New-Item -ItemType Directory -Path $publicDirectory -Force | Out-Null }
$public | ConvertTo-Json -Depth 12 | Set-Content -LiteralPath $PublicOutput -Encoding utf8NoBOM

Write-Output "Root candidates: $($rootRows.Count)"
Write-Output "Selected tasks: $($privateRecords.Count)"
Write-Output "Fully read: $(@($privateRecords | Where-Object access_status -eq 'fully_read').Count)"
Write-Output "Inaccessible: $(@($privateRecords | Where-Object access_status -ne 'fully_read').Count)"
Write-Output "Private inventory: $privatePath"
Write-Output "Public index: $PublicOutput"
