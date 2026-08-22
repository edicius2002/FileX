#!/usr/bin/env bash
# P1 / tanda D — B10: validar la correccion de normalizacion FUERA del corpus d4.
#   D1  cribado de 7 detectores x 4 variantes en un solo proceso (n=1)
#   D2  validacion de n=9 de la pareja que importa, sobre los 15 documentos
#       (corpus completo + 4 rasterizaciones del PATRON ORO, que se leen y no se tocan)
#   D3  docling con y sin la correccion, por RapidOcrOptions.rapidocr_params
set -u
export PATH="/c/Program Files/Git/usr/bin:/c/Windows/System32:$PATH"
R="/d/Work/research/FileX"
D="$R/bench/salidas-ppp-norm"
. "$R/bench/lib/harness.sh"
PYAI="$R/.venv-ai/Scripts/python.exe"
PYPD="$R/.venv-paddle/Scripts/python.exe"
export RO_ROOT="D:/Work/research/FileX/bench/salidas-ppp-norm/modelos"

gpu_acquire "P1-tandaD-B10-normalizacion" || exit 1
echo "=== tanda D: $(date) ==="

echo "--- D1 cribado: 7 detectores x 4 variantes, n=1, corpus reducido ---"
timeout 5400 "$PYAI" "$D/survey_norm.py" cuda \
  "D:/Work/research/FileX/bench/salidas-ppp-norm/img_b10r" survey_cuda \
  2>&1 | tee "$D/logs/D1_survey_cuda.log"

echo "--- D2 validacion n=9 sobre los 15 documentos ---"
export REPS=9 SIN_MUESTREO=1
export IMGDIR="D:/Work/research/FileX/bench/salidas-ppp-norm/img_b10"
SUFIJO="_D_ro6sm_def" RO_VER="PP-OCRv6" RO_TIPO="small" RO_NORM=0 \
  timeout 3600 "$PYAI" "$D/ocr_lote_pn.py" rapidocr cuda "*.png" \
  2>&1 | tee "$D/logs/D2_ro6sm_def.log"
SUFIJO="_D_ro6sm_R6" RO_VER="PP-OCRv6" RO_TIPO="small" RO_NORM=1 \
  timeout 3600 "$PYAI" "$D/ocr_lote_pn.py" rapidocr cuda "*.png" \
  2>&1 | tee "$D/logs/D2_ro6sm_R6.log"
SUFIJO="_D_ro5mob_def" RO_VER="PP-OCRv5" RO_TIPO="mobile" RO_NORM=0 \
  timeout 3600 "$PYAI" "$D/ocr_lote_pn.py" rapidocr cuda "*.png" \
  2>&1 | tee "$D/logs/D2_ro5mob_def.log"
SUFIJO="_D_ro5mob_R6" RO_VER="PP-OCRv5" RO_TIPO="mobile" RO_NORM=1 \
  timeout 3600 "$PYAI" "$D/ocr_lote_pn.py" rapidocr cuda "*.png" \
  2>&1 | tee "$D/logs/D2_ro5mob_R6.log"
echo "--- referencia: PaddleOCR sobre los mismos 15 ---"
SUFIJO="_D_pd6med" timeout 3600 "$PYPD" "$D/ocr_lote_pn.py" paddleocr cuda "*.png" \
  2>&1 | tee "$D/logs/D2_paddleocr.log"

echo "--- D3 docling torch, nativo, sin y con R6 ---"
DOCS="patologico_escaneado,escaneado_d1,escaneado_d2,escaneado_d3,escaneado_d4,escaneado_d4c,escaneado_d4f"
SUFIJO="_D_def" DL_NORM=0 timeout 5400 "$PYAI" "$D/docling_lote_pn.py" cuda torch nativo "$DOCS" \
  2>&1 | tee "$D/logs/D3_docling_def.log"
SUFIJO="_D_R6" DL_NORM=1 timeout 5400 "$PYAI" "$D/docling_lote_pn.py" cuda torch nativo "$DOCS" \
  2>&1 | tee "$D/logs/D3_docling_R6.log"

gpu_release
echo "=== fin tanda D: $(date) ==="
