# Local package viewing only; no FreeCAD process is started by this launcher.
$ErrorActionPreference = 'Stop'
$env:PYTHONPATH = Join-Path $PSScriptRoot 'src'
Push-Location $PSScriptRoot
try {
    py -3.12 -m dmslicer.geometry_import --serve
} finally {
    Pop-Location
}
