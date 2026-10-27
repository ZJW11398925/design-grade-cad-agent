$ErrorActionPreference = "Stop"
Set-Location (Join-Path $PSScriptRoot "..")
$env:PYTHONPATH = if ($env:PYTHONPATH) { "src;" + $env:PYTHONPATH } else { "src" }
python -m pytest -q @args
exit $LASTEXITCODE
