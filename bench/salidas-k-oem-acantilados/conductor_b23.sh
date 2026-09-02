#!/usr/bin/env bash
# Conductor unico y desprendido: recorre las tres configuraciones GPU de B23
# EN SERIE, reiniciando el proceso Python entre cada una (el asignador de VRAM
# no devuelve memoria). Cada script toma y suelta filex.gpu.Lock por su cuenta.
#
# CORREGIDO el 01/09 por el master, tras fallar las tres en el mismo segundo
# con rc=2. Dos defectos, y el segundo es el peligroso:
#
#   (a) Se le pasaba al `python.exe` de WINDOWS una ruta de LINUX
#       ("/mnt/d/..."), y Windows la resuelve contra la unidad actual:
#       "D:\mnt\d\Work\research\FileX\...". El error exacto era
#       "can't open file ... [Errno 2]". Es la trampa que C39 ya dejo escrita
#       sobre `wslpath -w`. Aqui se arregla como worker1 ya lo hacia en las
#       tandas que SI funcionaron: `cd` al worktree y ruta RELATIVA.
#
#   (b) Faltaban USERPROFILE y HOME. Ese no habria fallado a gritos: habria
#       fallado en SILENCIO. `expanduser('~')` en Windows usa USERPROFILE, no
#       HOME, y con el heredado de WSL apunta a \\wsl.localhost -- los modelos
#       no estan donde el motor los busca, y la trampa 99 documenta el
#       resultado: proceso rc=0, celdas con rc=1, texto vacio y CER 100 %,
#       publicables y falsas. Las tandas buenas de worker1 SI los fijaban.
set -u

D="/mnt/d/Work/research/FileX/.ccb/workspaces/worker1"
PYAI="/mnt/d/Work/research/FileX/.venv-ai/Scripts/python.exe"
PYPD="/mnt/d/Work/research/FileX/.venv-paddle/Scripts/python.exe"
SAL="bench/salidas-k-oem-acantilados"
LOG="$D/$SAL/logs/conductor_b23.progreso.log"

cd "$D" || { echo "NO PUEDO ENTRAR EN $D" >> "$LOG"; exit 1; }

: > "$LOG"
echo "INICIO $(date)" >> "$LOG"

# Una funcion, para que las tres celdas no puedan divergir por copia-pega.
corre() {
  local nombre="$1" py="$2"
  echo "INICIO $nombre $(date)" >> "$LOG"
  WSLENV= PYTHONUTF8=1 PYTHONIOENCODING=utf-8 \
  USERPROFILE='C:\Users\krato' HOME='C:\Users\krato' \
    "$py" "$SAL/b23_k_d5.py" "$nombre" --reps 3 \
    > "$SAL/logs/b23_$nombre.jsonl" \
    2> "$SAL/logs/b23_$nombre.err.log"
  local rc=$?
  # El rc va al log SIEMPRE, y con el numero de celdas: `INICIO` dice que
  # empezo y `rc=0` dice que el proceso no reviento, pero solo el recuento
  # distingue "funciono" de "no escribio nada" (trampa 99).
  echo "FIN $nombre rc=$rc celdas=$(wc -l < "$SAL/logs/b23_$nombre.jsonl") $(date)" >> "$LOG"
}

corre rapidocr-r6 "$PYAI"
corre paddleocr   "$PYPD"
corre easyocr     "$PYAI"

echo "FIN CONDUCTOR $(date)" >> "$LOG"
