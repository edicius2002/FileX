#!/usr/bin/env bash
# Pasa la matriz ppp x deskew (img2) por los dos motores de la fase 3.
set -u
R="/d/Work/research/FileX"
. "$R/bench/lib/harness.sh"
gpu_acquire "ocrmypdf-fase4" || exit 1
export IMGDIR="D:\\Work\\research\\FileX\\bench\\salidas-ocrmypdf\\img2"

echo "===================== RapidOCR (GPU) / matriz ====================="
"$R/.venv-ai/Scripts/python.exe" "$R/bench/salidas-ocrmypdf/30_ocr_cadena.py" rapidocr cuda 2>&1 | grep -vE '^\x1b\[32m|Using engine_name|File exists'
echo
echo "===================== PaddleOCR (GPU) / matriz ====================="
"$R/.venv-paddle/Scripts/python.exe" "$R/bench/salidas-ocrmypdf/30_ocr_cadena.py" paddleocr cuda 2>&1 | grep -vE 'Creating model|Model files already exist'
gpu_release
echo "[lock] liberado"
