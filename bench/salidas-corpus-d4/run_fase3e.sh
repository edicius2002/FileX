#!/usr/bin/env bash
# G1 / fase 3e — la diferencia que si esta en el codigo: la NORMALIZACION.
#
# Leidos los dos ficheros de configuracion del MISMO modelo (PP-OCRv6 small det):
#   PaddleX  (~/.paddlex/official_models/PP-OCRv6_small_det/inference.yml)
#       NormalizeImage mean=[0.485,0.456,0.406] std=[0.229,0.224,0.225]
#       DBPostProcess  thresh=0.2  box_thresh=0.45  unclip_ratio=1.4  max_cand=3000
#   RapidOCR (rapidocr/config.yaml)
#       mean=[0.5,0.5,0.5] std=[0.5,0.5,0.5]
#       thresh=0.3  box_thresh=0.5  unclip_ratio=1.6  max_candidates=1000
# Son los MISMOS pesos con distinto preprocesado y distinto post-proceso.
# Si eso explica la asimetria, poner los valores de PaddleX en RapidOCR debe
# acercar sus cifras. Es la ultima hipotesis con soporte en el codigo.
set -u
export PATH="/usr/bin:/bin:/c/Windows/System32:$PATH"
R="/d/Work/research/FileX"
D="$R/bench/salidas-corpus-d4"
. "$R/bench/lib/harness.sh"
PYAI="$R/.venv-ai/Scripts/python.exe"
export IMGDIR="D:/Work/research/FileX/bench/salidas-corpus-d4/img_f3"
export REPS=9 SIN_MUESTREO=1
export RO_ROOT="D:/Work/research/FileX/bench/salidas-corpus-d4/modelos"

gpu_acquire "G1-fase3e-normalizacion" || exit 1
echo "=== fase 3e: $(date) ==="
ro(){
  echo; echo "--- rapidocr $1 : $2/$3 extra=$4"
  RO_VER="$2" RO_TIPO="$3" RO_LANGDET=ch RO_LANGREC=ch RO_EXTRA="$4" SUFIJO="_f3e$1" \
    timeout 1800 "$PYAI" "$D/ocr_lote_d4.py" rapidocr cuda "*.png" d4 \
    2>&1 | tee "$D/logs/f3e_rapid$1.log" | grep -E "^ppp|ERROR|Traceback"
}
NRGB='"Det.mean": [0.485,0.456,0.406], "Det.std": [0.229,0.224,0.225]'
NBGR='"Det.mean": [0.406,0.456,0.485], "Det.std": [0.225,0.224,0.229]'
POST='"Det.thresh": 0.2, "Det.box_thresh": 0.45, "Det.unclip_ratio": 1.4, "Det.max_candidates": 3000'

ro _sm_normRGB  PP-OCRv6 small "{$NRGB}"
ro _sm_normBGR  PP-OCRv6 small "{$NBGR}"
ro _sm_post     PP-OCRv6 small "{$POST}"
ro _sm_paddle   PP-OCRv6 small "{$NRGB, $POST}"
ro _med_paddle  PP-OCRv6 medium "{$NRGB, $POST}"
ro _v5m_paddle  PP-OCRv5 mobile "{$NRGB, $POST}"

gpu_release
echo "=== fin fase 3e: $(date) ==="
