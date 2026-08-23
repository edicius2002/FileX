# censo_gpu.ps1 — censo de procesos AJENOS al proyecto que pueden estar ocupando la GPU.
#
# POR QUE EXISTE (MEDIDO el 23/08, bench/lock-de-maquina.md §2):
# en esta maquina (Windows 10 + WDDM) `nvidia-smi --query-compute-apps=used_memory`
# devuelve [N/A] para TODOS los procesos y `nvidia-smi pmon` responde
# "The feature is not supported in this configuration". Es decir: NO se puede
# atribuir VRAM a un PID. Lo unico atribuible es la LINEA DE ORDENES, que si dice
# de que repositorio viene el proceso. Este censo no mide memoria: nombra sospechosos.
#
# Uso:  powershell -NoProfile -ExecutionPolicy Bypass -File censo_gpu.ps1 [marca]
#   marca = cadena que identifica a los procesos PROPIOS (por defecto "FileX").
#           Todo proceso candidato cuya linea de ordenes NO la contenga se declara ajeno.
param([string]$Marca = "FileX")

# Candidatos: lo que en esta maquina puede reservar VRAM de computo.
# No se incluyen navegadores ni el escritorio: esos son la LINEA BASE, no un intruso.
$nombres = @("python.exe","pythonw.exe","ffmpeg.exe","magick.exe","gswin64c.exe","node.exe","paddle.exe")
$filtro  = ($nombres | ForEach-Object { "Name='$_'" }) -join " or "

try {
    $procs = Get-CimInstance Win32_Process -Filter $filtro -ErrorAction Stop
} catch {
    Write-Output "CENSO_ERROR $($_.Exception.Message)"
    exit 3
}

$ajenos = @()
foreach ($p in $procs) {
    $cl = $p.CommandLine
    if (-not $cl) { continue }
    if ($cl -like "*$Marca*") { continue }   # es nuestro: no cuenta
    $ajenos += $p
}

# Se ordena por memoria RESIDENTE descendente. No es VRAM —eso no se puede saber
# aqui— pero un proceso que ha cargado CUDA y unos pesos tiene cientos de MB o
# GB de RAM, y los uvicorn, npm y scripts sueltos de la maquina tienen decenas.
# Es una heuristica para poner al sospechoso arriba, NO una atribucion.
$ajenos = $ajenos | Sort-Object -Property WorkingSetSize -Descending

Write-Output ("CENSO_AJENOS " + $ajenos.Count + " (ordenados por RAM residente; la VRAM por PID NO es observable en WDDM)")
$n = 0
foreach ($p in $ajenos) {
    $n++
    if ($n -gt 10) { break }
    $mb    = [int]($p.WorkingSetSize / 1MB)
    $corta = $p.CommandLine.Substring(0, [Math]::Min(120, $p.CommandLine.Length))
    Write-Output ("{0}`t{1}`t{2} MB RAM`t{3}" -f $p.ProcessId, $p.Name, $mb, $corta)
}
if ($ajenos.Count -gt 10) { Write-Output ("... y {0} mas" -f ($ajenos.Count - 10)) }
