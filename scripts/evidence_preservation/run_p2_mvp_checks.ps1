$ErrorActionPreference = "Stop"

$repositoryRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..\..")).Path
Push-Location $repositoryRoot
try {
    py -3.12 -m pytest -q
    if ($LASTEXITCODE -ne 0) { throw "P2 MVP pytest gate failed with exit code $LASTEXITCODE" }

    $previousPythonPath = $env:PYTHONPATH
    $env:PYTHONPATH = Join-Path $repositoryRoot "src"
    try {
        py -3.12 -m dmslicer.evidence_promotion --help | Out-Null
        if ($LASTEXITCODE -ne 0) { throw "P2 MVP CLI help gate failed with exit code $LASTEXITCODE" }
    } finally {
        $env:PYTHONPATH = $previousPythonPath
    }

    git diff --quiet origin/main -- docs/research_v2
    if ($LASTEXITCODE -ne 0) { throw "Frozen docs/research_v2 differs from origin/main" }

    Write-Output "P2 MVP local checks: PASS"
} finally {
    Pop-Location
}
