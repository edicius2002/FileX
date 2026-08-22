#!/usr/bin/env bash
# G1 / fase 4 — la medida CPU/GPU que bench/ocr-ppp-nativos.md §10 dejo pendiente.
#
# HIPOTESIS A CONTRASTAR, declarada antes de medir:
#   "RapidOCR en CPU a ppp nativos ~= RapidOCR en GPU a 200 ppp"
# Si se confirma, la GPU deja de ser necesaria para el OCR de FileX y eso cambia
# el hito 6. El razonamiento: gpu-fase2.md §2 midio que la salida es IDENTICA en
# CPU y en GPU (la GPU no compra precision, solo velocidad) y las cifras de CPU de
# la fase 2 se tomaron a 200 ppp, con el x2 de interpolacion; como la regla R1
# ahorra x1,48-3,13 por numero de pixeles, deberia ahorrar igual en CPU.
#
# Se mide CPU y GPU, a ppp nativos y a 200 ppp, sobre el corpus existente
# (patologico, d1, d2, d3) y sobre d4.
set -u
export PATH="/usr/bin:/bin:/c/Windows/System32:$PATH"
R="/d/Work/research/FileX"
D="$R/bench/salidas-corpus-d4"
. "$R/bench/lib/harness.sh"
PYAI="$R/.venv-ai/Scripts/python.exe"
PYPD="$R/.venv-paddle/Scripts/python.exe"
export IMGDIR="D:/Work/research/FileX/bench/salidas-corpus-d4/img_f4"
export REPS=9 SIN_MUESTREO=1 MEDIR_CPU=1

# Las tandas de CPU tambien toman el lock: no usan la tarjeta, pero si comparten
# CPU con lo que corra en GPU, y una tanda de CPU medida mientras otro agente
# satura la tarjeta no vale nada. Ademas hay OTROS AGENTES midiendo en CPU en
# paralelo: por eso cada cabecera lleva `cpu_pico_pct` y la etiqueta se marca
# CPU_OCUPADA si supera el 25 %.
gpu_acquire "G1-fase4-cpugpu" || exit 1
echo "=== fase 4: $(date) ==="

for dev in cuda cpu; do
  echo; echo "########## rapidocr $dev ##########"
  SUFIJO="_f4_$dev" timeout 3600 "$PYAI" "$D/ocr_lote_d4.py" rapidocr $dev "*.png" d4 \
    2>&1 | tee "$D/logs/f4_rapidocr_$dev.log" | grep -E "^ppp|^\{|ERROR"
done

for dev in cuda cpu; do
  echo; echo "########## paddleocr $dev ##########"
  SUFIJO="_f4_$dev" timeout 3600 "$PYPD" "$D/ocr_lote_d4.py" paddleocr $dev "*.png" d4 \
    2>&1 | tee "$D/logs/f4_paddleocr_$dev.log" | grep -E "^ppp|^\{|ERROR"
done

# EasyOCR en CPU es inutilizable (8,1-8,6 s/pagina medidos): se limita a 3 imagenes
# para confirmar el orden de magnitud sin gastar media hora.
for dev in cuda cpu; do
  echo; echo "########## easyocr $dev (subconjunto d3/d4) ##########"
  SUFIJO="_f4_$dev" timeout 3600 "$PYAI" "$D/ocr_lote_d4.py" easyocr $dev \
    "ppp?00__escaneado_d[34].png" d4 \
    2>&1 | tee "$D/logs/f4_easyocr_$dev.log" | grep -E "^ppp|^\{|ERROR"
done

# Docling: backend por dispositivo. El dato ya medido dice que `torch` en CPU es
# PEOR que `onnxruntime` (2,1-2,3 s frente a 1,6 s), asi que si FileX elige backend
# por dispositivo, en CPU debe usar onnxruntime y en CUDA torch. Se comprueba.
DOCS="patologico_escaneado,escaneado_d1,escaneado_d2,escaneado_d3,escaneado_d4"
for cfg in "cuda torch" "cpu torch" "cpu onnxruntime"; do
  set -- $cfg
  echo; echo "########## docling $1 backend=$2 ##########"
  SUFIJO="_f4_$1_$2" timeout 5400 "$PYAI" "$D/docling_lote_d4.py" $1 $2 nativo "$DOCS" \
    2>&1 | tee "$D/logs/f4_docling_$1_$2.log" | grep -E "^nativo|^\{|ERROR"
done

# La configuracion CORREGIDA que salio de la fase 3e (normalizacion de ImageNet +
# post-proceso de PaddleX). Se mide en CPU y en GPU porque, si la correccion vale,
# la pregunta "¿hace falta GPU?" hay que responderla sobre el motor BUENO, no
# sobre el mal configurado.
export RO_ROOT="D:/Work/research/FileX/bench/salidas-corpus-d4/modelos"
export RO_VER=PP-OCRv6 RO_TIPO=small
export RO_EXTRA='{"Det.mean": [0.485,0.456,0.406], "Det.std": [0.229,0.224,0.225], "Det.thresh": 0.2, "Det.box_thresh": 0.45, "Det.unclip_ratio": 1.4, "Det.max_candidates": 3000}'
for dev in cuda cpu; do
  echo; echo "########## rapidocr CORREGIDO (v6 small + norm PaddleX) $dev ##########"
  SUFIJO="_f4corr_$dev" timeout 3600 "$PYAI" "$D/ocr_lote_d4.py" rapidocr $dev "*.png" d4 \
    2>&1 | tee "$D/logs/f4_rapidocr_corr_$dev.log" | grep -E "^ppp|^\{|ERROR"
done

gpu_release
echo "=== fin fase 4: $(date) ==="
