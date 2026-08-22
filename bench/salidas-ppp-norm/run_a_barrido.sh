#!/usr/bin/env bash
# P1 / tanda A — barrido de ppp sobre escaneado_d4 (200 ppp nativos), 11 puntos
# entre 100 y 400. Medianas de n=9, SIN muestreador de VRAM (los tiempos buenos);
# la VRAM va en su propia tanda.
set -u
export PATH="/c/Program Files/Git/usr/bin:/c/Windows/System32:$PATH"
R="/d/Work/research/FileX"
D="$R/bench/salidas-ppp-norm"
. "$R/bench/lib/harness.sh"
PYAI="$R/.venv-ai/Scripts/python.exe"
PYPD="$R/.venv-paddle/Scripts/python.exe"
export RO_ROOT="D:/Work/research/FileX/bench/salidas-ppp-norm/modelos"
export REPS=9 SIN_MUESTREO=1
G="ppp*__escaneado_d4.png"

gpu_acquire "P1-tandaA-barrido-ppp" || exit 1
echo "=== tanda A: $(date) ==="

echo "--- paddleocr v6 medium (cuda) ---"
SUFIJO="_A_pd6med" timeout 3600 "$PYPD" "$D/ocr_lote_pn.py" paddleocr cuda "$G" \
  2>&1 | tee "$D/logs/A_paddleocr.log"

echo "--- rapidocr v5 mobile DEFECTO (cuda) ---"
SUFIJO="_A_ro5mob_def" RO_VER="PP-OCRv5" RO_TIPO="mobile" RO_NORM=0 \
  timeout 3600 "$PYAI" "$D/ocr_lote_pn.py" rapidocr cuda "$G" \
  2>&1 | tee "$D/logs/A_rapidocr_v5mob_def.log"

echo "--- rapidocr v6 small DEFECTO (cuda) ---"
SUFIJO="_A_ro6sm_def" RO_VER="PP-OCRv6" RO_TIPO="small" RO_NORM=0 \
  timeout 3600 "$PYAI" "$D/ocr_lote_pn.py" rapidocr cuda "$G" \
  2>&1 | tee "$D/logs/A_rapidocr_v6sm_def.log"

echo "--- rapidocr v6 small + R6 CORREGIDO (cuda) ---"
SUFIJO="_A_ro6sm_R6" RO_VER="PP-OCRv6" RO_TIPO="small" RO_NORM=1 \
  timeout 3600 "$PYAI" "$D/ocr_lote_pn.py" rapidocr cuda "$G" \
  2>&1 | tee "$D/logs/A_rapidocr_v6sm_R6.log"

gpu_release
echo "=== fin tanda A: $(date) ==="
