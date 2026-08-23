#!/usr/bin/env bash
# G4 / B19 — tandas B..G: los tres motores GPU, cada uno con sus DOS VIAS de entrada.
#
# Un PROCESO POR (motor, via). No es cosmetica: `k-por-motor.md` §6.3 midio que el
# asignador de VRAM de PaddleOCR y de EasyOCR NO DEVUELVE la memoria (11 498 y 11 327
# MiB clavados, con 9 y 24 lecturas identicas al MiB), y que reiniciar el proceso lo
# arregla mientras esperar no sirve. Aqui las imagenes son pequeñas (<=3,23 Mpx), pero
# la disciplina se mantiene: el sidecar de OCR no es un proceso de vida larga.
#
# El lock de GPU se toma UNA vez para toda la tanda y se suelta al final (o al salir,
# por el trap de harness.sh). CLAUDE.md §1: el lock es del PROYECTO, no de la maquina.
set -u
export PATH="/c/Program Files/Git/usr/bin:/c/Windows/System32:$PATH"
R="/d/Work/research/FileX"
D="$R/bench/salidas-phys-multi"
. "$R/bench/lib/harness.sh"
PYAI="$R/.venv-ai/Scripts/python.exe"
PYPD="$R/.venv-paddle/Scripts/python.exe"
export REPS=9 SIN_MUESTREO=1 VRAM_TOPE=11300
G="*.png"

gpu_acquire "G4-B19-phys-multimotor" || exit 1
echo "=== tanda GPU: $(date) ==="
nvidia-smi --query-gpu=memory.used,utilization.gpu --format=csv,noheader

# --- sondas de LECTURA (¿quien decodifica y quien consulta el metadato?) ---
for M in rapidocr easyocr; do
  timeout 1800 "$PYAI" "$D/sonda_lectura_pm.py" "$M" cuda \
    "$D/img/escaneado_d4__k1000__sin.png" \
    "$D/img/escaneado_d4__k1000__p0400.png" \
    2>&1 | tee "$D/logs/sonda_lectura_$M.log"
done
timeout 1800 "$PYPD" "$D/sonda_lectura_pm.py" paddleocr cuda \
  "$D/img/escaneado_d4__k1000__sin.png" \
  "$D/img/escaneado_d4__k1000__p0400.png" \
  2>&1 | tee "$D/logs/sonda_lectura_paddleocr.log"

# --- rejilla principal: motor x via x variante x documento ---
for V in ruta array; do
  VIA="$V" timeout 5400 "$PYAI" "$D/ocr_lote_pm.py" rapidocr cuda "$G" \
    2>&1 | tee "$D/logs/B_rapidocr_$V.log"
  nvidia-smi --query-gpu=memory.used --format=csv,noheader
done
for V in ruta array; do
  VIA="$V" timeout 5400 "$PYPD" "$D/ocr_lote_pm.py" paddleocr cuda "$G" \
    2>&1 | tee "$D/logs/C_paddleocr_$V.log"
  nvidia-smi --query-gpu=memory.used --format=csv,noheader
done
for V in ruta array; do
  VIA="$V" timeout 5400 "$PYAI" "$D/ocr_lote_pm.py" easyocr cuda "$G" \
    2>&1 | tee "$D/logs/D_easyocr_$V.log"
  nvidia-smi --query-gpu=memory.used --format=csv,noheader
done

gpu_release
echo "=== fin tanda GPU: $(date) ==="
