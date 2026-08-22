#!/usr/bin/env bash
# M1 / B13 — tanda G: completar el punto ×1,50, que faltaba en la rejilla y que es
# EXACTAMENTE el `k` vigente de Tesseract (CLAUDE.md trampa 8, P2, n=1). Sin este
# punto, el `k` de Tesseract solo se podia juzgar por sus vecinos ×1,4 y ×1,6.
set -u
export PATH="/c/Program Files/Git/usr/bin:/c/Windows/System32:$PATH"
R="/d/Work/research/FileX"
D="$R/bench/salidas-k-motor"
. "$R/bench/lib/harness.sh"
PYAI="$R/.venv-ai/Scripts/python.exe"
PYPD="$R/.venv-paddle/Scripts/python.exe"
export REPS=9 SIN_MUESTREO=1 VRAM_TOPE=11900
G="k1500__*.png"
F="f1.5"
DOCS="escaneado_d3,escaneado_d4c,patologico_escaneado,escaneado_d4"

echo "--- tesseract (CPU, sin lock) ---"
SUFIJO="_D_tess_spa_150" timeout 3600 "$PYAI" "$D/tess_lote_km.py" "$G" spa \
  2>&1 | tee "$D/logs/G_tesseract_150.log"

gpu_acquire "M1-B13-tandaG-k150" || exit 1
echo "=== tanda G: $(date) ==="
SUFIJO="_G_pd6med_150" timeout 3600 "$PYPD" "$D/ocr_lote_km.py" paddleocr cuda "$G" \
  2>&1 | tee "$D/logs/G_paddleocr.log"
SUFIJO="_A_ro6sm_R6_150" RO_VER="PP-OCRv6" RO_TIPO="small" RO_NORM=1 \
  timeout 3600 "$PYAI" "$D/ocr_lote_km.py" rapidocr cuda "$G" \
  2>&1 | tee "$D/logs/G_rapidocr_v6sm_R6.log"
SUFIJO="_A_ro6sm_def_150" RO_VER="PP-OCRv6" RO_TIPO="small" RO_NORM=0 \
  timeout 3600 "$PYAI" "$D/ocr_lote_km.py" rapidocr cuda "$G" \
  2>&1 | tee "$D/logs/G_rapidocr_v6sm_def.log"
SUFIJO="_A_ro5mob_def_150" RO_VER="PP-OCRv5" RO_TIPO="mobile" RO_NORM=0 \
  timeout 3600 "$PYAI" "$D/ocr_lote_km.py" rapidocr cuda "$G" \
  2>&1 | tee "$D/logs/G_rapidocr_v5mob_def.log"
SUFIJO="_G_easy_150" timeout 3600 "$PYAI" "$D/ocr_lote_km.py" easyocr cuda "$G" \
  2>&1 | tee "$D/logs/G_easyocr.log"
SUFIJO="_C_dl_def_150" DL_NORM=0 \
  timeout 3600 "$PYAI" "$D/docling_lote_km.py" cuda torch "$F" "$DOCS" \
  2>&1 | tee "$D/logs/G_docling_def.log"
SUFIJO="_C_dl_R6_150" DL_NORM=1 \
  timeout 3600 "$PYAI" "$D/docling_lote_km.py" cuda torch "$F" "$DOCS" \
  2>&1 | tee "$D/logs/G_docling_R6.log"
gpu_release
echo "=== fin tanda G: $(date) ==="
