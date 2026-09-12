# One reusable local workbench; never start CAD or an additional viewer per case.
param([int]$Port = 56810, [switch]$NoBrowser)
$ErrorActionPreference = 'Stop'
$env:PYTHONPATH = Join-Path $PSScriptRoot 'src'
$viewerUrl = "http://127.0.0.1:$Port/"
$existingWorkbench = $false
try {
    $health = Invoke-RestMethod ($viewerUrl + 'health') -TimeoutSec 2
    $existingWorkbench = $health.app -eq 'dmslicer-geometry-workbench'
} catch { }
if (-not $existingWorkbench) {
    $occupied = Get-NetTCPConnection -State Listen -LocalPort $Port -ErrorAction SilentlyContinue
    if ($occupied) { throw "Port $Port belongs to another or older service. Nothing was stopped." }
    $logDirectory = Join-Path $PSScriptRoot 'work/viewer-service'
    New-Item -ItemType Directory -Force -Path $logDirectory | Out-Null
    $logName = Get-Date -Format 'yyyyMMdd-HHmmss-fffffff'
    Start-Process -FilePath (Get-Command py.exe).Source -ArgumentList @('-3.12', '-u', '-m', 'dmslicer.geometry_import', '--serve', '--port', $Port) -WorkingDirectory $PSScriptRoot -WindowStyle Hidden -RedirectStandardOutput (Join-Path $logDirectory "$logName.stdout.log") -RedirectStandardError (Join-Path $logDirectory "$logName.stderr.log") | Out-Null
    for ($attempt = 0; $attempt -lt 20; $attempt++) {
        try {
            $health = Invoke-RestMethod ($viewerUrl + 'health') -TimeoutSec 1
            if ($health.app -eq 'dmslicer-geometry-workbench') { $existingWorkbench = $true; break }
        } catch { }
        Start-Sleep -Milliseconds 200
    }
    if (-not $existingWorkbench) { throw "Workbench did not become ready. See $logDirectory" }
}
Write-Host "DM-Slicer workbench: $viewerUrl"
if (-not $NoBrowser) { Start-Process $viewerUrl }
