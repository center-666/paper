param([string]$RunId = ('validation_' + (Get-Date -Format 'yyyyMMdd_HHmmss')))
$ErrorActionPreference='Stop'
$project=Split-Path -Parent $PSScriptRoot
$python=Join-Path $project '.venv\Scripts\python.exe'
if(!(Test-Path -LiteralPath $python)){throw 'Project environment missing; see simulation/README.md'}
Push-Location $project
try {
    & $python simulation\validation_suite.py --plan simulation\validation_plan.json --out (Join-Path 'simulation\validation_runs' $RunId)
    if($LASTEXITCODE -ne 0){throw 'Validation failed; preserve directory for diagnosis'}
    $corrected=Join-Path 'simulation\validation_runs' ($RunId+'_shared_data')
    & $python simulation\corrected_tail_pair.py --source (Join-Path 'simulation\validation_runs' $RunId) --out $corrected
    if($LASTEXITCODE -ne 0){throw 'Corrected direct ablation failed'}
    & $python simulation\validation_output_audit.py $corrected
    if($LASTEXITCODE -ne 0){throw 'Output audit failed'}
} finally {Pop-Location}
