#!/usr/bin/env bash
# G5 / tanda A (B26) — reproducir el atasco del asignador de VRAM.
#   veneno   3 pequenas -> 1 folio de 4,35 Mpx -> 5 pequenas con esperas -> 8,88 Mpx
#   control  lo mismo SIN el folio grande (control positivo, trampa 36)
#
# Este .sh existe por la fila C38: 0 de 15 arneses .py toman el lock de GPU.
# El lock se toma AQUI, alrededor del proceso de Python.
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
export ESPERA_S=20

gpu_acquire "G5-tandaA-B26-asignador" || exit 1
echo "=== tanda A: $(date) ==="
gpu_state

for fase in veneno control; do
  export FASE="$fase"
  for m in rapidocr easyocr; do
    echo "--- $m / $fase ---"
    timeout 2400 "$PYAI" "$D/sidecar_op.py" "$m" cuda "A_${m}_${fase}" \
      2>&1 | tee "$D/logs/A_${m}_${fase}.log"
  done
  echo "--- paddleocr / $fase ---"
  timeout 2400 "$PYPD" "$D/sidecar_op.py" paddleocr cuda "A_paddleocr_${fase}" \
    2>&1 | tee "$D/logs/A_paddleocr_${fase}.log"
done

gpu_release
echo "=== fin tanda A: $(date) ==="
gpu_state
