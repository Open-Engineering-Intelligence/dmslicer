param(
    [string]$RepositoryRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")),
    [Parameter(Mandatory = $true)]
    [string]$CustodyInventory,
    [Parameter(Mandatory = $true)]
    [string]$WorktreesRoot
)

$ErrorActionPreference = "Stop"

function Fact($Value, [string]$Confidence, [AllowNull()][string]$Source) {
    [ordered]@{ value = $Value; confidence = $Confidence; source = $Source }
}

function UnknownFact() { Fact $null "U" $null }

function HashInput([string]$Goal, [string]$RelativePath) {
    $worktree = Join-Path $WorktreesRoot ("dmslicer-" + $Goal.ToLowerInvariant())
    $absolute = Join-Path $worktree ($RelativePath -replace '/', '\')
    if (-not (Test-Path -LiteralPath $absolute -PathType Leaf)) {
        throw "Missing input fixture for ${Goal}: $RelativePath"
    }
    [ordered]@{
        fixture_id = (($RelativePath -replace '\\', '/') -replace '[^A-Za-z0-9_.-]', '-')
        path = ($RelativePath -replace '\\', '/')
        sha256 = (Get-FileHash -LiteralPath $absolute -Algorithm SHA256).Hash.ToLowerInvariant()
        confidence = "L"
    }
}

function InputFiles([string]$Goal, [string[]]$Patterns) {
    $worktree = Join-Path $WorktreesRoot ("dmslicer-" + $Goal.ToLowerInvariant())
    $items = @()
    foreach ($pattern in $Patterns) {
        $items += Get-ChildItem -LiteralPath (Join-Path $worktree ($pattern.Split('*')[0] -replace '/', '\')) -File -Recurse -ErrorAction SilentlyContinue |
            Where-Object { ($_.FullName.Substring($worktree.Length + 1) -replace '\\', '/') -like $pattern }
    }
    @($items | Sort-Object FullName -Unique | ForEach-Object {
        $relative = $_.FullName.Substring($worktree.Length + 1) -replace '\\', '/'
        HashInput $Goal $relative
    })
}

function ArtifactKind([string]$Path) {
    $name = [IO.Path]::GetFileName($Path)
    $extension = [IO.Path]::GetExtension($Path).ToLowerInvariant()
    if ($extension -eq ".xml" -and $Path -match '(?i)(junit|pytest|06b_)') { return "JUNIT" }
    if ($name -eq "validation.json" -or $Path -match '(?i)revalidation.*\.json$') { return "VALIDATOR" }
    if ($extension -eq ".brep") { return "BREP" }
    if ($extension -eq ".step") { return "STEP" }
    if ($extension -eq ".fcstd") { return "FCStd" }
    if ($name -eq "VIEW_INDEX.md") { return "VIEW_INDEX" }
    if ($Path -match '(?i)human_review') { return "HUMAN_REVIEW" }
    if ($Path -match '(?i)(failure|diagnostic|candidate_probe|review)') { return "FAILURE_OR_REVIEW_EVIDENCE" }
    return "SUPPORTING_EVIDENCE"
}

function PublicArtifactPath($Entry) {
    $relative = $Entry.source_relative_path -replace '\\', '/'
    switch ($Entry.source_root_id) {
        "WT_05C_REPO" { return $relative }
        "WT_06B_WORK" { return $relative }
        default {
            $prefix = @{
                "02C" = "outputs/step_interface_case01"
                "03C" = "outputs/contact_canonical_03c"
                "04A" = "outputs/contact_partition_union_04a"
                "05B" = "outputs/contact_scale_covariance_05b"
                "05C" = "outputs/contact_fixed_tolerance_05c"
                "06A" = "outputs/planar_gap_assembly_correction_06a"
                "06B" = "outputs/planar_partial_overlap_correction_06b"
                "06C" = "outputs/planar_multipatch_interface_correction_06c"
                "06D" = "outputs/orientation_invariant_planar_correction_06d"
            }[$Entry.goal_id]
            if ($null -eq $prefix) { return $null }
            return "$prefix/$relative"
        }
    }
}

function ArtifactsForGoal([string]$Goal, $CustodyEntries) {
    $selected = @($CustodyEntries | Where-Object goal_id -eq $Goal | Sort-Object preserved_relative_path)
    if ($selected.Count -eq 0) {
        return @(
            [ordered]@{ artifact_id = "goal-$($Goal.ToLowerInvariant())-junit-unrecovered"; kind = "JUNIT"; path = $null; release_asset_name = $null; sha256 = $null; size_bytes = $null; validation_role = "historical JUnit not present in P0 custody sources"; confidence = "U" },
            [ordered]@{ artifact_id = "goal-$($Goal.ToLowerInvariant())-validator-unrecovered"; kind = "VALIDATOR"; path = $null; release_asset_name = $null; sha256 = $null; size_bytes = $null; validation_role = "historical validator output not present in P0 custody sources"; confidence = "U" },
            [ordered]@{ artifact_id = "goal-$($Goal.ToLowerInvariant())-geometry-unrecovered"; kind = "GEOMETRY"; path = $null; release_asset_name = $null; sha256 = $null; size_bytes = $null; validation_role = "historical STEP/BREP/FCStd output not present in P0 custody sources"; confidence = "U" }
        )
    }
    $index = 0
    return @($selected | ForEach-Object {
        $index++
        $kind = ArtifactKind $_.source_relative_path
        [ordered]@{
            artifact_id = "goal-$($Goal.ToLowerInvariant())-custody-{0:d4}" -f $index
            kind = $kind
            path = PublicArtifactPath $_
            release_asset_name = $null
            sha256 = $_.preserved_sha256
            size_bytes = [int64]$_.size_bytes
            validation_role = switch ($kind) {
                "JUNIT" { "software test evidence; not a scientific PASS assertion" }
                "VALIDATOR" { "artifact-backed validation evidence" }
                "BREP" { "authoritative B-rep geometry artifact; SHA-256 is integrity only" }
                "STEP" { "exchange geometry artifact; SHA-256 is integrity only" }
                "FCStd" { "manual inspection/debug document" }
                "VIEW_INDEX" { "manual inspection index" }
                "HUMAN_REVIEW" { "historical human-review packaging evidence" }
                "FAILURE_OR_REVIEW_EVIDENCE" { "retained failure, mismatch, diagnostic, or review evidence" }
                default { "supporting provenance or experiment evidence" }
            }
            confidence = "L"
        }
    })
}

$main = "5c09db91a5a2cf363beb4750384f532a3308f995"
$configs = [ordered]@{
    "02C" = @{ branch="fix/case01-foundation"; tip="b6460270f2932b8bc2bbe1bcb4c052daba1ae277"; impl="b6460270f2932b8bc2bbe1bcb4c052daba1ae277"; parent=$main; previous=$main; binding="79f60fa"; bindingConfidence="L"; bindingSource="outputs/step_interface_case01/manifest.json"; inputs=@("benchmarks/interface_case01/case01.step"); release="RELEASE_BLOCKED_PROVENANCE"; reason="The preserved bundle embeds Git HEAD 79f60fa, so it cannot be rebound to final branch tip b646027."; pytest=$null; scientific="Historical evidence bundle preserved; final-HEAD scientific result is not established by this bundle."; provenance="GAP: final branch tip and preserved evidence bundle are not bound." }
    "03A" = @{ branch="feat/contact-canonical-planar-dimensions"; tip="a1fc48b7efbd7f21c227b8da36aa5542b9f130b7"; impl="bd831be5664dda92b9d9d0e3dba71d941fce0090"; parent="b6460270f2932b8bc2bbe1bcb4c052daba1ae277"; previous="b6460270f2932b8bc2bbe1bcb4c052daba1ae277"; binding=$null; inputs=@("benchmarks/contact_canonical_03a/*/fixture.step"); release="NOT_IN_P0_RELEASE_SCOPE"; reason="Manifest only; 03A packaging is a sibling history that was not inherited by 03B-06D."; scientific=$null; provenance="No P0 canonical output custody set was selected for 03A." }
    "03B" = @{ branch="feat/contact-canonical-analytic-curves"; tip="5e96906f4103f103b9522a4c6e8462ad238c74af"; impl="5e96906f4103f103b9522a4c6e8462ad238c74af"; parent="bd831be5664dda92b9d9d0e3dba71d941fce0090"; previous="bd831be5664dda92b9d9d0e3dba71d941fce0090"; binding=$null; inputs=@("benchmarks/contact_canonical_03b/*/fixture.step"); release="NOT_IN_P0_RELEASE_SCOPE"; reason="Manifest only; no P0 canonical output custody set was selected for 03B."; scientific=$null; provenance="No P0 canonical output custody set was selected for 03B." }
    "03C" = @{ branch="feat/contact-canonical-interface-topology"; tip="4a2aad8d926ea14d9526e2b7a1428a9d652b87f9"; impl="4a2aad8d926ea14d9526e2b7a1428a9d652b87f9"; parent="5e96906f4103f103b9522a4c6e8462ad238c74af"; previous="5e96906f4103f103b9522a4c6e8462ad238c74af"; binding=$null; inputs=@("benchmarks/contact_canonical_03c/*/fixture.step"); release="RELEASE_BLOCKED_PROVENANCE"; reason="The pre-fix evidence binds 1c227cf, but the preserved post-fix directory does not explicitly bind its execution to 4a2aad8."; scientific="Pre-fix A12 area mismatch retained; repaired fixture evidence retained, but execution-to-fix-commit binding is incomplete."; provenance="PARTIAL: pre-fix baseline is explicit; post-fix execution commit is not explicit." }
    "04A" = @{ branch="feat/contact-partition-and-union"; tip="19354277520c40bf61193525cbf213946dbbb511"; impl="19354277520c40bf61193525cbf213946dbbb511"; parent="4a2aad8d926ea14d9526e2b7a1428a9d652b87f9"; previous="4a2aad8d926ea14d9526e2b7a1428a9d652b87f9"; binding=$null; inputs=@("benchmarks/contact_canonical_03a/A02/fixture.step","benchmarks/contact_canonical_03b/A08/fixture.step"); release="RELEASE_BLOCKED_PROVENANCE"; reason="A02/A08 fragile artifacts are preserved, but their historical task outputs do not explicitly bind execution to 1935427."; scientific="A02/A08 BREP, FCStd, STEP, validation, and VIEW_INDEX preserved without changing results."; provenance="PARTIAL: custody is verified; implementation-run binding is unresolved." }
    "04B" = @{ branch="feat/cylinder-partition-and-union"; tip="e50e1b8e7735f29a15175929000e799a54a83451"; impl="e50e1b8e7735f29a15175929000e799a54a83451"; parent="19354277520c40bf61193525cbf213946dbbb511"; previous="19354277520c40bf61193525cbf213946dbbb511"; binding=$null; inputs=@("benchmarks/cylinder_fit_04b/*/inputs.step"); release="NOT_IN_P0_RELEASE_SCOPE"; reason="Manifest only; no P0 canonical output custody set was selected for 04B."; scientific=$null; provenance="No P0 canonical output custody set was selected for 04B." }
    "05A" = @{ branch="feat/contact-tolerance-pilot"; tip="20b26450dffee96427a4375c310b8b303c1c9812"; impl="20b26450dffee96427a4375c310b8b303c1c9812"; parent="e50e1b8e7735f29a15175929000e799a54a83451"; previous="e50e1b8e7735f29a15175929000e799a54a83451"; binding=$null; inputs=@("benchmarks/contact_tolerance_pilot_05a/*/inputs.step"); release="NOT_IN_P0_RELEASE_SCOPE"; reason="Manifest only; no P0 canonical output custody set was selected for 05A."; scientific=$null; provenance="No P0 canonical output custody set was selected for 05A." }
    "05B" = @{ branch="feat/contact-scale-covariance-pilot"; tip="1de21fd41aac05e437f6ebb839344af171b6e878"; impl="1de21fd41aac05e437f6ebb839344af171b6e878"; parent="20b26450dffee96427a4375c310b8b303c1c9812"; previous="20b26450dffee96427a4375c310b8b303c1c9812"; binding=$null; inputs=@("benchmarks/contact_scale_covariance_05b/*/inputs.step"); release="RELEASE_BLOCKED_PROVENANCE"; reason="Mismatch evidence is complete locally, but the run artifacts do not explicitly bind to final implementation commit 1de21fd."; pytest="112 passed, 0 failures, 0 errors, 0 skipped; software result only."; timestamp="2026-09-09T15:21:43.469325"; scientific="Native mismatch 16/90; scale-normalized mismatch 1/90; primary verdict METHOD_MISMATCH."; provenance="PARTIAL: result counts and saved measurements are explicit; final implementation binding is not." }
    "05C" = @{ branch="feat/contact-fixed-tolerance-pilot"; tip="fa4436a2784574ffa336e87a9df898c35780a587"; impl="fa4436a2784574ffa336e87a9df898c35780a587"; parent="1de21fd41aac05e437f6ebb839344af171b6e878"; previous="1de21fd41aac05e437f6ebb839344af171b6e878"; binding="0d681a9"; bindingConfidence="L"; bindingSource="outputs/contact_fixed_tolerance_05c/input_resolution.json"; inputs=@("tests/data/contact_fixed_tolerance_05c/*/inputs.step"); release="RELEASE_BLOCKED_PROVENANCE"; reason="Preserved input resolution binds 0d681a9, not final branch tip fa4436a; outputs must not be rebound."; pytest="128 passed, 0 failures, 0 errors, 0 skipped; software result only."; timestamp="2026-09-09T19:14:37.381955"; scientific="86/90 constructible and measured; 75 MEASURED_PASS, 11 METHOD_MISMATCH, 4 OUT_OF_CONSTRUCTION_DOMAIN. Retained A01_delta_p0tauE_s100 area-method exceedance error -2.9765069484710693e-06 mm^2."; provenance="GAP: preserved run binds 0d681a9 rather than final fa4436a." }
    "06A" = @{ branch="feat/planar-gap-assembly-correction"; tip="aadf996a05bf87efee862964141b6aeb7f872baf"; impl="aadf996a05bf87efee862964141b6aeb7f872baf"; parent="fa4436a2784574ffa336e87a9df898c35780a587"; previous="fa4436a2784574ffa336e87a9df898c35780a587"; binding="aadf996a05bf87efee862964141b6aeb7f872baf"; bindingConfidence="L"; bindingSource="outputs/planar_gap_assembly_correction_06a/revalidation_authorization_and_finite_evidence.json"; inputs=@("benchmarks/contact_tolerance_pilot_05a/A01_delta_p0_5tauE/inputs.step","benchmarks/contact_tolerance_pilot_05a/A01_delta_p1_1tauE/inputs.step","benchmarks/contact_tolerance_pilot_05a/A01_delta_p0tauE/inputs.step","benchmarks/contact_tolerance_pilot_05a/A01_delta_m0_5tauE/inputs.step"); release="PUBLISHED"; url="https://github.com/Open-Engineering-Intelligence/dmslicer/releases/tag/goal-06a-evidence-aadf996"; reason="Published after the upload gate: local output explicitly records source_commit aadf996 and custody hashes verify."; pytest="195 passed, 0 failures, 0 errors, 0 skipped; software result only."; timestamp="2026-09-09T20:54:58.222441"; python="3.12.0"; pytestVersion="8.1.1"; exit=0; scientific="Accepted and rejected scenarios, including finite-evidence and authorization rejection behavior, are preserved separately from pytest."; provenance="PUBLISHED_GATE_READY: explicit source commit and verified custody copy." }
    "06B" = @{ branch="feat/planar-partial-overlap-correction"; tip="c23cc83a4c60620a8210e9aad01fb7adc1c72bde"; impl="c23cc83a4c60620a8210e9aad01fb7adc1c72bde"; parent="aadf996a05bf87efee862964141b6aeb7f872baf"; previous="aadf996a05bf87efee862964141b6aeb7f872baf"; binding="aadf996a05bf87efee862964141b6aeb7f872baf"; bindingConfidence="L"; bindingSource="outputs/planar_partial_overlap_correction_06b/*/operation.json"; inputs=@("benchmarks/planar_partial_overlap_correction_06b/*/inputs.step"); release="RELEASE_BLOCKED_PROVENANCE"; reason="Preserved operations record validator_source_commit aadf996 (06A), not 06B implementation commit c23cc83."; pytest="217 passed, 0 failures, 0 errors, 0 skipped; final software result only. Early JUnit has 6 tests and 2 failures."; timestamp="2026-09-09T21:33:54.406014"; scientific="Early P09 rejection and tampered-validator failures are retained; final scenario evidence is not promoted to scientific PASS by pytest."; provenance="GAP: operation validator binding points to 06A, not 06B implementation." }
    "06C" = @{ branch="feat/planar-multipatch-interface-correction"; tip="58ec93a67d8214c69bc92d5710c60d91aa1fe30c"; impl="58ec93a67d8214c69bc92d5710c60d91aa1fe30c"; parent="c23cc83a4c60620a8210e9aad01fb7adc1c72bde"; previous="c23cc83a4c60620a8210e9aad01fb7adc1c72bde"; binding="58ec93a67d8214c69bc92d5710c60d91aa1fe30c"; bindingConfidence="L"; bindingSource="outputs/planar_multipatch_interface_correction_06c/*/operation.json"; inputs=@("benchmarks/planar_multipatch_interface_correction_06c/*/inputs.step"); release="PUBLISHED"; url="https://github.com/Open-Engineering-Intelligence/dmslicer/releases/tag/goal-06c-evidence-58ec93a"; reason="Published after the upload gate: operation evidence explicitly records validator_source_commit 58ec93a and custody hashes verify."; pytest="260 passed, 0 failures, 0 errors, 0 skipped; software result only."; timestamp="2026-09-10T00:47:18.975733"; python="3.12.0"; pytestVersion="8.1.1"; scientific="Artifact-backed B-rep validation and unsupported ambiguous-interface result are retained; pytest is not used as scientific PASS."; provenance="PUBLISHED_GATE_READY: explicit validator commit and verified custody copy." }
    "06D" = @{ branch="feat/orientation-invariant-planar-correction"; tip="b42ba9e7b6efc6dd5a9dd9f7b1584b5a89066f8b"; impl="b7054f303896aa4a0762248a0b54686d8e733ead"; policy="b42ba9e7b6efc6dd5a9dd9f7b1584b5a89066f8b"; parent="58ec93a67d8214c69bc92d5710c60d91aa1fe30c"; previous="58ec93a67d8214c69bc92d5710c60d91aa1fe30c"; binding="b7054f303896aa4a0762248a0b54686d8e733ead"; bindingConfidence="CHAT"; bindingSource="P0 preservation authorization: bind 06D geometry evidence to b7054f3; b42ba9e is policy only"; inputs=@("benchmarks/orientation_invariant_planar_correction_06d/*/base_inputs.step","benchmarks/orientation_invariant_planar_correction_06d/*/inputs.step"); release="PUBLISHED"; url="https://github.com/Open-Engineering-Intelligence/dmslicer/releases/tag/goal-06d-evidence-b7054f3"; reason="Published after the upload gate: the authorized geometry implementation target is b7054f3; policy commit b42ba9e is excluded."; pytest="283 passed, 0 failures, 0 errors, 0 skipped; software result only."; timestamp="2026-09-10T07:39:53.922809+08:00"; scientific="Orientation-invariant scenario and controls are preserved; no scientific PASS is inferred from pytest."; human="Historical HUMAN_REVIEW package and VIEW_INDEX are preserved; manual inspection outcome remains separate."; provenance="PUBLISHED_GATE_READY after self-contained v2 package and sensitivity validation; policy commit excluded." }
}

$custody = (Get-Content -LiteralPath $CustodyInventory -Raw | ConvertFrom-Json).entries
$manifestDirectory = Join-Path $RepositoryRoot "docs\evidence_preservation\manifests"
New-Item -ItemType Directory -Path $manifestDirectory -Force | Out-Null

foreach ($goal in $configs.Keys) {
    $c = $configs[$goal]
    $inputs = InputFiles $goal $c.inputs
    $binding = if ($null -eq $c.binding) { UnknownFact } else { Fact $c.binding ($c.bindingConfidence ?? "U") $c.bindingSource }
    $tolerances = if ($goal -in @("03C","05B","05C","06A","06B","06C","06D")) {
        $items = @()
        if ($goal -in @("05B","05C","06A")) { $items += [ordered]@{ name="tau_E"; value=0.1; unit="mm"; role="experiment/correction distance threshold"; source="Goal benchmark or experiment evidence"; confidence="L" } }
        if ($goal -eq "03C") {
            $items += [ordered]@{ name="area_epsilon"; value=1e-8; unit="mm^2"; role="post-fix area validation"; source="outputs/contact_canonical_03c/a12_analytic_geometry_fix_20260909/FIX_REPORT.md"; confidence="L" }
            $items += [ordered]@{ name="coverage_epsilon"; value=1e-7; unit="dimensionless"; role="post-fix coverage validation"; source="outputs/contact_canonical_03c/a12_analytic_geometry_fix_20260909/FIX_REPORT.md"; confidence="L" }
        }
        if ($goal -in @("06A","06B","06C","06D")) {
            $source = "benchmarks/" + @{"06A"="planar_gap_assembly_correction_06a";"06B"="planar_partial_overlap_correction_06b";"06C"="planar_multipatch_interface_correction_06c";"06D"="orientation_invariant_planar_correction_06d"}[$goal] + "/manifest.json"
            $items += [ordered]@{ name="linear_epsilon"; value=1e-7; unit="mm"; role="geometry validation"; source=$source; confidence="L" }
            $items += [ordered]@{ name="area_epsilon"; value=1e-8; unit="mm^2"; role="geometry validation"; source=$source; confidence="L" }
            $items += [ordered]@{ name="volume_epsilon"; value=1e-6; unit="mm^3"; role="geometry validation"; source=$source; confidence="L" }
        }
        @($items)
    } else {
        @([ordered]@{ name="unrecovered"; value=$null; unit=$null; role=$null; source=$null; confidence="U" })
    }

    $failureCommits = @()
    $fixCommits = @()
    $known = @()
    $review = @()
    switch ($goal) {
        "03C" {
            $failureCommits += Fact "1c227cf75caadbb5508e261f3277b736dfc97cfd" "GH" "Git commit"
            $fixCommits += Fact "4a2aad8d926ea14d9526e2b7a1428a9d652b87f9" "GH" "Git commit"
            $known += Fact "Pre-fix A12 actual area 1803.7424900293827 mm^2 versus expected 1803.7852556496864 mm^2; error 0.042765620303711 mm^2. transformGeometry converted Plane/Circle geometry to BSpline before STEP export." "L" "outputs/contact_canonical_03c/a12_error_probe/probe_20260909_0001/diagnostic_summary.json"
        }
        "05B" {
            $fixCommits += Fact "1de21fd41aac05e437f6ebb839344af171b6e878" "GH" "Git commit"
            $known += Fact "Native mismatch 16/90; scale-normalized mismatch 1/90." "L" "outputs/contact_scale_covariance_05b/revalidation_v2/summary.json"
        }
        "05C" {
            foreach ($commit in @("5dd0359","52db2a8","0d681a9","fa4436a")) { $fixCommits += Fact $commit "GH" "Git commit" }
            $known += Fact "Retained A01_delta_p0tauE_s100 area-method exceedance: expected 33333333.333333332 mm^2, actual 33333333.333330356 mm^2, error -2.9765069484710693e-06 mm^2; failure type MEASURE_ONLY_OVER_LIMIT." "L" "artifacts/reference_results/05c_failure_breakdown.json"
        }
        "06B" {
            $known += Fact "Early JUnit: 6 tests, 2 failures, including P09 NO_POSITIVE_AREA_INTERFACE and tampered/NaN validator evidence." "L" "work/06b_initial.xml"
        }
        "06C" {
            foreach ($commit in @("121ad2e","6da8aec","25c9793","be96f46","58ec93a")) { $fixCommits += Fact $commit "GH" "Git commit" }
            $review += Fact "Initial critical finding: validator self-consistency did not bind validation to persisted geometry artifacts; corrupted supports, digests, or STEP reimport could still pass." "CHAT" "historical review thread 01a086a4-4e8c-78a0-ab7c-6a648d8a400c"
            $review += Fact "Initial important findings: incomplete STEP round-trip fields; incorrect boundary-topology heuristic; missing EMPTY member provenance; unsupported inputs collapsed; P11 FCStd naming/test gaps." "CHAT" "historical review thread 01a086a4-4e8c-78a0-ab7c-6a648d8a400c"
            $review += Fact "Intermediate finding: quantized digest was incorrectly used for deduplication, correspondence, and repeatability; final policy confines SHA-256 to byte integrity and uses B-rep checks for geometry equivalence." "CHAT" "historical review thread 01a086a4-4e8c-78a0-ab7c-6a648d8a400c"
            $review += Fact "Final review: Critical 0, Important 0." "CHAT" "historical review thread 01a086a4-4e8c-78a0-ab7c-6a648d8a400c"
        }
        "06D" {
            $fixCommits += Fact "b7054f303896aa4a0762248a0b54686d8e733ead" "GH" "Git commit"
            $review += Fact "Historical closeout records two important reviewer findings as fixed and zero unresolved findings; exact wording was not recoverable, so it is not reconstructed here." "CHAT" "historical task closeout"
        }
    }

    $criteria = @()
    if ($goal -in @("06C","06D")) {
        $criteria += Fact "B-rep validity/closure, surface and topology checks, minimum distance, common/area comparison, and bidirectional cut residual checks with explicit tolerances." "L" "Goal validator implementation and artifact evidence"
    } elseif ($goal -in @("04A","06A","06B")) {
        $criteria += Fact "Artifact-backed STEP/BREP validity, topology, area/volume, and scenario-specific acceptance or rejection criteria where present." "L" "Preserved validation and operation evidence"
    } else {
        $criteria += UnknownFact
    }

    $provenanceConfidence = if ($c.release -eq "PLANNED") {
        if ($goal -eq "06D") { "CHAT" } else { "L" }
    } else {
        "L"
    }

    $manifest = [ordered]@{
        schema_version = "1.0.0"
        goal_id = $goal
        identity = [ordered]@{
            branch = Fact $c.branch "GH" "local Git refs"
            branch_tip = Fact $c.tip "GH" "local Git refs"
            implementation_commit = Fact $c.impl "GH" "local Git object"
            policy_commit = if ($null -eq $c.policy) { UnknownFact } else { Fact $c.policy "GH" "local Git object; policy only" }
            parent_baseline = Fact $c.parent "GH" "Git ancestry"
            merge_base_main = Fact $main "GH" "git merge-base main <branch>"
            merge_base_previous_goal = Fact $c.previous "GH" "git merge-base <previous> <branch>"
            evidence_binding = $binding
        }
        inputs = @($inputs)
        environment = [ordered]@{
            freecad_version = if ($goal -in @("02C","03C")) { Fact "1.1.1" "L" "preserved environment/diagnostic evidence" } else { UnknownFact }
            occt_version = if ($goal -in @("02C","03C")) { Fact "7.8.1" "L" "preserved environment/diagnostic evidence" } else { UnknownFact }
            python_version = if ($null -eq $c.python) { UnknownFact } else { Fact $c.python "L" "preserved pytest log" }
            pytest_version = if ($null -eq $c.pytestVersion) { UnknownFact } else { Fact $c.pytestVersion "L" "preserved pytest log" }
        }
        execution = [ordered]@{
            command = $null
            exit_code = if ($null -eq $c.exit) { $null } else { [int]$c.exit }
            timestamp = if ($null -eq $c.timestamp) { $null } else { $c.timestamp }
            confidence = if ($null -eq $c.timestamp -and $null -eq $c.exit) { "U" } else { "L" }
        }
        tolerances = [object[]]$tolerances
        artifacts = @(ArtifactsForGoal $goal $custody)
        history = [ordered]@{
            failure_commits = @($failureCommits)
            fix_commits = @($fixCommits)
            known_failures_or_mismatches = @($known)
            reviewer_findings = @($review)
        }
        geometry_validation = [ordered]@{
            criteria = @($criteria)
            sha256_role = "file_and_download_integrity_only_not_geometry_equivalence"
        }
        results = [ordered]@{
            software_pytest = if ($null -eq $c.pytest) { UnknownFact } else { Fact $c.pytest "L" "preserved JUnit" }
            scientific_experiment = if ($null -eq $c.scientific) { UnknownFact } else { Fact $c.scientific "L" "preserved experiment evidence; independent of pytest"
            }
            human_inspection = if ($null -eq $c.human) { UnknownFact } else { Fact $c.human "L" "preserved review package/index; not inferred from pytest" }
            provenance = Fact $c.provenance $provenanceConfidence "P0 preservation audit"
        }
        release = [ordered]@{
            name = if ($c.release -eq "NOT_IN_P0_RELEASE_SCOPE") { $null } else { "goal-$($goal.ToLowerInvariant())-evidence-$($c.impl.Substring(0,7))" }
            target_commit = if ($c.release -eq "NOT_IN_P0_RELEASE_SCOPE") { $null } else { $c.impl }
            status = $c.release
            reason = $c.reason
            url = if ($null -eq $c.url) { $null } else { $c.url }
            supersedes = $null
            superseded_by = $null
        }
    }

    $destination = Join-Path $manifestDirectory ("goal-$($goal.ToLowerInvariant()).json")
    $manifest | ConvertTo-Json -Depth 12 | Set-Content -LiteralPath $destination -Encoding utf8NoBOM
}

Write-Output "Generated $($configs.Count) Goal manifests in $manifestDirectory"
