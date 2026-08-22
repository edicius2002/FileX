#!/usr/bin/env bash
# M1 / B13 — tanda D: recuperar las NUEVE celdas de PaddleOCR que la guardia de VRAM
# omitio en la tanda A.
#
# QUE PASO, y es un resultado en si mismo: el asignador de memoria de Paddle NO
# DEVUELVE la VRAM. En cuanto la tanda A llego a ×1,4 sobre un documento de 1 294 px
# nativos (1 812×2 402 = 4,35 Mpx) la VRAM se planto en 11 498 MiB y NO bajo: a partir
# de ahi la guardia omitio TODO, incluidas imagenes de 1,4 Mpx que caben de sobra.
# Un solo folio grande envenena el resto del lote.
#
# Solucion: un PROCESO POR FACTOR, para que el asignador arranque limpio, y tope
# subido a 11 900 (P1 midio 11 942 sin error, ppp-y-normalizacion.md §7). Dentro de
# cada proceso el glob va de menor a mayor, y si aun asi revienta el arnes registra el
# error por imagen y sigue.
set -u
export PATH="/c/Program Files/Git/usr/bin:/c/Windows/System32:$PATH"
R="/d/Work/research/FileX"
D="$R/bench/salidas-k-motor"
. "$R/bench/lib/harness.sh"
PYPD="$R/.venv-paddle/Scripts/python.exe"
export REPS=9 SIN_MUESTREO=1 VRAM_TOPE=11900

gpu_acquire "M1-B13-tandaD-paddle-resto" || exit 1
echo "=== tanda D: $(date) ==="

for G in "k1400__patologico_escaneado.png" "k1600__*.png" "k1800__*.png"; do
  echo "--- $G ---"
  SUFIJO="_D_pd6med_$(echo "$G" | tr -cd '0-9')" \
    timeout 3600 "$PYPD" "$D/ocr_lote_km.py" paddleocr cuda "$G" \
    2>&1 | tee -a "$D/logs/D_paddleocr_resto.log"
  nvidia-smi --query-gpu=memory.used --format=csv,noheader
done

gpu_release
echo "=== fin tanda D: $(date) ==="
