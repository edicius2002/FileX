$ErrorActionPreference = "Stop"
$D = "D:\Work\research\FileX\bench\salidas-mcp-cabos-2"
$neutral = $env:TEMP + "\c4_neutral"
New-Item -ItemType Directory -Force $neutral | Out-Null
# cwd neutro y SIN CLAUDE.md, para no cargar el del proyecto
Set-Location $neutral

$mcpPesado = "$D\c4_mcp_pesado.json"
$mcpLigero = "$D\c4_mcp_ligero.json"
$modelo = "haiku"

$PMIN = "Responde con una sola palabra en mayusculas: LISTO. No uses ninguna herramienta."
$PENUM = "Sin usar ninguna herramienta y sin buscar nada, responde tres puntos numerados: (1) cuantas herramientas cuyo nombre contenga la palabra probe tienes disponibles en este momento; (2) pega la descripcion COMPLETA y literal de la herramienta llamada probe_convert si puedes verla ahora mismo, o escribe exactamente NO_VEO_DESCRIPCION si solo ves su nombre sin descripcion; (3) enumera los recursos MCP (resources) y los prompts MCP que tengas disponibles, o escribe NINGUNO."

function Correr($etiqueta, $mcp, $prompt, $toolsVacio) {
    $log = "$D\c4_out_$etiqueta.json"
    $args = @("-p", $prompt, "--model", $modelo,
              "--strict-mcp-config", "--mcp-config", $mcp,
              "--setting-sources", "", "--disable-slash-commands",
              "--output-format", "json")
    if ($toolsVacio) { $args += @("--tools", "") }
    Write-Output ">>> $etiqueta"
    $t0 = Get-Date
    try {
        & claude @args > $log 2>"$D\c4_err_$etiqueta.txt"
    } catch {
        Write-Output "   ERROR: $_"
    }
    $ms = [math]::Round(((Get-Date) - $t0).TotalMilliseconds)
    Write-Output "   $ms ms -> $log"
}

# limpia logs de sonda previos
Remove-Item "$D\c4_log_pesado.jsonl","$D\c4_log_ligero.jsonl" -ErrorAction SilentlyContinue

# --- Medida de tokens: pesado vs ligero, con y sin herramientas internas ---
Correr "pmin_pesado_deftools" $mcpPesado $PMIN $false
Correr "pmin_ligero_deftools" $mcpLigero $PMIN $false
Correr "pmin_pesado_notools"  $mcpPesado $PMIN $true
Correr "pmin_ligero_notools"  $mcpLigero $PMIN $true

# --- Enumeracion: ve el modelo descripcion, recursos y prompts? ---
Correr "penum_pesado_deftools" $mcpPesado $PENUM $false
Correr "penum_pesado_notools"  $mcpPesado $PENUM $true

Write-Output "=== DONE ==="
