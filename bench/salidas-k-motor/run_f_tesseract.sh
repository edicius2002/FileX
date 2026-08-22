#!/usr/bin/env bash
# M1 / B13 (+ B14) — tanda F: Tesseract 5.5.0 nativo, CPU, castellano.
# NO toma el lock de GPU: no usa la tarjeta. Los dos testigos de ruido siguen puestos.
# TESSDATA_PREFIX apunta al tessdata de PDFgear (16 idiomas, `spa` incluido), que
# CLAUDE.md §2 documenta como preexistente. No se instala nada.
set -u
export PATH="/c/Program Files/Git/usr/bin:/c/Windows/System32:$PATH"
R="/d/Work/research/FileX"
D="$R/bench/salidas-k-motor"
export REPS=9
echo "=== tanda F: $(date) ==="
SUFIJO="${TSUF:-_D_tess_spa}" timeout 5400 "$R/.venv-ai/Scripts/python.exe" \
  "$D/tess_lote_km.py" "k*__*.png" spa 2>&1 | tee "$D/logs/F_tesseract.log"
echo "=== fin tanda F: $(date) ==="
