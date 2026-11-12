param([string]$RunId = ('five_node_' + (Get-Date -Format 'yyyyMMdd_HHmmss')))
$ErrorActionPreference='Stop'
$project=Split-Path -Parent $PSScriptRoot
$python=Join-Path $project '.venv\Scripts\python.exe'
if(!(Test-Path -LiteralPath $python)){throw 'Project virtual environment missing; see simulation/README.md'}
Push-Location $project
try {
    & $python simulation\run_study.py --config simulation\config.json --run-id $RunId
    if($LASTEXITCODE -ne 0){throw 'Study failed; inspect preserved run directory'}
    & $python simulation\analyze_increment.py (Join-Path 'simulation\runs' $RunId)
    if($LASTEXITCODE -ne 0){throw 'Output audit failed'}
} finally {Pop-Location}
