# FileX - para y (opcionalmente) borra todo lo levantado por up-all.ps1.
#
#   .\down-all.ps1            -> para y elimina contenedores y redes (conserva volúmenes/datos)
#   .\down-all.ps1 -Purge     -> además borra los volúmenes de datos
#   .\down-all.ps1 -Purge -Images  -> además borra las imágenes descargadas (~13 GB)

param(
    [switch]$Purge,
    [switch]$Images
)

$ErrorActionPreference = "Continue"
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $here

$volFlag = if ($Purge) { "-v" } else { "" }

foreach ($p in @(
    @{ f = "snapotter-compose.yml";  n = "filex-snapotter"  },
    @{ f = "convertx-compose.yml";   n = "filex-convertx"   },
    @{ f = "gotenberg-compose.yml";  n = "filex-gotenberg8" }
)) {
    if ($volFlag) {
        docker compose -f $p.f -p $p.n down -v --remove-orphans
    } else {
        docker compose -f $p.f -p $p.n down --remove-orphans
    }
}

# El proyecto GPU no se arranca en este carril, pero si alguien lo hubiera
# levantado, esto también lo recoge.
docker compose -f snapotter-gpu-compose.yml -p filex-snapotter-gpu down --remove-orphans 2>$null

# Volumen suelto del quick-start `docker run` (si se usó la variante one-liner).
if ($Purge) {
    docker volume rm SnapOtter-data 2>$null
}

if ($Images) {
    docker rmi snapotter/snapotter:latest ghcr.io/c4illin/convertx:latest gotenberg/gotenberg:8 postgres:17-alpine redis:8-alpine 2>$null
}

docker ps -a --filter "name=filex-" --format "table {{.Names}}\t{{.Status}}"
Write-Output "Listo."
