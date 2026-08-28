#!/usr/bin/env bash
# G5 — prueba de humo: una pagina por motor, para validar el arnes antes de la tanda.
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

gpu_acquire "G5-humo" || exit 1
gpu_state
timeout 900 "$PYAI" "$D/sidecar_op.py" rapidocr cuda "humo_rapidocr" 2>&1 | tail -25
timeout 900 "$PYAI" "$D/sidecar_op.py" easyocr cuda "humo_easyocr" 2>&1 | tail -12
timeout 900 "$PYPD" "$D/sidecar_op.py" paddleocr cuda "humo_paddleocr" 2>&1 | tail -12
gpu_release
