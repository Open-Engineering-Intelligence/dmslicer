param(
    [string]$ConversationIndex = "docs\evidence_preservation\conversation_evidence.json",
    [string]$ManifestDirectory = "docs\evidence_preservation\manifests"
)

$ErrorActionPreference = "Stop"

function New-Fact([object]$Value, [string]$Confidence, [string]$Source) {
    return [pscustomobject][ordered]@{ value = $Value; confidence = $Confidence; source = $Source }
}

$conversation = Get-Content -Raw -LiteralPath $ConversationIndex | ConvertFrom-Json
$manifestByGoal = @{}
foreach ($path in Get-ChildItem -LiteralPath $ManifestDirectory -Filter "goal-*.json" -File) {
    $manifest = Get-Content -Raw -LiteralPath $path.FullName | ConvertFrom-Json
    $manifestByGoal[$manifest.goal_id] = [pscustomobject]@{ path = $path.FullName; document = $manifest }
}

foreach ($record in $conversation.records) {
    if ($record.task_kind -eq "root" -and $manifestByGoal.ContainsKey($record.goal_id)) {
        $manifest = $manifestByGoal[$record.goal_id].document
        $record.branch = $manifest.identity.branch.value
        $record.initial_commit = $manifest.identity.parent_baseline.value
        $record.implementation_commit = $manifest.identity.implementation_commit.value
        $record.artifact_references = @($manifest.artifacts | Select-Object -First 6 | ForEach-Object { $_.path })
        if ($manifest.release.url) { $record.release_references = @($manifest.release.url) }
        if ($manifest.release.status -like "RELEASE_BLOCKED*") { $record.unresolved_gaps = @($manifest.release.reason) }
    }
}

