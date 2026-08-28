#!/usr/bin/env bash
# G5 / tanda B (B11) — A/B de la configuracion por defecto de `ocr_motor.py`.
#   A  RO_LEGADO=1  -> PP-OCRv5 mobile, normalizacion de fabrica  (hasta el 28/08)
#   B  por defecto  -> PP-OCRv6 small + R6                        (desde el 28/08)
# 21 documentos a ppp NATIVOS, n=9, dispositivo FIJADO (trampa 11).
set -u
export PATH="/c/Program Files/Git/usr/bin:/c/Windows/System32:$PATH"
R="/d/Work/research/FileX"
W="$R/.claude/worktrees/agent-a4c547156ef35c38f"
D="$W/bench/salidas-ocr-produccion"
. "$W/bench/lib/harness.sh"
PYAI="$R/.venv-ai/Scripts/python.exe"

DOCS="$("$PYAI" -c "
import json,sys
i=json.load(open(r'$(cygpath -w "$D/img_b11/indice.json")',encoding='utf-8'))
print(','.join(e['doc'] for e in i if e.get('rc')==0))")"
echo "documentos: $DOCS"

export IMG="$(cygpath -w "$D/img_b11")"
export OUT="$(cygpath -w "$D/ab")"
export DOCS REPS=9
mkdir -p "$D/ab"

gpu_acquire "G5-tandaB-B11-configuracion" || exit 1
echo "=== tanda B: $(date) ==="
gpu_state

echo "--- A: via LEGADO (v5 mobile, sin R6) ---"
RO_LEGADO=1 timeout 3600 "$PYAI" "$W/bench/scripts/ocr_motor.py" rapidocr cuda "B11_legado" \
  2>&1 | tee "$D/logs/B_legado.log"

echo "--- B: via VIGENTE (v6 small + R6) ---"
timeout 3600 "$PYAI" "$W/bench/scripts/ocr_motor.py" rapidocr cuda "B11_vigente" \
  2>&1 | tee "$D/logs/B_vigente.log"

gpu_release
echo "=== fin tanda B: $(date) ==="
