#!/usr/bin/env bash
# M1 / B13 — tanda H: las 23 celdas de EasyOCR que la guardia de VRAM omitio.
# Mismo fenomeno que en PaddleOCR: la VRAM que reserva torch dentro del proceso NO
# vuelve, asi que a partir de ~x1,0 la guardia omitio todo. UN PROCESO POR FACTOR.
set -u
export PATH="/c/Program Files/Git/usr/bin:/c/Windows/System32:$PATH"
R="/d/Work/research/FileX"
D="$R/bench/salidas-k-motor"
. "$R/bench/lib/harness.sh"
PYAI="$R/.venv-ai/Scripts/python.exe"
export REPS=9 SIN_MUESTREO=1 VRAM_TOPE=11900
gpu_acquire "M1-B13-tandaH-easy-resto" || exit 1
echo "=== tanda H: $(date) ==="
for K in 1000 1125 1250 1400 1600 1800; do
  echo "--- k$K ---"
  SUFIJO="_H_easy_$K" timeout 3600 "$PYAI" "$D/ocr_lote_km.py" easyocr cuda \
    "k${K}__*.png" 2>&1 | tee -a "$D/logs/H_easyocr_resto.log"
  nvidia-smi --query-gpu=memory.used --format=csv,noheader
done
gpu_release
echo "=== fin tanda H: $(date) ==="
