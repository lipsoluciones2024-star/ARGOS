$ErrorActionPreference = "Stop"
$venv = Join-Path $PSScriptRoot ".venv"
$python = Join-Path $venv "Scripts/python.exe"
if (-not (Test-Path $python)) {
    Write-Host "Creando entorno virtual .venv ..."
    python -m venv $venv
    & $python -m pip install -e "$PSScriptRoot[dev]"
}
Write-Host "Iniciando ARGOS agent (recoleccion) ..."
& $python -m argos.agent
