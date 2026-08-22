#!/usr/bin/env bash
# G1 / fase 3b — de "es la tuberia" a "es ESTE parametro de la tuberia".
#
# La fase 3 midio algo que no estaba en las tres hipotesis de ocr-ppp-nativos.md §6:
# con EL MISMO checkpoint (PP-OCRv6 small) PaddleOCR saca 3,80 % en d3 y RapidOCR
# 75,95 %. Luego la diferencia no esta en los pesos. Esta fase busca donde.
#
# Sospechoso principal: RapidOCR filtra por `Global.text_score` (0,5) y descarta
# la linea entera si el reconocedor no llega a esa confianza; PaddleOCR trae
# text_rec_score_thresh = 0. En texto degradado eso no baja la calidad: hace
# DESAPARECER el renglon, que es justo el patron observado (detecta el titular y
# pierde el cuerpo).
set -u
export PATH="/usr/bin:/bin:/c/Windows/System32:$PATH"
R="/d/Work/research/FileX"
D="$R/bench/salidas-corpus-d4"
. "$R/bench/lib/harness.sh"
PYAI="$R/.venv-ai/Scripts/python.exe"
export IMGDIR="D:/Work/research/FileX/bench/salidas-corpus-d4/img_f3"
export REPS=9 SIN_MUESTREO=1
export RO_ROOT="D:/Work/research/FileX/bench/salidas-corpus-d4/modelos"

gpu_acquire "G1-fase3b-tuberia" || exit 1
echo "=== fase 3b: $(date) ==="

ro(){  # $1=sufijo $2=VER $3=TIPO $4=JSON extra
  echo; echo "--- rapidocr $1 : $2/$3 extra=$4"
  RO_VER="$2" RO_TIPO="$3" RO_LANGDET=ch RO_LANGREC=ch RO_EXTRA="$4" SUFIJO="_f3b$1" \
    timeout 1800 "$PYAI" "$D/ocr_lote_d4.py" rapidocr cuda "*.png" d4 \
    2>&1 | tee "$D/logs/f3b_rapid$1.log" | grep -E "^ppp|ERROR|Traceback|error"
}

# --- el filtro de confianza, que es la sospecha principal ---
ro _sm_score00 PP-OCRv6 small '{"Global.text_score": 0.0}'
ro _sm_score01 PP-OCRv6 small '{"Global.text_score": 0.1}'
# --- los umbrales del detector ---
ro _sm_box03   PP-OCRv6 small '{"Det.box_thresh": 0.3}'
ro _sm_unc20   PP-OCRv6 small '{"Det.unclip_ratio": 2.0}'
ro _sm_lim1200 PP-OCRv6 small '{"Det.limit_side_len": 1200}'
# --- el clasificador de orientacion de linea ---
ro _sm_nocls   PP-OCRv6 small '{"Global.use_cls": false}'
# --- todo junto ---
ro _sm_todo    PP-OCRv6 small '{"Global.text_score": 0.0, "Det.box_thresh": 0.3, "Det.unclip_ratio": 2.0}'
# --- el mismo tratamiento sobre la config que usa FileX hoy (v5 mobile) ---
ro _v5m_score00 PP-OCRv5 mobile '{"Global.text_score": 0.0}'
ro _v5m_todo    PP-OCRv5 mobile '{"Global.text_score": 0.0, "Det.box_thresh": 0.3, "Det.unclip_ratio": 2.0}'

gpu_release
echo "=== fin fase 3b: $(date) ==="
