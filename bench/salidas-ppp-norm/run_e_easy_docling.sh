#!/usr/bin/env bash
# P1 / tanda E — los dos motores caros del barrido:
#   E1  docling+RapidOCR torch con `scale` explicito, mismo barrido de ppp sobre d4
#   E2  EasyOCR, CON muestreador de VRAM. Es el motor que llego a 11 877 de 12 288 MiB
#       con UNA pagina a 300 ppp, y aqui se sube hasta 400. Se espera que reviente:
#       el fallo, si llega, ES el dato (el techo de ppp es tambien un techo de VRAM).
set -u
export PATH="/c/Program Files/Git/usr/bin:/c/Windows/System32:$PATH"
R="/d/Work/research/FileX"
D="$R/bench/salidas-ppp-norm"
. "$R/bench/lib/harness.sh"
PYAI="$R/.venv-ai/Scripts/python.exe"
export RO_ROOT="D:/Work/research/FileX/bench/salidas-ppp-norm/modelos"

gpu_acquire "P1-tandaE-easyocr-docling" || exit 1
echo "=== tanda E: $(date) ==="

echo "--- E1 docling torch, barrido de ppp sobre d4 (scale EXPLICITO) ---"
REPS=9 SIN_MUESTREO=1 SUFIJO="_E_ppp" DL_NORM=0 \
  timeout 5400 "$PYAI" "$D/docling_lote_pn.py" cuda torch \
  100,125,150,175,200,225,250,280,320,400 escaneado_d4 \
  2>&1 | tee "$D/logs/E1_docling_ppp.log"

echo "--- E1b docling torch con R6, mismo barrido ---"
REPS=9 SIN_MUESTREO=1 SUFIJO="_E_ppp_R6" DL_NORM=1 \
  timeout 5400 "$PYAI" "$D/docling_lote_pn.py" cuda torch \
  100,125,150,175,200,225,250,280,320,400 escaneado_d4 \
  2>&1 | tee "$D/logs/E1b_docling_ppp_R6.log"

echo "--- E1c docling con su DEFECTO (scale=3,0 -> 216 ppp), que nadie eligio ---"
REPS=9 SIN_MUESTREO=1 SUFIJO="_E_defecto" DL_NORM=0 \
  timeout 3600 "$PYAI" "$D/docling_lote_pn.py" cuda torch defecto \
  escaneado_d4,escaneado_d3,escaneado_d2,escaneado_d1,patologico_escaneado \
  2>&1 | tee "$D/logs/E1c_docling_defecto.log"

echo "--- E2 EasyOCR, barrido con muestreador de VRAM (n=3, cribado) ---"
REPS=3 SIN_MUESTREO=0 SUFIJO="_E_vram" \
  timeout 5400 "$PYAI" "$D/ocr_lote_pn.py" easyocr cuda "ppp*__escaneado_d4.png" \
  2>&1 | tee "$D/logs/E2_easyocr_vram.log"

echo "--- E3 pasada de VRAM de los otros tres motores (n=3) ---"
REPS=3 SIN_MUESTREO=0 SUFIJO="_E_vram" RO_VER="PP-OCRv6" RO_TIPO="small" RO_NORM=1 \
  timeout 3600 "$PYAI" "$D/ocr_lote_pn.py" rapidocr cuda "ppp*__escaneado_d4.png" \
  2>&1 | tee "$D/logs/E3_rapidocr_vram.log"
REPS=3 SIN_MUESTREO=0 SUFIJO="_E_vram" \
  timeout 3600 "$R/.venv-paddle/Scripts/python.exe" "$D/ocr_lote_pn.py" paddleocr cuda \
  "ppp*__escaneado_d4.png" 2>&1 | tee "$D/logs/E3_paddleocr_vram.log"

gpu_release
echo "=== fin tanda E: $(date) ==="