$special = @{
    "01a07faa-fba4-7223-bfca-b1341cbbfe45" = [pscustomobject]@{
        implementation = "07655b8ed6b0030811f7431986c4658453855bf3"; failure = $null; fix = $null
        findings = @("Initial 02C closeout had 23 passing tests but lacked repeatability coverage and final provenance linkage.")
        diagnosis = @("The preserved evidence bundle remained bound to 79f60fa and cannot establish the later final branch tip.")
        validation = @("23 passed (historical task statement; CHAT).")
    }
    "01a07fc7-ebb6-7963-8df1-b0c62e7be72a" = [pscustomobject]@{
        implementation = "b6460270f2932b8bc2bbe1bcb4c052daba1ae277"; failure = $null; fix = "b6460270f2932b8bc2bbe1bcb4c052daba1ae277"
        findings = @(); diagnosis = @("Added repeatability snapshot/provenance coverage; existing P0 evidence is not silently rebound.")
        validation = @("32 passed and two-process repeatability PASS (historical task statement; CHAT).")
    }
    "01a080e6-2995-73e2-a581-9a386e703e58" = [pscustomobject]@{
        implementation = "a1fc48b7efbd7f21c227b8da36aa5542b9f130b7"; failure = $null; fix = $null
        findings = @(); diagnosis = @(); validation = @("55 passed; six FCStd files reopened successfully (historical task statement; CHAT).")
    }
    "01a08127-8407-7052-bc88-c0c14db7d176" = [pscustomobject]@{
        implementation = "5e96906f4103f103b9522a4c6e8462ad238c74af"; failure = $null; fix = $null
        findings = @(); diagnosis = @("Periodic spherical seam degeneracy was excluded from geometry boundary/component counts; analytic surfaces were preserved.")
        validation = @("60 passed and two independent FreeCADCmd reproductions PASS (historical task statement; CHAT).")
    }
    "01a08331-eab2-7693-975a-acc0fa432065" = [pscustomobject]@{
        implementation = "4a2aad8d926ea14d9526e2b7a1428a9d652b87f9"; failure = "1c227cf75caadbb5508e261f3277b736dfc97cfd"; fix = "4a2aad8d926ea14d9526e2b7a1428a9d652b87f9"
        findings = @(); diagnosis = @("A12 S1->S2 transformGeometry introduced 0.0427656319 mm^2 before STEP export; STEP roundtrip added about 1.16e-8 mm^2. Direct normalized dimensions retained Plane/Circle and reduced error to about 4.46e-11 mm^2.")
        validation = @("Topology remained one patch, one component, two boundaries, and one hole (historical diagnostic task; CHAT).")
    }
    "01a08362-2428-7d61-9be2-322a4ae44a5e" = [pscustomobject]@{
        implementation = "19354277520c40bf61193525cbf213946dbbb511"; failure = $null; fix = $null
        findings = @(); diagnosis = @("Historical A02/A08 artifacts were recovered from Codex custody, but their execution-to-final-commit binding remains incomplete.")
        validation = @("83 tests, 0 failures/errors/skipped; duration 357.461 s (historical task statement; CHAT).")
    }
    "01a08490-3770-7430-b860-aba97b3f35d3" = [pscustomobject]@{
        implementation = "20b26450dffee96427a4375c310b8b303c1c9812"; failure = $null; fix = $null
        findings = @(); diagnosis = @(); validation = @("104 passed across 30 samples (historical task statement; CHAT).")
    }
    "01a084dc-87bf-7ac0-9cfd-697cf6a7d3ca" = [pscustomobject]@{
        implementation = "1de21fd41aac05e437f6ebb839344af171b6e878"; failure = $null; fix = $null
        findings = @(); diagnosis = @("Native mismatch 16/90; normalized mismatch 1/90. Revalidation reused preserved records rather than rerunning geometry.")
        validation = @("112 passed (preserved JUnit and historical task statement kept as separate evidence layers).")
    }
    "01a08529-6057-7e92-b0a7-e478333fac7d" = [pscustomobject]@{
        implementation = "0d681a9de1bc4e6a6978849e65c1518bfed10c61"; failure = $null; fix = "0d681a9de1bc4e6a6978849e65c1518bfed10c61"
        findings = @(); diagnosis = @("Targeted offset-measurement fix only; the 21-case recovery, repeatability, FCStd, and full regression were not complete in this task.")
        validation = @("Targeted test only (historical task statement; CHAT).")
    }
    "01a08583-c4ea-73c0-8d55-475d04a69b10" = [pscustomobject]@{
        implementation = "fa4436a2784574ffa336e87a9df898c35780a587"; failure = $null; fix = "fa4436a2784574ffa336e87a9df898c35780a587"
        findings = @(); diagnosis = @("21-case recovery produced 20 validation passes and retained A01 as an area-method exceedance.")
        validation = @("128 passed in final JUnit (preserved local evidence).")
    }
    "01a085f9-f7d8-7db2-a268-12822b3de6e6" = [pscustomobject]@{
        implementation = "aadf996a05bf87efee862964141b6aeb7f872baf"; failure = $null; fix = $null
        findings = @(); diagnosis = @("This single task contains later 06B turns; 06B completed at c23cc83a4c60620a8210e9aad01fb7adc1c72bde rather than in a separate root task.")
        validation = @("06B closeout: 217 passed (preserved JUnit; shared 06A/06B conversation provenance).")
    }
    "01a08674-c6e0-7b63-9725-d200742cb855" = [pscustomobject]@{
        implementation = "58ec93a67d8214c69bc92d5710c60d91aa1fe30c"; failure = $null; fix = "58ec93a67d8214c69bc92d5710c60d91aa1fe30c"
        findings = @("Reviewer reported Critical 0, Important 0."); diagnosis = @("Removed hash-as-geometry misuse and separated raw representation identity from tolerance-aware B-rep evidence.")
        validation = @("43/43 targeted and 260/260 full tests passed (preserved JUnit/local evidence).")
    }
    "01a08848-1ebb-75d0-89c9-75e90c2bee1e" = [pscustomobject]@{
        implementation = "b7054f303896aa4a0762248a0b54686d8e733ead"; failure = $null; fix = "b7054f303896aa4a0762248a0b54686d8e733ead"
        findings = @(
            "Important: the covariance validator hardcoded/reconstructed direction data instead of validating measured base operation n'=R*n and t'=R*t; corrupt base references could still pass.",
            "Important: inverse-transform B-rep validation omitted required solid face/edge/vertex and surface/boundary-family checks, allowing split or resegmented boundaries to pass."
        )
        diagnosis = @("Reviewer ran before the single geometry commit, so no separate pre-fix commit exists; both fixes were incorporated into b7054f3.")
        validation = @("283 passed, 0 failures/errors/skipped; duration 930.54 s (preserved JUnit and historical closeout).")
    }
    "01a0887c-0ff5-7303-83ac-7de7484077e5" = [pscustomobject]@{
        implementation = "b7054f303896aa4a0762248a0b54686d8e733ead"; failure = $null; fix = "b7054f303896aa4a0762248a0b54686d8e733ead"
        findings = @(
            "Important: covariance evidence did not consume the measured base normal/direction/translation and could pass after corrupting the base reference and translation.",
            "Important: inverse-transform B-rep checks did not cover complete topology and boundary/surface families for solids and faces."
        )
        diagnosis = @("Reviewer verdict: not ready; Critical 0, Important 2. The parent task records both as fixed, unresolved 0.")
        validation = @()
    }
}

foreach ($record in $conversation.records) {
    if (-not $special.ContainsKey($record.task_id)) { continue }
    $item = $special[$record.task_id]
    $record.implementation_commit = $item.implementation
    $record.failure_commit = $item.failure
    $record.reviewer_finding = $item.findings
    $record.diagnosis = $item.diagnosis
    $record.fix_commit = $item.fix
    $record.validation = $item.validation
}

