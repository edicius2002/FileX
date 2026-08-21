# FileX - arranca los tres conversores competidores (SOLO CPU).
# Uso:  powershell -File D:\Work\research\FileX\docker\up-all.ps1
#
# NO arranca snapotter-gpu-compose.yml. El carril GPU es exclusivo de otro
# agente y la RTX 3060 ya tiene ~3,3 GB de VRAM ocupados por el escritorio.

$ErrorActionPreference = "Stop"
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $here

docker compose -f snapotter-compose.yml -p filex-snapotter   up -d
docker compose -f convertx-compose.yml  -p filex-convertx    up -d
docker compose -f gotenberg-compose.yml -p filex-gotenberg8  up -d

docker ps --filter "name=filex-" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

Write-Output ""
Write-Output "SnapOtter : http://localhost:1349  (admin / admin)"
Write-Output "ConvertX  : http://localhost:3100  (sin login, ALLOW_UNAUTHENTICATED=true)"
Write-Output "Gotenberg : http://localhost:3200  (API, sin auth)"
