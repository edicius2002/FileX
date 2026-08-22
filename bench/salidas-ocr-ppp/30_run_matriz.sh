#!/usr/bin/env bash
# G1 / paso 3 — la matriz completa: 4 documentos x 4 motores x (barrido de ppp + via extraida).
#
# Un proceso por motor, secuencial y bajo el lock de GPU: los motores no se comparten
# la tarjeta bien y ademas se quiere el pico de VRAM de cada uno por separado.
set -u
R="/d/Work/research/FileX"
L="$R/bench/salidas-ocr-ppp/logs"
mkdir -p "$L"
. "$R/bench/lib/harness.sh"
gpu_acquire "g1-ocr-ppp" || exit 1

export REPS="${REPS:-9}"
FILTRO='^\x1b|Using engine_name|File exists|Downloading|Creating model|already exist|it/s\]|%\|'

echo "########## $(date +%H:%M:%S)  RapidOCR (PP-OCRv5 mobile, ONNX) / CUDA ##########"
timeout 3600 "$R/.venv-ai/Scripts/python.exe" \
  "$R/bench/salidas-ocr-ppp/20_ocr_lote.py" rapidocr cuda 2>&1 \
  | grep -avE "$FILTRO" | tee "$L/rapidocr_cuda.log"

echo "########## $(date +%H:%M:%S)  PaddleOCR (PP-OCRv6 medium, es) / CUDA ##########"
timeout 3600 "$R/.venv-paddle/Scripts/python.exe" \
  "$R/bench/salidas-ocr-ppp/20_ocr_lote.py" paddleocr cuda 2>&1 \
  | grep -avE "$FILTRO" | tee "$L/paddleocr_cuda.log"

echo "########## $(date +%H:%M:%S)  EasyOCR (CRAFT + latin_g2) / CUDA ##########"
timeout 3600 "$R/.venv-ai/Scripts/python.exe" \
  "$R/bench/salidas-ocr-ppp/20_ocr_lote.py" easyocr cuda 2>&1 \
  | grep -avE "$FILTRO" | tee "$L/easyocr_cuda.log"

echo "########## $(date +%H:%M:%S)  docling + RapidOCR backend=torch / CUDA ##########"
timeout 5400 "$R/.venv-ai/Scripts/python.exe" \
  "$R/bench/salidas-ocr-ppp/21_docling_lote.py" cuda torch \
  75,100,125,150,175,200,250,300 2>&1 \
  | grep -avE "$FILTRO" | tee "$L/docling_torch_cuda.log"

echo "########## $(date +%H:%M:%S)  docling backend=torch / escala POR DEFECTO (216 ppp) ##########"
SUFIJO=_defecto timeout 1800 "$R/.venv-ai/Scripts/python.exe" \
  "$R/bench/salidas-ocr-ppp/21_docling_lote.py" cuda torch defecto 2>&1 \
  | grep -avE "$FILTRO" | tee "$L/docling_torch_defecto.log"

gpu_release
echo "[lock] liberado  $(date +%H:%M:%S)"
