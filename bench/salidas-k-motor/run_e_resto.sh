#!/usr/bin/env bash
# M1 / B13 — tanda E: la celda de EasyOCR que la guardia omitio, en proceso limpio.
# Mismo fenomeno que en PaddleOCR: la VRAM no baja dentro del proceso, asi que basta
# arrancar de nuevo. Tope subido a 11 900 (P1 midio 12 037 sin error en EasyOCR).
set -u
export PATH="/c/Program Files/Git/usr/bin:/c/Windows/System32:$PATH"
R="/d/Work/research/FileX"
D="$R/bench/salidas-k-motor"
. "$R/bench/lib/harness.sh"
PYAI="$R/.venv-ai/Scripts/python.exe"
export REPS=9 SIN_MUESTREO=1 VRAM_TOPE=11900

gpu_acquire "M1-B13-tandaE-easy-resto" || exit 1
echo "=== tanda E: $(date) ==="
SUFIJO="_E_easy_1800" timeout 3600 "$PYAI" "$D/ocr_lote_km.py" easyocr cuda \
  "k1800__patologico_escaneado.png" 2>&1 | tee "$D/logs/E_easyocr_resto.log"
gpu_release
echo "=== fin tanda E: $(date) ==="
