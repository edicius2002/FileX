#!/usr/bin/env bash
# FASE 3: cadena compuesta OCRmyPDF(preproceso) -> RapidOCR / PaddleOCR.
# Toma el lock de GPU, ejecuta ambos motores sobre las 65 imagenes y lo suelta.
set -u
R="/d/Work/research/FileX"
. "$R/bench/lib/harness.sh"
gpu_acquire "ocrmypdf-fase3" || exit 1

echo "===================== RapidOCR (GPU) ====================="
"$R/.venv-ai/Scripts/python.exe" "$R/bench/salidas-ocrmypdf/30_ocr_cadena.py" rapidocr cuda 2>&1

echo
echo "===================== PaddleOCR (GPU) ====================="
"$R/.venv-paddle/Scripts/python.exe" "$R/bench/salidas-ocrmypdf/30_ocr_cadena.py" paddleocr cuda 2>&1

gpu_release
echo "[lock] liberado"
