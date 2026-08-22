#!/usr/bin/env bash
# G1 — control de fidelidad definitivo: pasar el motor por las MISMAS imagenes que
# uso la fase 2 (`bench/salidas-fase2/img/`, solo lectura). De las 12 marcas, 11 se
# reprodujeron con las imagenes regeneradas aqui; la que no (RapidOCR sobre el
# patologico, 0,0 % publicado frente a 1,3 % aqui) se explica porque la fase 2
# rasterizo ese documento en sRGB y este barrido lo hace en escala de grises.
# Esto lo comprueba en vez de suponerlo.
set -u
R="/d/Work/research/FileX"
. "$R/bench/lib/harness.sh"
gpu_acquire "g1-ocr-ppp-ctrl" || exit 1
FILTRO='^\x1b|Using engine_name|File exists|Downloading|Creating model|already exist'
IMGDIR="D:\Work\research\FileX\bench\salidas-fase2\img" SUFIJO=_ctrlfase2 REPS=9 \
  timeout 900 "$R/.venv-ai/Scripts/python.exe" \
  "$R/bench/salidas-ocr-ppp/20_ocr_lote.py" rapidocr cuda 2>&1 \
  | grep -avE "$FILTRO" | tee "$R/bench/salidas-ocr-ppp/logs/ctrl_fase2_rapidocr.log"
gpu_release
