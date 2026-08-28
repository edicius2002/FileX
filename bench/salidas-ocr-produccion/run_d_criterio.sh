#!/usr/bin/env bash
# G5 / tanda D (B26) — CON QUE VARIABLE crece la VRAM que no se devuelve.
#   ascendente  0,21 -> 1,25 -> 2,22 -> 4,35 -> 8,88 Mpx y vuelta a la pequena
#   repetido    la MISMA pagina de 1,25 Mpx, 20 veces
# Las dos juntas separan "numero de paginas" de "megapixeles del documento MAYOR":
# con una sola de las dos, cualquiera de los dos criterios encaja.
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
export REPETICIONES=20

gpu_acquire "G5-tandaD-B26-criterio" || exit 1
echo "=== tanda D: $(date) ==="

for fase in repetido ascendente directo; do
  export FASE="$fase"
  for m in rapidocr easyocr; do
    echo "--- $m / $fase ---"
    timeout 2400 "$PYAI" "$D/sidecar_op.py" "$m" cuda "D_${m}_${fase}" \
      2>&1 | tee "$D/logs/D_${m}_${fase}.log" | grep -c '"paso"'
  done
  echo "--- paddleocr / $fase ---"
  timeout 2400 "$PYPD" "$D/sidecar_op.py" paddleocr cuda "D_paddleocr_${fase}" \
    2>&1 | tee "$D/logs/D_paddleocr_${fase}.log" | grep -c '"paso"'
done

gpu_release
echo "=== fin tanda D: $(date) ==="
