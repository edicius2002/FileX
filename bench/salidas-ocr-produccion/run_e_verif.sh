#!/usr/bin/env bash
# G5 / tanda E — verificacion del arnes modificado: que la sonda de pesos
# corregida devuelva ficheros DISTINTOS en las dos configuraciones, que es
# justo lo que la sonda vieja no hacia. En CPU y con un solo documento: es una
# comprobacion de instrumento, no una medida de precision.
set -u
export PATH="/c/Program Files/Git/usr/bin:/c/Windows/System32:$PATH"
R="/d/Work/research/FileX"
W="$R/.claude/worktrees/agent-a4c547156ef35c38f"
D="$W/bench/salidas-ocr-produccion"
PYAI="$R/.venv-ai/Scripts/python.exe"
export IMG="$(cygpath -w "$D/img_b11")"
export OUT="$(cygpath -w "$D/ab")"
export DOCS=escaneado_d3 REPS=1

echo "--- vigente (v6 small + R6) ---"
timeout 600 "$PYAI" "$W/bench/scripts/ocr_motor.py" rapidocr cpu verif_vigente \
  2>&1 | grep -o '"pesos": {[^}]*}'
echo "--- legado (v5 mobile, sin R6) ---"
RO_LEGADO=1 timeout 600 "$PYAI" "$W/bench/scripts/ocr_motor.py" rapidocr cpu verif_legado \
  2>&1 | grep -o '"pesos": {[^}]*}'
