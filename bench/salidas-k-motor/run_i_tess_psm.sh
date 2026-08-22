#!/usr/bin/env bash
# M1 / B13 — tanda I: Tesseract con `--psm 11` (texto disperso), la segunda
# configuracion. Motivo, MEDIDO en `sonda_tess.py`: con `--psm 3` (el defecto)
# Tesseract devuelve 107 bytes sobre `escaneado_d4` y CERO sobre `escaneado_d3`, y su
# curva de `k` es degenerada. Con `--psm 11` sobre las MISMAS imagenes baja de
# 84,56 % a 41,78 % en `d4`. El `--psm` pesa mas que el `k`.
set -u
export PATH="/c/Program Files/Git/usr/bin:/c/Windows/System32:$PATH"
R="/d/Work/research/FileX"
D="$R/bench/salidas-k-motor"
export REPS=9 TESS_PSM=11
echo "=== tanda I: $(date) ==="
SUFIJO="_I_tess11_spa" timeout 5400 "$R/.venv-ai/Scripts/python.exe" \
  "$D/tess_lote_km.py" "k*__*.png" spa 2>&1 | tee "$D/logs/I_tesseract_psm11.log"
echo "=== fin tanda I: $(date) ==="
