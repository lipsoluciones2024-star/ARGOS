# Instala ARGOS como Windows Service usando NSSM (sin requerir pywin32).
# Requiere nssm en PATH. Ejemplo:
#   .\deploy\windows\install-service.ps1 -Component server
#   .\deploy\windows\install-service.ps1 -Component agent
param(
    [ValidateSet("server", "agent")] [string] $Component = "server",
    [string] $Python = "python",
    [string] $Name = "ARGOS-$($Component)"
)

$ErrorActionPreference = "Stop"

if (-not (Get-Command nssm -ErrorAction SilentlyContinue)) {
    Write-Error "nssm no encontrado en PATH. Descarga desde https://nssm.cc"
    exit 1
}

$module = if ($Component -eq "agent") { "argos.agent" } else { "argos.server" }
$app = (Get-Command $Python).Source
$args = "-m", $module

Write-Host "Instalando servicio '$Name' -> $app -m $module"
nssm install $Name $app @args
nssm set $Name DisplayName "ARGOS $($Component.ToUpper())"
nssm set $Name AppDirectory (Get-Location)
nssm set $Name Start SERVICE_AUTO_START
nssm set $Name AppExit Default Restart
nssm start $Name
Write-Host "Servicio '$Name' instalado e iniciado."
