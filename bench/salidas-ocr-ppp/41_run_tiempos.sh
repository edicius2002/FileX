#!/usr/bin/env bash
# G1 / paso 4c (repeticion) — tiempos sin el muestreador de VRAM.
# La primera pasada murio al serializar (mu.join sobre un hilo no arrancado); las
# medidas se habian tomado bien pero no llegaron al JSON. Corregido y repetido.
set -u
R="/d/Work/research/FileX"
L="$R/bench/salidas-ocr-ppp/logs"
. "$R/bench/lib/harness.sh"
gpu_acquire "g1-ocr-ppp-tiempos" || exit 1
FILTRO='^\x1b|Using engine_name|File exists|Downloading|Creating model|already exist|it/s\]|%\|'
for m in rapidocr paddleocr easyocr; do
  venv=".venv-ai"; [ "$m" = paddleocr ] && venv=".venv-paddle"
  echo "########## $(date +%H:%M:%S)  tiempos limpios — $m ##########"
  SIN_MUESTREO=1 SUFIJO=_t timeout 1800 "$R/$venv/Scripts/python.exe" \
    "$R/bench/salidas-ocr-ppp/20_ocr_lote.py" "$m" cuda 2>&1 \
    | grep -avE "$FILTRO" | tee "$L/tiempos_$m.log"
done
gpu_release
echo "[lock] liberado  $(date +%H:%M:%S)"
