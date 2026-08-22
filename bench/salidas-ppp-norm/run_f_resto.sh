#!/usr/bin/env bash
# P1 / tanda F — lo que faltaba: el barrido sobre `patologico_escaneado` (el unico
# escaneado del corpus que NO sale del generador sintetico) y el refinamiento de
# PaddleOCR entre 250 y 300 ppp sobre d4, que es donde la tanda A localizo el
# acantilado y donde solo habia dos puntos.
set -u
export PATH="/c/Program Files/Git/usr/bin:/c/Windows/System32:$PATH"
R="/d/Work/research/FileX"
D="$R/bench/salidas-ppp-norm"
. "$R/bench/lib/harness.sh"
PYAI="$R/.venv-ai/Scripts/python.exe"
PYPD="$R/.venv-paddle/Scripts/python.exe"
export RO_ROOT="D:/Work/research/FileX/bench/salidas-ppp-norm/modelos"
export REPS=9 SIN_MUESTREO=1
export IMGDIR="D:/Work/research/FileX/bench/salidas-ppp-norm/img_docs2"

gpu_acquire "P1-tandaF-patologico-refinamiento" || exit 1
echo "=== tanda F: $(date) ==="
SUFIJO="_F_pd6med" timeout 3600 "$PYPD" "$D/ocr_lote_pn.py" paddleocr cuda "*.png" \
  2>&1 | tee "$D/logs/F_paddleocr.log"
SUFIJO="_F_ro6sm_R6" RO_VER="PP-OCRv6" RO_TIPO="small" RO_NORM=1 \
  timeout 3600 "$PYAI" "$D/ocr_lote_pn.py" rapidocr cuda "*.png" \
  2>&1 | tee "$D/logs/F_rapidocr_v6sm_R6.log"
gpu_release
echo "=== fin tanda F: $(date) ==="
