#!/usr/bin/env bash
# M1 / B13 — tanda A: las CINCO configuraciones que consumen PNG, sobre las 40
# rasterizaciones (4 documentos x 10 factores). Medianas de n=9, GPU fijada.
#
# Las cuatro primeras son las de bench/ppp-y-normalizacion.md §2.7 que consumen PNG;
# EasyOCR va en su propio proceso al final porque es el que mas VRAM pide (+10 030 MiB
# medidos en §7) y conviene que un OOM suyo no se lleve por delante a los otros.
#
# NO se fija RO_ROOT: los pesos que se usan son los que ya estan en
# .venv-ai/Lib/site-packages/rapidocr/models/ (fecha 19 ago), que es de donde salieron
# las cifras de bench/salidas-corpus-d4/. NO se instala nada: solo se leen.
set -u
export PATH="/c/Program Files/Git/usr/bin:/c/Windows/System32:$PATH"
R="/d/Work/research/FileX"
D="$R/bench/salidas-k-motor"
. "$R/bench/lib/harness.sh"
PYAI="$R/.venv-ai/Scripts/python.exe"
PYPD="$R/.venv-paddle/Scripts/python.exe"
export REPS=9 SIN_MUESTREO=1 VRAM_TOPE=11300
G="k*__*.png"

gpu_acquire "M1-B13-tandaA-k-por-motor" || exit 1
echo "=== tanda A: $(date) ==="
nvidia-smi --query-gpu=memory.used,utilization.gpu --format=csv,noheader

echo "--- 1/4 paddleocr v6 medium (cuda) ---"
SUFIJO="_A_pd6med" timeout 5400 "$PYPD" "$D/ocr_lote_km.py" paddleocr cuda "$G" \
  2>&1 | tee "$D/logs/A_paddleocr.log"

echo "--- 2/4 rapidocr v6 small + R6 (cuda) ---"
SUFIJO="_A_ro6sm_R6" RO_VER="PP-OCRv6" RO_TIPO="small" RO_NORM=1 \
  timeout 5400 "$PYAI" "$D/ocr_lote_km.py" rapidocr cuda "$G" \
  2>&1 | tee "$D/logs/A_rapidocr_v6sm_R6.log"

echo "--- 3/4 rapidocr v6 small DEFECTO (cuda) ---"
SUFIJO="_A_ro6sm_def" RO_VER="PP-OCRv6" RO_TIPO="small" RO_NORM=0 \
  timeout 5400 "$PYAI" "$D/ocr_lote_km.py" rapidocr cuda "$G" \
  2>&1 | tee "$D/logs/A_rapidocr_v6sm_def.log"

echo "--- 4/4 rapidocr v5 mobile DEFECTO (cuda) ---"
SUFIJO="_A_ro5mob_def" RO_VER="PP-OCRv5" RO_TIPO="mobile" RO_NORM=0 \
  timeout 5400 "$PYAI" "$D/ocr_lote_km.py" rapidocr cuda "$G" \
  2>&1 | tee "$D/logs/A_rapidocr_v5mob_def.log"

gpu_release
echo "=== fin tanda A: $(date) ==="