$conversation | ConvertTo-Json -Depth 15 | Set-Content -LiteralPath $ConversationIndex -Encoding utf8NoBOM

foreach ($goal in $manifestByGoal.Keys) {
    $entry = $manifestByGoal[$goal]
    $manifest = $entry.document
    $manifest.schema_version = "1.1.0"
    $manifest | Add-Member -NotePropertyName run_id -NotePropertyValue ("p0-preservation-{0}-{1}" -f $goal.ToLowerInvariant(), $manifest.identity.implementation_commit.value.Substring(0, 7)) -Force
    $manifest | Add-Member -NotePropertyName run_role -NotePropertyValue (New-Fact "preservation_control_plane" "L" "P0/P1 custody audit; not a historical experiment execution run") -Force
    $refs = @($conversation.records | Where-Object { $_.related_goal_ids -contains $goal } | ForEach-Object {
        [pscustomobject][ordered]@{
            task_id = $_.task_id
            relationship = $_.task_kind
            archive_id = $_.private_archive.archive_id
            confidence = "CHAT"
            source = "P1 private read-only conversation custody; public metadata in conversation_evidence.json"
        }
    })
    $manifest | Add-Member -NotePropertyName conversation_provenance -NotePropertyValue $refs -Force

    switch ($goal) {
        "02C" {
            $manifest.history.fix_commits = @(
                (New-Fact "07655b8ed6b0030811f7431986c4658453855bf3" "GH" "Git commit; initial 02C closeout")
                (New-Fact "b6460270f2932b8bc2bbe1bcb4c052daba1ae277" "GH" "Git commit; repeatability completion")
            )
            $manifest.history.reviewer_findings = @(New-Fact "Initial closeout lacked repeatability coverage and final provenance linkage; later task added repeatability, but did not rebind the older evidence bundle." "CHAT" "Codex tasks 01a07faa... and 01a07fc7...")
            $manifest.results.software_pytest = New-Fact "32 passed and two-process repeatability PASS; historical task statement only." "CHAT" "Codex task 01a07fc7-ebb6-7963-8df1-b0c62e7be72a"
        }
        "03A" { $manifest.results.software_pytest = New-Fact "55 passed; six FCStd artifacts reopened successfully; historical task statement only." "CHAT" "Codex task 01a080e6-2995-73e2-a581-9a386e703e58" }
        "03B" { $manifest.results.software_pytest = New-Fact "60 passed and two independent FreeCADCmd reproductions PASS; historical task statement only." "CHAT" "Codex task 01a08127-8407-7052-bc88-c0c14db7d176" }
        "03C" {
            $manifest.history.known_failures_or_mismatches = @($manifest.history.known_failures_or_mismatches | Where-Object source -notlike "Codex task 01a08331*") + @(New-Fact "Conversation diagnostic localized A12 error creation to S1->S2 transformGeometry: 0.0427656319 mm^2 before export; STEP roundtrip added about 1.16e-8 mm^2. Direct normalized construction retained Plane/Circle with about 4.46e-11 mm^2 error." "CHAT" "Codex task 01a08331-eab2-7693-975a-acc0fa432065")
        }
        "04A" { $manifest.results.software_pytest = New-Fact "83 tests, 0 failures, 0 errors, 0 skipped; duration 357.461 s; historical task statement only." "CHAT" "Codex task 01a08362-2428-7d61-9be2-322a4ae44a5e" }
        "05A" { $manifest.results.software_pytest = New-Fact "104 passed across 30 samples; historical task statement only." "CHAT" "Codex task 01a08490-3770-7430-b860-aba97b3f35d3" }
        "06D" {
            $manifest.history.known_failures_or_mismatches = @($manifest.history.known_failures_or_mismatches | Where-Object source -notlike "Reviewer task 01a0887c*") + @(New-Fact "No separate pre-fix commit exists because review preceded the single geometry commit; failure_commit remains unknown/not applicable rather than inferred." "CHAT" "Reviewer task 01a0887c-0ff5-7303-83ac-7de7484077e5")
            $manifest.history.reviewer_findings = @(
                (New-Fact "Important: covariance validation hardcoded/reconstructed direction data instead of validating measured base operation n'=R*n and t'=R*t; corrupted base references could pass." "CHAT" "Reviewer task 01a0887c-0ff5-7303-83ac-7de7484077e5")
                (New-Fact "Important: inverse-transform B-rep validation omitted solid face/edge/vertex and surface/boundary-family checks, and analogous face boundary checks; split or resegmented boundaries could pass." "CHAT" "Reviewer task 01a0887c-0ff5-7303-83ac-7de7484077e5")
            )
        }
    }
    $manifest | ConvertTo-Json -Depth 20 | Set-Content -LiteralPath $entry.path -Encoding utf8NoBOM
}

Write-Output "Enriched conversation index and $($manifestByGoal.Count) manifests."
