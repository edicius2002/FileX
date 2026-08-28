#!/usr/bin/env bash
# G5 / tanda C (B26 + B11) — coste del ARRANQUE EN FRIO, que es lo que cuesta
# reciclar el proceso del sidecar. Un proceso POR REPETICION: medir el arranque
# en frio dentro de un proceso de vida larga no lo mide.
#   n=10, la primera se DESCARTA (Windows Defender infla el primer arranque de un
#   binario recien tocado, trampa 7).
set -u
export PATH="/c/Program Files/Git/usr/bin:/c/Windows/System32:$PATH"
R="/d/Work/research/FileX"
W="$R/.claude/worktrees/agent-a4c547156ef35c38f"
D="$W/bench/salidas-ocr-produccion"
. "$W/bench/lib/harness.sh"
PYAI="$R/.venv-ai/Scripts/python.exe"
PYPD="$R/.venv-paddle/Scripts/python.exe"
export IMGDIR="$(cygpath -w "$D/img")"
export OUTDIR="$(cygpath -w "$D")"
export FASE=frio
N="${N:-10}"

gpu_acquire "G5-tandaC-B26-arranque-frio" || exit 1
echo "=== tanda C: $(date) ==="

corrida(){ # $1 py  $2 motor  $3 dispositivo  $4 etiqueta
  local py="$1" m="$2" dev="$3" etq="$4" i
  for i in $(seq 1 "$N"); do
    timeout 900 "$py" "$D/sidecar_op.py" "$m" "$dev" "${etq}_i${i}" \
      2>&1 | grep -E '"evento": "(cargado|fin)"|"paso"' \
      >> "$D/logs/C_${etq}.log"
  done
  echo "  $etq: $N corridas"
}

# RapidOCR: la configuracion VIGENTE y la LEGADO, en las dos maquinas.
RO_VER=PP-OCRv6 RO_TIPO=small RO_NORM=1 corrida "$PYAI" rapidocr cuda C_ro6small_R6_cuda
RO_VER=PP-OCRv6 RO_TIPO=small RO_NORM=1 corrida "$PYAI" rapidocr cpu  C_ro6small_R6_cpu
RO_VER=PP-OCRv5 RO_TIPO=mobile RO_NORM=0 corrida "$PYAI" rapidocr cuda C_ro5mob_def_cuda
RO_VER=PP-OCRv5 RO_TIPO=mobile RO_NORM=0 corrida "$PYAI" rapidocr cpu  C_ro5mob_def_cpu
corrida "$PYAI" easyocr cuda C_easyocr_cuda
corrida "$PYAI" easyocr cpu  C_easyocr_cpu
corrida "$PYPD" paddleocr cuda C_paddleocr_cuda
corrida "$PYPD" paddleocr cpu  C_paddleocr_cpu

gpu_release
echo "=== fin tanda C: $(date) ==="
