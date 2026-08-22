#!/usr/bin/env bash
# G1 / fase 3c — la perilla que si mueve la aguja: `Det.limit_side_len`.
#
# Hallazgo de 3b: RapidOCR REESCALA la imagen por dentro antes de detectar
# (limit_type=min, limit_side_len=736). O sea: da igual a que ppp se le entregue
# la pagina, el detector la lleva a SU tamaño. Eso explica por que corregir los
# ppp (regla R1) no movio a RapidOCR en bench/ocr-ppp-nativos.md y si movio a
# PaddleOCR. Aqui se barre esa perilla.
set -u
export PATH="/usr/bin:/bin:/c/Windows/System32:$PATH"
R="/d/Work/research/FileX"
D="$R/bench/salidas-corpus-d4"
. "$R/bench/lib/harness.sh"
PYAI="$R/.venv-ai/Scripts/python.exe"
export IMGDIR="D:/Work/research/FileX/bench/salidas-corpus-d4/img_f3"
export REPS=9 SIN_MUESTREO=1
export RO_ROOT="D:/Work/research/FileX/bench/salidas-corpus-d4/modelos"

gpu_acquire "G1-fase3c-limitside" || exit 1
echo "=== fase 3c: $(date) ==="
ro(){
  echo; echo "--- rapidocr $1 : $2/$3 extra=$4"
  RO_VER="$2" RO_TIPO="$3" RO_LANGDET=ch RO_LANGREC=ch RO_EXTRA="$4" SUFIJO="_f3c$1" \
    timeout 1800 "$PYAI" "$D/ocr_lote_d4.py" rapidocr cuda "*.png" d4 \
    2>&1 | tee "$D/logs/f3c_rapid$1.log" | grep -E "^ppp|ERROR|Traceback"
}
for L in 960 1600 2000; do
  ro "_sm_lim$L" PP-OCRv6 small "{\"Det.limit_side_len\": $L}"
done
ro _sm_lim1200_box03 PP-OCRv6 small '{"Det.limit_side_len": 1200, "Det.box_thresh": 0.3}'
for L in 1200 2000; do
  ro "_v5m_lim$L" PP-OCRv5 mobile "{\"Det.limit_side_len\": $L}"
done
ro _med_lim1200 PP-OCRv6 medium '{"Det.limit_side_len": 1200}'
gpu_release
echo "=== fin fase 3c: $(date) ==="
