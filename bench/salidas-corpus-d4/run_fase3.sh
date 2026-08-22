#!/usr/bin/env bash
# G1 / fase 3 — la asimetria de PaddleOCR. Cruza TAMAÑO de modelo, idioma del
# RECONOCEDOR e idioma del DETECTOR sobre d3 (100 ppp nativos) y d4 (200 ppp).
#
# La pregunta viene de bench/ocr-ppp-nativos.md §6: PaddleOCR (PP-OCRv6 medium)
# resuelve d3 con 2,5 % y Docling+RapidOCR torch (PP-OCRv6 SMALL) falla con 75,9 %,
# luego el limite NO es la generacion del backbone. Quedaban tres candidatos:
# tamaño, idioma del reconocedor, idioma del detector.
#
# Instrumento A: PaddleOCR forzando los NOMBRES de modelo. Mismo motor, mismo
#   preprocesado, misma imagen: lo unico que cambia es el checkpoint. Los pesos
#   caen en C:\Users\krato\.paddlex\official_models, FUERA de los venv.
# Instrumento B: RapidOCR ONNX con Global.model_root_dir apuntando a un directorio
#   propio, para no escribir dentro de .venv-ai.
set -u
export PATH="/usr/bin:/bin:/c/Windows/System32:$PATH"
R="/d/Work/research/FileX"
D="$R/bench/salidas-corpus-d4"
. "$R/bench/lib/harness.sh"
PYAI="$R/.venv-ai/Scripts/python.exe"
PYPD="$R/.venv-paddle/Scripts/python.exe"

export IMGDIR="D:/Work/research/FileX/bench/salidas-corpus-d4/img_f3"
export REPS=9 SIN_MUESTREO=1

gpu_acquire "G1-fase3-asimetria" || exit 1
echo "=== fase 3: $(date) ==="

pd(){  # $1=sufijo  $2=det  $3=rec  $4=lang(opcional)
  echo; echo "--- paddle $1 : det=$2 rec=$3 lang=${4:-}"
  PD_DET="$2" PD_REC="$3" PD_LANG="${4:-}" SUFIJO="_f3$1" \
    timeout 1800 "$PYPD" "$D/ocr_lote_d4.py" paddleocr cuda "*.png" d4 \
    2>&1 | tee "$D/logs/f3_paddle$1.log" | grep -E "^ppp|ERROR|Traceback|error"
}

# --- A: tamaño dentro de PP-OCRv6 (misma generacion, mismo idioma "multi") ---
pd _v6med   PP-OCRv6_medium_det PP-OCRv6_medium_rec
pd _v6small PP-OCRv6_small_det  PP-OCRv6_small_rec
pd _v6tiny  PP-OCRv6_tiny_det   PP-OCRv6_tiny_rec
# --- A: detector contra reconocedor, cruzados ---
pd _detM_recS PP-OCRv6_medium_det PP-OCRv6_small_rec
pd _detS_recM PP-OCRv6_small_det  PP-OCRv6_medium_rec
# --- A: idioma del RECONOCEDOR, con el detector FIJO (PP-OCRv5) ---
pd _v5_latin PP-OCRv5_server_det latin_PP-OCRv5_mobile_rec
pd _v5_en    PP-OCRv5_server_det en_PP-OCRv5_mobile_rec
pd _v5_ch    PP-OCRv5_server_det PP-OCRv5_server_rec
# --- A: el `lang` de la API, que es lo que usa el resto del proyecto ---
pd _lang_es "" "" es
pd _lang_en "" "" en

ro(){  # $1=sufijo $2=VER $3=TIPO $4=LANGDET $5=LANGREC
  echo; echo "--- rapidocr $1 : $2/$3 det=$4 rec=$5"
  RO_ROOT="D:/Work/research/FileX/bench/salidas-corpus-d4/modelos" \
  RO_VER="$2" RO_TIPO="$3" RO_LANGDET="$4" RO_LANGREC="$5" SUFIJO="_f3$1" \
    timeout 1800 "$PYAI" "$D/ocr_lote_d4.py" rapidocr cuda "*.png" d4 \
    2>&1 | tee "$D/logs/f3_rapid$1.log" | grep -E "^ppp|ERROR|Traceback|error"
}

# --- B: la linea base actual de FileX y el idioma del reconocedor ---
ro _v5m_recch  PP-OCRv5 mobile ch ch
ro _v5m_reclat PP-OCRv5 mobile ch latin
# --- B: escalera de tamaño dentro de PP-OCRv6 (idioma "multi", no hay variable) ---
ro _v6tiny   PP-OCRv6 tiny   ch ch
ro _v6small  PP-OCRv6 small  ch ch
ro _v6medium PP-OCRv6 medium ch ch
# --- B: idioma del DETECTOR (solo existe en PP-OCRv4) ---
ro _v4_detch  PP-OCRv4 mobile ch    ch
ro _v4_deten  PP-OCRv4 mobile en    ch
ro _v4_detmul PP-OCRv4 mobile multi ch

gpu_release
echo "=== fin fase 3: $(date) ==="
