#!/usr/bin/env bash
# M1 / B13 — tanda C: las dos configuraciones de docling, que NO consumen PNG:
# rasterizan ellas mismas desde el PDF con `OcrOptions.scale`. Por eso el barrido se
# les pasa como lista de FACTORES (`f0.5,...`) y el arnes calcula scale = ppp/72.
set -u
export PATH="/c/Program Files/Git/usr/bin:/c/Windows/System32:$PATH"
R="/d/Work/research/FileX"
D="$R/bench/salidas-k-motor"
. "$R/bench/lib/harness.sh"
PYAI="$R/.venv-ai/Scripts/python.exe"
export REPS=9 SIN_MUESTREO=1 VRAM_TOPE=11300
F="f0.5,0.625,0.75,0.875,1.0,1.125,1.25,1.4,1.6,1.8"
DOCS="escaneado_d3,escaneado_d4c,patologico_escaneado,escaneado_d4"

gpu_acquire "M1-B13-tandaC-docling" || exit 1
echo "=== tanda C: $(date) ==="
nvidia-smi --query-gpu=memory.used,utilization.gpu --format=csv,noheader

echo "--- 1/2 docling + RapidOCR torch DEFECTO ---"
SUFIJO="_C_dl_def" DL_NORM=0 \
  timeout 5400 "$PYAI" "$D/docling_lote_km.py" cuda torch "$F" "$DOCS" \
  2>&1 | tee "$D/logs/C_docling_def.log"

echo "--- 2/2 docling + RapidOCR torch + R6 ---"
SUFIJO="_C_dl_R6" DL_NORM=1 \
  timeout 5400 "$PYAI" "$D/docling_lote_km.py" cuda torch "$F" "$DOCS" \
  2>&1 | tee "$D/logs/C_docling_R6.log"

gpu_release
echo "=== fin tanda C: $(date) ==="
