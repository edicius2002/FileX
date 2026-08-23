#!/usr/bin/env bash
# G4 / B19 — tanda A: CONTROL con Tesseract sobre los MISMOS ficheros que veran los
# tres motores GPU. Es el control que hace interpretable el resultado principal:
# si los tres motores GPU no se mueven, hay que probar que estos ficheros SI mueven
# a alguien. CPU pura: NO toca la GPU y NO toma el lock (asi no bloquea al otro
# agente que trabaja en filex/ y bench/hito7-superficies.md).
set -u
export PATH="/c/Program Files/Git/usr/bin:/c/Windows/System32:$PATH"
R="/d/Work/research/FileX"
D="$R/bench/salidas-phys-multi"
PYAI="$R/.venv-ai/Scripts/python.exe"
export REPS=9

echo "=== tanda A (tesseract, CPU): $(date) ==="
timeout 7200 "$PYAI" "$D/tess_pm.py" "*.png" "3,6,11" "A_tess" spa \
  2>&1 | tee "$D/logs/A_tesseract.log"
echo "=== fin tanda A: $(date) ==="
