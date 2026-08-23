#!/usr/bin/env bash
# G4 / B19 — tanda E: la via `array` sobre un raster EN COLOR.
#
# Por que existe. La rejilla principal sale limpia: `ruta` y `array` dan el MISMO
# md5 en 150 de 150 pares. Pero los 50 rasteres de esa rejilla son en ESCALA DE
# GRISES, y en gris R=G=B: un intercambio RGB/BGR es invisible. Los tres motores
# tratan el ndarray como BGR (rapidocr/utils/load_image.py:88-91,
# paddlex/.../image_reader.py:51-55) mientras que por la via de la ruta easyocr
# decodifica con `skimage.io.imread`, que devuelve RGB
# (easyocr/imgproc.py:11-18, easyocr/utils.py:741).
#
# Es decir: la equivalencia medida podria ser un artefacto del corpus. Con un raster
# de tres canales DISTINTOS la pregunta se contesta de verdad. Un solo fichero, dos
# vias, tres motores: 6 celdas.
set -u
export PATH="/c/Program Files/Git/usr/bin:/c/Windows/System32:$PATH"
R="/d/Work/research/FileX"
D="$R/bench/salidas-phys-multi"
. "$R/bench/lib/harness.sh"
PYAI="$R/.venv-ai/Scripts/python.exe"
PYPD="$R/.venv-paddle/Scripts/python.exe"
export REPS=9 SIN_MUESTREO=1 VRAM_TOPE=11300 IMGDIR="$D/img_color" SUFIJO="_color"
G="*.png"

gpu_acquire "G4-B19-via-color" || exit 1
echo "=== tanda E (color): $(date) ==="
for V in ruta array; do
  VIA="$V" timeout 1800 "$PYAI" "$D/ocr_lote_pm.py" rapidocr cuda "$G" \
    2>&1 | tee "$D/logs/E_rapidocr_color_$V.log"
  VIA="$V" timeout 1800 "$PYPD" "$D/ocr_lote_pm.py" paddleocr cuda "$G" \
    2>&1 | tee "$D/logs/E_paddleocr_color_$V.log"
  VIA="$V" timeout 1800 "$PYAI" "$D/ocr_lote_pm.py" easyocr cuda "$G" \
    2>&1 | tee "$D/logs/E_easyocr_color_$V.log"
done
gpu_release
echo "=== fin tanda E: $(date) ==="
