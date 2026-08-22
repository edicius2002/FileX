#!/usr/bin/env bash
# P1 / tanda B — el barrido sobre los OTROS documentos (d4f 240 ppp nativos, d4c,
# d3 100 ppp nativos, patologico 200 ppp nativos). Es lo que separa "techo absoluto
# en ppp" de "techo relativo sobre el nativo".
set -u
export PATH="/c/Program Files/Git/usr/bin:/c/Windows/System32:$PATH"
R="/d/Work/research/FileX"
D="$R/bench/salidas-ppp-norm"
. "$R/bench/lib/harness.sh"
PYAI="$R/.venv-ai/Scripts/python.exe"
PYPD="$R/.venv-paddle/Scripts/python.exe"
export RO_ROOT="D:/Work/research/FileX/bench/salidas-ppp-norm/modelos"
export REPS=9 SIN_MUESTREO=1
export IMGDIR="D:/Work/research/FileX/bench/salidas-ppp-norm/img_docs"

gpu_acquire "P1-tandaB-otros-docs" || exit 1
echo "=== tanda B: $(date) ==="

echo "--- paddleocr v6 medium ---"
SUFIJO="_B_pd6med" timeout 3600 "$PYPD" "$D/ocr_lote_pn.py" paddleocr cuda "*.png" \
  2>&1 | tee "$D/logs/B_paddleocr.log"

echo "--- rapidocr v6 small + R6 ---"
SUFIJO="_B_ro6sm_R6" RO_VER="PP-OCRv6" RO_TIPO="small" RO_NORM=1 \
  timeout 3600 "$PYAI" "$D/ocr_lote_pn.py" rapidocr cuda "*.png" \
  2>&1 | tee "$D/logs/B_rapidocr_v6sm_R6.log"

echo "--- rapidocr v5 mobile defecto ---"
SUFIJO="_B_ro5mob_def" RO_VER="PP-OCRv5" RO_TIPO="mobile" RO_NORM=0 \
  timeout 3600 "$PYAI" "$D/ocr_lote_pn.py" rapidocr cuda "*.png" \
  2>&1 | tee "$D/logs/B_rapidocr_v5mob_def.log"

echo
echo "=== tanda C — mismos pixeles, distinto tamaño de pagina ==="
export IMGDIR="D:/Work/research/FileX/bench/salidas-ppp-norm/img_pg"
echo "--- paddleocr v6 medium ---"
SUFIJO="_C_pd6med" timeout 3600 "$PYPD" "$D/ocr_lote_pn.py" paddleocr cuda "*.png" d4 \
  2>&1 | tee "$D/logs/C_paddleocr.log"
echo "--- rapidocr v6 small + R6 ---"
SUFIJO="_C_ro6sm_R6" RO_VER="PP-OCRv6" RO_TIPO="small" RO_NORM=1 \
  timeout 3600 "$PYAI" "$D/ocr_lote_pn.py" rapidocr cuda "*.png" d4 \
  2>&1 | tee "$D/logs/C_rapidocr_v6sm_R6.log"

gpu_release
echo "=== fin tandas B+C: $(date) ==="
