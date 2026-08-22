#!/usr/bin/env bash
# G1 / paso 4 — lo que falta despues de la matriz:
#   a) la celda "imagen extraida" de docling (entra por InputFormat.IMAGE, escala 1.0)
#   b) la rodilla de d3 con mas puntos de ppp (110/130/140/160), que es la pregunta
#      que decide la regla de FileX
#   c) una pasada de tiempos SIN el muestreador de VRAM (que los inflaba un 30-60 %)
set -u
R="/d/Work/research/FileX"
L="$R/bench/salidas-ocr-ppp/logs"
M="/c/Program Files/ImageMagick-7.1.2-Q16-HDRI/magick"
mkdir -p "$L"
. "$R/bench/lib/harness.sh"
gpu_acquire "g1-ocr-ppp-cierre" || exit 1
FILTRO='^\x1b|Using engine_name|File exists|Downloading|Creating model|already exist|it/s\]|%\|'

# --- b) puntos extra alrededor de la rodilla, solo d3 ---
mkdir -p "$R/bench/salidas-ocr-ppp/img2"
for ppp in 110 130 140 160; do
  "$M" -density "$ppp" "D:/Work/research/FileX/corpus/pdf/escaneado_d3.pdf[0]" \
       -colorspace Gray -alpha remove -background white -flatten \
       "D:/Work/research/FileX/bench/salidas-ocr-ppp/img2/ppp${ppp}__escaneado_d3.png" 2>/dev/null
done
ls -1 "$R/bench/salidas-ocr-ppp/img2/" | tr '\n' ' '; echo

echo "########## $(date +%H:%M:%S)  rodilla d3 — PaddleOCR ##########"
IMGDIR="D:\\Work\\research\\FileX\\bench\\salidas-ocr-ppp\\img2" SUFIJO=_rodilla \
  timeout 900 "$R/.venv-paddle/Scripts/python.exe" \
  "$R/bench/salidas-ocr-ppp/20_ocr_lote.py" paddleocr cuda 2>&1 \
  | grep -avE "$FILTRO" | tee "$L/rodilla_paddleocr.log"

echo "########## $(date +%H:%M:%S)  rodilla d3 — RapidOCR ##########"
IMGDIR="D:\\Work\\research\\FileX\\bench\\salidas-ocr-ppp\\img2" SUFIJO=_rodilla \
  timeout 900 "$R/.venv-ai/Scripts/python.exe" \
  "$R/bench/salidas-ocr-ppp/20_ocr_lote.py" rapidocr cuda 2>&1 \
  | grep -avE "$FILTRO" | tee "$L/rodilla_rapidocr.log"

# --- a) docling por la via de la imagen extraida ---
echo "########## $(date +%H:%M:%S)  docling / imagen extraida (escala 1.0) ##########"
timeout 1800 "$R/.venv-ai/Scripts/python.exe" \
  "$R/bench/salidas-ocr-ppp/22_docling_img.py" cuda torch 2>&1 \
  | grep -avE "$FILTRO" | tee "$L/docling_img.log"

# --- c) tiempos limpios: mismas 40 imagenes, sin el hilo que muestrea nvidia-smi ---
for m in rapidocr paddleocr easyocr; do
  venv=".venv-ai"; [ "$m" = paddleocr ] && venv=".venv-paddle"
  echo "########## $(date +%H:%M:%S)  tiempos limpios — $m ##########"
  SIN_MUESTREO=1 SUFIJO=_t timeout 1800 "$R/$venv/Scripts/python.exe" \
    "$R/bench/salidas-ocr-ppp/20_ocr_lote.py" "$m" cuda 2>&1 \
    | grep -avE "$FILTRO" | tee "$L/tiempos_$m.log"
done

gpu_release
echo "[lock] liberado  $(date +%H:%M:%S)"
