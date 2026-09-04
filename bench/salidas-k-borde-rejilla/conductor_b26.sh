#!/usr/bin/env bash
# Conductor UNICO y desprendido (trampa 100: desprender salva la tarea, no la
# secuencia -- el bucle que lanza la configuracion siguiente tiene que vivir
# fuera del turno del agente, o el barrido se para en cada relevo).
#
# Recorre las TRES configuraciones cuyo optimo publicado toca el borde x1,60
# EN SERIE, reiniciando el proceso Python entre cada una: el asignador no
# devuelve la VRAM (trampa 67), y aqui se sube hasta x4,00, que multiplica los
# pixeles por 6,25 respecto de x1,60. Cada script toma y suelta filex.gpu.Lock
# por su cuenta; Tesseract es CPU y no lo toma.
#
# Rutas ABSOLUTAS en las dos direcciones (trampa 100: los venvs viven en D:,
# no en el worktree; un $ROOT/.venv-ai da rc=127 en el mismo segundo).
# USERPROFILE y HOME fijados a mano (trampa 99: expanduser('~') en Windows usa
# USERPROFILE, y el heredado de WSL apunta a \\wsl.localhost -- los modelos no
# estarian donde los motores los buscan, y el sintoma es rc=0 en el proceso con
# celdas a CER 100 %, publicables y falsas).
set -u

D="/c/Users/krato/orca/workspaces/FileX/filex-k-borde-rejilla"
PYAI="/d/Work/research/FileX/.venv-ai/Scripts/python.exe"
PYFX="/d/Work/research/FileX/.venv-mcp-filex/Scripts/python.exe"
SAL="bench/salidas-k-borde-rejilla"
LOG="$D/$SAL/logs/conductor_b26.progreso.log"

# Rejilla COMPLETA: los 7 factores de B23 (remedidos, para que el
# arrepentimiento salga de una sola tanda) + los NUEVE nuevos por encima de
# x1,60. El criterio de parada es "ya no mejora" o el techo de VRAM, no "se me
# acabo la lista" -- si el optimo sigue huyendo en x6,00, hay que subir mas.
FACT="0.75,0.875,1.00,1.125,1.25,1.40,1.60,1.75,2.00,2.25,2.50,3.00,3.50,4.00,5.00,6.00"
REPS=9

cd "$D" || { echo "NO PUEDO ENTRAR EN $D" >> "$LOG"; exit 1; }

: > "$LOG"
echo "INICIO CONDUCTOR $(date) factores=$FACT reps=$REPS" >> "$LOG"
echo "VRAM al empezar: $(nvidia-smi --query-gpu=memory.free --format=csv,noheader)" >> "$LOG"

corre() {
  local nombre="$1" py="$2"
  echo "INICIO $nombre $(date) vram_libre=$(nvidia-smi --query-gpu=memory.free --format=csv,noheader,nounits)" >> "$LOG"
  WSLENV= PYTHONUTF8=1 PYTHONIOENCODING=utf-8 \
  USERPROFILE='C:\Users\krato' HOME='C:\Users\krato' \
    "$py" "$SAL/b26_borde.py" "$nombre" --reps "$REPS" --factores "$FACT" \
    > "$SAL/logs/b26_$nombre.jsonl" \
    2> "$SAL/logs/b26_$nombre.err.log"
  local rc=$?
  # El rc SIEMPRE al log, con el recuento de celdas: `INICIO` dice que empezo
  # y `rc=0` dice que el proceso no reviento, pero solo el recuento distingue
  # "funciono" de "no escribio nada" (trampa 99).
  echo "FIN $nombre rc=$rc celdas=$(wc -l < "$SAL/logs/b26_$nombre.jsonl") $(date) vram_libre=$(nvidia-smi --query-gpu=memory.free --format=csv,noheader,nounits)" >> "$LOG"
}

# De mayor a menor coste declarado de VRAM. Tesseract el ultimo: es CPU.
corre docling-r6 "$PYAI"
corre easyocr    "$PYAI"
corre tess11     "$PYFX"

echo "FIN CONDUCTOR $(date)" >> "$LOG"
