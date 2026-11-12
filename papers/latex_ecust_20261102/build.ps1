$ErrorActionPreference = 'Stop'
$paperPython = if ($env:PAPER_PYTHON) { $env:PAPER_PYTHON } else { 'python' }
& $paperPython (Join-Path $PSScriptRoot 'build.py')
exit $LASTEXITCODE
