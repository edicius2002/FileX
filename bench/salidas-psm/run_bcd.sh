#!/usr/bin/env bash
# G2 / B17-B18-B14 — tandas B, C y D, en serie para no contender consigo mismas.
# Tesseract va en CPU: esta tanda NO toma el lock de GPU (CLAUDE.md §1).
set -u
cd "D:/Work/research/FileX/bench/salidas-psm" || exit 1
PY="D:/Work/research/FileX/.venv-ai/Scripts/python.exe"
export REPS=9

# --- B: interaccion --psm x k, con la resolucion DECLARADA (im_ppi) --------------
timeout 10800 "$PY" tess_psm.py "im_ppi__*__escaneado_d[234]*.png" "3,4,6,11,12" \
  "B_inter_ppi" spa > logs/tanda_b.log 2>&1
echo "B rc=$?"

# --- C: la MISMA rejilla con el metadato roto (im, pHYs unit=0) -----------------
timeout 10800 "$PY" tess_psm.py "im__*__escaneado_d[34].png" "3,6,11" \
  "C_inter_im" spa > logs/tanda_c.log 2>&1
echo "C rc=$?"

# --- D: resolucion DECLARADA con los PIXELES FIJOS -------------------------------
for dpi in 70 100 150 200 300 400; do
  TESS_DPI="$dpi" timeout 7200 "$PY" tess_psm.py "im__k1000__*.png" "3,6,11" \
    "D_dpi${dpi}" spa > "logs/tanda_d_${dpi}.log" 2>&1
  echo "D_${dpi} rc=$?"
done
# el caso "sin declarar" con la misma etiqueta de familia, para que la tabla se cierre
timeout 7200 "$PY" tess_psm.py "im__k1000__*.png" "3,6,11" "D_dpi0" spa \
  > logs/tanda_d_0.log 2>&1
echo "D_0 rc=$?"
echo "FIN"
