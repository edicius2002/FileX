#!/usr/bin/env bash
# G1 / cribado de candidatas d4 — una sola pasada (REPS=1) por los cuatro motores.
# Objetivo: elegir la candidata con mejor GRADIENTE, no medir tiempos.
# Por eso SIN_MUESTREO=1 y REPS=1: aqui solo interesa el CER.
set -u
export PATH="/usr/bin:/bin:/c/Windows/System32:$PATH"
R="/d/Work/research/FileX"
D="$R/bench/salidas-corpus-d4"
. "$R/bench/lib/harness.sh"

PYAI="$R/.venv-ai/Scripts/python.exe"
PYPD="$R/.venv-paddle/Scripts/python.exe"

gpu_acquire "G1-cribado-d4" || exit 1
echo "=== cribado d4: $(date) ==="

export REPS=1 SIN_MUESTREO=1

echo; echo "--- PaddleOCR (PP-OCRv6 medium, es) ---"
SUFIJO="_criba" timeout 1800 "$PYPD" "$D/ocr_lote_d4.py" paddleocr cuda "*.png" d4 \
  2>&1 | tee "$D/logs/criba_paddleocr.log"

echo; echo "--- RapidOCR (PP-OCRv5 mobile, ONNX) ---"
SUFIJO="_criba" timeout 1800 "$PYAI" "$D/ocr_lote_d4.py" rapidocr cuda "*.png" d4 \
  2>&1 | tee "$D/logs/criba_rapidocr.log"

echo; echo "--- EasyOCR (CRAFT + latin_g2) ---"
SUFIJO="_criba" timeout 1800 "$PYAI" "$D/ocr_lote_d4.py" easyocr cuda "*.png" d4 \
  2>&1 | tee "$D/logs/criba_easyocr.log"

echo; echo "--- Docling + RapidOCR backend=torch (PP-OCRv6 small) ---"
DOCS="d4_limpio,escaneado_d4a,escaneado_d4b,escaneado_d4c,escaneado_d4d,escaneado_d4e,escaneado_d4f,abl_d4d_blur12,abl_d4d_jq45,abl_d4d_niv20,abl_d4d_rui35,abl_d4d_ang0"
SUFIJO="_criba" timeout 2400 "$PYAI" "$D/docling_lote_d4.py" cuda torch nativo "$DOCS" \
  2>&1 | tee "$D/logs/criba_docling.log"

gpu_release
echo "=== fin cribado: $(date) ==="
