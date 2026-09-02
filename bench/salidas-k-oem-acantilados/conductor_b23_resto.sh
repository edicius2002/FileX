#!/usr/bin/env bash
# Conductor unico y desprendido (trampa 100): recorre las 4 configuraciones
# que le faltaban a B23 EN SERIE, reiniciando el proceso Python entre cada una
# (el asignador de VRAM no devuelve memoria -- trampa 67). Cada script toma y
# suelta filex.gpu.Lock por su cuenta, y dentro de cada uno los documentos se
# recorren de MAYOR a MENOR tamano (DOCS ya viene en ese orden: d5a 90ppp,
# d5c 80, d5 72, d5b 60).
#
# Ronda 5 (ESTADO-Y-REPARTO.md): CCB esta desmontado, el worktree vive en
# C:\Users\krato\orca\workspaces\FileX\filex-gpu; los venvs SIGUEN en D:. Ruta
# absoluta en las dos direcciones, como advierte ENCARGO.md, para no repetir
# el rc=127 de la trampa 100.
set -u

D="/c/Users/krato/orca/workspaces/FileX/filex-gpu"
PYAI="/d/Work/research/FileX/.venv-ai/Scripts/python.exe"
SAL="bench/salidas-k-oem-acantilados"
LOG="$D/$SAL/logs/conductor_b23resto.progreso.log"

cd "$D" || { echo "NO PUEDO ENTRAR EN $D" >> "$LOG"; exit 1; }

: > "$LOG"
echo "INICIO $(date)" >> "$LOG"

corre() {
  local script="$1" nombre="$2"
  echo "INICIO $nombre $(date)" >> "$LOG"
  WSLENV= PYTHONUTF8=1 PYTHONIOENCODING=utf-8 \
    "$PYAI" "$SAL/$script" "$nombre" --reps 3 \
    > "$SAL/logs/b23resto_$nombre.jsonl" \
    2> "$SAL/logs/b23resto_$nombre.err.log"
  local rc=$?
  # rc SIEMPRE al log, con el numero de celdas escritas: distingue "funciono"
  # de "no escribio nada" (trampa 99), igual que conductor_b23.sh.
  echo "FIN $nombre rc=$rc celdas=$(wc -l < "$SAL/logs/b23resto_$nombre.jsonl") $(date)" >> "$LOG"
}

# Mayor a menor "coste" declarado de motor (Docling es el mas caro en VRAM
# segun trampa 67/k-por-motor.md; RapidOCR standalone es el que menos). No
# hay staircase real entre configs porque cada una reinicia el proceso, pero
# se conserva el orden por si alguna vez deja de reiniciarse.
corre b23_resto_docling.py   docling-def
corre b23_resto_docling.py   docling-r6
corre b23_resto_rapidocr.py  rapidocr-v6-def
corre b23_resto_rapidocr.py  rapidocr-v5-def

echo "FIN CONDUCTOR $(date)" >> "$LOG"
