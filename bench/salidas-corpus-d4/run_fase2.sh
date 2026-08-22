#!/usr/bin/env bash
# G1 / fase 2 — validacion de d4 contra los cuatro motores. Medianas de n=9.
#
# DOS PASADAS, y no es un capricho: el hilo que muestrea nvidia-smi cada 100 ms
# infla las medianas entre un 30 y un 60 % (bench/ocr-ppp-nativos.md §7.1). Una
# sola pasada no puede dar pico de VRAM Y tiempo limpio a la vez.
#   pasada V: con muestreo  -> peak_vram valido, tiempos inflados (se descartan)
#   pasada T: SIN_MUESTREO=1 -> tiempos validos, sin pico de VRAM
set -u
export PATH="/usr/bin:/bin:/c/Windows/System32:$PATH"
R="/d/Work/research/FileX"
D="$R/bench/salidas-corpus-d4"
. "$R/bench/lib/harness.sh"
PYAI="$R/.venv-ai/Scripts/python.exe"
PYPD="$R/.venv-paddle/Scripts/python.exe"
DOCS="d4_limpio,escaneado_d4a,escaneado_d4b,escaneado_d4c,escaneado_d4,escaneado_d4e,escaneado_d4f"

gpu_acquire "G1-fase2-d4" || exit 1
echo "=== fase 2: $(date) ==="
export REPS=9

for pasada in V T; do
  if [ "$pasada" = "V" ]; then export SIN_MUESTREO=0; SUF="_vram";
  else export SIN_MUESTREO=1; SUF="_t"; fi
  echo; echo "########## pasada $pasada (SIN_MUESTREO=$SIN_MUESTREO) ##########"

  echo "--- paddleocr ---"
  SUFIJO="$SUF" timeout 2400 "$PYPD" "$D/ocr_lote_d4.py" paddleocr cuda "*.png" d4 \
    2>&1 | tee "$D/logs/f2_paddleocr$SUF.log"
  echo "--- rapidocr ---"
  SUFIJO="$SUF" timeout 2400 "$PYAI" "$D/ocr_lote_d4.py" rapidocr cuda "*.png" d4 \
    2>&1 | tee "$D/logs/f2_rapidocr$SUF.log"
  echo "--- easyocr ---"
  SUFIJO="$SUF" timeout 2400 "$PYAI" "$D/ocr_lote_d4.py" easyocr cuda "*.png" d4 \
    2>&1 | tee "$D/logs/f2_easyocr$SUF.log"
  echo "--- docling+rapidocr torch ---"
  SUFIJO="$SUF" timeout 3600 "$PYAI" "$D/docling_lote_d4.py" cuda torch nativo "$DOCS" \
    2>&1 | tee "$D/logs/f2_docling$SUF.log"
done

gpu_release
echo "=== fin fase 2: $(date) ==="
