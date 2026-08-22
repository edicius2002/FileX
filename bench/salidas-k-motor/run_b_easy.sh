#!/usr/bin/env bash
# M1 / B13 — tanda B: EasyOCR, en su propio proceso.
# Va aparte porque es el que mas VRAM pide: +10 030 MiB medidos en
# bench/ppp-y-normalizacion.md §7, con pico de 12 037 de 12 288 SIN dar error.
# Con la base actual (~2 750 MiB de escritorio) el punto de x1,8 puede no caber:
# la guardia de VRAM omite la celda y, si aun asi revienta, el arnes registra el
# error por imagen y sigue. Un "no cabe en la tarjeta" es un resultado, no un fallo.
set -u
export PATH="/c/Program Files/Git/usr/bin:/c/Windows/System32:$PATH"
R="/d/Work/research/FileX"
D="$R/bench/salidas-k-motor"
. "$R/bench/lib/harness.sh"
PYAI="$R/.venv-ai/Scripts/python.exe"
export REPS=9 SIN_MUESTREO=1 VRAM_TOPE=11300
G="k*__*.png"

gpu_acquire "M1-B13-tandaB-easyocr" || exit 1
echo "=== tanda B: $(date) ==="
nvidia-smi --query-gpu=memory.used,utilization.gpu --format=csv,noheader

SUFIJO="_B_easy" timeout 5400 "$PYAI" "$D/ocr_lote_km.py" easyocr cuda "$G" \
  2>&1 | tee "$D/logs/B_easyocr.log"

gpu_release
echo "=== fin tanda B: $(date) ==="
