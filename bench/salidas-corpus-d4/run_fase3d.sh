#!/usr/bin/env bash
# G1 / fase 3d — el A/B causal, en los DOS sentidos.
#
# Lo que se descubrio leyendo las dos configuraciones por defecto:
#   RapidOCR  : Det.limit_side_len = 736, limit_type = min  -> REESCALA la pagina
#   PaddleOCR : text_det_limit_side_len = 64, limit_type = min -> NO la reescala
# Con d3 (647x850) eso significa que RapidOCR entrega al detector una imagen
# ampliada y PaddleOCR la original. Si esa es la causa de la asimetria, entonces:
#   (a) RapidOCR con limit_side_len=64 debe ACERCARSE a PaddleOCR, y
#   (b) PaddleOCR con text_det_limit_side_len=736 debe ROMPERSE como RapidOCR.
# Las dos direcciones, o no es causal.
set -u
export PATH="/usr/bin:/bin:/c/Windows/System32:$PATH"
R="/d/Work/research/FileX"
D="$R/bench/salidas-corpus-d4"
. "$R/bench/lib/harness.sh"
PYAI="$R/.venv-ai/Scripts/python.exe"
PYPD="$R/.venv-paddle/Scripts/python.exe"
export IMGDIR="D:/Work/research/FileX/bench/salidas-corpus-d4/img_f3"
export REPS=9 SIN_MUESTREO=1
export RO_ROOT="D:/Work/research/FileX/bench/salidas-corpus-d4/modelos"

gpu_acquire "G1-fase3d-ab" || exit 1
echo "=== fase 3d: $(date) ==="
ro(){
  echo; echo "--- rapidocr $1 : $2/$3 extra=$4"
  RO_VER="$2" RO_TIPO="$3" RO_LANGDET=ch RO_LANGREC=ch RO_EXTRA="$4" SUFIJO="_f3d$1" \
    timeout 1800 "$PYAI" "$D/ocr_lote_d4.py" rapidocr cuda "*.png" d4 \
    2>&1 | tee "$D/logs/f3d_rapid$1.log" | grep -E "^ppp|ERROR|Traceback"
}
pd(){
  echo; echo "--- paddle $1 : det=$2 rec=$3 extra=$4"
  PD_DET="$2" PD_REC="$3" PD_EXTRA="$4" SUFIJO="_f3d$1" \
    timeout 1800 "$PYPD" "$D/ocr_lote_d4.py" paddleocr cuda "*.png" d4 \
    2>&1 | tee "$D/logs/f3d_paddle$1.log" | grep -E "^ppp|ERROR|Traceback"
}

# (a) RapidOCR con el escalado de PaddleOCR
ro _sm_lim64   PP-OCRv6 small  '{"Det.limit_side_len": 64}'
ro _med_lim64  PP-OCRv6 medium '{"Det.limit_side_len": 64}'
ro _v5m_lim64  PP-OCRv5 mobile '{"Det.limit_side_len": 64}'
# y con el umbral de caja de PaddleOCR (0,6) ademas
ro _sm_lim64_box06 PP-OCRv6 small '{"Det.limit_side_len": 64, "Det.box_thresh": 0.6}'

# (b) PaddleOCR con el escalado de RapidOCR
pd _v6med_lim736 PP-OCRv6_medium_det PP-OCRv6_medium_rec '{"text_det_limit_side_len": 736}'
pd _v6sml_lim736 PP-OCRv6_small_det  PP-OCRv6_small_rec  '{"text_det_limit_side_len": 736}'
pd _v6med_box05  PP-OCRv6_medium_det PP-OCRv6_medium_rec '{"text_det_box_thresh": 0.5}'

gpu_release
echo "=== fin fase 3d: $(date) ==="
